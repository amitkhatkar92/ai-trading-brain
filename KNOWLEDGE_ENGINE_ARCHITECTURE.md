# KNOWLEDGE ENGINE ARCHITECTURE

**Document Series:** Investment Intelligence Operating System — Engineering Document Library
**Document Number:** 7 of 10
**Document Class:** Knowledge Engineering Architecture
**Status:** Authoritative
**Version:** 1.0.0
**Date:** 2026-07-02
**Authors:** Human Principal / Engineering Foundation
**Governs:** Every knowledge object, knowledge service, knowledge lifecycle, and knowledge governance policy in the IIOS

---

## Scope and Authority

This document is the authoritative engineering design for the Knowledge Engine of the Investment Intelligence Operating System. The Knowledge Engine is the component responsible for transforming validated information into structured, reusable, evolving knowledge — the foundation of every intelligent decision the system makes.

Without the Knowledge Engine, the IIOS is a sophisticated information processor. With it, the IIOS becomes a learning intelligence: a system that builds an ever-deeper understanding of markets, strategies, regimes, and its own operational behaviour.

This document does **NOT** contain:
- Source code or implementation details
- AI model design, neural network architectures, or machine learning algorithms
- Prompt engineering or language model integration
- Database schema definitions

This document **DOES** contain:
- The philosophical foundation of knowledge in the IIOS
- The complete 10-level knowledge architecture hierarchy
- Detailed design of every knowledge object type
- The complete knowledge lifecycle from discovery to archival
- Knowledge organization, taxonomy, and graph design
- All 10 knowledge services with full interface specifications
- The knowledge quality framework with scoring models
- Knowledge governance policies and ownership structures
- 75 mandatory Knowledge Constitution rules
- A comprehensive Knowledge Readiness Checklist

---

## Parent Documents

| Document | Authority |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Engineering design bridge |
| `ENGINEERING_STANDARDS.md` | Mandatory engineering standards |
| `CORE_FRAMEWORK_ARCHITECTURE.md` | Core framework and base classes |
| `DATABASE_PERSISTENCE_ARCHITECTURE.md` | Persistence design authority |

---

## Knowledge Engine Position in the IIOS Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     IIOS INTELLIGENCE STACK                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  L17 ControlTower                 (Executive oversight)            │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  L15 ResearchLab + L16 Validation (Strategy promotion gates)       │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  L13 LearningSystem + L14 Analytics (Performance learning)         │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  ┌──────────────────────────────────────────────────────────────┐  │     │
│  │  │          KNOWLEDGE ENGINE  (This document)                   │  │     │
│  │  │                                                              │  │     │
│  │  │  Knowledge Discovery → Validation → Classification          │  │     │
│  │  │  Storage → Retrieval → Evolution → Governance               │  │     │
│  │  │                                                              │  │     │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │     │
│  │  │  │  Knowledge   │  │  Knowledge   │  │   Knowledge      │  │  │     │
│  │  │  │  Store       │  │  Graph       │  │   Services (10)  │  │  │     │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────┘  │  │     │
│  │  └──────────────────────────────────────────────────────────────┘  │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  L10 DebateAndDecision            (Intelligence consumption)        │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │  L1–L9 Data, Analysis, Strategy   (Knowledge production)           │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Knowledge Flow Overview

```
  Reality                   ┐
  │                         │
  ▼                         │
  Information ──────────────┤ INPUT TO KNOWLEDGE ENGINE
  │                         │
  ▼                         │
  Observation / Event ──────┘
  │
  ▼ ─────────────────────────────────────────────────────────────────────
  │           KNOWLEDGE ENGINE PROCESSING PIPELINE
  │
  ├──> [Knowledge Discovery Service]     Identifies knowledge candidates
  │
  ├──> [Knowledge Validation Service]    Verifies evidence and accuracy
  │
  ├──> [Knowledge Classification Service] Assigns domain, category, type
  │
  ├──> [Knowledge Graph Service]         Links to related knowledge nodes
  │
  ├──> [Knowledge Storage]               Persists versioned knowledge
  │
  ├──> [Knowledge Retrieval Service]     Answers knowledge queries
  │
  ├──> [Knowledge Evolution Service]     Updates confidence and patterns
  │
  └──> [Knowledge Governance Service]    Enforces quality and ownership
  │
  ▼ ─────────────────────────────────────────────────────────────────────
  │           KNOWLEDGE CONSUMERS
  │
  ├──> MetaLearning (L3)      — regime-to-strategy maps
  ├──> StrategyLab (L5)       — strategy design inputs
  ├──> DebateAndDecision (L10) — conviction scoring context
  ├──> LearningSystem (L13)   — performance learning
  └──> ResearchLab (L15)      — research queries
```

---

## Table of Contents

- [Part I — Knowledge Philosophy](#part-i)
- [Part II — Knowledge Architecture](#part-ii)
- [Part III — Knowledge Objects](#part-iii)
- [Part IV — Knowledge Lifecycle](#part-iv)
- [Part V — Knowledge Organization](#part-v)
- [Part VI — Knowledge Services](#part-vi)
- [Part VII — Knowledge Quality](#part-vii)
- [Part VIII — Knowledge Governance](#part-viii)
- [Part IX — Knowledge Constitution](#part-ix)
- [Part X — Knowledge Readiness Checklist](#part-x)
- [Document Footer](#document-footer)
- [Supplement A — Knowledge Object Catalogue](#supplement-a)
- [Supplement B — Knowledge Graph Design](#supplement-b)
- [Supplement C — Knowledge Domain Taxonomy](#supplement-c)
- [Supplement D — Knowledge Quality Scoring Reference](#supplement-d)
- [Supplement E — Knowledge Service Interface Reference](#supplement-e)
- [Supplement F — Knowledge Governance Decision Records](#supplement-f)

---
## PART I — KNOWLEDGE PHILOSOPHY

### 1.1 What Is Knowledge?

Knowledge is not data. Knowledge is not information. Knowledge is not a record. Knowledge is the **structured, validated, reusable understanding of how the world works** — derived from observed reality, tested by evidence, organised into patterns, and applied to decision-making.

In the Investment Intelligence Operating System, knowledge is the bridge between the raw stream of market reality and the intelligent decisions the system makes. Without knowledge, every cognitive cycle would begin from scratch, with no memory, no patterns, no accumulated understanding. With knowledge, each cycle begins from an elevated starting point — the cumulative product of thousands of cycles, millions of data points, and hundreds of validated learning events.

The Knowledge Engine is the architectural component that creates, maintains, evolves, and distributes this understanding across the entire system.

---

### 1.2 The Epistemic Hierarchy

The IIOS recognises a clear hierarchy of epistemic concepts. Understanding the distinction between these concepts is essential to understanding why the Knowledge Engine is architecturally distinct from the data layer, the information layer, and the learning layer.

**Reality:**

Reality is the objective state of the world that exists independently of any observer. Reality includes: the actual price of NIFTY50 at a specific nanosecond, the actual sentiment of institutional investors at this moment, the actual P&L of every open position. Reality is not stored by the system — it is observed, sampled, and approximated.

Reality has three properties that are architecturally critical:
- It is continuous (events happen at every moment, not just at sampling intervals)
- It is partially observable (the system can only see what its feeds expose)
- It is irreversible (once a price moves, the past price cannot be recaptured through observation)

**Information:**

Information is a structured representation of observed reality. It is produced when reality is sampled, measured, and encoded. A price bar — Open 21,450, High 21,523, Low 21,410, Close 21,498 at 09:30 IST — is information. It is a structured representation of the reality of NIFTY50 prices during that 1-minute window.

Information has properties:
- It has a timestamp (when was reality observed?)
- It has a source (which feed, which exchange reported this?)
- It has a precision limit (rounded to 2 decimal places, 1-minute bars lose tick-level reality)
- It is raw — it does not yet carry interpretation or significance

The IIOS data layer produces information. The knowledge engine begins only after information has been produced and validated.

**Entity:**

An entity is a named, persistent object in the domain that has an identity and a lifecycle. An entity is not raw reality — it is a conceptual object that the system defines and tracks. `Strategy("momentum_breakout_v3")` is an entity. `Portfolio(id="paper_001")` is an entity. `Agent("RiskAgent_7")` is an entity.

Entities are abstractions over reality — they are the system's way of naming and tracking the things that matter. An entity has attributes (fields that describe its current state) and history (the evolution of those attributes over time). The entity ontology defines all entities the system recognises.

**Relationship:**

A relationship is a defined connection between two entities that has meaning in the domain. `Strategy GENERATED Hypothesis` is a relationship. `Trade TAUGHT Learning` is a relationship. `Agent OPINED_ON Hypothesis` is a relationship.

Relationships are not inferred — they are asserted by the system when events occur. They form the structure of the knowledge graph. Understanding relationships is what separates knowledge from a collection of isolated facts.

**Event:**

An event is a discrete, timestamped occurrence that changes the state of one or more entities. A trade being opened, a kill-switch activating, a strategy being promoted — these are events. Events are the mechanism by which reality affects the entity model.

Events are facts: they happened, and their occurrence is immutable. Events generate information (the event record) and often produce new knowledge (what does this event teach us about how the system behaves?).

**Observation:**

An observation is the act of perceiving a specific aspect of reality and recording it as information. Not all reality becomes observations — only what is sampled by the system's feeds. An observation has a source (the feed that made it), a method (how the data was collected), and a context (what else was happening at the time of the observation).

Observations are the raw material from which information is constructed. Multiple observations of the same aspect of reality can be combined to produce higher-quality information (averaging, de-noising, cross-referencing).

**Evidence:**

Evidence is information or a collection of observations that supports or refutes a hypothesis. Evidence is contextualised information — it is not just data, it is data with meaning relative to a claim.

In the IIOS, evidence plays a critical role in knowledge validation. Before a pattern can become knowledge, it must be supported by evidence. Evidence has:
- A source (which feed, which historical dataset)
- A strength (how many supporting observations, how consistent)
- A relevance window (this evidence is relevant to this regime or time period)

Knowledge without evidence is speculation, not knowledge.

**Knowledge:**

Knowledge is **validated, structured understanding that has been derived from evidence and organised for reuse**. Knowledge answers the question: "What can we reliably say about how markets, strategies, or agents behave, and why?"

Knowledge in the IIOS has six defining properties:

| Property | Description |
|---|---|
| Evidence-backed | Every knowledge item is supported by a quantified body of evidence |
| Structured | Knowledge is organised in defined knowledge objects with typed fields |
| Versioned | Knowledge evolves over time; every version is preserved |
| Confidence-scored | Every knowledge item carries a confidence score reflecting the strength of its evidence |
| Contextualised | Knowledge is anchored to the conditions under which it was learned |
| Reusable | Knowledge is designed to be retrieved and applied in future cycles |

**Wisdom:**

Wisdom is the ability to apply knowledge appropriately in context — knowing not just what is true, but when and how to use it. In a trading system, wisdom is the difference between knowing that a momentum strategy has a 70% win rate and knowing that this win rate was achieved in trending markets, does not hold in consolidating markets, and is sensitive to the R:R threshold used.

Wisdom in the IIOS is encoded in:
- Regime-conditional knowledge (this pattern is true IN THIS REGIME)
- Confidence-weighted application (use this knowledge when confidence > 0.75)
- Contextual retrieval (retrieve knowledge relevant to the current market state)

The Knowledge Engine does not produce wisdom directly — it produces the knowledge structures from which the reasoning layers (DebateAndDecision, MetaLearning) can derive wisdom.

**Intelligence:**

Intelligence is the capacity to acquire knowledge and apply it effectively to achieve goals. In the IIOS, intelligence is the emergent property of:
- The breadth and depth of the knowledge base
- The quality and accuracy of the knowledge
- The speed and precision of knowledge retrieval
- The effectiveness of knowledge application in decision-making

Intelligence is not a component — it is the system-level property that emerges when the Knowledge Engine, the Reasoning Architecture, and the Learning Architecture work together.

---

### 1.3 Why Knowledge Is the Foundation of Intelligence

The progression from data to intelligence follows a pyramid:

```
                    ┌──────────────────────────┐
                    │      INTELLIGENCE        │ ◄ Emergent: effective goal achievement
                    │  (Applied Understanding) │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │         WISDOM           │ ◄ Knowing WHEN and HOW to apply knowledge
                    │  (Contextual Application)│
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │        KNOWLEDGE         │ ◄ KNOWLEDGE ENGINE LAYER
                    │ (Validated Understanding)│   Validated, structured, versioned
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │       INFORMATION        │ ◄ Structured observations of reality
                    │  (Structured Observation)│
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │          DATA            │ ◄ Raw signals and values
                    │    (Raw Reality Proxy)   │
                    └──────────────────────────┘
```

Each level of this pyramid transforms the level below it:
- Data becomes information when it is structured and labelled
- Information becomes knowledge when it is validated, contextualised, and organised
- Knowledge becomes wisdom when it is paired with the right context for application
- Wisdom becomes intelligence when it is applied effectively to achieve goals

The Knowledge Engine operates at the third level — transforming information into knowledge. It is the most architecturally critical component because every level above it depends on it. The reasoning layers cannot reason without knowledge. The learning layers cannot improve without knowledge of what has been learned. The debate agents cannot opine without the knowledge of strategy history, regime behaviour, and market patterns.

---

### 1.4 The Role of the Knowledge Engine in the IIOS

The Knowledge Engine in the IIOS has five primary roles:

**Role 1: Knowledge Curator**
The Knowledge Engine decides what qualifies as knowledge. Not every data point, observation, or event becomes knowledge. The engine applies validation criteria: minimum evidence volume, minimum confidence level, minimum consistency across market conditions. Only validated observations become knowledge.

**Role 2: Knowledge Organiser**
The Knowledge Engine structures knowledge into defined types, assigns it to domains, connects it to related knowledge through the knowledge graph, and maintains the taxonomic hierarchy. Without this organisation, knowledge would be a flat list of observations — impossible to retrieve meaningfully.

**Role 3: Knowledge Distributor**
The Knowledge Engine answers knowledge queries from all consuming layers. When StrategyLab asks "what is the win rate of momentum strategies in BULL_TRENDING regimes?", the Knowledge Engine retrieves, assembles, and delivers the answer. This retrieval is not a database query — it is a semantically aware knowledge lookup that considers context, confidence, and recency.

**Role 4: Knowledge Evolver**
The Knowledge Engine updates knowledge as new evidence accumulates. When a strategy's win rate improves over 3 months from 52% to 61%, the Knowledge Engine creates a new version of that knowledge record, preserving the history of the improvement and updating the confidence score.

**Role 5: Knowledge Guardian**
The Knowledge Engine enforces quality standards. Low-confidence knowledge is labelled as provisional. Stale knowledge triggers freshness alerts. Contradictory knowledge triggers a consistency review. The Knowledge Engine prevents the system from acting on unreliable knowledge.

---

### 1.5 Knowledge in the Context of Financial Trading

Trading systems are uniquely demanding environments for knowledge:

**Non-stationarity:** Market patterns change over time. Knowledge that was true in a trending market may be false in a ranging market. The Knowledge Engine must track not just what is known, but when it was learned and under what conditions.

**Adversarial environment:** Markets adapt. When many participants identify and exploit the same pattern, the pattern deteriorates. The Knowledge Engine must detect knowledge decay — the decline of a pattern's reliability over time — and deprecate stale knowledge before it causes harm.

**High stakes:** A wrong knowledge claim in a medical system might cause harm to one patient. In a trading system, a wrong knowledge claim can cause financial loss in every cycle. Knowledge confidence scoring and evidence thresholds must be calibrated conservatively.

**Regime dependency:** Almost all market knowledge is regime-conditional. "Momentum strategies outperform in trending regimes" is true knowledge. "Momentum strategies outperform" without regime qualification is dangerously incomplete knowledge. The Knowledge Engine enforces regime context on all market knowledge.

**Time horizon sensitivity:** A strategy that works on daily bars may fail on intraday bars. A pattern that holds for 6 months may be noise over 2 years. The Knowledge Engine tracks the time horizon and data resolution context for every knowledge claim.

**Feedback latency:** In some domains, knowledge can be validated immediately. In trading, feedback is delayed (a trade takes days or weeks to play out). The Knowledge Engine manages this feedback loop, tracking knowledge claims that are awaiting confirmation and updating confidence when confirmation arrives.

---

### 1.6 Knowledge as a Strategic Asset

Every knowledge item in the IIOS Knowledge Engine represents accumulated learning — the product of real cycles, real trades, and real market conditions. This knowledge cannot be purchased, downloaded, or substituted. It is the IIOS's unique competitive advantage.

The Knowledge Engine is therefore not just a technical component — it is the steward of the system's most valuable asset. Every engineering decision about the Knowledge Engine must be evaluated through this lens:

- Does this decision protect the integrity of existing knowledge?
- Does this decision make knowledge more accessible to consuming layers?
- Does this decision ensure knowledge remains accurate and current?
- Does this decision preserve the history and lineage of knowledge evolution?

Knowledge is the memory of the system. The Knowledge Engine is the architecture of that memory.

---

## PART II — KNOWLEDGE ARCHITECTURE

### 2.1 The 10-Level Knowledge Hierarchy

The IIOS Knowledge Architecture organises all knowledge into 10 levels of abstraction. Each level represents a different depth of processing, a different degree of validation, and a different scope of applicability.

```
Level 10 ─── META KNOWLEDGE          ─── Knowledge about the knowledge system itself
Level 9  ─── INSTITUTIONAL KNOWLEDGE ─── Cross-strategy, cross-regime operational truths
Level 8  ─── PREDICTIVE KNOWLEDGE    ─── Forward-looking probabilistic claims
Level 7  ─── STRATEGIC KNOWLEDGE     ─── Strategy-level rules and performance maps
Level 6  ─── BEHAVIORAL KNOWLEDGE    ─── Agent, market, and participant behavior patterns
Level 5  ─── TEMPORAL KNOWLEDGE      ─── Time-dependent patterns and seasonality
Level 4  ─── CONTEXTUAL KNOWLEDGE    ─── Regime, sector, and condition-specific facts
Level 3  ─── DERIVED KNOWLEDGE       ─── Computed from combining lower-level knowledge
Level 2  ─── VALIDATED KNOWLEDGE     ─── Verified by evidence, confidence-scored
Level 1  ─── RAW KNOWLEDGE           ─── Candidate knowledge, pending validation
```

---

### 2.2 Level 1 — Raw Knowledge

**Definition:** Raw knowledge is a candidate knowledge item that has been extracted from observations or events but has not yet been validated. It represents the raw output of the knowledge discovery process.

**Origin:** Raw knowledge items are generated by:
- The Knowledge Discovery Service detecting a recurring pattern in market data
- The Learning Engine identifying a statistically significant correlation in trade outcomes
- A walk-forward test revealing unexpected strategy behaviour
- ResearchLab producing an exploratory finding

**Properties:**

| Property | Value |
|---|---|
| Confidence score | 0.0 – 0.3 (provisional) |
| Evidence volume | Below minimum threshold (< 30 observations) |
| Validation status | PENDING |
| Scope | Narrow — derived from limited data |
| Regime qualification | Often absent or uncertain |
| Usability | Not yet usable by consuming layers |

**Lifecycle:** Raw knowledge is the starting point of the knowledge lifecycle. It is created, tagged as PENDING_VALIDATION, and placed in the validation queue. If validation succeeds, it advances to Level 2 (Validated Knowledge). If validation fails (insufficient evidence, inconsistent behaviour, or contradicts well-established knowledge), it is deprecated and archived.

**Governance:** Raw knowledge is owned by the service that discovered it. It cannot be consumed by other layers until it has been validated and promoted.

**Example:** "NIFTY50 appears to show a positive morning momentum effect in the first 30 minutes of trading." This is a raw knowledge claim — it may be true, but it has not yet been confirmed with sufficient evidence across multiple market conditions.

---

### 2.3 Level 2 — Validated Knowledge

**Definition:** Validated knowledge is a knowledge item that has passed the evidence threshold, consistency checks, and confidence scoring. It is reliable enough to be used by consuming layers.

**Validation criteria (all must be met):**

| Criterion | Minimum Requirement |
|---|---|
| Evidence volume | ≥ 30 independent observations |
| Time span of evidence | ≥ 90 trading days |
| Consistency | Pattern holds in ≥ 60% of qualifying conditions |
| Confidence score | ≥ 0.55 |
| Regime qualification | At least one regime context attached |
| Contradicted by higher-level knowledge? | No contradictions |

**Properties:**

| Property | Value |
|---|---|
| Confidence score | 0.55 – 0.80 |
| Evidence volume | ≥ 30 observations |
| Validation status | VALIDATED |
| Scope | Defined with regime and context conditions |
| Usability | Available to consuming layers with confidence caveats |

**Usage by consuming layers:** Validated knowledge can be used by StrategyLab, MetaLearning, and DebateAndDecision. However, it is presented with its confidence score, and decision-making components must weight it accordingly. High-stakes decisions (position sizing, kill-switch thresholds) should not rely on knowledge with confidence < 0.70.

**Example:** "Momentum strategies with entry confirmation (close above 20-period high) achieve a win rate of 58% ± 4% in BULL_TRENDING regimes over the observed 180-day evidence window." Confidence: 0.67.

---

### 2.4 Level 3 — Derived Knowledge

**Definition:** Derived knowledge is produced by combining two or more lower-level knowledge items through a defined reasoning process. It is not directly observed from data — it is computed from existing knowledge.

**Derivation methods:**

| Method | Description | Example |
|---|---|---|
| Inference | "If A and B, then C" | If momentum works in BULL and reversal works in BEAR, then combined regime-conditional allocation outperforms fixed allocation |
| Aggregation | Combine multiple validated facts into a summary | Sector rotation pattern derived from individual sector timing knowledge |
| Comparison | Compare two knowledge items to derive a relative claim | Momentum strategy outperforms reversal strategy in BULL by 12% expected P&L |
| Projection | Extend a known pattern to a new context | If a strategy works in NSE, it may work in BSE with the same underlying dynamics |
| Synthesis | Combine knowledge across different domains | Macro knowledge + technical knowledge → combined signal quality score |

**Traceability requirement:** Every derived knowledge item must carry a complete derivation trace — the identifiers and versions of all source knowledge items and the derivation method used. This enables auditability and recomputation if source knowledge changes.

**Confidence propagation:** Derived knowledge inherits confidence from its sources through a defined formula. The confidence of derived knowledge cannot exceed the minimum confidence of its inputs, and may be further discounted based on the reliability of the derivation method.

```
confidence(derived) = min(confidence(source_1), confidence(source_2), ...) × derivation_reliability_factor
```

---

### 2.5 Level 4 — Contextual Knowledge

**Definition:** Contextual knowledge is knowledge that is explicitly conditioned on the current state of the market, economic environment, or system. It is not universally true — it is true only within a defined context.

**Context dimensions in the IIOS:**

| Dimension | Examples |
|---|---|
| Market regime | BULL_TRENDING, BEAR_VOLATILE, RANGE_BOUND, CRISIS |
| Sector context | IT_OUTPERFORMING, BANK_LAGGING, FMCG_STABLE |
| Volatility state | LOW_VIX (<15), MEDIUM_VIX (15–25), HIGH_VIX (25–45), EXTREME_VIX (>45) |
| Liquidity state | HIGH_VOLUME, LOW_VOLUME, EXPIRY_DAY, RESULTS_SEASON |
| Time context | FIRST_30_MINUTES, PRE_EXPIRY, POST_RESULTS, BUDGET_DAY |
| Global context | RISK_ON, RISK_OFF, US_EARNINGS_WEEK, FED_DECISION_DAY |
| Portfolio state | HEAVY_LONG, HEAVY_SHORT, NEUTRAL, NEAR_DAILY_LOSS_LIMIT |

**Why contextual knowledge is architecturally separate:** A flat knowledge base cannot answer the question "what do we know that is relevant right now?" Contextual knowledge is indexed by context dimensions, enabling the retrieval engine to return knowledge that matches the current state of all dimensions.

**Context decay:** Contextual knowledge has a freshness dimension tied to its context. If the regime changes from BULL_TRENDING to RANGE_BOUND, knowledge valid for BULL_TRENDING is not immediately relevant. The Knowledge Engine tracks which context conditions are currently active and surfaces relevant contextual knowledge accordingly.

---

### 2.6 Level 5 — Temporal Knowledge

**Definition:** Temporal knowledge is knowledge about patterns that manifest over time — seasonality, cyclicality, regime transitions, and time-of-day effects.

**Temporal pattern types:**

| Pattern Type | Example | Relevance |
|---|---|---|
| Intraday | Morning momentum dissipates by 11:00 IST | Every trading day |
| Day-of-week | Thursday expiry effects on premium decay | Every Thursday |
| Monthly | Expiry-week volatility premium | 3rd Thursday each month |
| Quarterly | Results season FII flows | Q1, Q2, Q3, Q4 |
| Seasonal | Budget rally / budget correction | January–February |
| Regime duration | Bull regimes average 45 trading days | Regime lifecycle modelling |
| Regime transition | Bull→Bear transitions triggered by VIX > 22 and breadth < 40% | Regime prediction |

**Temporal knowledge vs. static knowledge:** Static knowledge claims are timeless ("momentum works in bull markets"). Temporal knowledge claims are time-anchored ("momentum is most effective in the first 90 minutes of a bull trading day"). The Knowledge Engine explicitly tags all temporal knowledge with its time dimension.

**Temporal decay:** Some temporal patterns are structural (intraday effects driven by market microstructure) and are stable. Others are driven by participant behaviour and may shift as market composition changes. The Knowledge Engine tracks confidence decay rate for temporal knowledge — how quickly historical evidence becomes less relevant.

---

### 2.7 Level 6 — Behavioral Knowledge

**Definition:** Behavioral knowledge captures patterns in how market participants, agents, strategies, or the system itself behave under specific conditions.

**Behavioral knowledge categories:**

**Market Participant Behaviour:**
- FII (Foreign Institutional Investors) tend to accumulate on dips in BULL regimes
- Retail OI (Open Interest) builds up before major events and collapses after
- Option writers (smart money) tend to be correct on the range of weekly expiry

**Strategy Behaviour:**
- Strategy X has a drawdown recovery pattern that averages 8 trading days after a 3% max drawdown
- Strategy Y underperforms when sector breadth < 50% even in a BULL regime
- Momentum strategies generate false breakouts at a higher rate in low-volume sessions

**Agent Behaviour:**
- TechnicalAgent is most accurate in TRENDING regimes (accuracy 72%), least accurate in VOLATILE (accuracy 51%)
- BullAgent is systematically optimistic in the first 30 minutes — calibrate down by 0.8 points
- RiskAgent underweights macro risk — complement with GlobalContextAgent

**System Behaviour:**
- The system's cycle latency increases by 40ms when VIX > 30 (broader options chain)
- Kill-switch activates more often on Thursdays (expiry day volatility spikes)
- DataFeedManager failover rate increases during the 15–16:00 IST window (RBI announcements)

---

### 2.8 Level 7 — Strategic Knowledge

**Definition:** Strategic knowledge is the highest level of domain-specific knowledge about trading strategies. It captures how strategies should be configured, weighted, and combined for optimal performance.

**Strategic knowledge components:**

| Component | Description |
|---|---|
| Strategy performance maps | Win rate, Sharpe, drawdown for each strategy in each regime |
| Strategy combination rules | Which strategies are complementary, which are redundant |
| Regime allocation weights | Optimal capital allocation per strategy type in each regime |
| Entry condition effectiveness | Which entry conditions have the highest predictive validity |
| Exit condition effectiveness | Which exit conditions preserve most of the captured gain |
| Position sizing rules | What position sizing method works best for each strategy type |
| R:R calibration | Optimal R:R thresholds by strategy type and regime |
| Strategy synergy knowledge | Strategy pairs that produce lower correlation and higher Sharpe when combined |

**Strategic knowledge authority:** Strategic knowledge supersedes lower-level knowledge in decision-making. If contextual knowledge suggests a bullish signal but strategic knowledge says "this strategy has a 72% loss rate in RANGE_BOUND regimes and the current regime is RANGE_BOUND", the strategic knowledge takes precedence.

---

### 2.9 Level 8 — Predictive Knowledge

**Definition:** Predictive knowledge is forward-looking probabilistic claims derived from historical patterns, statistical models, and ensemble reasoning.

**Predictive knowledge is not prediction.** The Knowledge Engine does not forecast market prices. It stores the probability distributions and calibrated expectations derived from historical evidence. These are the inputs to the reasoning layers — not the outputs.

**Predictive knowledge types:**

| Type | Example |
|---|---|
| Regime persistence | "BULL_TRENDING regimes last an average of 43 trading days (σ=12 days)" |
| Transition probability | "P(BULL→BEAR | VIX>22 and 5-day decline>3%) = 0.68" |
| Strategy expectancy | "Momentum strategy in BULL_TRENDING: E[P&L per trade] = 0.81% (win) or -0.52% (loss)" |
| Signal success rate | "Breakout above 52-week high: P(follow-through > 2%) within 5 days = 0.61" |
| Agent prediction calibration | "TechnicalAgent score of 8+ preceded a successful trade in 67% of cases in BULL regimes" |
| Volatility term structure | "VIX mean-reverts from >35 to <25 within 8 trading days in 71% of historical cases" |

**Confidence bounds:** Every predictive knowledge item carries a confidence interval derived from the sample size and consistency of the underlying evidence. Narrow intervals indicate reliable predictions. Wide intervals indicate that the prediction is directional but imprecise.

---

### 2.10 Level 9 — Institutional Knowledge

**Definition:** Institutional knowledge is the accumulated operational understanding of the IIOS as a system — the knowledge of how the system itself behaves, what works, what doesn't, and why.

**What makes it "institutional":** Institutional knowledge transcends any single strategy or market condition. It is the system-level wisdom about the IIOS's own strengths, weaknesses, failure modes, and recovery patterns.

**Institutional knowledge domains:**

| Domain | Contents |
|---|---|
| System reliability | When the system is most reliable (regimes, times of day, volatility conditions) |
| Data feed quality | When each feed is most reliable, when failovers are most likely |
| Agent ensemble calibration | How to weight the 62-agent ensemble in each regime for best conviction score calibration |
| Decision threshold calibration | When the 6.5 conviction threshold is optimal, when it should be raised or lowered |
| Kill-switch calibration | Historical accuracy of kill-switch triggers — false positives vs. false negatives |
| Learning engine effectiveness | When the learning engine produces reliable updates vs. when it is data-starved |
| Cycle timing knowledge | Which parts of the trading day produce the best signal-to-noise ratio |
| Failure mode knowledge | What causes system errors, how long recovery takes, what mitigates each failure mode |

---

### 2.11 Level 10 — Meta Knowledge

**Definition:** Meta knowledge is knowledge about the knowledge system itself. It answers questions about how knowledge is produced, what quality it has, how it should be used, and when it can be trusted.

**Meta knowledge in the IIOS:**

| Meta Knowledge Type | Description |
|---|---|
| Knowledge coverage | Which domains have rich knowledge vs. thin knowledge |
| Knowledge staleness map | Which knowledge domains have not been updated recently |
| Confidence calibration history | How well confidence scores predict actual knowledge reliability |
| Knowledge usage patterns | Which knowledge items are most frequently retrieved, by which consumers |
| Knowledge decay rates | How quickly different types of knowledge lose accuracy over time |
| Knowledge conflict map | Where conflicting knowledge claims exist and their resolution history |
| Governance effectiveness | How often knowledge governance catches quality issues before they affect decisions |
| Discovery effectiveness | Which discovery methods produce the highest-quality knowledge |

**Why meta knowledge matters:** The consuming layers need to know not just what the knowledge base contains, but how much they can trust it. Meta knowledge provides this second-order reliability signal. A consuming layer that knows the knowledge in a particular domain has decayed significantly can down-weight that knowledge accordingly.

---
## PART III — KNOWLEDGE OBJECTS

### 3.1 Knowledge Object Design Philosophy

A knowledge object is a first-class, typed, versioned, and auditable unit of knowledge in the IIOS. Unlike raw data records (which are facts about past events) or information records (which are structured observations), knowledge objects carry **meaning, confidence, context, and lineage**.

Every knowledge object in the IIOS is:
- **Typed** — it belongs to exactly one knowledge object type with defined fields
- **Versioned** — every change creates a new version; history is preserved
- **Evidence-backed** — it carries references to the evidence that supports it
- **Confidence-scored** — it carries a numerical confidence score with defined semantics
- **Context-qualified** — it specifies the conditions under which it applies
- **Lineage-tracked** — it records how it was discovered, from what sources, and by which service
- **Governed** — it has a defined owner and is subject to quality review

The 15 knowledge object types are described below. They form the complete vocabulary of the Knowledge Engine.

---

### 3.2 Knowledge Record

**Purpose:** The fundamental unit of knowledge storage. Every piece of knowledge in the IIOS is ultimately represented as one or more Knowledge Records.

**Structure:**

| Field | Type | Description |
|---|---|---|
| `knowledge_id` | UUID4 | Unique, permanent identifier |
| `knowledge_type` | KnowledgeType enum | One of the 15 types |
| `knowledge_level` | int (1–10) | Hierarchy level |
| `domain` | string | Knowledge domain (strategy, market, system, etc.) |
| `category` | string | Knowledge category within the domain |
| `title` | string | Human-readable description of what is known |
| `claim` | string | The precise knowledge claim |
| `confidence_score` | float (0.0–1.0) | Current confidence estimate |
| `evidence_ids` | List[UUID4] | References to supporting evidence |
| `context_conditions` | JSON | Regime, volatility, and other context qualifiers |
| `valid_from` | datetime | When this version became active |
| `valid_to` | datetime | When this version was superseded (null if current) |
| `version` | int | Version number (monotonically increasing) |
| `status` | KnowledgeStatus | PENDING, VALIDATED, DEPRECATED, ARCHIVED |
| `owner_id` | string | Which service or component owns this knowledge |
| `lineage_id` | UUID4 | Reference to the Knowledge Lineage record |
| `created_at` | datetime | When this version was created |
| `created_by` | string | Which service created this version |

**Lifecycle:** A Knowledge Record is created in PENDING status. It transitions to VALIDATED after evidence review. It may be DEPRECATED when superseded by better knowledge or when evidence contradicts it. DEPRECATED records are ARCHIVED after the defined retention period.

---

### 3.3 Knowledge Pattern

**Purpose:** Represents a recurring, statistically validated pattern observed in market data, strategy performance, or system behaviour. A pattern is the most common form of knowledge in a trading system.

**Pattern definition:**

A Knowledge Pattern consists of:
- A **precondition** — the set of observable conditions that precede the pattern
- A **consequence** — what reliably follows when the precondition is met
- An **occurrence rate** — the fraction of qualifying situations where the consequence was observed
- A **magnitude distribution** — how strong the consequence typically is
- A **context window** — how much time elapses between precondition and consequence

**Pattern types in the IIOS:**

| Pattern Type | Example |
|---|---|
| Price pattern | Higher-high, higher-low structure over 5 bars → continuation in BULL with 63% probability |
| Volume pattern | Volume spike > 2× average on breakout → higher breakout success rate (71%) |
| Options pattern | Call OI buildup at round strikes before expiry → resistance at those levels |
| Regime pattern | VIX > 22 on declining breadth → regime transition to BEAR within 5 days in 68% of cases |
| Strategy pattern | After 3 consecutive losses, strategy win rate drops to 38% (over-fitting signal) |
| Agent pattern | When all 5 BULL agents score > 7 simultaneously, conviction > 8 is achieved in 81% of cases |
| Sector pattern | IT outperformance of NIFTY by > 2% for 3 consecutive days precedes market weakness in 61% of cases |

**Pattern confidence:** Pattern confidence is computed as `n_supporting / n_qualifying × (1 - uncertainty_discount)`, where `uncertainty_discount` reflects the variability of the pattern strength across observations.

---

### 3.4 Knowledge Rule

**Purpose:** A Knowledge Rule is a deterministic, high-confidence conditional statement that governs system behaviour. Unlike patterns (which are probabilistic), rules are categorical: IF condition THEN consequence.

**Rule types:**

| Rule Type | Applicability | Example |
|---|---|---|
| Safety rule | Always active | "If daily loss > 2% of capital, halt all trading" |
| Risk rule | Active when not in kill-switch state | "No single trade may risk more than 0.5% of capital" |
| Strategy eligibility rule | Active during strategy selection | "Strategy is eligible only if win_rate ≥ 0.50 AND Sharpe > 0.8" |
| Signal quality rule | Active during hypothesis evaluation | "Minimum R:R of 1.5:1 required to generate a hypothesis" |
| Regime override rule | Active on regime change | "On regime change to CRISIS: disable all directional strategies" |
| Expiry rule | Active on specific dates | "Do not open new positions after 14:00 on Thursday expiry day" |

**Rule governance:** Rules are the most restrictive knowledge type. They cannot be modified without ADR and Human Principal approval. They cannot be overridden by any pattern or derived knowledge. Rules are marked with `is_inviolable=True` in the Knowledge Record.

**Rule confidence:** By convention, rules have confidence = 1.0 (they are treated as inviolable). A rule that has been observed to fail under any condition is demoted to a Pattern with the appropriate confidence score.

---

### 3.5 Knowledge Fact

**Purpose:** A Knowledge Fact is a singular, specific, documented observation of reality that has been verified and admitted to the knowledge base. Facts are the building blocks of patterns and rules.

**Fact types:**

| Fact Type | Example |
|---|---|
| Market fact | "NIFTY50 closed above 22,000 on 47 of the last 60 trading days" |
| Strategy fact | "MomentumBreakoutV3 has executed 127 trades over the last 180 days" |
| Performance fact | "MomentumBreakoutV3 win rate = 61.4% (78/127 winning trades)" |
| Agent fact | "TechnicalAgent score correlation with trade outcome: r=0.61 in BULL regimes" |
| Regime fact | "The BULL_TRENDING regime has been active for 37 consecutive trading days" |
| System fact | "Average cycle latency has been 172ms for the last 30 days" |

**Fact immutability:** Facts, once validated, are immutable. A fact cannot be revised — if new evidence contradicts a fact, a new fact is created and the old fact is deprecated with a note pointing to the superseding fact. This preserves the complete historical record of what was believed to be true at each point in time.

---

### 3.6 Knowledge Graph Node

**Purpose:** Every Knowledge Record has a corresponding Knowledge Graph Node. The node is the representation of the knowledge item within the Knowledge Graph — it contains not just the knowledge itself, but its connections to related knowledge.

**Node structure:**

| Field | Description |
|---|---|
| `node_id` | Maps to `knowledge_id` of the corresponding Knowledge Record |
| `node_type` | One of: FACT, PATTERN, RULE, CONTEXT, ENTITY, REGIME |
| `edge_count` | Number of edges connecting this node to others |
| `centrality_score` | How central this node is in the knowledge graph (PageRank-style) |
| `cluster_id` | Which knowledge cluster this node belongs to |
| `incoming_edges` | List of (source_node, relationship_type, weight) |
| `outgoing_edges` | List of (target_node, relationship_type, weight) |

**Edge types in the knowledge graph:**

| Edge Type | Meaning |
|---|---|
| `SUPPORTS` | Node A is evidence supporting Node B |
| `CONTRADICTS` | Node A contradicts Node B |
| `DERIVED_FROM` | Node A was derived from Node B |
| `APPLIES_IN` | Node A (pattern) applies in Node B (context) |
| `SUPERSEDES` | Node A (new version) supersedes Node B (old version) |
| `CO_OCCURS_WITH` | Nodes A and B tend to be true simultaneously |
| `ENABLES` | Node A being true enables Node B to be applicable |
| `INHIBITS` | Node A being true inhibits Node B from applying |

---

### 3.7 Knowledge Cluster

**Purpose:** A Knowledge Cluster groups related Knowledge Records that collectively describe a coherent aspect of the domain. Clusters are the primary unit of knowledge organisation for retrieval.

**Cluster design:**

| Aspect | Description |
|---|---|
| Formation | Clusters are formed by the Knowledge Classification Service based on semantic similarity and graph connectivity |
| Membership | A Knowledge Record can belong to exactly one primary cluster and optionally additional secondary clusters |
| Coherence score | Each cluster carries a coherence score — how tightly the members relate to each other |
| Cluster summary | A human-readable summary of the cluster's collective knowledge is maintained |
| Representative node | The node with highest centrality score serves as the cluster's representative |
| Update trigger | When a new knowledge item is added to a cluster, the cluster summary is regenerated |

**Cluster examples:**

| Cluster Name | Contents |
|---|---|
| `MOMENTUM_BULL_KNOWLEDGE` | All patterns, facts, and rules related to momentum strategies in BULL regimes |
| `VIX_REGIME_TRANSITIONS` | All patterns about how VIX levels relate to regime changes |
| `THURSDAY_EXPIRY_EFFECTS` | All temporal knowledge about Thursday option expiry behaviour |
| `TECHNICAL_AGENT_CALIBRATION` | All facts and patterns about TechnicalAgent's prediction accuracy |
| `POSITION_SIZING_KNOWLEDGE` | All rules and patterns about effective position sizing |
| `FEED_RELIABILITY_KNOWLEDGE` | All institutional knowledge about data feed reliability patterns |

---

### 3.8 Knowledge Context

**Purpose:** A Knowledge Context is a structured description of the conditions under which a Knowledge Record is valid. It allows the retrieval engine to match knowledge to the current system state.

**Context dimensions:**

| Dimension | Type | Examples |
|---|---|---|
| `regime` | Enum | BULL_TRENDING, BEAR_VOLATILE, RANGE_BOUND, CRISIS, SIDEWAYS |
| `volatility_state` | Enum | LOW, MEDIUM, HIGH, EXTREME |
| `volume_state` | Enum | HIGH, NORMAL, LOW, EXPIRY |
| `sector_state` | JSON | `{"IT": "OUTPERFORMING", "BANK": "NEUTRAL"}` |
| `global_state` | Enum | RISK_ON, RISK_OFF, NEUTRAL |
| `time_of_day` | TimeRange | `09:15-10:00`, `10:00-14:00`, `14:00-15:30` |
| `day_of_week` | List | `["MON", "TUE", "WED", "THU", "FRI"]` |
| `expiry_proximity` | Enum | WEEK_OF, DAY_OF, OTHER |
| `portfolio_state` | JSON | `{"exposure_pct": "< 0.6", "daily_pnl_pct": "> -0.5"}` |
| `event_context` | List | `["RESULTS_SEASON", "BUDGET_WEEK", "FED_MEETING"]` |

**Context matching:** When a consuming layer queries for knowledge, it provides a `QueryContext` that describes the current state of all dimensions. The retrieval engine returns knowledge whose Context overlaps with the QueryContext. Partial matches are returned with a relevance score based on how many dimensions match.

---

### 3.9 Knowledge Version

**Purpose:** A Knowledge Version represents a specific point-in-time state of a Knowledge Record. The version history of a knowledge item is the record of how understanding has evolved.

**Version structure:**

| Field | Description |
|---|---|
| `version_id` | UUID4 — unique per version |
| `knowledge_id` | The parent Knowledge Record ID |
| `version_number` | Monotonically increasing integer |
| `confidence_delta` | How much confidence changed from the previous version (positive = improvement) |
| `evidence_delta` | How many new evidence items were added since the previous version |
| `claim_changed` | Boolean — did the knowledge claim itself change? |
| `context_changed` | Boolean — did the context conditions change? |
| `superseded_by` | Version ID of the version that replaced this one (null if current) |
| `created_at` | Timestamp |
| `created_by` | Service that created this version |
| `change_reason` | Enum: NEW_EVIDENCE, CONTRADICTION_RESOLVED, CLAIM_REFINED, CONTEXT_UPDATED, CONFIDENCE_UPDATE |

**Version immutability:** Every version, once created, is immutable. The current version of a knowledge item is defined by the most recent version with `superseded_by = null`. Reading the version history allows reconstruction of how the system's understanding evolved.

---

### 3.10 Knowledge Confidence

**Purpose:** A Knowledge Confidence object encapsulates the complete confidence assessment for a Knowledge Record, including how confidence was computed and what it means.

**Confidence components:**

| Component | Description |
|---|---|
| `raw_score` | The raw probability estimate from the evidence |
| `sample_size_discount` | Discount applied for small sample sizes (Laplace smoothing) |
| `consistency_score` | How consistent the pattern is across different market conditions |
| `recency_weight` | Weight applied to recent evidence vs. older evidence |
| `regime_coverage` | How many regimes have contributing evidence |
| `final_confidence` | Composite score after all adjustments |
| `confidence_interval_lower` | Lower bound (e.g., 0.55 at 95% CI) |
| `confidence_interval_upper` | Upper bound (e.g., 0.73 at 95% CI) |
| `last_updated` | When confidence was last recomputed |
| `update_trigger` | What triggered the last update |

**Confidence interpretation:**

| Score | Label | Interpretation | Usability |
|---|---|---|---|
| 0.00 – 0.30 | SPECULATIVE | Insufficient evidence | Not usable by consuming layers |
| 0.30 – 0.55 | PROVISIONAL | Some evidence but not yet reliable | Use only in low-stakes contexts |
| 0.55 – 0.70 | MODERATE | Reliably validated in majority of conditions | Use with confidence caveat |
| 0.70 – 0.85 | HIGH | Well-validated, consistent across conditions | Use confidently |
| 0.85 – 1.00 | VERY HIGH | Extensively validated, robust across all conditions | Use as primary input |
| 1.00 | INVIOLABLE | Rule — treated as absolute | Use without discounting |

---

### 3.11 Knowledge Dependency

**Purpose:** A Knowledge Dependency records that one knowledge item depends on another — meaning the validity or applicability of the dependent item relies on the parent item being true.

**Dependency types:**

| Dependency Type | Meaning |
|---|---|
| `REQUIRES` | Dependent knowledge is only applicable if the dependency is validated |
| `ASSUMES` | Dependent knowledge implicitly assumes the dependency is true |
| `CONFLICTS_WITH` | Dependent knowledge contradicts the dependency — cannot both be true simultaneously |
| `ENHANCES` | Dependent knowledge is more reliable when the dependency is also true |
| `WEAKENS` | Dependent knowledge is less reliable when the dependency is also true |

**Dependency impact on confidence:** If a knowledge item's dependency is deprecated or has its confidence significantly reduced, the dependent knowledge item's confidence is automatically re-evaluated. A chain of dependency impacts is propagated by the Knowledge Evolution Service.

---

### 3.12 Knowledge Source

**Purpose:** A Knowledge Source records where a knowledge item came from — which system, service, dataset, or process produced the underlying evidence.

**Source types:**

| Source Type | Example |
|---|---|
| `MARKET_DATA` | OHLCV data from Yahoo Finance or Dhan |
| `TRADE_OUTCOME` | Closed trade P&L and timing from TradeMonitor |
| `BACKTEST_RUN` | Strategy performance on historical market data |
| `WALK_FORWARD_TEST` | Out-of-sample test result from ValidationEngine |
| `AGENT_CALIBRATION` | Agent prediction accuracy data from LearningEngine |
| `MONTE_CARLO_SIMULATION` | Stress test outcomes from RiskControl |
| `REGIME_DETECTION` | Regime labels produced by MarketIntelligence |
| `HUMAN_ANNOTATION` | Manually annotated knowledge from Human Principal |
| `DERIVED_FROM_KNOWLEDGE` | Produced by combining other knowledge items |

**Source quality rating:** Each source type has a quality rating that influences confidence calculation. Trade outcomes from live or paper trading are the highest-quality evidence. Backtest results carry a quality discount for lookahead and overfitting risk. Human annotations carry a quality discount for subjectivity.

| Source Type | Quality Multiplier |
|---|---|
| Live trade outcome | 1.00 |
| Paper trade outcome | 0.95 |
| Walk-forward test result | 0.85 |
| Backtest result | 0.70 |
| Monte Carlo simulation | 0.65 |
| Derived from knowledge | 0.80 |
| Human annotation | 0.75 |

---

### 3.13 Knowledge Evidence

**Purpose:** A Knowledge Evidence record is the documentation of a specific observation or test result that supports or refutes a Knowledge Record.

**Evidence structure:**

| Field | Description |
|---|---|
| `evidence_id` | UUID4 |
| `knowledge_id` | The knowledge item this evidence supports |
| `evidence_type` | SUPPORTING, CONTRADICTING, NEUTRAL |
| `source_id` | Reference to the Knowledge Source |
| `observed_at` | When this evidence was produced |
| `regime_at_observation` | Market regime at the time of the observation |
| `value` | The observed value (e.g., win rate = 0.61) |
| `context_snapshot` | Key market state fields at the time of observation |
| `weight` | Source quality multiplier (from source type rating) |

**Evidence accumulation:** As new trades close, walk-forward tests complete, and backtests run, new evidence records are added to the knowledge base. The Knowledge Evolution Service monitors evidence accumulation and triggers confidence score updates when evidence volume crosses defined thresholds.

---

### 3.14 Knowledge Owner

**Purpose:** A Knowledge Owner is a component or role that has authority over a knowledge item — responsible for its creation, validation, and quality.

**Ownership model:**

| Owner Type | Responsibilities | Examples |
|---|---|---|
| Service owner | Created the knowledge; responsible for its evidence management | StrategyLab owns strategy performance knowledge |
| Domain owner | Responsible for all knowledge in a knowledge domain | MarketIntelligence owns regime knowledge |
| Governance reviewer | Approves knowledge status transitions | KnowledgeGovernanceService |
| Human Principal | Final authority for inviolable rules | Human Principal |

**Ownership transfer:** When a component is deprecated or replaced, its knowledge ownership transfers to its successor. Knowledge without an active owner is flagged for review by the KnowledgeGovernanceService.

---

### 3.15 Knowledge Lineage

**Purpose:** Knowledge Lineage is the complete traceable chain from the raw observations that first suggested a knowledge claim through every version of that claim to its current state.

**Lineage record structure:**

| Field | Description |
|---|---|
| `lineage_id` | UUID4 |
| `knowledge_id` | The knowledge item |
| `discovery_method` | How it was first discovered |
| `discovery_service` | Which service first identified it |
| `discovery_timestamp` | When it was first identified as a candidate |
| `initial_evidence_count` | Evidence count at discovery |
| `version_history` | Ordered list of version IDs |
| `confidence_trajectory` | List of (timestamp, confidence_score) pairs |
| `status_history` | List of (timestamp, status) pairs |
| `source_chain` | All sources that contributed evidence |
| `derived_from` | If derived, list of parent knowledge IDs and derivation method |
| `derived_children` | List of knowledge IDs derived from this knowledge |

**Lineage as audit evidence:** The Knowledge Lineage record is the audit trail for a knowledge item. For any knowledge claim used in a trading decision, a human auditor can trace exactly how that claim was produced, what evidence supported it, how confident the system was, and what versions preceded it.

---
## PART IV — KNOWLEDGE LIFECYCLE

### 4.1 Lifecycle Overview

Every knowledge item in the IIOS travels through a complete lifecycle from the moment a pattern is first observed to the moment the knowledge is archived. The lifecycle is not optional — every knowledge item follows it, enforced by the Knowledge Engine's governance system.

The lifecycle has 12 stages:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE LIFECYCLE                                     │
│                                                                             │
│  ① DISCOVERY ──► ② VALIDATION ──► ③ CREATION ──► ④ CLASSIFICATION         │
│       │                │               │               │                   │
│       │ [FAIL]         │ [FAIL]        │               │                   │
│       ▼                ▼               │               │                   │
│  CANDIDATE         REJECTED           │               │                   │
│  ARCHIVE           ARCHIVE            │               │                   │
│                                       ▼               ▼                   │
│                               ⑤ STORAGE ──────► ⑥ RETRIEVAL              │
│                                       │               │                   │
│                                       ▼               │                   │
│                               ⑦ USAGE ◄──────────────┘                   │
│                                       │                                   │
│                                       ▼                                   │
│                               ⑧ LEARNING ──► ⑨ EVOLUTION ──► ⑩ VERSIONING│
│                                                               │           │
│                                                       ┌───────▼────────┐  │
│                                                       │ ⑪ DEPRECATION  │  │
│                                                       └───────┬────────┘  │
│                                                               │           │
│                                                       ┌───────▼────────┐  │
│                                                       │ ⑫ ARCHIVAL     │  │
│                                                       └────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.2 Stage 1 — Discovery

**Definition:** The discovery stage is when the Knowledge Engine first identifies a candidate knowledge item from raw observations, data patterns, or reasoning outputs.

**Discovery triggers:**

| Trigger | Origin Service | Knowledge Type |
|---|---|---|
| Statistical pattern detection | LearningEngine | Pattern, Fact |
| Walk-forward test anomaly | ValidationEngine | Pattern, Rule candidate |
| Agent calibration run | LearningEngine | Behavioral Knowledge |
| Regime transition analysis | MarketIntelligence | Temporal, Contextual |
| Manual submission | Human Principal | Rule, Fact |
| Contradiction detection | Knowledge Governance Service | Meta Knowledge |
| Strategy evolution run | StrategyLab | Strategic Knowledge |

**Discovery output:** A candidate knowledge item is created in `PENDING_DISCOVERY` status. It is assigned a `knowledge_id`, a preliminary `knowledge_type`, a `discovery_timestamp`, and a reference to the originating service and observation.

**Discovery quality gate:** Not every observation triggers a discovery event. The Knowledge Discovery Service applies minimum thresholds:
- Pattern: At least 10 qualifying occurrences before a discovery is filed
- Fact: The fact must be directly observable (not inferred) from at least one authoritative source
- Rule: Rules can only be submitted by the Human Principal or by a service with RULE_CREATION permission

**Discovery rejection:** If the minimum thresholds are not met, the observation is stored as a pre-discovery observation in the Evidence Store, where it waits until enough evidence accumulates to trigger a formal discovery event.

---

### 4.3 Stage 2 — Validation

**Definition:** The validation stage is the formal review of a candidate knowledge item against evidence quality standards, consistency requirements, and existing knowledge.

**Validation process (sequential checks — all must pass):**

```
Candidate Knowledge Item
        │
        ▼
[Check 1: Evidence Volume]
  ≥ 30 observations? ──── NO ──► VALIDATION_FAIL (insufficient evidence)
        │ YES
        ▼
[Check 2: Time Span]
  Evidence spans ≥ 90 trading days? ── NO ──► VALIDATION_FAIL (time span too short)
        │ YES
        ▼
[Check 3: Consistency]
  Pattern holds in ≥ 60% of qualifying conditions? ── NO ──► VALIDATION_FAIL (inconsistent)
        │ YES
        ▼
[Check 4: Confidence Threshold]
  Raw confidence ≥ 0.55? ── NO ──► VALIDATION_FAIL (below confidence floor)
        │ YES
        ▼
[Check 5: Contradiction Check]
  Contradicts existing HIGH-confidence knowledge? ── YES ──► VALIDATION_HOLD (conflict review)
        │ NO
        ▼
[Check 6: Context Qualification]
  At least one regime or context condition attached? ── NO ──► VALIDATION_FAIL (unqualified)
        │ YES
        ▼
VALIDATION_PASS → Status: VALIDATED
```

**Validation failure handling:**
- `VALIDATION_FAIL`: The candidate is deprecated. Evidence is retained in the Evidence Store for future re-evaluation if more evidence accumulates.
- `VALIDATION_HOLD`: The contradiction is escalated to the KnowledgeGovernanceService for human review. The candidate remains in PENDING status until the conflict is resolved.

**Validation override:** Human Principal can override a VALIDATION_FAIL for Rule-type knowledge by assigning it `is_inviolable=True`. This allows the creation of safety rules that are not required to meet the statistical evidence thresholds.

---

### 4.4 Stage 3 — Creation

**Definition:** The creation stage is when a validated knowledge item is formally created as a Knowledge Record and registered in the knowledge base.

**Creation steps:**

| Step | Action | Service |
|---|---|---|
| 1 | Assign final `knowledge_id` (UUID4) | Knowledge Engine |
| 2 | Assign `knowledge_level` (1–10 hierarchy) | Knowledge Classification Service |
| 3 | Set `knowledge_type` from the 15-type vocabulary | Knowledge Classification Service |
| 4 | Compose the `claim` statement in standardised language | Knowledge Engine |
| 5 | Compute initial `confidence_score` and confidence interval | Knowledge Quality Service |
| 6 | Attach all supporting evidence IDs | Knowledge Engine |
| 7 | Build `context_conditions` from validation context | Knowledge Engine |
| 8 | Assign `owner_id` to the creating service | Knowledge Engine |
| 9 | Create the Knowledge Lineage record | Knowledge Engine |
| 10 | Set status to `VALIDATED`, version to 1 | Knowledge Engine |
| 11 | Write to Knowledge Store (via KnowledgeRepository) | Database Persistence |
| 12 | Register node in Knowledge Graph | Knowledge Graph Service |
| 13 | Assign to initial cluster | Knowledge Classification Service |
| 14 | Write creation audit event | AuditService |

**Creation atomicity:** Steps 11–14 are executed in a single transaction. If any step fails, the creation is rolled back and retried. A knowledge item is either fully created and graph-registered, or it does not exist.

---

### 4.5 Stage 4 — Classification

**Definition:** The classification stage assigns the knowledge item to its position in the taxonomy, connects it to the knowledge graph, and assigns it to a cluster.

**Classification outputs:**

| Output | Description |
|---|---|
| Domain assignment | Which of the top-level knowledge domains (e.g., MARKET, STRATEGY, SYSTEM) |
| Category assignment | Which subcategory within the domain |
| Hierarchy level confirmation | Confirms the level 1–10 assignment |
| Taxonomy path | Full path in the taxonomy tree (e.g., MARKET > REGIME > TRANSITIONS) |
| Graph connections | All edges added to the knowledge graph |
| Cluster assignment | Primary and secondary cluster memberships |
| Search index entries | Keywords and semantic tags for retrieval |

**Classification rules:**

| Rule | Description |
|---|---|
| Every knowledge item has exactly one domain | No knowledge is domain-less or cross-domain at the record level |
| Every knowledge item has at least one cluster | Unclustered knowledge is invisible to retrieval |
| Graph connections are bidirectional | Adding an edge A→B also creates B→A with the inverse relationship type |
| Classification can be revised | If new context changes the appropriate classification, re-classification is allowed (creates a new version) |

---

### 4.6 Stage 5 — Storage

**Definition:** The storage stage is the durable persistence of the created and classified knowledge item.

**Storage targets:**

| Store | What Is Stored | Technology |
|---|---|---|
| Knowledge Store (primary) | Knowledge Record, Knowledge Version, Knowledge Evidence | `knowledge.db` (SQLite) |
| Knowledge Graph | Knowledge Graph Node, edge list, cluster membership | `knowledge.db` graph tables |
| Evidence Store | Knowledge Evidence records | `knowledge.db` |
| Lineage Store | Knowledge Lineage records | `knowledge.db` |
| Search Index | Knowledge Record search entries | `knowledge.db` FTS5 |
| Cache Layer | Hot knowledge items for cycle-time retrieval | TTL in-memory cache |

**Storage durability:** Knowledge Records are stored with `PRAGMA synchronous = NORMAL` (Tier 2 — Persistent, as per DATABASE_PERSISTENCE_ARCHITECTURE.md). This is appropriate because knowledge can be reconstructed from evidence if needed, whereas audit and trade records require FULL synchronous mode.

**Storage confirmation:** A knowledge item is not considered created until all storage targets have been successfully written and confirmed. Partial storage is detected on startup via integrity checks and repaired by re-running the creation stage for the partially created item.

---

### 4.7 Stage 6 — Retrieval

**Definition:** The retrieval stage is when a consuming layer queries the Knowledge Engine for relevant knowledge.

**Retrieval patterns:**

| Pattern | Method | Use Case |
|---|---|---|
| ID lookup | `KnowledgeStore.get(knowledge_id)` | Direct access by known ID |
| Context query | `KnowledgeStore.find_by_context(query_context)` | "What do we know that's relevant right now?" |
| Domain query | `KnowledgeStore.find_by_domain(domain, category)` | "What do we know about momentum strategies?" |
| Cluster retrieval | `KnowledgeStore.get_cluster(cluster_id)` | Retrieve all knowledge in a topic cluster |
| Graph traversal | `KnowledgeGraph.traverse(start_node, relationship_types, depth)` | "What does this knowledge lead to?" |
| Confidence-filtered | `KnowledgeStore.find_above_confidence(min_confidence, context)` | "What do we know with confidence > 0.70?" |
| Search | `KnowledgeSearchService.search(query_string, context)` | Free-text and semantic search |

**Retrieval result structure:** Every retrieval returns a `KnowledgeQueryResult` that includes:
- The matching Knowledge Records, sorted by relevance score
- The confidence score for each item
- The context match score (how closely the item's context matches the query context)
- The freshness indicator (how recently the item was updated)
- A combined relevance score (weighted combination of confidence, context match, and freshness)

**Retrieval caching:** Context-based queries with the same `QueryContext` are cached for the duration of the current cognitive cycle. This ensures that multiple consuming layers in the same cycle see consistent knowledge without redundant database reads.

---

### 4.8 Stage 7 — Usage

**Definition:** The usage stage tracks how knowledge is consumed in decision-making, which is fed back into the knowledge evolution process.

**Usage tracking:**

| Usage Event | Information Captured |
|---|---|
| Knowledge item retrieved | knowledge_id, cycle_id, consumer_service, retrieval_timestamp |
| Knowledge item used in decision | knowledge_id, cycle_id, decision_id, influence_weight |
| Knowledge item led to winning trade | knowledge_id, trade_id, outcome, P&L |
| Knowledge item led to losing trade | knowledge_id, trade_id, outcome, P&L |
| Knowledge item rejected by agent | knowledge_id, agent_name, rejection_reason |
| Knowledge item contradicted by outcome | knowledge_id, contradicting_evidence_id |

**Usage feedback loop:** Usage tracking is the mechanism by which the system learns which knowledge items are most valuable. Items that are frequently retrieved and frequently associated with winning outcomes gain increased confidence. Items that are retrieved but consistently associated with losing outcomes trigger a confidence review.

---

### 4.9 Stage 8 — Learning

**Definition:** The learning stage is when usage outcomes are fed back into the knowledge base as new evidence, updating confidence scores and potentially triggering evolution.

**Learning events:**

| Event | Learning Action |
|---|---|
| Trade closed (win) | Add SUPPORTING evidence to all knowledge items used in the decision |
| Trade closed (loss) | Add CONTRADICTING evidence to knowledge items that predicted success |
| Walk-forward test completed | Add SUPPORTING or CONTRADICTING evidence based on out-of-sample result |
| Regime change observed | Update temporal knowledge confidence for the previous regime's patterns |
| Strategy auto-disabled | Add CONTRADICTING evidence to knowledge items supporting that strategy's eligibility |
| Strategy re-enabled after recovery | Add SUPPORTING evidence to strategy resilience knowledge |

**Learning batch processing:** Learning updates are processed in EOD batches, not in real time. This prevents individual trades from causing excessive confidence fluctuations. The batch processing applies smoothing to prevent overfitting to recent outcomes.

---

### 4.10 Stage 9 — Evolution

**Definition:** The evolution stage is when the Knowledge Engine updates a knowledge item in response to accumulated learning signals.

**Evolution triggers:**

| Trigger | Threshold | Evolution Action |
|---|---|---|
| Confidence increase > 0.05 | After 30+ new supporting evidence items | Create new version with higher confidence |
| Confidence decrease > 0.05 | After 20+ contradicting evidence items | Create new version with lower confidence; alert if below 0.55 |
| Context conditions change | Regime map update | Create new version with updated context |
| Claim refinement needed | Research finding | Create new version with refined claim |
| New evidence changes time horizon | Long-term pattern analysis | Update temporal parameters |
| Dependency confidence changes | Parent knowledge item updated | Recalculate derived confidence |

**Evolution vs. deprecation threshold:**

| Post-evolution confidence | Action |
|---|---|
| ≥ 0.70 | Promote to HIGH confidence — no action needed |
| 0.55 – 0.70 | Maintain MODERATE confidence — monitor |
| 0.40 – 0.55 | Demote to PROVISIONAL — alert consumers |
| < 0.40 | Initiate deprecation review |

---

### 4.11 Stage 10 — Versioning

**Definition:** The versioning stage captures every evolution of a knowledge item as an immutable version record.

**Versioning rules:**

| Rule | Description |
|---|---|
| Every evolution creates a new version | No in-place modification of existing versions |
| Version numbers are sequential and gapless | No gaps in version sequence (detected by integrity check) |
| Each version is immutable after creation | The version record cannot be modified |
| The current version has `valid_to = null` | Querying without a version returns the current version |
| Historical versions are accessible | Any consumer can request a specific version by number |
| Version chain is auditable | The complete history of changes is reconstructable from version records |

**Version comparison:** The Knowledge Version Service provides a `diff()` operation that compares any two versions of the same knowledge item and returns a structured `KnowledgeDiff` showing exactly what changed, when, and why.

---

### 4.12 Stage 11 — Deprecation

**Definition:** The deprecation stage marks a knowledge item as no longer reliable or applicable.

**Deprecation triggers:**

| Trigger | Description |
|---|---|
| Confidence falls below 0.40 after evolution | Knowledge is no longer reliable |
| Superseded by higher-confidence version | The claim is true but expressed better in a new item |
| Context conditions no longer exist | The regime or market condition this knowledge applied to no longer occurs |
| Contradiction with inviolable Rule | The knowledge contradicts an established safety rule |
| Market structure change | The market has fundamentally changed (e.g., regulatory change) |
| Human Principal review finding | Manual review determines the knowledge is incorrect |

**Deprecation process:**

```
Step 1: Knowledge item flagged for deprecation review
Step 2: KnowledgeGovernanceService notified
Step 3: Review period (7 calendar days) — new evidence may prevent deprecation
Step 4: If deprecation confirmed: status → DEPRECATED; valid_to → review completion timestamp
Step 5: All dependent knowledge items notified (via Knowledge Dependency graph)
Step 6: All consuming layers alerted (via EventBus: KNOWLEDGE_DEPRECATED event)
Step 7: Cache entries for this knowledge item invalidated
Step 8: Deprecation audit event written
```

**Deprecation vs. deletion:** DEPRECATED knowledge is never deleted. It is retained in the knowledge base with `status = DEPRECATED` and remains accessible for research and historical analysis. Consuming layers that query for knowledge automatically filter out DEPRECATED items unless explicitly requesting deprecated knowledge.

---

### 4.13 Stage 12 — Archival

**Definition:** The archival stage moves deprecated knowledge to cold storage after its active retention period expires.

**Archival criteria:**
- Status = DEPRECATED
- Time since deprecation > 1 year
- No active references from current consuming layers

**Archival process:**
- Serialize complete knowledge record + all versions + all evidence + lineage to JSON
- Compute SHA-256 of serialised JSON
- Compress to `.json.gz`
- Move to `archive/knowledge/` directory
- Record archival event in AuditService
- Remove from live knowledge.db (soft delete with archival reference)
- Verify archived file is readable and checksum matches

**Archival is permanent.** Archived knowledge can be restored for research but is not automatically available to consuming layers. Restoration requires explicit Human Principal authorisation.

---
## PART V — KNOWLEDGE ORGANIZATION

### 5.1 Organization Philosophy

Knowledge is only as useful as the system's ability to find it at the right time. A knowledge base with excellent knowledge poorly organised is equivalent to a library with excellent books in random piles on the floor. The Knowledge Engine's organisation design makes all stored knowledge accessible, searchable, and contextually retrievable in real time.

The IIOS knowledge organisation has five layers:
1. **Knowledge Domains** — the top-level categories of what the system knows
2. **Knowledge Categories** — subcategories within each domain
3. **Knowledge Hierarchies** — depth levels that add specificity
4. **Knowledge Taxonomy** — the complete naming system for classifying knowledge
5. **Knowledge Graph** — the network of relationships between knowledge items

---

### 5.2 Knowledge Domains

The IIOS defines seven primary knowledge domains. Every knowledge item belongs to exactly one domain.

**Domain 1: MARKET**

The MARKET domain contains all knowledge about how financial markets behave.

| Category | Description |
|---|---|
| MARKET.REGIME | Knowledge about market regimes — their characteristics, transitions, durations, and signals |
| MARKET.PRICE_ACTION | Knowledge about price patterns — breakouts, reversals, consolidations, momentum |
| MARKET.VOLUME | Knowledge about volume patterns and their predictive significance |
| MARKET.OPTIONS | Knowledge about options market dynamics — IV, OI, premium decay, expiry effects |
| MARKET.SECTOR | Knowledge about sector rotation, sector correlation, and sector-relative performance |
| MARKET.MACRO | Knowledge about macro factors — FII flows, budget effects, interest rate sensitivities |
| MARKET.GLOBAL | Knowledge about global market influence — S&P correlation, USD/INR effects, oil sensitivity |
| MARKET.CALENDAR | Knowledge about time-based market effects — expiry, results, budget, holidays |
| MARKET.LIQUIDITY | Knowledge about liquidity conditions and their effects on signal quality |

**Domain 2: STRATEGY**

The STRATEGY domain contains all knowledge about trading strategy behaviour and performance.

| Category | Description |
|---|---|
| STRATEGY.PERFORMANCE | Win rates, Sharpe ratios, drawdown statistics by strategy and regime |
| STRATEGY.ENTRY | Knowledge about entry condition effectiveness |
| STRATEGY.EXIT | Knowledge about exit condition effectiveness |
| STRATEGY.SIZING | Knowledge about position sizing methods and their outcomes |
| STRATEGY.COMBINATION | Knowledge about strategy combinations and their portfolio-level properties |
| STRATEGY.EVOLUTION | Knowledge about how strategy variants perform relative to their parents |
| STRATEGY.FAILURE | Knowledge about how and why strategies fail |
| STRATEGY.RECOVERY | Knowledge about how strategies recover after drawdowns |

**Domain 3: AGENT**

The AGENT domain contains all knowledge about the behaviour and accuracy of the 62 AI debate agents.

| Category | Description |
|---|---|
| AGENT.ACCURACY | Per-agent prediction accuracy by regime, time horizon, and signal type |
| AGENT.BIAS | Systematic biases in agent scoring (over-bullishness, under-weighting risk) |
| AGENT.CALIBRATION | How to weight and adjust agent scores for best ensemble accuracy |
| AGENT.ENSEMBLE | Knowledge about how agent combinations perform as ensembles |
| AGENT.FAILURE | When and why individual agents produce poor-quality opinions |

**Domain 4: SYSTEM**

The SYSTEM domain contains all institutional knowledge about the IIOS's own operational behaviour.

| Category | Description |
|---|---|
| SYSTEM.RELIABILITY | When the system is most and least reliable |
| SYSTEM.LATENCY | Latency patterns and their causes |
| SYSTEM.FEED | Data feed reliability, failover patterns, and quality indicators |
| SYSTEM.DECISION | Decision engine calibration knowledge — when conviction thresholds are appropriate |
| SYSTEM.RISK | Risk system behaviour — kill-switch calibration, position limit effects |
| SYSTEM.LEARNING | How well the learning system is performing |

**Domain 5: RISK**

The RISK domain contains all knowledge about risk management effectiveness.

| Category | Description |
|---|---|
| RISK.POSITION_SIZING | Position sizing method effectiveness by regime and strategy type |
| RISK.STOP_LOSS | Stop-loss placement effectiveness — too tight, too wide, optimal |
| RISK.DRAWDOWN | Drawdown behaviour and recovery patterns |
| RISK.KILL_SWITCH | Kill-switch calibration — false positives, false negatives, thresholds |
| RISK.CORRELATION | Portfolio correlation knowledge — when positions are too correlated |
| RISK.SCENARIO | Monte Carlo and stress test knowledge — which scenarios are most relevant |

**Domain 6: PORTFOLIO**

The PORTFOLIO domain contains all knowledge about portfolio-level behaviour and management.

| Category | Description |
|---|---|
| PORTFOLIO.ALLOCATION | Capital allocation effectiveness by regime and strategy |
| PORTFOLIO.CONCENTRATION | When concentration improves performance vs. when it increases risk |
| PORTFOLIO.DIVERSIFICATION | Optimal diversification levels by market condition |
| PORTFOLIO.REBALANCING | Rebalancing timing and method effectiveness |

**Domain 7: OPERATIONS**

The OPERATIONS domain contains all knowledge about the operational management of the trading system.

| Category | Description |
|---|---|
| OPERATIONS.EXECUTION | Execution quality — slippage, fill rates, timing |
| OPERATIONS.SCHEDULING | Optimal scheduling knowledge — best cycle times, scan intervals |
| OPERATIONS.MAINTENANCE | When maintenance activities cause least disruption |

---

### 5.3 Knowledge Hierarchies

Within each domain and category, knowledge is further organised into levels of specificity:

**Example hierarchy for STRATEGY.PERFORMANCE:**

```
STRATEGY (Domain)
└── PERFORMANCE (Category)
    └── MOMENTUM (Subcategory)
        └── BULL_TRENDING (Context)
            └── ENTRY_ABOVE_20H (Entry method)
                └── SPECIFIC KNOWLEDGE RECORDS
                    └── [KR-001] "MomentumBreakoutV3 win rate 61% in BULL_TRENDING"
                    └── [KR-002] "Momentum entry above 20H has higher R:R than 10H in BULL"
```

**Hierarchy traversal:** A consuming layer can retrieve knowledge at any level of the hierarchy. Querying at `STRATEGY.PERFORMANCE.MOMENTUM` returns all momentum performance knowledge regardless of context. Querying at `STRATEGY.PERFORMANCE.MOMENTUM.BULL_TRENDING` returns only momentum performance knowledge for bull trending markets.

---

### 5.4 Knowledge Taxonomy

The Knowledge Taxonomy is the complete naming system for knowledge classification. Every knowledge item has a taxonomy path that uniquely identifies its position in the domain hierarchy.

**Taxonomy path format:** `{DOMAIN}.{CATEGORY}.{SUBCATEGORY}.{CONTEXT_QUALIFIER}`

**Taxonomy governance rules:**

| Rule | Description |
|---|---|
| No new domain without ADR | Domain creation is a major architectural event |
| Categories must be approved by domain owner | Domain owners control their category structure |
| Taxonomy paths are immutable after assignment | Moving knowledge requires deprecation and re-creation |
| Maximum hierarchy depth: 5 levels | Deeper hierarchies are impractical for retrieval |
| Path separators use `.` only | No `/`, `::`, or other separators |

**Taxonomy anti-patterns:**

| Anti-Pattern | Problem | Correct Alternative |
|---|---|---|
| `MISC` category | Un-classifiable knowledge belongs nowhere | Force correct classification; create new category if needed |
| Knowledge in multiple domains | Knowledge duplication creates consistency problems | One knowledge item, one domain |
| Over-deep hierarchies | `MARKET.PRICE.NSE.NIFTY.LARGE_CAP.MOMENTUM.BULL.MORNING` is unnavigable | Maximum 5 levels |
| Context-in-taxonomy-path | `MARKET.REGIME.BULL.VOLATILE` (context should be in the Context object) | `MARKET.REGIME` + context conditions in Context field |

---

### 5.5 Knowledge Graph

The Knowledge Graph is a directed, weighted graph where:
- **Nodes** are Knowledge Graph Nodes (one per Knowledge Record)
- **Edges** are typed relationships between knowledge items

**Graph design goals:**

| Goal | How Achieved |
|---|---|
| Discover related knowledge | Graph traversal from any starting node |
| Identify knowledge dependencies | Follow `REQUIRES` and `ASSUMES` edges |
| Find contradicting knowledge | Follow `CONTRADICTS` edges |
| Understand knowledge lineage | Follow `DERIVED_FROM` edges |
| Identify high-value knowledge | Use centrality scores |
| Find knowledge clusters | Community detection algorithm on the graph |

**Graph properties:**

| Property | Value |
|---|---|
| Graph type | Directed, weighted, typed |
| Node count | Grows with knowledge base (expected 1,000–10,000 nodes after 1 year) |
| Edge types | 8 defined relationship types |
| Self-loops | Not permitted (knowledge cannot support itself) |
| Maximum edge weight | 1.0 (minimum 0.0) |
| Weight meaning | Strength of the relationship |
| Update frequency | On every knowledge creation, version update, or deprecation |

---

### 5.6 Knowledge Clusters

Clusters group related knowledge items for efficient retrieval and analysis.

**Cluster formation algorithm:**

```
Step 1: Compute pairwise semantic similarity for all knowledge items in the same domain
Step 2: Build a similarity graph (edge weight = semantic similarity)
Step 3: Apply community detection to identify natural clusters
Step 4: Assign names to clusters based on their most central node's taxonomy path
Step 5: Compute coherence score for each cluster
Step 6: Assign each knowledge item to its primary cluster and up to 2 secondary clusters
```

**Cluster maintenance:** Clusters are re-computed weekly (Sunday 02:00 IST). New knowledge items are tentatively assigned to the nearest existing cluster between re-computations.

**Cluster use cases:**

| Use Case | How Clusters Enable It |
|---|---|
| "Tell me everything about momentum in bull markets" | Single cluster retrieval |
| "What do we know about Thursday effects?" | Single cluster retrieval |
| "Summarise the knowledge for this strategy" | Retrieve by strategy_id across relevant clusters |
| Knowledge coverage audit | Review which clusters have sufficient/insufficient depth |
| Knowledge gap identification | Clusters with very few members or low coherence indicate gaps |

---

### 5.7 Knowledge Dependencies

Dependencies between knowledge items create a directed acyclic graph (DAG) of logical relationships.

**Dependency management rules:**

| Rule | Description |
|---|---|
| No circular dependencies | Detected and prevented by the Knowledge Graph Service |
| Dependency confidence propagation | If parent confidence drops significantly, child's confidence is recalculated |
| Dependency deprecation cascade | Deprecating a widely-depended-upon item triggers impact analysis before proceeding |
| Dependency validation | A derived knowledge item cannot be created unless all its dependencies are VALIDATED |

**Dependency impact analysis:**

When a knowledge item is scheduled for deprecation, the Knowledge Governance Service performs an impact analysis:
1. Find all knowledge items that declare a `REQUIRES` or `ASSUMES` dependency on this item
2. For each dependent: compute expected confidence after parent deprecation
3. If any dependent's projected confidence would fall below 0.40: escalate to Human Principal
4. If no dependents would be critically affected: proceed with deprecation

---

### 5.8 Knowledge Traceability

Every knowledge item can be traced:
- **Forward:** What knowledge was derived from this item? What decisions used this item?
- **Backward:** What evidence supported this item? What raw observations underlie the evidence?

**Traceability chain:**

```
Raw Market Observation (NIFTY bar, VIX reading, option OI)
      │
      ▼
Knowledge Evidence Record (specific observation that supports a claim)
      │
      ▼
Knowledge Record (the validated claim)
      │
      ▼
Knowledge Graph Node (the claim in the network context)
      │
      ▼
Decision Context (the knowledge used in a specific cycle's decision)
      │
      ▼
Trade Outcome (what happened when the decision was acted upon)
      │
      ▼
Learning Event (the outcome fed back to update knowledge confidence)
```

**Full traceability requirement (Constitution rule KC-C-07):** For any knowledge item used in any decision, a complete traceability chain from raw observations to trade outcome must be accessible via the Knowledge Engine's traceability API. This is not optional — it is a governance requirement.

---

### 5.9 Knowledge Network

The Knowledge Network is the complete interconnected structure of all knowledge in the IIOS — domains, categories, clusters, graph, and dependencies viewed as a unified whole.

**Network health metrics:**

| Metric | Description | Target |
|---|---|---|
| Total knowledge items | Count of VALIDATED or DEPRECATED items | Growing |
| Network density | Edges per node | ≥ 3 (well-connected) |
| Knowledge coverage | Domains with ≥ 10 validated items | All 7 domains |
| Isolated nodes | Knowledge items with no graph connections | 0 (every item is connected) |
| Average confidence | Mean confidence across all VALIDATED items | ≥ 0.65 |
| Stale items | Items not updated in > 90 days | < 10% of total |
| Contradiction count | Items with CONTRADICTS edges to other VALIDATED items | 0 (all contradictions resolved) |
| Coverage depth | Average hierarchy depth | 3–5 levels |

---

## PART VI — KNOWLEDGE SERVICES

### 6.1 Service Architecture Overview

The Knowledge Engine is implemented as a collection of 10 specialised services. Each service has a single responsibility, a defined interface, and a governance role. No service directly accesses another service's database — they communicate via the Knowledge Engine API.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE ENGINE SERVICES                                │
│                                                                              │
│  External inputs:                                                            │
│  LearningEngine, MarketIntelligence, StrategyLab, ValidationEngine          │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────┐   ┌────────────────────┐   ┌───────────────────────┐  │
│  │  Discovery      │   │   Validation        │   │   Classification      │  │
│  │  Service        │──>│   Service          │──>│   Service             │  │
│  └─────────────────┘   └────────────────────┘   └───────────┬───────────┘  │
│                                                              │               │
│  ┌──────────────────────────────────────────────────────────▼───────────┐  │
│  │                    Knowledge Store (knowledge.db)                      │  │
│  └──────────────────────────────────────────────────────────┬───────────┘  │
│                                                              │               │
│  ┌─────────────────┐   ┌────────────────────┐   ┌───────────▼───────────┐  │
│  │  Search         │   │   Retrieval         │   │   Graph               │  │
│  │  Service        │   │   Service          │   │   Service             │  │
│  └──────┬──────────┘   └─────────┬──────────┘   └───────────────────────┘  │
│         │                        │                                           │
│  ┌──────▼──────────────────────────────────────────────────────────────┐   │
│  │               Consuming layers (MetaLearning, StrategyLab, etc.)    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────┐   ┌────────────────────┐   ┌───────────────────────┐  │
│  │  Evolution      │   │   Version           │   │   Analytics           │  │
│  │  Service        │   │   Service          │   │   Service             │  │
│  └─────────────────┘   └────────────────────┘   └───────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Governance Service                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 6.2 Knowledge Discovery Service

**Purpose:** Monitor all incoming data streams, learning outputs, and system events to identify candidate knowledge items.

**Inputs:**

| Input Source | Input Type | What Is Monitored |
|---|---|---|
| LearningEngine | Trade outcome batches | Statistical patterns in win rates, P&L distributions |
| ValidationEngine | Walk-forward test results | Out-of-sample patterns and anomalies |
| MarketIntelligence | Regime history | Regime transition patterns, regime duration distributions |
| StrategyLab | Evolution run outputs | Parameter sensitivity patterns |
| ControlTower | System health logs | Operational behaviour patterns |
| Human Principal | Manual submissions | Manually asserted knowledge |

**Discovery methods:**

| Method | Description | Produces |
|---|---|---|
| Frequency analysis | Count occurrences of event types in historical records | Fact candidates |
| Correlation detection | Compute correlations between observable features and outcomes | Pattern candidates |
| Anomaly detection | Identify statistically unusual events | Behavioral candidates |
| Comparative analysis | Compare performance across conditions | Contextual candidates |
| Regression analysis | Identify stable predictive relationships | Predictive candidates |
| Manual submission | Human Principal submits knowledge directly | Rule candidates |

**Outputs:** A stream of `KnowledgeCandidate` objects, each containing: a draft claim, preliminary evidence references, estimated confidence, and the discovery method used.

**Failure handling:** If a discovery run fails (data unavailable, computation timeout), the run is retried on the next EOD cycle. Partial runs are not submitted — the Knowledge Validation Service only receives complete candidate packages. If discovery fails 3 consecutive times for the same domain, a WARNING alert is sent.

**Consumers:** Knowledge Validation Service

---

### 6.3 Knowledge Validation Service

**Purpose:** Apply the 6-step validation process to every candidate knowledge item and make the VALIDATED / REJECTED / HOLD decision.

**Inputs:** `KnowledgeCandidate` objects from the Discovery Service

**Validation pipeline:**

| Step | Validator | Threshold | Failure Action |
|---|---|---|---|
| Evidence volume | `EvidenceVolumeValidator` | ≥ 30 observations | REJECT |
| Time span | `TimeSpanValidator` | ≥ 90 trading days | REJECT |
| Consistency | `ConsistencyValidator` | ≥ 60% qualifying conditions | REJECT |
| Confidence floor | `ConfidenceValidator` | ≥ 0.55 | REJECT |
| Contradiction check | `ContradictionDetector` | No conflict with HIGH-confidence items | HOLD |
| Context qualification | `ContextValidator` | ≥ 1 regime or context condition | REJECT |

**Override rules:**
- Human Principal can submit a Rule-type candidate that bypasses the statistical thresholds
- Human Principal override is logged to AuditService and requires explicit `is_inviolable=True` flag

**Outputs:** Validated Knowledge Candidates → Knowledge Classification Service
- REJECTED candidates → Candidate Archive with rejection reason
- HOLD candidates → Governance Service queue

**Dependencies:** Knowledge Store (for contradiction checking), Evidence Store, AuditService

**Failure handling:**
- Contradiction detection failure (knowledge store unreachable): defer to next run
- Validator computation error: log ERROR, skip this candidate, retry in next batch
- Persistent validation service failure: alert via Telegram (CRITICAL)

---

### 6.4 Knowledge Classification Service

**Purpose:** Assign validated knowledge to its correct position in the taxonomy, connect it to the knowledge graph, and assign it to a cluster.

**Inputs:** Validated `KnowledgeCandidate` from the Validation Service

**Classification steps:**

| Step | Method | Output |
|---|---|---|
| Domain assignment | Rule-based matching on claim content and evidence sources | Domain (one of 7) |
| Category assignment | Domain-specific classification rules | Category |
| Subcategory assignment | Subcategory rule set or domain owner override | Subcategory |
| Knowledge level assignment | Evidence type and abstraction analysis | Level 1–10 |
| Context qualification | Extract regime, time, and market condition qualifiers | Context object |
| Graph edge identification | Find related knowledge items for graph connection | Edge list |
| Cluster assignment | Semantic similarity to existing cluster centroids | Primary cluster |
| Search index generation | Extract keywords and semantic tags | Search index entries |

**Outputs:** Fully classified Knowledge Records ready for storage

**Consumers:** Knowledge Storage (via KnowledgeRepository), Knowledge Graph Service

**Failure handling:**
- Unknown domain: escalate to Knowledge Governance Service for human classification
- Graph edge conflict (would create circular dependency): reject edge, log conflict
- Cluster assignment failure: assign to DEFAULT cluster pending next re-clustering

---

### 6.5 Knowledge Search Service

**Purpose:** Enable full-text, semantic, and structured retrieval of knowledge by any consuming layer or research process.

**Inputs:**

| Input Type | Description |
|---|---|
| `TextQuery` | Free-text search string |
| `StructuredQuery` | Typed query with field filters (domain, category, confidence_min) |
| `ContextQuery` | Current market state — returns knowledge relevant to this context |
| `GraphQuery` | Start node + relationship types + depth |
| `ClusterQuery` | Cluster ID — return all items in cluster |

**Search methods:**

| Method | Engine | Use Case |
|---|---|---|
| Full-text search | SQLite FTS5 | "What do we know about expiry effects?" |
| Structured field query | KnowledgeRepository.find_where() | "All VALIDATED patterns in MARKET.REGIME with confidence > 0.70" |
| Context matching | Context similarity scoring | "Knowledge relevant to current BULL_TRENDING, HIGH_VIX state" |
| Graph traversal | In-memory graph traversal | "What knowledge supports or contradicts this item?" |
| Semantic similarity | Embedding-based ranking | "Knowledge similar to this description" |

**Outputs:** `KnowledgeQueryResult` containing ranked, confidence-annotated Knowledge Records

**Caching:** Context queries are cached per cognitive cycle (same `QueryContext` → cached result for the cycle duration). Text and structured queries are cached with a 60-second TTL.

**Dependencies:** Knowledge Store, Knowledge Graph, in-memory TTL cache

**Failure handling:**
- FTS5 index not available: fall back to LIKE-based search (slower but functional)
- Graph traversal cycles detected: cap depth at 10, return partial results
- Search timeout (> 2,000ms): return cached or partial results, log WARNING

**Consumers:** All 17 IIOS layers, Streamlit dashboard, research tools

---

### 6.6 Knowledge Retrieval Service

**Purpose:** Provide the primary programmatic interface for consuming layers to access specific knowledge items by known ID, type, or context.

**Inputs:**

| Method | Input | Description |
|---|---|---|
| `get` | `knowledge_id: str` | Direct ID lookup |
| `get_current` | `knowledge_id: str` | Latest version of a knowledge item |
| `get_version` | `knowledge_id: str, version: int` | Specific historical version |
| `find_by_context` | `QueryContext` | Context-matched retrieval |
| `find_by_type` | `KnowledgeType, domain` | All items of a type in a domain |
| `find_cluster` | `cluster_id: str` | All items in a cluster |
| `find_relevant_for_strategy` | `strategy_id: str, context: QueryContext` | Strategy-specific knowledge |
| `find_relevant_for_decision` | `hypothesis_id: str, context: QueryContext` | Decision-specific knowledge |
| `find_dependencies` | `knowledge_id: str` | All dependencies of a knowledge item |
| `find_dependents` | `knowledge_id: str` | All items that depend on this item |

**Retrieval result enrichment:** The Retrieval Service enriches results with:
- Freshness indicator (how recently updated)
- Relevance score (how well it matches the query context)
- Usage frequency (how often this item is retrieved)
- Confidence trajectory (is confidence trending up or down?)

**Consumers:** All 17 IIOS layers (primarily L3 MetaLearning, L5 StrategyLab, L10 DebateAndDecision)

**Dependencies:** Knowledge Store, Knowledge Graph, Search Service (for context matching), TTL Cache

**Performance target:** < 50ms for cached context queries; < 200ms for cold database queries

**Failure handling:**
- Cache miss + database timeout: return last cached result with STALE flag
- Requested version not found: raise `KnowledgeVersionNotFoundError`
- Context matching computation timeout: return top-10 by recency with reduced relevance scoring

---

### 6.7 Knowledge Evolution Service

**Purpose:** Monitor knowledge quality signals and trigger knowledge evolution when confidence or context conditions change significantly.

**Inputs:**

| Input | Source | Frequency |
|---|---|---|
| Closed trade outcomes | TradeMonitor | EOD batch |
| Walk-forward test results | ValidationEngine | Weekly |
| Regime change events | MarketIntelligence | On regime change |
| Agent calibration updates | LearningEngine | EOD batch |
| Strategy performance updates | StrategyPerformanceTracker | EOD batch |

**Evolution pipeline:**

```
Step 1: Receive learning batch (trade outcomes, test results)
Step 2: For each knowledge item referenced in the batch:
    2a: Add new evidence records to Evidence Store
    2b: Recompute confidence score using updated evidence
    2c: Compare new confidence to previous confidence
    2d: If delta > 0.05 OR context changed: trigger evolution
Step 3: For each triggered evolution:
    3a: Create new Knowledge Version with updated values
    3b: Update Knowledge Graph node properties (confidence, recency)
    3c: Update cluster coherence scores
    3d: Propagate confidence delta to dependent knowledge items
    3e: Check if new confidence falls below deprecation threshold
    3f: If below threshold: initiate deprecation review
Step 4: Log all evolutions to AuditService
Step 5: Emit KNOWLEDGE_EVOLVED events to EventBus for consuming layers
```

**Consumers:** Knowledge Store (writes), Knowledge Governance Service (deprecation escalations), EventBus (evolution notifications)

**Dependencies:** Knowledge Store, Evidence Store, LearningRepository, AuditService

**Failure handling:**
- Evidence batch processing error: skip the failed item, log ERROR, continue batch
- Confidence computation overflow: cap at 1.0, log WARNING
- Dependency propagation cycle (should be impossible with DAG enforcement): log CRITICAL, stop propagation

---

### 6.8 Knowledge Version Service

**Purpose:** Manage the complete version history of all knowledge items and provide version comparison, diff, and rollback capabilities.

**Inputs:**

| Operation | Initiator | Description |
|---|---|---|
| Create version | Evolution Service | New version on evolution |
| Deprecate version | Governance Service | Mark version as superseded |
| Query version history | Any service | Return all versions of a knowledge item |
| Diff versions | Research / Governance | Compare two versions |
| Rollback | Human Principal | Restore a previous version as current |

**Version diff output (KnowledgeDiff):**

```
KnowledgeDiff {
  knowledge_id: "uuid-1234...",
  version_from: 3,
  version_to: 4,
  changed_at: "2026-07-02T16:00:00Z",
  changed_by: "KnowledgeEvolutionService",
  changes: [
    {field: "confidence_score", from: 0.62, to: 0.71, change_reason: "NEW_EVIDENCE"},
    {field: "evidence_ids", added: ["ev-789..."], removed: [], count_delta: +5},
    {field: "context_conditions", from: {"regime": "BULL"}, to: {"regime": ["BULL", "TREND"], "volatility_state": "LOW_MEDIUM"}}
  ]
}
```

**Version rollback:** Rollback creates a new version that has the same values as the specified historical version. The rolled-back version is not deleted — the rollback creates a new version pointing backward. Rollback requires Human Principal authorisation and is audited.

**Consumers:** Knowledge Governance Service, Research tools, Human Principal

---

### 6.9 Knowledge Graph Service

**Purpose:** Maintain the knowledge graph, compute graph metrics, and answer graph-based queries.

**Graph operations:**

| Operation | Description |
|---|---|
| `add_node(knowledge_id)` | Register a new Knowledge Record as a graph node |
| `add_edge(from_id, to_id, edge_type, weight)` | Add a typed, weighted relationship |
| `remove_node(knowledge_id)` | Mark a node as deprecated (edges remain for historical queries) |
| `get_neighbours(node_id, edge_types, depth)` | Graph traversal |
| `get_path(from_id, to_id)` | Shortest path between two knowledge items |
| `compute_centrality()` | Recompute centrality scores for all nodes |
| `detect_communities()` | Re-run community detection for cluster update |
| `find_contradictions()` | Return all pairs of nodes with CONTRADICTS edges |
| `get_dependency_chain(node_id)` | Complete dependency DAG for a node |

**Graph integrity rules:**

| Rule | Description |
|---|---|
| No self-loops | Detected and rejected on edge addition |
| No circular `DERIVED_FROM` chains | Detected using DFS before edge addition |
| Consistent edge types | Edge types are enforced from the 8-type vocabulary |
| Deprecated nodes persist | Deprecated nodes are marked but not removed — history preserved |

**Performance:** The Knowledge Graph is maintained in memory during operation and persisted to `knowledge.db` on every update. Graph traversals run in-memory with O(V+E) complexity. For graphs up to 10,000 nodes, this is well within the 200ms retrieval target.

**Consumers:** Knowledge Classification Service, Knowledge Retrieval Service, Knowledge Analytics Service, Knowledge Governance Service

---

### 6.10 Knowledge Analytics Service

**Purpose:** Generate analytics and insights about the knowledge base itself — coverage, health, trends, and gaps.

**Analytics outputs:**

| Report | Frequency | Description |
|---|---|---|
| Knowledge coverage report | Weekly | Which domains have deep vs. thin coverage |
| Confidence trend report | Weekly | Which knowledge items are improving vs. degrading |
| Knowledge staleness report | Weekly | Items not updated in > 90 days |
| Contradiction report | Daily | Any new CONTRADICTS edges in the graph |
| Knowledge growth report | Monthly | New validated items per domain per month |
| Usage analysis report | Monthly | Most/least retrieved knowledge items |
| Gap analysis report | Monthly | Domains or categories with no knowledge items |
| Evolution velocity report | Monthly | How quickly is the knowledge base improving? |

**Meta knowledge production:** The Analytics Service is the primary producer of Level 10 (Meta Knowledge). Its reports are written back to the knowledge base as Meta Knowledge Records.

**Consumers:** ControlTower (L17), Human Principal (via Telegram), Streamlit dashboard

**Failure handling:**
- Analytics job failure: log ERROR, skip report, retry next scheduled run
- Missing domain data: produce partial report with explicit data-missing notation

---

### 6.11 Knowledge Governance Service

**Purpose:** Enforce knowledge quality standards, manage ownership, handle conflict resolution, and oversee deprecation.

**Governance responsibilities:**

| Responsibility | Mechanism |
|---|---|
| Quality gate enforcement | Monitor confidence scores; alert when items fall below thresholds |
| Ownership management | Track owner assignments; alert on ownerless knowledge |
| Conflict resolution | Manage VALIDATION_HOLD items; escalate to Human Principal |
| Deprecation review | Review deprecation candidates; manage 7-day review window |
| Access policy enforcement | Validate that only authorised services write knowledge |
| Knowledge freshness | Trigger freshness review for items not updated in > 90 days |
| Rule integrity | Verify that inviolable Rules are not being contradicted by patterns |
| Audit generation | Produce weekly governance summary for Human Principal |

**Governance escalation ladder:**

```
Level 1: Automated (Knowledge Governance Service)
├── Confidence alert (< 0.55): log + metric
├── Stale knowledge: freshness trigger
└── Contradiction detected: initiate hold review

Level 2: Telegram alert (Human Principal attention required)
├── Multiple items falling below 0.40: CRITICAL alert
├── Inviolable Rule being contradicted: CRITICAL alert
└── Deprecation of high-centrality item: WARNING alert

Level 3: Human Principal decision required
├── Unresolvable contradiction between HIGH-confidence items
├── Rollback of knowledge version
└── Override of validation failure for Rule-type knowledge
```

**Consumers:** All other Knowledge Services (governance receives escalations from all), Human Principal

---
## PART VII — KNOWLEDGE QUALITY

### 7.1 Quality Philosophy

Knowledge quality is not a post-hoc measurement — it is a design constraint that is enforced at every stage of the knowledge lifecycle. A knowledge base that accepts low-quality knowledge without governance is worse than no knowledge base: it gives the system false confidence and leads to systematic decision errors.

The IIOS Knowledge Quality Framework defines 10 quality dimensions, a composite scoring model, and a complete set of quality metrics. Every knowledge item is scored on all 10 dimensions, and the scores are used to govern what knowledge can be consumed, and with what weight.

---

### 7.2 Quality Dimension 1 — Accuracy

**Definition:** Accuracy measures how well the knowledge claim describes actual market reality. An accurate knowledge claim makes predictions that are confirmed by observed outcomes.

**Accuracy measurement:**

| Method | Description |
|---|---|
| Backtesting accuracy | How often did this pattern correctly predict outcomes on historical data? |
| Walk-forward accuracy | How often did this pattern correctly predict outcomes on out-of-sample data? |
| Live/paper trading accuracy | How often did this pattern correctly predict outcomes in real-time trading? |
| Cross-validation | Does the pattern hold consistently across different validation windows? |

**Accuracy scoring:**

| Accuracy Value | Score | Interpretation |
|---|---|---|
| ≥ 0.75 | 1.0 | Highly accurate |
| 0.65 – 0.75 | 0.8 | Accurate |
| 0.55 – 0.65 | 0.6 | Moderately accurate |
| 0.45 – 0.55 | 0.3 | Below accuracy floor (needs validation review) |
| < 0.45 | 0.0 | Inaccurate — deprecation candidate |

**Accuracy decay:** Accuracy degrades over time as markets evolve. The Knowledge Engine applies an accuracy decay model: if a knowledge item has not received new supporting evidence in > 90 days, its accuracy score is discounted by 10% per subsequent 30-day period (up to a maximum 50% discount, after which a freshness review is triggered).

---

### 7.3 Quality Dimension 2 — Completeness

**Definition:** Completeness measures whether a knowledge claim is fully specified — whether all necessary context conditions, qualifications, and caveats are present.

**Completeness checklist:**

| Completeness Requirement | Present? |
|---|---|
| At least one regime context condition | ✓ or ✗ |
| Time horizon specified (intraday / daily / weekly) | ✓ or ✗ |
| Evidence volume stated | ✓ or ✗ |
| Confidence score present | ✓ or ✗ |
| Claim is testable (not vague or circular) | ✓ or ✗ |
| Exceptions or counter-conditions documented | ✓ or ✗ |
| Failure mode documented (when does this not hold?) | ✓ or ✗ |

**Completeness scoring:** `completeness_score = items_present / total_items`

A knowledge item with completeness < 0.70 cannot be used in high-stakes decisions (position sizing, kill-switch thresholds). It is flagged for review by the Knowledge Governance Service.

---

### 7.4 Quality Dimension 3 — Consistency

**Definition:** Consistency measures whether the knowledge claim holds uniformly across all conditions where it is claimed to apply, and whether it is free from contradiction with other validated knowledge.

**Consistency types:**

| Consistency Type | Description |
|---|---|
| Internal consistency | The claim does not contradict itself |
| Cross-evidence consistency | All supporting evidence items point in the same direction |
| Cross-regime consistency | The pattern holds in all claimed regimes (not just the most favourable) |
| Cross-timeframe consistency | The pattern holds at all claimed time resolutions |
| Cross-knowledge consistency | The claim does not contradict other validated HIGH-confidence knowledge |

**Consistency scoring:** Each type contributes equally (0.20 each). Total consistency score = sum of scores across all 5 types.

**Inconsistency response:**
- Minor inconsistency (1 type failing): log, update context conditions to exclude the inconsistent regime
- Moderate inconsistency (2 types failing): trigger confidence review
- Major inconsistency (3+ types failing): initiate deprecation review

---

### 7.5 Quality Dimension 4 — Freshness

**Definition:** Freshness measures how recently the knowledge item was last validated or updated with new evidence.

**Freshness calculation:**

```
days_since_last_evidence = (today - last_evidence_date).days
freshness_score = max(0.0, 1.0 - (days_since_last_evidence / 180))
```

This gives a score of 1.0 for knowledge updated today and 0.0 for knowledge not updated in 180+ days.

**Freshness thresholds:**

| Days Since Last Evidence | Freshness Score | Action |
|---|---|---|
| 0 – 30 | 0.83 – 1.0 | No action required |
| 30 – 90 | 0.50 – 0.83 | Monitor — scheduled for next evidence batch |
| 90 – 180 | 0.0 – 0.50 | Freshness alert — prioritise in next discovery run |
| > 180 | 0.0 (floor) | Stale — governance review triggered |

**Freshness exception:** Reference data (market calendar, sector classification) and inviolable Rules do not have freshness requirements. They are exempt from freshness scoring.

---

### 7.6 Quality Dimension 5 — Reliability

**Definition:** Reliability measures the stability of knowledge performance across different market conditions, strategies, and time periods. A reliable knowledge item performs consistently — not just in ideal conditions.

**Reliability vs. accuracy:** A knowledge item can be accurate on average but unreliable if its accuracy varies wildly between regimes. Reliability penalises high variance.

**Reliability scoring:**

```
reliability_score = accuracy_mean / (1 + accuracy_standard_deviation)
```

A knowledge item with accuracy 0.65 ± 0.05 has a reliability score of 0.65 / 1.05 = 0.619.
A knowledge item with accuracy 0.65 ± 0.25 has a reliability score of 0.65 / 1.25 = 0.520.

The high-variance item is less reliable, even though it has the same mean accuracy.

---

### 7.7 Quality Dimension 6 — Confidence

**Definition:** Confidence is the probabilistic assessment of how likely the knowledge claim is to be accurate in the next qualifying situation. It is the composite of all evidence-based signals.

This dimension is described in full in Section 3.10 (Knowledge Confidence object). As a quality dimension, confidence is measured and scored directly from the Knowledge Confidence object's `final_confidence` field.

| Confidence | Quality Score |
|---|---|
| ≥ 0.85 | 1.0 |
| 0.70 – 0.85 | 0.8 |
| 0.55 – 0.70 | 0.6 |
| 0.40 – 0.55 | 0.3 |
| < 0.40 | 0.0 |

---

### 7.8 Quality Dimension 7 — Explainability

**Definition:** Explainability measures how clearly the knowledge claim can be explained to a human — whether the underlying mechanism is understood, not just the observed correlation.

**Why explainability matters:** A knowledge item that says "NIFTY tends to move up in the first 20 minutes of trading" is less explainable (observed pattern, mechanism unclear) than one that says "NIFTY tends to move up in the first 20 minutes due to overnight foreign institutional buy orders clearing through the open — this effect is strongest when FII net position is positive and when S&P overnight return is positive."

More explainable knowledge is more trustworthy and more robust to regime changes — if the mechanism is understood, it is possible to predict when the pattern will hold and when it won't.

**Explainability scoring:**

| Explainability Level | Score | Criterion |
|---|---|---|
| Full | 1.0 | Mechanism is understood and documented |
| Partial | 0.7 | Plausible mechanism exists and is documented |
| Structural | 0.5 | Mechanism can be hypothesised from market structure |
| Empirical | 0.3 | Pattern is observed but no mechanism is proposed |
| Unknown | 0.1 | No attempt to explain the mechanism |

---

### 7.9 Quality Dimension 8 — Traceability

**Definition:** Traceability measures how completely the knowledge item's lineage is documented — from raw observations to validated claim.

**Traceability requirements:**

| Requirement | Weight |
|---|---|
| Complete evidence record list (all evidence IDs present) | 0.30 |
| Complete lineage record (discovery method, service, timestamp) | 0.25 |
| Complete version history (no version gaps) | 0.20 |
| Complete derivation trace (for derived knowledge) | 0.15 |
| Graph connection to at least one related node | 0.10 |

**Traceability score:** Weighted sum of requirements met.

**Non-negotiable:** A knowledge item with traceability score = 0.0 (no evidence, no lineage) cannot exist. This is a creation-time validation rule.

---

### 7.10 Quality Dimension 9 — Reproducibility

**Definition:** Reproducibility measures whether the validation process that created this knowledge item can be repeated and would produce the same result.

**Reproducibility checklist:**

| Requirement | Description |
|---|---|
| Evidence is preserved | All evidence records used in validation are still accessible |
| Validation method is documented | The exact validation process is recorded |
| Data sources are identified | The market data used for validation is in the historical database |
| Validation parameters are recorded | Evidence thresholds, confidence formula, weights used |
| Re-validation produces same result | Running the validation process again yields same confidence ± 0.05 |

**Reproducibility score:** 0.20 per requirement met. A score < 0.60 requires investigation.

---

### 7.11 Quality Dimension 10 — Auditability

**Definition:** Auditability measures whether the complete history of the knowledge item — creation, evolution, usage, and deprecation — can be retrieved and verified by an auditor.

**Auditability requirements:**

| Requirement | Score Contribution |
|---|---|
| Creation audit event exists in AuditService | 0.20 |
| Every version change has an audit event | 0.20 |
| Every deprecation has an audit event | 0.10 |
| Every governance review has an audit record | 0.20 |
| All usage in decisions is traceable via cycle_id | 0.20 |
| All trade outcomes linked back to contributing knowledge | 0.10 |

---

### 7.12 Composite Quality Score

**Formula:**

```
quality_score = (
    w_accuracy       × accuracy_score       +
    w_completeness   × completeness_score   +
    w_consistency    × consistency_score    +
    w_freshness      × freshness_score      +
    w_reliability    × reliability_score    +
    w_confidence     × confidence_score     +
    w_explainability × explainability_score +
    w_traceability   × traceability_score   +
    w_reproducibility× reproducibility_score+
    w_auditability   × auditability_score
)
```

**Weights:**

| Dimension | Weight |
|---|---|
| Accuracy | 0.20 |
| Confidence | 0.18 |
| Consistency | 0.12 |
| Reliability | 0.12 |
| Traceability | 0.10 |
| Completeness | 0.10 |
| Freshness | 0.08 |
| Auditability | 0.05 |
| Explainability | 0.03 |
| Reproducibility | 0.02 |
| **Total** | **1.00** |

**Quality score interpretation:**

| Quality Score | Label | Usage Policy |
|---|---|---|
| 0.85 – 1.00 | EXCELLENT | Use without restriction |
| 0.70 – 0.85 | GOOD | Use confidently |
| 0.55 – 0.70 | ACCEPTABLE | Use with confidence caveats |
| 0.40 – 0.55 | MARGINAL | Use only in low-stakes contexts |
| < 0.40 | POOR | Do not use; initiate review |

---

### 7.13 Quality Metrics

**Metrics reported by the Knowledge Analytics Service:**

| Metric | Formula | Target |
|---|---|---|
| Mean quality score | Mean of all VALIDATED items' quality scores | ≥ 0.70 |
| Quality distribution P25/P50/P75 | Percentile breakdown | P25 ≥ 0.55 |
| Items below POOR threshold | Count with score < 0.40 | 0 |
| Stale items percentage | % of items with freshness = 0.0 | < 5% |
| Un-explained items | Count with explainability < 0.30 | < 10% |
| Incomplete items | Count with completeness < 0.70 | < 5% |
| Non-traceable items | Count with traceability < 0.60 | 0 |
| Inconsistent items | Count with consistency < 0.60 | 0 |
| Average confidence | Mean confidence score | ≥ 0.65 |
| Knowledge confidence trend | 30-day rolling mean confidence | Positive or flat |

---

## PART VIII — KNOWLEDGE GOVERNANCE

### 8.1 Governance Framework

Knowledge Governance is the set of policies, processes, and controls that ensure the knowledge base remains accurate, trustworthy, and useful. Without governance, knowledge bases degrade: stale knowledge accumulates, contradictions go unresolved, and low-quality claims influence high-stakes decisions.

The Knowledge Governance Framework has eight pillars:

```
┌─────────────────────────────────────────────────────────────────────┐
│                KNOWLEDGE GOVERNANCE FRAMEWORK                        │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  OWNERSHIP   │  │  APPROVAL    │  │      VERSIONING          │  │
│  │  Who owns?   │  │  Who allows? │  │  How does it change?     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   REVIEW     │  │  EVOLUTION   │  │      DEPRECATION         │  │
│  │  How often?  │  │  How improves│  │  When to retire?         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐                               │
│  │COMPATIBILITY │  │   SECURITY   │                               │
│  │How compatible│  │  Who accesses│                               │
│  └──────────────┘  └──────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 8.2 Ownership

**Every knowledge item has exactly one owner.** Ownership is assigned at creation time and cannot be unilaterally changed.

**Ownership levels:**

| Level | Owner Type | What They Own |
|---|---|---|
| L1 — Service owner | Creating service | Specific knowledge items it created |
| L2 — Domain owner | Domain's primary engine | All knowledge in the domain |
| L3 — Governance reviewer | KnowledgeGovernanceService | Governance process for all items |
| L4 — Human Principal | Human Principal | All inviolable Rules; can override any decision |

**Ownership matrix:**

| Domain | Domain Owner | Service Owners |
|---|---|---|
| MARKET | MarketIntelligence | GlobalDataAI, MarketMonitor |
| STRATEGY | StrategyLab | MetaStrategyController, StrategyGenerator |
| AGENT | LearningEngine | AgentCalibrator |
| SYSTEM | ControlTower | SystemMonitor, DiagnosticsService |
| RISK | RiskGuardian | RiskManagerAI, PortfolioAllocation |
| PORTFOLIO | TradeMonitor | OrderManager |
| OPERATIONS | MasterOrchestrator | DataFeedManager |

**Ownership transfer:** Ownership transfer requires Governance Service approval. If a service is retired, its knowledge is transferred to the domain owner before the service is decommissioned.

---

### 8.3 Approval Policy

Knowledge items require approval at different levels based on their type and potential impact:

| Knowledge Type | Approval Required | Approver |
|---|---|---|
| Raw Knowledge (Level 1) | None | Automatic creation |
| Validated Knowledge (Levels 2–4) | Automated validation pass | KnowledgeValidationService |
| Derived Knowledge (Level 3) | Source knowledge must be VALIDATED | Automated check |
| Behavioral Knowledge (Level 6) | Domain owner review | Domain owner service |
| Strategic Knowledge (Level 7) | Human Principal | Human Principal |
| Inviolable Rule | Human Principal explicit approval | Human Principal |
| Knowledge override (validation bypass) | Human Principal | Human Principal |
| Knowledge deprecation (high-centrality) | Human Principal | Human Principal |
| Knowledge rollback | Human Principal | Human Principal |

**Approval audit trail:** Every approval decision is written to AuditService with: the approver's identity, the approval timestamp, the approval reason, and the knowledge item's state at the time of approval.

---

### 8.4 Review Policy

**Scheduled reviews:**

| Review Type | Frequency | Reviewer | Scope |
|---|---|---|---|
| Quality review | Weekly | KnowledgeGovernanceService | Items with quality score < 0.60 |
| Freshness review | Weekly | KnowledgeGovernanceService | Items not updated in > 90 days |
| Contradiction review | Daily | KnowledgeGovernanceService | Items with CONTRADICTS edges |
| Coverage review | Monthly | Human Principal | Domain coverage gaps |
| Strategic knowledge review | Quarterly | Human Principal | Level 7–9 knowledge items |
| Full knowledge audit | Annual | Human Principal | Complete knowledge base |

**Review outcome options:**

| Outcome | Description | Action |
|---|---|---|
| No action | Knowledge is sound | Record review completion in audit |
| Update required | Minor inaccuracies or missing context | Evolution Service triggered |
| Deprecation recommended | Knowledge is no longer reliable | Deprecation review initiated |
| Rule revision | Safety rule needs updating | Human Principal ADR required |

---

### 8.5 Evolution Governance

Evolution of knowledge is governed by defined thresholds and approval rules:

| Evolution Type | Automatic? | Approval? |
|---|---|---|
| Confidence update (delta < 0.05) | Yes | None |
| Confidence update (delta ≥ 0.05) | Yes | Domain owner notification |
| Context condition update | Yes | Domain owner notification |
| Claim text refinement | No | Domain owner approval |
| Claim text change (substantive) | No | Human Principal approval |
| Confidence drop below 0.55 | Yes (with alert) | Governance alert + 7-day review |
| Confidence drop below 0.40 | Yes (with CRITICAL alert) | Human Principal review |

**Evolution immutability:** Evolution never modifies existing records. It creates new versions. The old version is permanently preserved. This is enforced at the repository level — `KnowledgeRepository.save_new_version()` is the only evolution write method.

---

### 8.6 Deprecation Governance

**Deprecation decision matrix:**

| Item Type | Centralit | Impact | Deprecation Authority |
|---|---|---|---|
| Low-centrality (< 3 connections) | Low | Low | Automated (Governance Service) |
| Medium-centrality (3–10 connections) | Medium | Medium | Domain owner approval |
| High-centrality (> 10 connections) | High | High | Human Principal approval |
| Inviolable Rule | Any | Critical | Human Principal + ADR |

**Deprecation protection:** A knowledge item with centrality > 10 cannot be deprecated without:
1. Impact analysis showing which consuming layers are affected
2. Identification of replacement knowledge
3. Human Principal written approval
4. A 14-day transition period during which both old and new knowledge are available

---

### 8.7 Compatibility Policy

When a knowledge item is deprecated and replaced by a new version, compatibility must be maintained during the transition:

| Period | Old Item | New Item | Consuming Layer Behaviour |
|---|---|---|---|
| Days 1–7 (transition start) | VALIDATED | VALIDATED | Both returned; new item is preferred |
| Days 8–14 (transition middle) | DEPRECATED (soft) | VALIDATED | Old item returned with DEPRECATED flag |
| Day 15+ (transition complete) | DEPRECATED | VALIDATED | Only new item returned |

**Breaking changes:** If the new knowledge item contradicts (not just supersedes) the old one, this is a breaking change. Breaking changes require Human Principal explicit approval and are communicated to all registered consuming layers via the EventBus `KNOWLEDGE_BREAKING_CHANGE` event.

---

### 8.8 Knowledge Security

Security governs who can access, create, modify, and delete knowledge.

**Knowledge security matrix:**

| Action | Permitted By | Audit? |
|---|---|---|
| Read validated knowledge | Any authenticated service | No |
| Read deprecated knowledge | KnowledgeGovernanceService, Human Principal | Yes |
| Create knowledge (automated) | Service owners (via KnowledgeValidationService) | Yes |
| Create Rule knowledge | Human Principal only | Yes |
| Update knowledge (evolution) | KnowledgeEvolutionService only | Yes |
| Deprecate knowledge | As per deprecation authority matrix | Yes |
| Rollback knowledge | Human Principal only | Yes |
| Delete knowledge (forbidden) | Nobody | N/A |
| Archive knowledge | KnowledgeArchivalService (automated) | Yes |

**Knowledge injection protection:** The knowledge base is a high-value target for manipulation. If an adversary could inject false knowledge (e.g., "momentum strategies have 90% win rate in BULL regimes"), the system would over-allocate capital and suffer losses.

Protections against knowledge injection:
- All knowledge creation requires authenticated service owner identity
- Human-submitted knowledge requires Telegram authentication (chat_id check)
- All creation events are audited with the originator's identity
- Knowledge validation requires evidence from the historical data store — claims without data-backed evidence cannot be created

---

### 8.9 Knowledge Sharing

**Internal sharing:** Knowledge is available to all 17 IIOS layers through the Knowledge Retrieval Service. No internal component is denied access to validated knowledge.

**Selective exposure:** Deprecated, POOR-quality, and PROVISIONAL knowledge is not included in standard retrieval results. Consuming layers must explicitly request these tiers.

**External sharing:** Knowledge in the IIOS is proprietary. No knowledge is shared externally (via API, export file, or Telegram). The Telegram bot reports knowledge-derived summaries (e.g., "strategy in BULL regime: win rate HIGH") but never exports raw knowledge records.

**Research sharing:** Research tools (backtesting, strategy exploration) have read access to the full knowledge base including deprecated items. Write access from research tools is limited to submitting discovery candidates — they cannot directly write validated knowledge.

---
## PART IX — KNOWLEDGE CONSTITUTION

### 9.1 Constitutional Authority

The Knowledge Constitution is the supreme set of engineering rules governing how every knowledge item in the IIOS is created, managed, consumed, evolved, and eventually retired. These rules apply to every engineer, every service, every component, and every automated process in the AI Trading Brain.

These rules are mandatory. They are not optional. They are not subject to time pressure exceptions. Any deviation requires an Architecture Decision Record and Human Principal approval.

---

### 9.2 Category A — Foundation Rules

| Rule ID | Rule |
|---|---|
| KC-A-01 | Knowledge cannot exist without evidence. Every knowledge item references at least one evidence record. |
| KC-A-02 | Every knowledge item has a unique, permanent, UUID4 identifier that is never reused. |
| KC-A-03 | Every knowledge item has a domain, a category, and a taxonomy path assigned at creation time. |
| KC-A-04 | Every knowledge item belongs to exactly one primary knowledge cluster. |
| KC-A-05 | Every knowledge item has exactly one owner. Ownerless knowledge is not permitted. |
| KC-A-06 | Every knowledge item is assigned a knowledge level (1–10) based on its abstraction and derivation depth. |
| KC-A-07 | No knowledge item may reference a deprecated or archived knowledge item as its primary basis. |
| KC-A-08 | Every knowledge item created by an automated service must be created through the KnowledgeValidationService. Direct writes to the knowledge store are prohibited. |
| KC-A-09 | The Knowledge Engine's services are the exclusive interface to the knowledge base. No component reads from `knowledge.db` directly. |
| KC-A-10 | Every knowledge item in the system can be explained in a single English sentence. A claim that cannot be so stated is insufficiently precise. |

---

### 9.3 Category B — Evidence Rules

| Rule ID | Rule |
|---|---|
| KC-B-01 | No knowledge item is created without at least 30 independent observations supporting its claim. This minimum is enforced at validation time. |
| KC-B-02 | Evidence must span at least 90 trading days before validation. Patterns observed over shorter windows are stored as pre-discovery observations, not knowledge. |
| KC-B-03 | Evidence is immutable. Once an evidence record is written, it cannot be modified. Corrections are new evidence records. |
| KC-B-04 | Every evidence record carries the market regime at the time of the observation. Context-free evidence is not admitted to the evidence store. |
| KC-B-05 | Evidence sources are categorised and quality-weighted. Live trade outcomes carry weight 1.0. Backtest results carry weight 0.70. Human annotations carry weight 0.75. |
| KC-B-06 | Contradicting evidence (evidence that refutes a claim) is as important as supporting evidence and must be retained. Selective evidence retention is a governance violation. |
| KC-B-07 | Evidence accumulation is the mechanism of knowledge improvement. No evidence record is deleted once it has been admitted to the evidence store. |
| KC-B-08 | The total evidence volume for any knowledge item is always queryable. A knowledge consumer may always ask "how much evidence supports this claim?" |
| KC-B-09 | Walk-forward test evidence carries a higher weight than backtest evidence. Out-of-sample validation is the gold standard. |
| KC-B-10 | Evidence that was produced during a different market regime than the one claimed by the knowledge item must be tagged accordingly and discounted appropriately. |

---

### 9.4 Category C — Lineage and Traceability Rules

| Rule ID | Rule |
|---|---|
| KC-C-01 | Every knowledge item has a Knowledge Lineage record created at the same time as the knowledge item. A knowledge item without a lineage record cannot exist. |
| KC-C-02 | The lineage record documents the discovery method, the discovery service, and the discovery timestamp. |
| KC-C-03 | For derived knowledge, the lineage record lists all parent knowledge items and the derivation method. No derived knowledge exists without a derivation trace. |
| KC-C-04 | The confidence trajectory (list of (timestamp, confidence) pairs) is maintained in the lineage record for every knowledge item. |
| KC-C-05 | The status history (list of (timestamp, status) pairs) is maintained in the lineage record for every knowledge item. |
| KC-C-06 | Every knowledge item's lineage is auditable from raw observation to current version without gaps. |
| KC-C-07 | For any knowledge item used in a trading decision, a complete traceability chain — from the raw market observations that informed it to the trade outcome — must be accessible via the Knowledge Engine's traceability API. |
| KC-C-08 | Knowledge lineage records are immutable. Lineage is never revised; updates append to the existing record. |
| KC-C-09 | The derived children of a knowledge item are listed in the lineage record. If a parent knowledge item is deprecated, all its derived children must be reviewed. |
| KC-C-10 | Every service that contributes evidence to a knowledge item is listed in the Knowledge Source records associated with that item. |

---

### 9.5 Category D — Versioning Rules

| Rule ID | Rule |
|---|---|
| KC-D-01 | Knowledge is never overwritten. Every change creates a new version. |
| KC-D-02 | Version numbers are monotonically increasing integers with no gaps. A gap in version numbers indicates data corruption. |
| KC-D-03 | Every version record is immutable after creation. The content of a version cannot be changed after the version is written. |
| KC-D-04 | The current version of a knowledge item is the version with the highest version number and `valid_to = null`. |
| KC-D-05 | Historical versions are accessible by version number to any authorised service. Version access is a read-only operation. |
| KC-D-06 | The reason for every version change is recorded in the version record's `change_reason` field. |
| KC-D-07 | A knowledge rollback creates a new version — it does not restore an old version in-place. The version history is never rewritten. |
| KC-D-08 | The complete version history of any knowledge item must be reconstructable from version records alone. |
| KC-D-09 | Version diff (KnowledgeDiff) is available for any two versions of the same knowledge item. The diff operation is always available without degraded service. |
| KC-D-10 | Versioning applies to all 15 knowledge object types without exception. |

---

### 9.6 Category E — Quality Rules

| Rule ID | Rule |
|---|---|
| KC-E-01 | Every validated knowledge item has a composite quality score computed from all 10 quality dimensions. |
| KC-E-02 | No knowledge item with a quality score below 0.40 (POOR) may be used in a trading decision. |
| KC-E-03 | Knowledge items used in position sizing decisions must have confidence ≥ 0.70 and quality score ≥ 0.65. |
| KC-E-04 | Inviolable Rules have quality score = 1.00 by convention. They are not scored on statistical quality dimensions. |
| KC-E-05 | Freshness is a mandatory quality dimension. A knowledge item that has not received new evidence in > 180 days has freshness = 0.0 and cannot be used in cycle-critical decisions without explicit Human Principal acknowledgement. |
| KC-E-06 | Every knowledge item's quality score is recomputed at least weekly. Quality scores are never stale for more than 7 days. |
| KC-E-07 | Knowledge items with traceability score = 0.0 cannot exist in the knowledge base. This is enforced at creation time. |
| KC-E-08 | Inconsistent knowledge items (consistency score < 0.60) are flagged for immediate governance review. They are not used in decisions during the review period. |
| KC-E-09 | The mean quality score across the entire knowledge base is reported weekly. If the mean falls below 0.65, the system issues a CRITICAL knowledge health alert. |
| KC-E-10 | Quality scores are never manually adjusted. They are always computed from the defined formula and the current evidence. |

---

### 9.7 Category F — Lifecycle Rules

| Rule ID | Rule |
|---|---|
| KC-F-01 | Every knowledge item follows the defined 12-stage lifecycle. No stage may be skipped. |
| KC-F-02 | Knowledge items cannot advance from RAW to VALIDATED without passing all 6 validation checks. |
| KC-F-03 | Knowledge may only be written to the knowledge store after the Classification stage is complete. Unclassified knowledge cannot be persisted. |
| KC-F-04 | DEPRECATED knowledge is never deleted. It is retained permanently in the knowledge base with `status = DEPRECATED`. |
| KC-F-05 | DEPRECATED knowledge is archived to cold storage after 1 year of deprecation. Archival is permanent. |
| KC-F-06 | The deprecation review period is 7 calendar days for non-critical items and 14 calendar days for high-centrality items. No item is deprecated without completing its review period. |
| KC-F-07 | A knowledge item that enters deprecation review does not lose VALIDATED status during the review period. Consuming layers continue to use it (with a UNDER_REVIEW flag) during the review. |
| KC-F-08 | The archival process is verified (checksum + read test) before any knowledge item is removed from the live knowledge store. |
| KC-F-09 | No knowledge item progresses to the learning stage without having been used in at least one real or paper trading cycle. Pre-cycle knowledge cannot be marked as "learned from trading". |
| KC-F-10 | The complete knowledge lifecycle is audited. Every stage transition has a corresponding audit event in AuditService. |

---

### 9.8 Category G — Usage and Consumption Rules

| Rule ID | Rule |
|---|---|
| KC-G-01 | Only VALIDATED knowledge items are used in trading decisions. PROVISIONAL and RAW knowledge may not directly influence trade approvals. |
| KC-G-02 | Every knowledge item used in a decision is referenced in the DecisionRecord by knowledge_id and version. |
| KC-G-03 | When a decision layer uses knowledge, it must respect the knowledge item's context conditions. Knowledge applied outside its stated context conditions is flagged as a governance violation. |
| KC-G-04 | Knowledge confidence is always surfaced to the consuming layer. No layer may treat knowledge as certain when its confidence is < 1.0. |
| KC-G-05 | Knowledge with confidence < 0.55 must be explicitly discounted in decision-making. The discount factor is `confidence_score / 0.55`. |
| KC-G-06 | Inviolable Rules override patterns and contextual knowledge. No evidence-based pattern can override a Rule. |
| KC-G-07 | All knowledge consumption is tracked. Every retrieval is recorded with the consuming service, the cycle_id, and the decision_id if applicable. |
| KC-G-08 | If multiple knowledge items conflict on the same question, the higher-confidence item takes precedence. If confidence is equal, the higher-level item (by hierarchy) takes precedence. |
| KC-G-09 | Knowledge retrieved but not used in the final decision is also tracked. Understanding why knowledge was consulted but not used informs future relevance scoring. |
| KC-G-10 | Knowledge items that are consistently retrieved but consistently lead to losing trades trigger an automatic confidence review after 10 such associations. |

---

### 9.9 Category H — Governance Rules

| Rule ID | Rule |
|---|---|
| KC-H-01 | Every knowledge item has a governance status: NORMAL, UNDER_REVIEW, or SUSPENDED. |
| KC-H-02 | SUSPENDED knowledge (pending contradiction resolution) is not used in decisions. |
| KC-H-03 | Any component may flag a knowledge item for governance review. No component may resolve a governance review except the KnowledgeGovernanceService. |
| KC-H-04 | Governance reviews are never indefinite. Every review has a deadline. Unresolved reviews after the deadline are escalated to Human Principal. |
| KC-H-05 | The creation of inviolable Rules requires Human Principal approval through the Telegram interface. The approval event is audited. |
| KC-H-06 | The deprecation of any knowledge item with centrality > 10 requires Human Principal approval. |
| KC-H-07 | Knowledge is never modified by direct database edit. All modifications go through the Knowledge Engine's version creation process. |
| KC-H-08 | The Knowledge Governance Service produces a weekly governance summary. If not produced, a governance health alert is sent. |

---

### 9.10 Category I — Security Rules

| Rule ID | Rule |
|---|---|
| KC-I-01 | Knowledge is never extracted from the system via external API. The Knowledge Retrieval Service answers queries but does not export knowledge records to external systems. |
| KC-I-02 | Knowledge injection by an external actor is prevented by requiring all knowledge to originate from authenticated internal services or the Human Principal's Telegram interface. |
| KC-I-03 | All knowledge creation events are audited with the creating service's identity. |
| KC-I-04 | Knowledge involving trading strategies, win rates, or system performance is classified as RESTRICTED (data classification tier S3). |
| KC-I-05 | Knowledge audit records are subject to the same tamper-evidence requirements as operational audit records. |
| KC-I-06 | The knowledge graph is not accessible to external clients. Its structure and topology are proprietary. |
| KC-I-07 | Knowledge access logs are retained for 90 days, enabling post-incident analysis of how knowledge was used prior to any adverse event. |

---

### 9.11 Knowledge Constitution Reference Table

| ID | Category | Rule Summary | Enforcement |
|---|---|---|---|
| KC-A-01 | Foundation | No knowledge without evidence | Validation check |
| KC-A-02 | Foundation | UUID4 permanent identifier | CI type check |
| KC-A-03 | Foundation | Domain + category + taxonomy path | Validation check |
| KC-A-04 | Foundation | One primary cluster | Classification check |
| KC-A-05 | Foundation | One owner | Creation check |
| KC-A-06 | Foundation | Knowledge level assigned | Classification check |
| KC-A-07 | Foundation | No deprecated basis | Validation check |
| KC-A-08 | Foundation | Via KnowledgeValidationService | PR review |
| KC-A-09 | Foundation | No direct DB access | PR review |
| KC-A-10 | Foundation | Single-sentence claim | Review |
| KC-B-01 | Evidence | ≥ 30 observations | Validation check |
| KC-B-02 | Evidence | ≥ 90 trading days | Validation check |
| KC-B-03 | Evidence | Evidence is immutable | Repository design |
| KC-B-04 | Evidence | Regime at observation required | Creation check |
| KC-B-05 | Evidence | Quality weights by source | Configuration |
| KC-B-06 | Evidence | Contradicting evidence retained | Review |
| KC-B-07 | Evidence | No evidence deletion | Repository design |
| KC-B-08 | Evidence | Evidence volume always queryable | API check |
| KC-B-09 | Evidence | Walk-forward > backtest weight | Configuration |
| KC-B-10 | Evidence | Regime mismatch tagged | Creation check |
| KC-C-01 | Lineage | Lineage record at creation | Atomic creation |
| KC-C-02 | Lineage | Lineage documents discovery | Creation check |
| KC-C-03 | Lineage | Derivation trace required | Derived item check |
| KC-C-04 | Lineage | Confidence trajectory maintained | Evolution service |
| KC-C-05 | Lineage | Status history maintained | Governance service |
| KC-C-06 | Lineage | No lineage gaps | Integrity check |
| KC-C-07 | Lineage | Full trace for decision knowledge | Traceability API |
| KC-C-08 | Lineage | Lineage is immutable | Repository design |
| KC-C-09 | Lineage | Children listed in lineage | Creation check |
| KC-C-10 | Lineage | All contributing services listed | Creation check |
| KC-D-01 | Versioning | Knowledge never overwritten | Repository design |
| KC-D-02 | Versioning | Sequential version numbers | Integrity check |
| KC-D-03 | Versioning | Versions are immutable | Repository design |
| KC-D-04 | Versioning | Current = highest + valid_to null | API check |
| KC-D-05 | Versioning | Historical versions accessible | API check |
| KC-D-06 | Versioning | Change reason recorded | Creation check |
| KC-D-07 | Versioning | Rollback = new version | Process design |
| KC-D-08 | Versioning | Full history reconstructable | Integrity check |
| KC-D-09 | Versioning | Diff always available | API check |
| KC-D-10 | Versioning | All 15 types versioned | PR review |
| KC-E-01 | Quality | Composite quality score computed | Analytics service |
| KC-E-02 | Quality | Score < 0.40 not usable | Retrieval filter |
| KC-E-03 | Quality | High-stakes decisions need ≥ 0.65 | Consumer rule |
| KC-E-04 | Quality | Rules score = 1.00 | Configuration |
| KC-E-05 | Quality | Stale = freshness 0.0 | Freshness check |
| KC-E-06 | Quality | Scores recomputed weekly | CI scheduled job |
| KC-E-07 | Quality | Traceability = 0 forbidden | Creation check |
| KC-E-08 | Quality | Inconsistent items flagged | Governance service |
| KC-E-09 | Quality | Mean score alert < 0.65 | Monitoring |
| KC-E-10 | Quality | Scores never manually adjusted | PR review |
| KC-F-01 | Lifecycle | 12-stage lifecycle enforced | Process design |
| KC-F-02 | Lifecycle | All validation checks required | Validation service |
| KC-F-03 | Lifecycle | Classification before storage | Process design |
| KC-F-04 | Lifecycle | Deprecated never deleted | Repository design |
| KC-F-05 | Lifecycle | Archive after 1 year deprecated | CI scheduled job |
| KC-F-06 | Lifecycle | Review period enforced | Governance service |
| KC-F-07 | Lifecycle | VALIDATED during review | Governance service |
| KC-F-08 | Lifecycle | Archival verified | CI test |
| KC-F-09 | Lifecycle | Learning after real cycle use | Process design |
| KC-F-10 | Lifecycle | All transitions audited | AuditService |
| KC-G-01 | Usage | VALIDATED only in decisions | Retrieval filter |
| KC-G-02 | Usage | Knowledge ID in DecisionRecord | CI test |
| KC-G-03 | Usage | Context conditions respected | Consumer check |
| KC-G-04 | Usage | Confidence surfaced to consumer | API design |
| KC-G-05 | Usage | Low confidence discounted | Consumer rule |
| KC-G-06 | Usage | Rules override patterns | Process design |
| KC-G-07 | Usage | All consumption tracked | Usage logger |
| KC-G-08 | Usage | Higher confidence takes precedence | Consumer rule |
| KC-G-09 | Usage | Unconsumed retrievals tracked | Usage logger |
| KC-G-10 | Usage | Loss-pattern triggers review | Monitoring |
| KC-H-01 | Governance | Governance status on all items | Schema check |
| KC-H-02 | Governance | SUSPENDED not in decisions | Retrieval filter |
| KC-H-03 | Governance | Governance via GovernanceService | PR review |
| KC-H-04 | Governance | No indefinite reviews | Governance service |
| KC-H-05 | Governance | Rules need Human Principal | PR review |
| KC-H-06 | Governance | High-centrality deprecation approved | Governance policy |
| KC-H-07 | Governance | No direct DB modification | PR review |
| KC-H-08 | Governance | Weekly summary generated | CI scheduled job |
| KC-I-01 | Security | No external knowledge export | API design |
| KC-I-02 | Security | Injection prevention | Authentication check |
| KC-I-03 | Security | Creation events audited | AuditService |
| KC-I-04 | Security | Strategy knowledge is RESTRICTED | Classification |
| KC-I-05 | Security | Audit tamper-evident | Persistence design |
| KC-I-06 | Security | Graph not accessible externally | API design |
| KC-I-07 | Security | Access logs 90 days | Retention policy |

**Total mandatory rules: 75**

---
## PART X — KNOWLEDGE READINESS CHECKLIST

### 10.1 Purpose of the Readiness Checklist

The Knowledge Readiness Checklist is the master verification framework used to ensure that the Knowledge Engine is operating correctly and that every knowledge item in the knowledge base meets the standards required for use in intelligent decision-making.

The checklist has two purposes:
1. **Per-item readiness:** Applied to every individual knowledge item before it is used in a trading decision
2. **System readiness:** Applied to the Knowledge Engine as a whole at system startup and in weekly governance reviews

---

### 10.2 Per-Item Knowledge Readiness Checklist

This checklist is evaluated for every knowledge item before it is returned to a consuming layer.

**Section A: Identity and Foundation**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| A-1 | Knowledge item has UUID4 identifier | `knowledge_id` is a valid UUID4 | Reject — creation error |
| A-2 | Taxonomy path is assigned | `domain.category` at minimum is set | Reject — unclassified |
| A-3 | Owner is assigned | `owner_id` is set and owner is an active service | Flag — governance review |
| A-4 | Knowledge level is set | `knowledge_level` is 1–10 | Reject — classification error |
| A-5 | Status is VALIDATED | `status == VALIDATED` | Return with status warning |

**Section B: Evidence Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| B-1 | Evidence records present | ≥ 1 evidence record linked | Reject — evidence violation |
| B-2 | Evidence volume meets threshold | ≥ 30 evidence records | Return with PROVISIONAL flag |
| B-3 | Evidence time span adequate | Evidence spans ≥ 90 trading days | Return with LIMITED_WINDOW flag |
| B-4 | Evidence includes current regime | At least one evidence record from the current or recent regime | Return with REGIME_GAP flag |
| B-5 | No expired evidence sources | All evidence sources are from active, non-deprecated data feeds | Return with SOURCE_WARNING flag |

**Section C: Confidence Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| C-1 | Confidence score is present | `confidence_score` is set | Reject — computation error |
| C-2 | Confidence meets minimum | `confidence_score ≥ 0.55` | Return with LOW_CONFIDENCE flag |
| C-3 | Confidence interval is present | `confidence_interval_lower` and `_upper` are set | Return with missing interval warning |
| C-4 | Confidence is not stale | `last_updated` is within 90 days | Return with STALE_CONFIDENCE flag |
| C-5 | Confidence trajectory is not declining | Last 3 confidence values are stable or improving | Return with DECLINING_CONFIDENCE flag |

**Section D: Context Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| D-1 | Context conditions are present | At least one context condition is set | Reject — context-free knowledge |
| D-2 | Context conditions match current state | At least one dimension of context matches current QueryContext | Return with CONTEXT_MISMATCH flag |
| D-3 | No expired context conditions | Context references current regimes/conditions | Return with STALE_CONTEXT flag |
| D-4 | Volatility state covered | Knowledge context includes volatility dimension | Return with MISSING_VOLATILITY_CONTEXT flag |

**Section E: Freshness Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| E-1 | Last evidence date is present | `last_evidence_date` is set | Return with missing date warning |
| E-2 | Evidence is recent | Last evidence within 90 days | Return with STALE flag |
| E-3 | Freshness score is acceptable | `freshness_score ≥ 0.30` | Return with STALE_CRITICAL flag; do not use in decisions |
| E-4 | Not flagged for freshness review | `governance_status != FRESHNESS_REVIEW` | Return with UNDER_REVIEW flag |

**Section F: Lineage and Traceability Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| F-1 | Lineage record exists | Knowledge Lineage record linked | Reject — lineage violation |
| F-2 | Discovery method documented | `discovery_method` is set in lineage | Flag — incomplete lineage |
| F-3 | Version history is complete | No gaps in version sequence | Flag — integrity issue |
| F-4 | Derivation trace complete (if derived) | All parent knowledge IDs are present and VALIDATED | Return with PARENT_DEGRADED flag |
| F-5 | Traceability score is adequate | `traceability_score ≥ 0.60` | Return with LOW_TRACEABILITY flag |

**Section G: Governance Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| G-1 | Not under suspension | `governance_status != SUSPENDED` | Reject — suspended knowledge |
| G-2 | Not under contradiction review | `governance_status != CONTRADICTION_HOLD` | Return with HELD flag |
| G-3 | Most recent review is within 90 days | Last governance review within 90 days | Return with OVERDUE_REVIEW flag |
| G-4 | No open governance escalation | No open escalation in governance queue | Return with ESCALATION_OPEN flag |
| G-5 | Quality score is acceptable | `quality_score ≥ 0.40` | Reject if < 0.40; return LOW_QUALITY flag if 0.40–0.55 |

**Section H: Graph Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| H-1 | Graph node exists | Knowledge Graph Node is registered | Flag — graph out of sync |
| H-2 | At least one graph connection | Edge count ≥ 1 | Flag — isolated node |
| H-3 | No unresolved contradiction edges | No active CONTRADICTS edge to a VALIDATED item | Return with CONTRADICTION flag |
| H-4 | Cluster assignment is current | Cluster was re-computed within 7 days | Return with STALE_CLUSTER flag |

---

### 10.3 Knowledge Engine System Readiness Checklist

This checklist is evaluated at system startup and in weekly governance reviews.

**Section I: Service Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| I-1 | Discovery Service is running | `KnowledgeDiscoveryService.is_running()` == True | Block startup |
| I-2 | Validation Service is running | `KnowledgeValidationService.is_running()` == True | Block startup |
| I-3 | Classification Service is running | `KnowledgeClassificationService.is_running()` == True | Block startup |
| I-4 | Retrieval Service is running | `KnowledgeRetrievalService.is_running()` == True | Block startup |
| I-5 | Search Service is running | `KnowledgeSearchService.is_running()` == True | Block startup |
| I-6 | Evolution Service is running | `KnowledgeEvolutionService.is_running()` == True | Block startup |
| I-7 | Graph Service is running | `KnowledgeGraphService.is_running()` == True | Block startup |
| I-8 | Governance Service is running | `KnowledgeGovernanceService.is_running()` == True | Block startup |
| I-9 | Analytics Service is running | `KnowledgeAnalyticsService.is_running()` == True | Warning only |
| I-10 | Version Service is running | `KnowledgeVersionService.is_running()` == True | Warning only |

**Section J: Knowledge Base Health**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| J-1 | knowledge.db passes integrity check | `PRAGMA integrity_check` returns "ok" | Block startup — critical corruption |
| J-2 | Knowledge base has sufficient coverage | ≥ 10 VALIDATED items in all 7 domains | Warning — thin coverage alert |
| J-3 | Mean quality score is acceptable | Mean quality score ≥ 0.65 | Warning — knowledge health alert |
| J-4 | No items in POOR quality tier | 0 items with quality score < 0.40 | Warning — governance action required |
| J-5 | No unresolved contradictions | 0 items with CONTRADICTS edges to active VALIDATED items | Warning — contradiction review |
| J-6 | No suspended items older than 14 days | 0 items in CONTRADICTION_HOLD > 14 days | Warning — escalation overdue |
| J-7 | Inviolable Rules are all VALIDATED | All items with `is_inviolable=True` have status VALIDATED | Block startup — safety rule missing |
| J-8 | Freshness is adequate | < 5% of items have freshness_score = 0.0 | Warning — knowledge staleness |
| J-9 | Graph is connected | No isolated knowledge nodes | Warning — isolated nodes |
| J-10 | Version histories are complete | 0 version sequence gaps detected | Warning — integrity issue |

**Section K: Governance Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| K-1 | Weekly governance summary produced | Last governance summary within 7 days | Warning — governance health |
| K-2 | All ownerless items resolved | 0 items with no active owner | Warning — ownership review |
| K-3 | All deprecation reviews within deadline | 0 reviews past their deadline | Warning — escalation required |
| K-4 | Audit log is current | Most recent audit event within 24 hours | Warning — audit health |
| K-5 | Knowledge freshness reviews processed | Freshness review queue is empty | Warning — stale knowledge |
| K-6 | Analytics reports are current | Last analytics report within 7 days | Warning — analytics health |
| K-7 | All HOLD items have escalation owner | 0 HOLD items without escalation owner | Warning — governance gap |
| K-8 | All domains have an active domain owner | No domain with retired/inactive owner | Warning — ownership gap |

**Section L: Integration Readiness**

| # | Check | Pass Condition | Fail Action |
|---|---|---|---|
| L-1 | Consuming layers are registered | MetaLearning, StrategyLab, DebateAndDecision all registered as consumers | Warning — consumer gap |
| L-2 | Cache is populated | In-memory cache contains ≥ 100 hot knowledge items | Warning — cold cache |
| L-3 | Knowledge graph is loaded into memory | Knowledge Graph in-memory structure is populated | Block startup if empty |
| L-4 | Search index is built | FTS5 search index populated and queryable | Warning — search degraded |
| L-5 | Evidence store is accessible | Evidence records queryable without error | Warning — evidence access |
| L-6 | Lineage store is accessible | Lineage records queryable without error | Warning — lineage access |

---

### 10.4 Readiness Score Calculation

**Per-item readiness score:**

```
readiness_score = (
    section_A_passed / section_A_total × 0.15 +
    section_B_passed / section_B_total × 0.15 +
    section_C_passed / section_C_total × 0.15 +
    section_D_passed / section_D_total × 0.10 +
    section_E_passed / section_E_total × 0.10 +
    section_F_passed / section_F_total × 0.15 +
    section_G_passed / section_G_total × 0.15 +
    section_H_passed / section_H_total × 0.05
)
```

**Readiness decision:**

| Readiness Score | Decision | Action |
|---|---|---|
| ≥ 0.90 | READY | Return to consumer without caveat |
| 0.75 – 0.90 | READY_WITH_FLAGS | Return with advisory flags |
| 0.60 – 0.75 | CONDITIONALLY_READY | Return for low-stakes use only |
| < 0.60 | NOT_READY | Do not return; log reason |

---

### 10.5 Readiness Reporting

**Startup readiness report:** At every system startup, the Knowledge Engine produces a readiness report covering Sections I, J, K, and L. This report is:
- Logged to the application log at INFO level
- Sent to the Telegram bot as a startup notification (summary only)
- Written to the ControlTower dashboard

**Weekly readiness report:** Every Sunday, the Knowledge Engine produces a full readiness report covering all sections for all knowledge items. This report is saved to `data/reports/knowledge_readiness_YYYY-MM-DD.json` and summarised in the weekly Telegram summary.

**Readiness alert policy:**

| Alert Condition | Level | Recipient |
|---|---|---|
| Any service in Section I fails | CRITICAL | Telegram |
| J-1 integrity check fails | CRITICAL | Telegram |
| J-7 inviolable Rule missing | CRITICAL | Telegram |
| Mean quality score < 0.65 | WARNING | Telegram |
| > 10% stale items | WARNING | Telegram |
| Any Section K governance gap | WARNING | Telegram |
| Readiness score of any domain falls below 0.60 | WARNING | Telegram |

---
## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | KNOWLEDGE ENGINE ARCHITECTURE |
| Document version | 1.0.0 |
| Date | 2026-07-02 |
| Parts | 10 (I–X) |
| Mandatory rules | 75 (KC-A-01 through KC-I-07) |
| Rule categories | 9 (Foundation, Evidence, Lineage, Versioning, Quality, Lifecycle, Usage, Governance, Security) |
| Knowledge hierarchy levels | 10 (Raw through Meta Knowledge) |
| Knowledge object types | 15 |
| Knowledge services | 10 |
| Quality dimensions | 10 |
| Quality weights defined | Yes (all 10 dimensions with weights summing to 1.0) |
| Knowledge domains | 7 (Market, Strategy, Agent, System, Risk, Portfolio, Operations) |
| Knowledge lifecycle stages | 12 |
| Readiness checklist sections | 12 (A through L) |
| Per-item checks | 38 |
| System checks | 32 |
| Evidence source types | 8 (with quality multipliers) |
| Edge types in knowledge graph | 8 |
| Governance levels | 3 (Automated, Telegram alert, Human Principal decision) |

---

### Master Compliance Checklist

**Before creating any new knowledge item:**
- [ ] Evidence volume ≥ 30 independent observations
- [ ] Evidence time span ≥ 90 trading days
- [ ] Consistency ≥ 60% of qualifying conditions
- [ ] Confidence ≥ 0.55 (unless inviolable Rule)
- [ ] No contradiction with HIGH-confidence items
- [ ] At least one regime context condition set
- [ ] Taxonomy path (domain.category) assigned
- [ ] Knowledge Lineage record created simultaneously
- [ ] Knowledge Graph node registered
- [ ] Creation audit event written

**Before using knowledge in a decision:**
- [ ] Status == VALIDATED
- [ ] Governance status is not SUSPENDED or CONTRADICTION_HOLD
- [ ] Freshness score ≥ 0.30 (or Human Principal acknowledgement for stale)
- [ ] Quality score ≥ 0.40 (≥ 0.65 for position sizing decisions)
- [ ] Context conditions match current state
- [ ] Confidence is surfaced to the consuming layer
- [ ] Knowledge ID and version recorded in DecisionRecord

**Before deprecating a knowledge item:**
- [ ] Confidence has fallen below 0.40 OR contradicted by inviolable Rule OR Human Principal review
- [ ] Impact analysis completed (dependent knowledge items identified)
- [ ] High-centrality items (> 10 connections): Human Principal approval obtained
- [ ] Review period completed (7 days non-critical, 14 days high-centrality)
- [ ] Deprecation audit event written
- [ ] All consumers notified via KNOWLEDGE_DEPRECATED event

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
| `CORE_FRAMEWORK_ARCHITECTURE.md` | Core framework and base classes |
| `DATABASE_PERSISTENCE_ARCHITECTURE.md` | Persistence design authority |
| `KNOWLEDGE_ENGINE_ARCHITECTURE.md` | This document — Knowledge Engine design authority |

---

### Closing Statement

The Knowledge Engine is the intelligence layer of the IIOS. Everything beneath it — market data, information processing, strategy design, risk control — is ultimately in service of what the Knowledge Engine produces: structured, validated, evolving understanding of how markets work, how strategies behave, and how the system can improve.

Every decision the IIOS makes is a knowledge-driven decision. Without the Knowledge Engine, the system is reactive, stateless, and unable to learn. With it, the system becomes progressively more capable — building institutional memory that no individual trade, no market event, and no system restart can erase.

Knowledge is the compound interest of intelligence. This document is its architecture.

---

## SUPPLEMENT A — KNOWLEDGE OBJECT CATALOGUE

### A.1 Complete Knowledge Object Type Reference

| Object Type | Level(s) | Primary Domain | Confidence Required | Versioned | Evidence Required |
|---|---|---|---|---|---|
| Knowledge Record | 1–10 (all) | All | By level | Yes | Yes |
| Knowledge Pattern | 1–6 | Market, Strategy, Agent | ≥ 0.55 | Yes | ≥ 30 obs |
| Knowledge Rule | Any (special) | Risk, Strategy | 1.00 (inviolable) or ≥ 0.70 | Yes | Human Principal |
| Knowledge Fact | 1–2 | All | ≥ 0.55 | Yes | ≥ 1 obs |
| Knowledge Graph Node | 1–10 (all) | All (graph layer) | Inherits from KR | No | N/A |
| Knowledge Cluster | N/A (grouping) | All | N/A (container) | Yes (membership) | N/A |
| Knowledge Context | N/A (qualifier) | All | N/A (qualifier) | Yes | N/A |
| Knowledge Version | N/A (metadata) | All | N/A (metadata) | N/A | N/A |
| Knowledge Confidence | N/A (scoring) | All | N/A (computed) | Yes (recomputed) | All linked evidences |
| Knowledge Dependency | N/A (relationship) | All | N/A (relationship) | Yes | N/A |
| Knowledge Source | N/A (provenance) | All | N/A (metadata) | No | N/A |
| Knowledge Evidence | N/A (data) | All | N/A (data) | No | Self-referential |
| Knowledge Owner | N/A (governance) | All | N/A (governance) | No | N/A |
| Knowledge Consumer | N/A (governance) | All | N/A (governance) | No | N/A |
| Knowledge Lineage | N/A (audit) | All | N/A (audit) | Append-only | N/A |

### A.2 Knowledge Object Relationships

```
Knowledge Record ─── has ─────────────────► Knowledge Lineage (1:1)
      │
      ├─── has ─────────────────────────────► Knowledge Confidence (1:1)
      │
      ├─── has ─────────────────────────────► Knowledge Context (1:N)
      │
      ├─── has ─────────────────────────────► Knowledge Version (1:N)
      │
      ├─── has ─────────────────────────────► Knowledge Evidence (1:N, via Source)
      │
      ├─── represented by ──────────────────► Knowledge Graph Node (1:1)
      │
      ├─── belongs to ──────────────────────► Knowledge Cluster (N:1 primary, N:M secondary)
      │
      ├─── has ─────────────────────────────► Knowledge Owner (N:1)
      │
      ├─── consumed by ─────────────────────► Knowledge Consumer (N:M)
      │
      └─── depends on ─────────────────────► Knowledge Dependency (N:M)
```

---

## SUPPLEMENT B — KNOWLEDGE GRAPH DESIGN

### B.1 Graph Design Principles

The Knowledge Graph is the relational layer of the Knowledge Engine. It transforms a flat list of knowledge records into a navigable network of meaning.

**Design axioms:**

| Axiom | Description |
|---|---|
| Every node is a knowledge item | The graph contains only knowledge — not evidence, not events, not raw data |
| Edges carry meaning | Each edge type has precise semantic meaning; no generic "related to" edges |
| The graph is directional | Edges have a source and a target; the inverse relationship has its own edge type |
| The graph is weighted | Edge weight reflects the strength of the relationship (0.0–1.0) |
| The graph is immutable for history | Once an edge is added, its presence is recorded permanently; deprecation marks it inactive |

### B.2 Graph Traversal Patterns

**Pattern 1: Support chain traversal**
Used to answer: "What supports this knowledge claim?"

```
Starting from: Knowledge item K
Follow: SUPPORTS edges (incoming) with depth=3
Result: All knowledge items that directly or transitively support K
```

**Pattern 2: Impact analysis traversal**
Used to answer: "If this knowledge is deprecated, what else is affected?"

```
Starting from: Knowledge item K (being deprecated)
Follow: outgoing REQUIRES and ASSUMES edges with depth=unlimited
Result: All dependent knowledge items in the dependency DAG
```

**Pattern 3: Contradiction detection**
Used by: Knowledge Governance Service (daily)

```
For all pairs (A, B) where A and B are both VALIDATED:
Find pairs where A has a CONTRADICTS edge to B
Return all contradiction pairs with confidence scores for triage
```

**Pattern 4: Knowledge cluster discovery**
Used by: Classification Service (weekly)

```
Build undirected graph of knowledge items in same domain
Edge weight = semantic similarity score
Apply Louvain community detection
Output: cluster membership for all nodes
```

### B.3 Graph Maintenance Schedule

| Task | Frequency | Service |
|---|---|---|
| Add new node | On every knowledge creation | Classification Service |
| Add new edges | On every classification | Classification Service |
| Compute centrality scores | Weekly | Graph Service |
| Detect communities (clusters) | Weekly | Graph Service |
| Find contradictions | Daily | Governance Service |
| Mark deprecated nodes | On deprecation | Governance Service |
| Verify no cycles in DERIVED_FROM edges | On every edge addition | Graph Service |
| Export graph snapshot | Monthly | Analytics Service |

---

## SUPPLEMENT C — KNOWLEDGE DOMAIN TAXONOMY

### C.1 Complete Taxonomy Reference

**MARKET Domain (full taxonomy):**

```
MARKET
├── REGIME
│   ├── CHARACTERISTICS (what defines each regime)
│   ├── TRANSITIONS (how regimes change)
│   ├── DURATIONS (how long regimes last)
│   └── SIGNALS (observable signals of regime state)
├── PRICE_ACTION
│   ├── BREAKOUTS
│   ├── REVERSALS
│   ├── CONSOLIDATIONS
│   └── MOMENTUM
├── VOLUME
│   ├── VOLUME_PATTERNS
│   ├── VOLUME_SIGNALS
│   └── VOLUME_REGIMES
├── OPTIONS
│   ├── IV_DYNAMICS
│   ├── OI_PATTERNS
│   ├── PREMIUM_DECAY
│   └── EXPIRY_EFFECTS
├── SECTOR
│   ├── ROTATION
│   ├── CORRELATION
│   └── RELATIVE_PERFORMANCE
├── MACRO
│   ├── FII_FLOWS
│   ├── BUDGET_EFFECTS
│   └── RATE_SENSITIVITY
├── GLOBAL
│   ├── SP500_CORRELATION
│   ├── FX_EFFECTS
│   └── COMMODITY_EFFECTS
├── CALENDAR
│   ├── EXPIRY_EFFECTS
│   ├── RESULTS_SEASON
│   └── BUDGET_SEASON
└── LIQUIDITY
    ├── HIGH_VOLUME_EFFECTS
    └── LOW_VOLUME_EFFECTS
```

**STRATEGY Domain (full taxonomy):**

```
STRATEGY
├── PERFORMANCE
│   ├── WIN_RATE (by strategy and regime)
│   ├── RISK_ADJUSTED (Sharpe by strategy and regime)
│   └── DRAWDOWN (max drawdown patterns)
├── ENTRY
│   ├── BREAKOUT_ENTRIES
│   ├── MOMENTUM_ENTRIES
│   └── REVERSAL_ENTRIES
├── EXIT
│   ├── TARGET_EXITS
│   ├── STOP_LOSS_EXITS
│   └── TIME_EXITS
├── SIZING
│   ├── KELLY_SIZING
│   ├── FIXED_FRACTION
│   └── VOLATILITY_BASED
├── COMBINATION
│   ├── COMPLEMENTARY_STRATEGIES
│   └── REDUNDANT_STRATEGIES
├── EVOLUTION
│   ├── VARIANT_PERFORMANCE
│   └── LINEAGE_PATTERNS
├── FAILURE
│   ├── FAILURE_CONDITIONS
│   └── FAILURE_SIGNATURES
└── RECOVERY
    ├── RECOVERY_PATTERNS
    └── RECOVERY_TIMING
```

---

## SUPPLEMENT D — KNOWLEDGE QUALITY SCORING REFERENCE

### D.1 Quality Score Computation Example

**Example: MomentumBreakoutV3 performance knowledge in BULL_TRENDING regime**

| Dimension | Raw Value | Score |
|---|---|---|
| Accuracy | WFT accuracy = 0.68 | 0.80 |
| Completeness | 6/7 requirements met | 0.857 |
| Consistency | 4/5 consistency types pass | 0.80 |
| Freshness | Last evidence 45 days ago | 0.75 |
| Reliability | 0.68 / (1 + 0.12 std dev) | 0.607 |
| Confidence | 0.71 | 0.80 |
| Explainability | Mechanism documented (partial) | 0.70 |
| Traceability | All 5 requirements met | 1.00 |
| Reproducibility | 4/5 requirements met | 0.80 |
| Auditability | All 6 requirements met | 1.00 |

**Composite quality score:**

```
quality_score = (
  0.20 × 0.80   +  # Accuracy
  0.18 × 0.80   +  # Confidence
  0.12 × 0.80   +  # Consistency
  0.12 × 0.607  +  # Reliability
  0.10 × 1.00   +  # Traceability
  0.10 × 0.857  +  # Completeness
  0.08 × 0.75   +  # Freshness
  0.05 × 1.00   +  # Auditability
  0.03 × 0.70   +  # Explainability
  0.02 × 0.80      # Reproducibility
) = 0.807
```

**Result: GOOD quality (0.807). Usable confidently.**

### D.2 Quality Degradation Scenarios

| Scenario | Affected Dimension | Quality Impact |
|---|---|---|
| 90 days without new evidence | Freshness → 0.50 | Quality drops ~0.04 |
| Win rate drops from 0.68 to 0.52 | Accuracy → 0.30 | Quality drops ~0.10 |
| New contradicting evidence found | Consistency drops | Quality drops ~0.06 |
| Lineage record incomplete | Traceability → 0.40 | Quality drops ~0.06 |
| Context conditions not updated after regime change | Completeness, Freshness | Quality drops ~0.08 |

### D.3 Quality Monitoring Rules

| Quality Threshold | Monitoring Action |
|---|---|
| Score falls below 0.70 (GOOD → ACCEPTABLE) | Log INFO; schedule for next evidence batch |
| Score falls below 0.55 (ACCEPTABLE → MARGINAL) | Log WARNING; restrict to low-stakes use |
| Score falls below 0.40 (MARGINAL → POOR) | Log ERROR; remove from retrieval; initiate review |
| Score recovers above 0.55 | Log INFO; restore to standard retrieval |

---

## SUPPLEMENT E — KNOWLEDGE SERVICE INTERFACE REFERENCE

### E.1 Knowledge Discovery Service API

| Method | Signature | Returns | Description |
|---|---|---|---|
| `discover_from_outcomes` | `(trade_outcomes: List[TradeOutcome], cycle_id: str)` | `List[KnowledgeCandidate]` | Extract candidates from trade batch |
| `discover_from_test_result` | `(test_result: WalkForwardResult)` | `List[KnowledgeCandidate]` | Extract from walk-forward test |
| `discover_temporal_patterns` | `(regime_history: List[RegimeRecord])` | `List[KnowledgeCandidate]` | Extract temporal patterns |
| `submit_manual_candidate` | `(claim: str, evidence: List[str], type: KnowledgeType)` | `KnowledgeCandidate` | Human Principal submission |
| `get_discovery_queue_size` | `()` | `int` | Candidates awaiting validation |
| `get_last_run_timestamp` | `()` | `datetime` | When last discovery run completed |

### E.2 Knowledge Validation Service API

| Method | Signature | Returns | Description |
|---|---|---|---|
| `validate` | `(candidate: KnowledgeCandidate)` | `ValidationResult` | Run all 6 checks |
| `validate_batch` | `(candidates: List[KnowledgeCandidate])` | `List[ValidationResult]` | Batch validation |
| `override_validation` | `(candidate_id: str, override_reason: str)` | `ValidationResult` | Human Principal override |
| `get_validation_queue_size` | `()` | `int` | Candidates awaiting validation |
| `get_rejected_candidates` | `(from_dt, to_dt: datetime)` | `List[RejectedCandidate]` | Rejected candidates in window |
| `get_held_candidates` | `()` | `List[HeldCandidate]` | Candidates in VALIDATION_HOLD |

### E.3 Knowledge Retrieval Service API

| Method | Signature | Returns | Description |
|---|---|---|---|
| `get` | `(knowledge_id: str)` | `Optional[KnowledgeRecord]` | Latest version |
| `get_version` | `(knowledge_id: str, version: int)` | `Optional[KnowledgeRecord]` | Specific version |
| `find_by_context` | `(context: QueryContext, limit: int = 50)` | `List[KnowledgeQueryResult]` | Context-matched retrieval |
| `find_by_domain` | `(domain: str, category: str = None, min_confidence: float = 0.55)` | `List[KnowledgeRecord]` | Domain-based retrieval |
| `find_for_strategy` | `(strategy_id: str, context: QueryContext)` | `List[KnowledgeQueryResult]` | Strategy-specific knowledge |
| `find_for_decision` | `(hypothesis_id: str, context: QueryContext)` | `List[KnowledgeQueryResult]` | Decision-relevant knowledge |
| `find_above_confidence` | `(min_confidence: float, domain: str = None)` | `List[KnowledgeRecord]` | Confidence-filtered |
| `find_cluster` | `(cluster_id: str)` | `List[KnowledgeRecord]` | All items in cluster |
| `find_dependencies` | `(knowledge_id: str)` | `List[KnowledgeDependency]` | Direct dependencies |
| `find_dependents` | `(knowledge_id: str)` | `List[KnowledgeDependency]` | Items that depend on this |

### E.4 Knowledge Governance Service API

| Method | Signature | Returns | Description |
|---|---|---|---|
| `flag_for_review` | `(knowledge_id: str, reason: str, flagged_by: str)` | `GovernanceCase` | Flag an item |
| `resolve_case` | `(case_id: str, resolution: str, resolved_by: str)` | `GovernanceCase` | Close a governance case |
| `initiate_deprecation` | `(knowledge_id: str, reason: str)` | `DeprecationCase` | Start deprecation review |
| `approve_deprecation` | `(case_id: str, approved_by: str)` | `DeprecationCase` | Approve deprecation |
| `reject_deprecation` | `(case_id: str, reason: str)` | `DeprecationCase` | Cancel deprecation |
| `compute_impact_analysis` | `(knowledge_id: str)` | `ImpactAnalysisReport` | Dependency impact if deprecated |
| `get_open_cases` | `()` | `List[GovernanceCase]` | All open governance cases |
| `get_weekly_summary` | `()` | `GovernanceSummary` | Weekly governance report |
| `suspend_knowledge` | `(knowledge_id: str, reason: str)` | `GovernanceCase` | Immediately suspend usage |
| `reinstate_knowledge` | `(knowledge_id: str, reason: str)` | `GovernanceCase` | Lift suspension |

---

## SUPPLEMENT F — KNOWLEDGE GOVERNANCE DECISION RECORDS

### F.1 KGDR-001: Evidence-First Knowledge Creation

| Field | Content |
|---|---|
| **ID** | KGDR-001 |
| **Title** | All knowledge requires evidence; no assertion without data |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** In a trading system, unsupported beliefs can be just as harmful as no knowledge at all. If the system accepts knowledge claims without data — e.g., "momentum always works" — it will trade on false premises.

**Decision:** All knowledge creation requires evidence. The only exception is inviolable Rules submitted by the Human Principal, where the Human Principal's expertise is the evidence. But even these rules are tagged as `is_inviolable=True` to distinguish them from data-backed knowledge.

**Consequences:** No knowledge is created speculatively. Candidate knowledge waits in the discovery queue until evidence accumulates. This creates a delay between pattern observation and knowledge formalisation — accepted as a necessary cost of quality control.

---

### F.2 KGDR-002: Confidence as a First-Class Citizen

| Field | Content |
|---|---|
| **ID** | KGDR-002 |
| **Title** | Every knowledge item carries a quantified, computed confidence score |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** Without confidence scores, a consuming layer cannot distinguish between "we are 90% sure" and "we are 55% sure". Both are VALIDATED, but they should be weighted very differently in decisions.

**Decision:** Every knowledge item carries a computed, multi-component confidence score. Confidence is always surfaced to consuming layers. Consuming layers must discount decisions based on confidence. Inviolable Rules have confidence = 1.00 by convention.

**Consequences:** All 15 knowledge object types carry confidence. Consuming layers must be designed to handle confidence-weighted inputs. Position sizing decisions require minimum confidence ≥ 0.70.

---

### F.3 KGDR-003: Regime Context is Mandatory

| Field | Content |
|---|---|
| **ID** | KGDR-003 |
| **Title** | All market knowledge must be qualified by at least one regime or context condition |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** Markets are non-stationary. A trading strategy that works in a bull trending market may fail catastrophically in a bear volatile market. Knowledge without regime qualification is either incomplete or false.

**Decision:** The Knowledge Validation Service rejects any market knowledge claim that does not include at least one regime or context condition. The claim "momentum works" fails. The claim "momentum works in BULL_TRENDING regimes with confidence 0.71" passes.

**Consequences:** All knowledge producers must provide regime context when submitting knowledge. This requires that evidence records carry the regime state at the time of observation — which is enforced by the Evidence creation rules (KC-B-04).

---

### F.4 KGDR-004: Deprecation is Not Deletion

| Field | Content |
|---|---|
| **ID** | KGDR-004 |
| **Title** | Deprecated knowledge is preserved permanently; it is never physically deleted |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** Knowledge that was once true may be valuable for research even after it is no longer applicable. Understanding why a pattern stopped working is itself a knowledge asset. Additionally, the ability to audit past decisions requires access to the knowledge that informed them.

**Decision:** Deprecation sets `status = DEPRECATED` and `valid_to = timestamp`. It never removes the record. Deprecated knowledge is archived to cold storage after 1 year. Archived knowledge can be restored for research.

**Consequences:** The knowledge database grows permanently. This is managed by archival to compressed historical files. The audit trail remains complete for the full operational life of the system.

---

### F.5 KGDR-005: Knowledge Governance as a Continuous Process

| Field | Content |
|---|---|
| **ID** | KGDR-005 |
| **Title** | Governance is continuous; not event-driven or periodic-only |
| **Status** | Accepted |
| **Date** | 2024-01-01 |

**Context:** A governance process that only runs weekly will miss intraday knowledge quality issues. When the system is actively trading, knowledge quality must be monitored continuously.

**Decision:** The KnowledgeGovernanceService runs continuously. Daily tasks include contradiction detection and freshness monitoring. Weekly tasks include full quality review. Real-time tasks include suspension of knowledge items that fail critical checks. The Governance Service generates alerts immediately when critical thresholds are crossed.

**Consequences:** The Governance Service is a Tier 1 service — it starts before any cognitive cycle can run. Its failure generates a CRITICAL alert. A single day of governance service failure is acceptable (cycles proceed with last-known governance state). Multiple days require Human Principal intervention.

---

## SUPPLEMENT G — KNOWLEDGE ENGINE ANTI-PATTERN REFERENCE

### G.1 Knowledge Anti-Patterns

The following patterns are explicitly prohibited in the IIOS Knowledge Engine. Each represents a class of knowledge quality failure observed in real AI systems.

| Anti-Pattern | Why Prohibited | Correct Alternative |
|---|---|---|
| Knowledge without regime context | All market knowledge is regime-conditional; unqualified claims are systematically wrong in some regimes | Always attach at least one regime context condition before validation |
| Accepting a pattern after < 30 observations | Small samples produce unreliable confidence estimates; 30 observations is the minimum for meaningful statistics | Store as pre-discovery observation; wait for more evidence |
| Treating backtest results as equivalent to live results | Backtests have lookahead bias and overfitting risk; a backtest "fact" is not as reliable as a live trading fact | Apply the source quality multiplier (0.70 for backtest vs 1.00 for live) |
| Keeping contradicting knowledge items both VALIDATED | If two knowledge items contradict each other and both are validated, the system has no way to decide which to use; conflicts are resolved, not deferred | Initiate CONTRADICTION_HOLD; resolve through governance review |
| Confidence = 1.0 for any data-backed pattern | No empirically observed pattern is truly certain; 1.0 is reserved for inviolable Rules | Cap data-backed patterns at 0.99; use 1.00 only for Rules |
| Reusing evidence across two independent knowledge items | Reusing evidence inflates effective sample size; creates false confidence | Evidence is allocated to the knowledge item it was collected for |
| Using knowledge outside its stated context | A momentum pattern in BULL regime applied in RANGE_BOUND regime will produce systematic losses | Validate context match before applying knowledge |
| Silent knowledge degradation | If knowledge confidence drops without alerting consuming layers, decisions continue using outdated quality assessments | Emit KNOWLEDGE_EVOLVED event on every confidence change |
| Deprecating without impact analysis | Deprecating a knowledge item that high-centrality components depend on can cascade to removing key knowledge from many decisions | Always run `compute_impact_analysis()` before deprecating |
| Ingesting human annotation without quality discount | Human experts have biases and may be wrong; their annotations are not ground truth | Apply 0.75 quality multiplier to human-annotated evidence |
| Knowledge as a property of a single component | If a component knows something that other components need, it should be in the knowledge base — not hoarded as a component attribute | All cross-component knowledge belongs in the Knowledge Engine |
| Deleting low-quality knowledge | Even poor-quality knowledge has historical and audit value | Deprecate and archive; never delete |
| Pattern = Rule | A high-confidence pattern (0.88) is still probabilistic; a Rule is deterministic | Never elevate a pattern to Rule status without Human Principal approval and `is_inviolable=True` |
| Knowledge without lineage | A knowledge item whose origin is unknown cannot be audited, reproduced, or validated | Enforce lineage creation atomically with knowledge creation |
| Querying knowledge outside the retrieval service | Direct database queries bypass caching, usage tracking, and context filtering | Use KnowledgeRetrievalService for all knowledge access |

---

### G.2 Knowledge System Health Dashboard

The Knowledge Engine exposes the following health indicators to the ControlTower Streamlit dashboard.

**Real-time indicators (updated every 60 seconds):**

| Indicator | Source | Alert Threshold |
|---|---|---|
| Total VALIDATED knowledge items | Knowledge Analytics Service | < 50 (warning) |
| Total PENDING validation | KnowledgeValidationService | > 100 (warning) |
| Total HOLD items | KnowledgeGovernanceService | > 10 (warning) |
| Service health (all 10 services) | KnowledgeGovernanceService | Any service DOWN (critical) |
| Mean quality score | Knowledge Analytics Service | < 0.65 (warning) |
| Contradiction count | KnowledgeGraphService | > 0 (warning) |
| Cache hit rate | Knowledge Retrieval Service | < 70% (warning) |

**Weekly indicators (updated Sunday):**

| Indicator | Source | Alert Threshold |
|---|---|---|
| Knowledge growth (new items this week) | Knowledge Analytics Service | 0 for 4 consecutive weeks (warning) |
| Mean freshness score | Knowledge Analytics Service | < 0.60 (warning) |
| Stale items percentage | Knowledge Analytics Service | > 10% (warning) |
| Coverage gap count (empty categories) | Knowledge Analytics Service | > 5 (warning) |
| Knowledge evolution count (evolutions this week) | Knowledge Evolution Service | 0 for 4 consecutive weeks (warning) |
| Governance cases closed | Knowledge Governance Service | 0 open cases = healthy |

---

### G.3 Knowledge Engine Glossary

| Term | Definition |
|---|---|
| Candidate knowledge | A potential knowledge item extracted by the Discovery Service that has not yet been validated |
| Centrality score | A measure of how many other knowledge items connect to a given node in the knowledge graph (high centrality = high influence) |
| Claim | The precise, testable statement of what a knowledge item asserts |
| Cluster coherence | A measure of how closely related the knowledge items within a cluster are |
| Context condition | A qualifier that specifies the market or system conditions under which a knowledge item applies |
| Derived knowledge | Knowledge produced by combining other validated knowledge items through a defined reasoning process |
| Discovery | The process of identifying a candidate knowledge item from raw observations |
| Domain | The top-level category of what a knowledge item is about (MARKET, STRATEGY, AGENT, SYSTEM, RISK, PORTFOLIO, OPERATIONS) |
| Evidence | A specific observation that supports or refutes a knowledge claim |
| Evidence weight | A quality multiplier applied to evidence based on its source (live trades = 1.0; backtest = 0.70) |
| Freshness | How recently a knowledge item has received new supporting evidence |
| Governance status | One of NORMAL, UNDER_REVIEW, SUSPENDED, or CONTRADICTION_HOLD |
| Inviolable Rule | A knowledge item with `is_inviolable=True` that overrides all patterns and cannot be contradicted by data |
| Knowledge cluster | A group of related knowledge items that collectively describe a coherent aspect of the domain |
| Knowledge evolution | The process of creating a new version of a knowledge item in response to accumulated evidence |
| Knowledge graph | The network of all knowledge items connected by typed, weighted relationships |
| Knowledge level | A position (1–10) in the knowledge hierarchy, from Raw Knowledge to Meta Knowledge |
| Knowledge lineage | The complete audit trail from raw observation to current knowledge version |
| Provisional | A knowledge item with confidence < 0.55 that may be used only in low-stakes contexts |
| Quality score | The composite score across 10 quality dimensions used to assess how reliable a knowledge item is |
| Regime context | The market regime condition (BULL_TRENDING, BEAR_VOLATILE, etc.) under which a knowledge item applies |
| Validation | The 6-step process of determining whether a candidate knowledge item meets quality standards |
| Version | An immutable snapshot of a knowledge item at a specific point in time |

---