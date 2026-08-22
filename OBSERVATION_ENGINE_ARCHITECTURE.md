# OBSERVATION ENGINE ARCHITECTURE

**Document:** OBSERVATION_ENGINE_ARCHITECTURE.md  
**Version:** 1.0.0  
**Classification:** IIOS Engineering Architecture Series  
**Status:** AUTHORITATIVE  

---

## Document Purpose and Scope

This document defines the complete engineering architecture of the **Observation Engine** — the first cognitive engine of the Investment Intelligence Operating System (IIOS). The Observation Engine is the perceptual layer of the IIOS. It is the mechanism by which the system becomes aware of the world.

The Observation Engine:
- Continuously monitors the investment universe across all defined observation domains
- Converts raw information and data streams into structured, governed, quality-scored observations
- Records every observation immutably with complete timestamping, context, and lineage
- Makes observations available to all downstream analytical engines through a governed distribution layer

The Observation Engine does NOT:
- Interpret observations
- Draw conclusions from observations
- Generate predictions or forecasts
- Issue recommendations or signals
- Classify information as bullish, bearish, positive, or negative
- Make judgements about the significance of what is observed

The Observation Engine observes. All interpretation is the responsibility of downstream engines.

This document is **not** implementation. It defines the engineering architecture only — the what and the how of the engine's structure, not the code that implements it.

---

## Parent Documents

| Document | Relationship |
|---|---|
| INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md | IIOS master architecture; defines the Observation Engine's position in the system |
| MASTER_KNOWLEDGE_ARCHITECTURE.md | Defines knowledge hierarchy; Observation Engine is the base of the evidence chain |
| INFORMATION_ONTOLOGY.md | Defines all information types that the Observation Engine captures |
| ENTITY_ONTOLOGY.md | Defines all entity types that observations are attributed to |
| RELATIONSHIP_ONTOLOGY.md | Defines relationship types observed between entities |
| EVENT_ONTOLOGY.md | Defines event types that observations detect and record |
| INFORMATION_ENGINE_ARCHITECTURE.md | Information management layer; provides managed information objects as inputs |
| ENTITY_ENGINE_ARCHITECTURE.md | Provides canonical entity identity for observation attribution |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | Consumes observations as relationship evidence |
| EVENT_ENGINE_ARCHITECTURE.md | Consumes observations as event detection inputs |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | Consumes observations as the raw material of evidence |
| CORE_FRAMEWORK_ARCHITECTURE.md | Core IIOS services consumed by the Observation Engine |
| ENGINEERING_STANDARDS.md | Standards governing all IIOS architecture documents |

---

## Observation Engine Position in the IIOS

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INVESTMENT UNIVERSE                                   │
│  [Equity Markets] [Bond Markets] [Derivatives] [FX] [Commodities]              │
│  [Corporate Actions] [Macroeconomic Releases] [News] [Alternative Data]        │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │ raw data streams
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         INFORMATION ENGINE                                      │
│  (acquires, validates, normalises, enriches, distributes managed information)   │
└──────────────────────────────────┬──────────────────────────────────────────────┘
                                   │ managed information objects
                                   ▼
┌═════════════════════════════════════════════════════════════════════════════════╗
║                        OBSERVATION ENGINE  ◄── THIS DOCUMENT                  ║
║  (perceives, records, classifies, timestamps, and distributes structured       ║
║   observations — the perceptual layer of the IIOS)                             ║
║                                                                                 ║
║  Domain Collectors:                                                             ║
║  [Market] [Company] [Sector] [Macro] [Portfolio] [Risk] [Order] [Trade]        ║
║  [News] [Social] [Alternative] [AI] [System] [Behavior] [Temporal]             ║
╚══════════════════════════════════════════════════════════════════════════════════╝
                                   │ structured observations
                        ┌──────────┼───────────┐
                        ▼          ▼           ▼
           ┌────────────────┐  ┌───────────┐  ┌─────────────────┐
           │ Evidence Engine│  │Event Engine│  │Knowledge Engine │
           │ (assembles     │  │(detects    │  │(infers from     │
           │  evidence from │  │ events)    │  │ evidence chains)│
           │  observations) │  └───────────┘  └─────────────────┘
           └────────────────┘
                        │
                        ▼
           ┌────────────────────────────────────────┐
           │ Analytical Layers                      │
           │ [Regime Engine] [Strategy Engine]      │
           │ [Risk Engine] [Decision Engine]        │
           └────────────────────────────────────────┘
```

---

## Observation Engine Information Flow

```
Information Object (from Information Engine)
    │
    ▼
Observation Collector (domain-specific receptor)
    │ detects observable content
    ▼
Observation Detector (what is observable here?)
    │ extracted observation candidates
    ▼
Observation Validator (is this a valid observation?)
    │ validated observation records
    ▼
Observation Timestamp Manager (when exactly?)
    │ timestamped records
    ▼
Observation Context Manager (under what conditions?)
    │ context-enriched records
    ▼
Observation Classification Engine (what type?)
    │ classified observations
    ▼
Observation Quality Manager (how trustworthy?)
    │ quality-scored observations
    ▼
Observation Registry (canonical storage)
    │
    ├──► Observation Index Manager (searchable)
    ├──► Observation History Manager (temporal record)
    ├──► Observation Aggregator (aggregated views)
    └──► Observation Distribution (to consumers)
```

---

## Table of Contents

| Section | Title |
|---|---|
| Part I | Observation Philosophy — 20 Conceptual Distinctions |
| Part II | Observation Engine Architecture — 16 Observation Domains |
| Part III | Core Components — 22 Components across 6 Clusters |
| Part IV | Observation Lifecycle — 12 Stages with State Machine |
| Part V | Observation Services — 17 Service Definitions |
| Part VI | Observation Processing Architecture — 15 Processing Patterns |
| Part VII | Observation Quality Framework — 14 Quality Dimensions |
| Part VIII | Observation Governance — 11 Governance Dimensions |
| Part IX | Observation Constitution — 70 Constitutional Rules |
| Part X | Observation Readiness Checklist — 14 Sections |
| Supplement A | Observation Type Catalogue |
| Supplement B | Component Interface Reference |
| Supplement C | Processing Pipeline Patterns |
| Supplement D | Quality Framework Reference |
| Supplement E | Governance Decision Records |
| Supplement F | Anti-Pattern Reference |
| Supplement G | Observation Glossary |
| Appendix | Operational Runbook |
| Footer | Summary Metrics and Compliance Checklist |

---
## PART I — OBSERVATION PHILOSOPHY

### 1.1 The Purpose of Observation

Before the IIOS can reason, it must perceive. Before it can conclude, it must notice. Before it can recommend, it must first have observed. The Observation Engine is the IIOS's instrument of perception — the mechanism by which the system registers the state of the investment universe at every moment.

The discipline of the Observation Engine is total restraint from interpretation. Every human failure in investment management can be traced, at some level, to a failure to observe clearly — to seeing what was expected rather than what was present, to conflating observation with conclusion, to mistaking the act of noticing with the act of understanding. The Observation Engine is designed to make this failure architecturally impossible.

An observation is the purest epistemic act: this happened, here, at this time, under these conditions. Nothing more. The Observation Engine records this act faithfully, completely, and without opinion.

**Why observations must never contain interpretation:**

1. Interpretation requires a model. The model may be wrong. If interpretation is embedded in the observation, the observation becomes model-dependent — it inherits the model's errors. A pure observation, free of interpretation, remains valid even when the model that would have interpreted it proves incorrect.

2. The same observation may have different interpretations in different contexts. A rising VIX observed in a bear market has different significance than the same rising VIX observed in a bull market. If the observation carries an interpretation, it becomes context-locked. As a pure record, it can be re-evaluated in any context.

3. Multiple downstream engines consume the same observations for different purposes. The Evidence Engine uses observations to build evidence chains. The Event Engine uses observations to detect event occurrences. The Regime Engine uses observations to classify market states. If observations carried interpretations, each engine would receive pre-interpreted inputs that conflict with their own interpretive frameworks.

4. Interpretations change over time as models improve and market understanding deepens. Observations do not change — they are fixed records of what was. If observations and interpretations are fused, improving the model requires reprocessing all historical observations, which is architecturally untenable.

5. Regulatory and audit requirements demand a clear record of what the system observed versus what it concluded. Fusing observation and interpretation makes this distinction impossible.

---

### 1.2 Conceptual Distinctions — 20 Terms

The following 20 distinctions define the conceptual boundaries within which the Observation Engine operates. Imprecise use of these terms in architecture leads to engines that observe and conclude simultaneously, undermining the separation of concerns that makes the IIOS analytically reliable.

---

#### 1.2.1 Information

**Information** is data that has been validated, typed, and contextualised by the Information Engine. Information is the input to the Observation Engine. Information exists in the Information Registry, governed, versioned, and quality-scored. When the Observation Engine processes a managed information object, it produces zero or more observations from that information.

The critical distinction: information is what the system holds; an observation is what the system perceives from what it holds. A price quote is information. The act of noticing that a price crossed a threshold is an observation derived from that information.

---

#### 1.2.2 Observation

An **Observation** is a structured, immutable, timestamped record of a perceived state or change in the investment universe. An observation is what the Observation Engine produces. It is defined by:
- What was perceived (the observed content — a value, a state, a change)
- What entity was observed (the subject of the observation)
- When it was perceived (the observation timestamp)
- Under what conditions it was perceived (the observation context)
- From what information source it was derived (the observation lineage)
- How reliable the perception is (the observation confidence)

An observation never contains a conclusion about what the observed state means. It records only the state itself.

---

#### 1.2.3 Evidence

**Evidence** is an observation (or collection of observations) that has been assembled by the Evidence Engine to support or refute a specific hypothesis. Evidence is directional — it points toward or away from a conclusion. An observation becomes evidence only when the Evidence Engine assigns it a role in a reasoning chain. The Observation Engine produces observations; it is the Evidence Engine's responsibility to select and assemble them as evidence. The Observation Engine never designates an observation as evidence.

---

#### 1.2.4 Knowledge

**Knowledge** is a justified, reliable conclusion derived from evidence through reasoning. Knowledge is the output of the Knowledge Engine. The Observation Engine is foundationally separated from knowledge by two layers: observation → evidence → knowledge. No element of the Observation Engine's output constitutes knowledge. An observation that NIFTY50 is at 22,345 is not knowledge that the market is bullish; it is simply a record that a measurement was made.

---

#### 1.2.5 Signal

A **Signal** is a derived, directional indicator produced by an analytical engine from one or more observations — indicating a likely state or directional tendency. Signals are interpretations. The Observation Engine does not produce signals. A rising RSI is not a signal; it is an observation of a computed indicator value. The interpretation "RSI rising = potential momentum" is a signal produced by a strategy engine from that observation.

---

#### 1.2.6 Indicator

An **Indicator** is a computed metric derived from a series of observations. Indicators (RSI, MACD, ATR, Bollinger Bands, etc.) are computed from price observations and are themselves observations — specifically, observations of computed states derived from price history. The Observation Engine records the computed values of indicators. It does not interpret whether those values are high or low relative to some norm. Computing that RSI = 72 is an observation; interpreting that RSI = 72 as "overbought" is an interpretation.

---

#### 1.2.7 Event

An **Event** is a timestamped, immutable occurrence — a change in system or world state. Events are managed by the Event Engine. Observations can be the inputs that the Event Engine uses to detect that an event has occurred. For example: a series of price observations showing a 5% intraday drop is input to the Event Engine, which detects and records the SIGNIFICANT_INTRADAY_DROP event. The Observation Engine's role is to record the price observations; the Event Engine's role is to detect and classify the event.

---

#### 1.2.8 Pattern

A **Pattern** is a recurring structural feature in a series of observations — a temporal or spatial regularity. The Observation Engine records observations; it does not detect patterns. Pattern detection is the responsibility of the Pattern Detection Engine (a component of the Knowledge Engine). However, the Observation Engine may record a pattern-indicating observation — for example, it can observe that a price has traced a specific geometric shape (head-and-shoulders configuration). This is an observation of a geometric relationship, not a pattern prediction.

---

#### 1.2.9 Fact

A **Fact** is an observation that has been corroborated to a high confidence threshold — an observation treated as ground truth. The Observation Engine contributes to fact formation by providing high-quality, multi-source-corroborated observations, but the designation of an observation as a Fact is made by the Knowledge Engine. The Observation Engine records the NIFTY50 closing price as 22,345.60; the Knowledge Engine establishes this as a fact after corroboration.

---

#### 1.2.10 Measurement

A **Measurement** is a specific, quantified observation of a numerically expressed state. "NIFTY50 = 22,345.60 at 15:30:00" is a measurement. Measurements are the most precise category of observation — they have a numeric value, a unit, an as-of timestamp, and a measurement error specification. The Observation Engine records measurements as a specific observation type within the broader observation taxonomy.

---

#### 1.2.11 Observation Context

**Observation Context** is the state of the investment universe and the IIOS at the moment an observation was made. Context is what makes an observation interpretable — without context, observations lose meaning. The Observation Context record captures: the active market session, the prevailing market regime (as determined by the most recent regime observation), the VIX level, the NIFTY50 level, concurrent significant events, and the liquidity state. Context is captured by the Context Manager and attached to every observation. Context is not interpretation — it is a structured description of conditions that existed alongside the observation.

---

#### 1.2.12 Observation Confidence

**Observation Confidence** measures the IIOS's certainty that an observation accurately represents the true state of the investment universe. Confidence is affected by: the trust tier of the information source from which the observation was derived; the number of independent sources that corroborate the observation; the freshness of the underlying information; and the completeness of the observation record. Confidence is in [0.0, 1.0] and is a time-varying quantity — an observation's confidence may decrease as the underlying information becomes stale.

---

#### 1.2.13 Observation Quality

**Observation Quality** is the multi-dimensional assessment of an observation's fitness for use by downstream engines. The Observation Engine uses a 14-dimension quality framework (see Part VII) to compute the Observation Quality Score (OQS). Quality is distinct from confidence: confidence measures the certainty that the observation is correct; quality measures the completeness, freshness, consistency, and coverage of the observation record. An observation can have high confidence but low quality (for example, if it is missing optional fields needed by a downstream consumer).

---

#### 1.2.14 Observation Timestamp

An **Observation Timestamp** is the precise moment at which the observed state existed in the real world. The observation timestamp is the most important temporal attribute of an observation — it answers "when did this happen?" Every observation has exactly one observation_timestamp. This is distinct from the capture_timestamp (when the IIOS became aware of the state) and the storage_timestamp (when the observation was written to the Registry). The gap between observation_timestamp and capture_timestamp is the observation latency.

---

#### 1.2.15 Observation Source

An **Observation Source** is the information object or data stream from which an observation was derived. Every observation has at least one source reference. The source determines the initial confidence contribution from the source trust tier. Multiple observations from multiple sources about the same state may be corroborated to produce a single high-confidence composite observation.

---

#### 1.2.16 Observation Window

An **Observation Window** is the temporal range over which a specific observation is computed or applies. A 20-day moving average observation has an observation window of 20 trading days ending at the observation timestamp. A rolling volatility observation has an observation window specified by the window_days parameter. The observation window is a mandatory field for any observation that represents a computed aggregate over time.

---

#### 1.2.17 Observation Scope

**Observation Scope** defines which entities and domains the observation applies to or relates to. Scope has two dimensions: entity scope (which entities are observed?) and domain scope (which observation domain does this belong to — Market, Company, Sector, Macro, etc.). Scope is assigned by the Classification Engine during observation classification.

---

#### 1.2.18 Observation Granularity

**Observation Granularity** is the level of detail at which an observation is recorded. Price observations may be captured at tick granularity (every trade), minute granularity (OHLCV per minute), or daily granularity (EOD OHLCV). Macro observations may be captured at monthly or quarterly granularity. Granularity is a property of the observation type and is defined in the Observation Catalog for each type.

---

#### 1.2.19 Observation Frequency

**Observation Frequency** is how often observations of a given type are made. Some observations are continuous (tick data — potentially thousands per second). Some are periodic (regulatory filings — quarterly). Some are event-triggered (corporate action observations — triggered when an action is announced). Frequency is a type-level property stored in the Observation Catalog.

---

#### 1.2.20 Observation Aggregation

**Observation Aggregation** is the process of combining multiple individual observations into a composite observation that represents a higher-level state. A daily OHLCV bar is an aggregation of all tick observations for that day. A sector-average P/E observation is an aggregation of individual company P/E observations. Aggregated observations are clearly labelled as such and carry references to all their constituent observations in their lineage record.

---

### 1.3 Observation Engine Design Principles

| Principle | Statement |
|---|---|
| Perception only | The Observation Engine perceives and records; it never interprets, concludes, or recommends. |
| Immutability | Every observation, once written, is immutable. Corrections create new versions; old versions are preserved. |
| Complete attribution | Every observation is attributed to its source, its entity subjects, and its context. |
| Temporal precision | Every observation has a precisely specified observation timestamp. |
| Quality transparency | Every observation carries an explicit quality score; consumers always know the quality of what they are using. |
| Lineage always | Every observation can be traced to its origin through its complete derivation lineage. |
| Context richness | Every observation is accompanied by the context in which it was made. |
| Governance mandatory | Every observation is owned, classified, secured, and retained per governance policy. |
| Searchability | Every observation is indexed and searchable by any combination of entity, domain, type, time range, and quality tier. |
| Auditability | Every creation, read, update (versioning), and archive operation is recorded in the audit trail. |

---
## PART II — OBSERVATION ENGINE ARCHITECTURE

### 2.1 Architectural Overview

The Observation Engine organises all observations into 16 observation domains. Each domain is a distinct area of the investment universe that the IIOS observes. Domains are not mutually exclusive — a single information object may trigger observations in multiple domains. Domains are not hierarchical in terms of importance; they are parallel observation channels that operate concurrently.

```
┌────────────────────────────────────────────────────────────────────────┐
│                    OBSERVATION ENGINE DOMAIN ARCHITECTURE              │
│                                                                        │
│  Domain 01: OBSERVATION ROOT   (abstract base — all observations)      │
│                                                                        │
│  Domain 02: MARKET OBSERVATION                                         │
│    ├─ Price Observation  ├─ Volume Observation  ├─ Depth Observation  │
│    ├─ Volatility Observation   └─ Derivative Observation              │
│                                                                        │
│  Domain 03: COMPANY OBSERVATION                                        │
│    ├─ Earnings Observation  ├─ Financial Observation                  │
│    ├─ Corporate Action Observation  └─ Management Observation         │
│                                                                        │
│  Domain 04: SECTOR OBSERVATION                                         │
│    ├─ Sector Performance Observation  ├─ Sector Rotation Observation  │
│    └─ Sector Breadth Observation                                       │
│                                                                        │
│  Domain 05: MACRO OBSERVATION                                          │
│    ├─ Economic Indicator Observation  ├─ Monetary Observation         │
│    ├─ Currency Observation  └─ Commodity Observation                  │
│                                                                        │
│  Domain 06: PORTFOLIO OBSERVATION                                      │
│    ├─ Holding Observation  ├─ PnL Observation                         │
│    └─ Allocation Observation                                           │
│                                                                        │
│  Domain 07: RISK OBSERVATION                                           │
│    ├─ Volatility Risk Observation  ├─ Correlation Observation         │
│    ├─ Drawdown Observation  └─ Exposure Observation                   │
│                                                                        │
│  Domain 08: ORDER OBSERVATION                                          │
│    ├─ Order State Observation  └─ Order Book Observation              │
│                                                                        │
│  Domain 09: TRADE OBSERVATION                                          │
│    ├─ Fill Observation  ├─ Trade Lifecycle Observation                │
│    └─ Slippage Observation                                             │
│                                                                        │
│  Domain 10: NEWS OBSERVATION                                           │
│    ├─ News Presence Observation  └─ News Coverage Observation         │
│                                                                        │
│  Domain 11: SOCIAL OBSERVATION                                         │
│    ├─ Mention Volume Observation  └─ Engagement Observation           │
│                                                                        │
│  Domain 12: ALTERNATIVE DATA OBSERVATION                               │
│    ├─ Web Observation  └─ Supply Chain Observation                    │
│                                                                        │
│  Domain 13: AI OBSERVATION                                             │
│    ├─ Model Output Observation  └─ Score Observation                  │
│                                                                        │
│  Domain 14: SYSTEM OBSERVATION                                         │
│    ├─ Performance Observation  └─ Health Observation                  │
│                                                                        │
│  Domain 15: BEHAVIOR OBSERVATION                                       │
│    ├─ Flow Observation  └─ Positioning Observation                    │
│                                                                        │
│  Domain 16: TEMPORAL OBSERVATION                                       │
│    ├─ Calendar Observation  └─ Cycle Observation                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Domain Definitions

---

#### 2.2.1 Domain 01 — Observation Root

The Observation Root is the abstract base domain. It defines the mandatory properties shared by every observation in every other domain. No observation is an instance of Observation Root — every observation is an instance of one of the 15 concrete domains. Observation Root defines:

- observation_id (canonical identifier)
- observation_type (type code from Observation Catalog)
- domain (one of the 15 concrete domains)
- entity_refs (one or more entity identifiers observed)
- observation_timestamp (moment the state was observed in the world)
- capture_timestamp (moment the IIOS captured the observation)
- source_ref (reference to the information object from which derived)
- context_id (observation context record reference)
- observation_quality_score (OQS in [0.0, 1.0])
- observation_confidence (confidence in [0.0, 1.0])
- freshness_tier (FRESH, AGING, STALE, CRITICAL_STALE, EXPIRED)
- lineage_id (reference to lineage record)
- version_number (version of this observation record)
- governance_tier (CRITICAL, HIGH, MEDIUM, LOW)
- status (ACTIVE, SUPERSEDED, ARCHIVED, RETIRED)

---

#### 2.2.2 Domain 02 — Market Observation

**Market Observations** are observations of the traded markets — the prices, volumes, depths, volatilities, and derivative structures of financial instruments. Market Observations are the highest-frequency domain: they are produced continuously during market hours.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Price Observation | The price level of a financial instrument at a specific moment: bid, ask, last, mid |
| Volume Observation | The quantity of an instrument traded in a period: volume, open interest, turnover |
| Depth Observation | The order book structure: bid depth levels, ask depth levels, spread |
| Volatility Observation | Observed volatility measures: realised volatility, implied volatility, VIX level |
| Derivative Observation | Options and futures state: options chain structure, futures basis, term structure |
| Index Observation | Index level, index composition change observation |
| Session Observation | Opening, closing, intraday high/low, after-hours activity |
| Market Breadth Observation | Advance-decline ratio, stocks above moving averages, new highs/lows |

**Key characteristics:**
- Sub-second granularity for tick-level observations
- Continuous during market hours (09:15–15:30 IST for NSE)
- Highest observation frequency domain
- Critical governance tier for execution-relevant observations

**Example observation records:**

```
Market Price Observation:
  observation_id:        OBS-MKT-PRC-20260703-00014823
  entity_ref:            TATASTEEL_NSE
  observation_type:      PRICE_QUOTE
  bid:                   156.30
  ask:                   156.35
  last:                  156.32
  observation_timestamp: 2026-07-03T11:42:37.423Z
  session:               MARKET_OPEN

Market Volatility Observation:
  observation_id:        OBS-MKT-VOL-20260703-00002341
  entity_ref:            NIFTY50_INDEX
  observation_type:      REALISED_VOLATILITY
  window_days:           20
  vol_annualised:        0.1842
  observation_timestamp: 2026-07-03T09:30:00Z
```

---

#### 2.2.3 Domain 03 — Company Observation

**Company Observations** are observations of the state of publicly listed companies — their financial results, corporate actions, management changes, and regulatory disclosures. Company Observations occur at much lower frequency than Market Observations (quarterly earnings, periodic filings) but carry very high informational weight.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Earnings Observation | Reported EPS, revenue, margins; comparison to prior period and estimates |
| Balance Sheet Observation | Observed asset levels, liability levels, debt ratios, working capital |
| Cash Flow Observation | Observed operating, investing, financing cash flows |
| Corporate Action Observation | Observed announcement of dividend, split, bonus, rights, buyback |
| Management Change Observation | Observed appointment, departure, or role change of key officers |
| Filing Observation | Observed exchange filing, regulatory disclosure, annual report publication |
| Guidance Observation | Observed forward guidance issued by management |
| Analyst Coverage Observation | Observed change in analyst rating, target price, or coverage initiation |

**Observation frequency:** Quarterly (earnings), ad-hoc (corporate actions, filings, management changes), annually (annual reports).

**Governance tier:** HIGH to CRITICAL depending on sub-domain (corporate actions are CRITICAL; analyst coverage is MEDIUM).

---

#### 2.2.4 Domain 04 — Sector Observation

**Sector Observations** aggregate observations across all companies within a sector to capture sector-level states. These observations are derived — they are computed from Company and Market Observations.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Sector Performance Observation | Observed aggregate return of a sector's constituent instruments |
| Sector Relative Performance Observation | Observed performance of a sector relative to the NIFTY50 |
| Sector Breadth Observation | Proportion of sector constituents advancing vs declining |
| Sector Rotation Observation | Observed pattern of capital movement across sectors |
| Sector Valuation Observation | Observed aggregate P/E, P/B, dividend yield for the sector |
| Sector Volume Observation | Observed aggregate volume and open interest for the sector |

---

#### 2.2.5 Domain 05 — Macro Observation

**Macro Observations** record the state of the macroeconomic environment — economic indicators, monetary policy settings, currency levels, and commodity prices. These observations form the global backdrop against which all market observations are contextualised.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Economic Indicator Observation | Observed GDP, CPI, IIP, PMI, WPI release values |
| Monetary Policy Observation | Observed RBI repo rate, reverse repo, CRR, SLR, policy stance |
| Currency Observation | Observed USD/INR rate, DXY level, cross rates |
| Commodity Observation | Observed Brent crude, gold, silver, agricultural commodity prices |
| Government Bond Observation | Observed 10-year G-Sec yield, yield curve shape |
| Global Market Observation | Observed S&P500 level, Nikkei225 level, DAX level (for global context) |
| FII/DII Flow Observation | Observed net FII and DII buying/selling for the session |

**Observation frequency:** Monthly (CPI, IIP), quarterly (GDP), daily (currency, commodity, bond), session (FII/DII flow), as-announced (monetary policy).

---

#### 2.2.6 Domain 06 — Portfolio Observation

**Portfolio Observations** record the state of the managed portfolios — holdings, valuations, P&L, and allocation at every point in time.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Holding Observation | Observed quantity and current value of a position in the portfolio |
| Portfolio Value Observation | Observed total portfolio equity, cash, and unrealised P&L |
| PnL Observation | Observed realised and unrealised P&L at portfolio and position level |
| Allocation Observation | Observed allocation percentages by strategy, sector, instrument |
| Cash Observation | Observed available cash and cash utilisation |
| Drawdown Observation | Observed current drawdown from portfolio high-water mark |

**Observation frequency:** Real-time for holdings and portfolio value during market hours; EOD for summary snapshots.

---

#### 2.2.7 Domain 07 — Risk Observation

**Risk Observations** record the observed risk state of the portfolio and individual positions — without drawing conclusions about whether risk is acceptable or excessive.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Volatility Risk Observation | Observed current implied and realised volatility levels |
| Correlation Observation | Observed pairwise correlations between portfolio positions |
| VaR Observation | Observed Value-at-Risk computed at specified confidence levels |
| Drawdown Risk Observation | Observed drawdown level and trajectory |
| Concentration Observation | Observed concentration of portfolio in a single instrument, sector, or strategy |
| Greeks Observation | Observed delta, gamma, theta, vega of options positions |
| Stress Scenario Observation | Observed portfolio value under predefined stress scenarios |

---

#### 2.2.8 Domain 08 — Order Observation

**Order Observations** record the state of every order submitted by the execution layer — without evaluating whether the order was well-timed or appropriate.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Order State Observation | Observed current status of an order (PENDING, PLACED, PARTIAL, FILLED, CANCELLED) |
| Order Book Position Observation | Observed position of a limit order in the order book |
| Order Price Observation | Observed relationship between order price and current market |
| Order Age Observation | Observed elapsed time since order submission |

---

#### 2.2.9 Domain 09 — Trade Observation

**Trade Observations** record the complete lifecycle of executed trades — fills, slippage, duration, and outcome metrics.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Fill Observation | Observed fill price, fill quantity, fill timestamp for each order execution |
| Trade Entry Observation | Observed conditions at the moment a trade was initiated |
| Trade Exit Observation | Observed conditions at the moment a trade was closed |
| Slippage Observation | Observed difference between expected price and actual fill price |
| Trade Duration Observation | Observed hold duration of a completed trade |
| Commission Observation | Observed commission, taxes, and charges for a trade |

---

#### 2.2.10 Domain 10 — News Observation

**News Observations** record the presence, volume, and coverage breadth of news about entities in the investment universe — without assessing the news as positive or negative.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| News Presence Observation | Observed publication of news articles mentioning a specific entity |
| News Volume Observation | Observed count of news articles about an entity in a time window |
| News Source Observation | Observed diversity of sources covering an entity |
| News Recency Observation | Observed frequency of recent (< 24 hours) news about an entity |

---

#### 2.2.11 Domain 11 — Social Observation

**Social Observations** record the observable presence of an entity in social media and online discourse — without interpreting the sentiment or significance.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Mention Volume Observation | Observed count of mentions of an entity on monitored platforms |
| Engagement Observation | Observed likes, shares, comments on posts mentioning an entity |
| Trending Observation | Observed elevation of an entity's mention rate above baseline |

---

#### 2.2.12 Domain 12 — Alternative Data Observation

**Alternative Data Observations** record non-traditional data signals about entities in the investment universe — web activity, supply chain indicators, satellite-derived data, and other alternative sources.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Web Traffic Observation | Observed web traffic metrics for a company's digital properties |
| Job Posting Observation | Observed count and category of job postings by a company |
| Supply Chain Observation | Observed supply chain activity indicators (shipping, freight, logistics) |
| Patent Observation | Observed patent filing activity by a company |

---

#### 2.2.13 Domain 13 — AI Observation

**AI Observations** record the outputs of AI and ML models within the IIOS — including model predictions, confidence scores, and anomaly detections. AI Observations are observations of the AI system's state, not interpretations.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Model Output Observation | Observed output value of an ML model for a specific input |
| Model Confidence Observation | Observed confidence score of an ML model's prediction |
| Anomaly Detection Observation | Observed anomaly score for an entity or time series |
| Model Performance Observation | Observed model accuracy metrics over a recent evaluation window |

---

#### 2.2.14 Domain 14 — System Observation

**System Observations** record the observable state of the IIOS itself — performance metrics, health indicators, and operational parameters.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Latency Observation | Observed processing latency for system components |
| Throughput Observation | Observed message processing rates |
| Error Rate Observation | Observed error rates across system components |
| Resource Observation | Observed CPU, memory, disk, network utilisation |
| Cycle Health Observation | Observed health status of the IIOS's trading cycle |

---

#### 2.2.15 Domain 15 — Behavior Observation

**Behavior Observations** record the observable behaviour patterns of market participants — institutional flows, short interest, and positioning data.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Institutional Flow Observation | Observed FII and DII net flows by session and category |
| Short Interest Observation | Observed short interest and short ratio for an instrument |
| Options Positioning Observation | Observed put-call ratio, max pain level, open interest concentration |
| Futures Positioning Observation | Observed futures roll positions, basis, term structure |

---

#### 2.2.16 Domain 16 — Temporal Observation

**Temporal Observations** record the observable state of the investment calendar — expiry events, seasonality patterns, and cyclical positioning.

**Sub-domains:**

| Sub-domain | What is observed |
|---|---|
| Expiry Observation | Observed proximity to F&O expiry (days to expiry, expiry week flag) |
| Earnings Season Observation | Observed proportion of a sector's companies that have reported in the current season |
| Calendar Event Observation | Observed scheduled economic releases, RBI meetings, budget events |
| Seasonality Observation | Observed seasonal period (Q1–Q4, budget season, harvest season) |
| Cycle Position Observation | Observed position in multi-year economic or credit cycles |

---
## PART III — CORE COMPONENTS

The Observation Engine is implemented through 22 tightly co-ordinated components. Each component has a single, well-defined responsibility. Components are organised into six operational clusters: Registry & Catalog, Collection, Capture & Validation, Context & Classification, Quality, and Governance.

---

### 3.1 REGISTRY & CATALOG CLUSTER

---

#### Component 01 — Observation Registry

**Purpose:** The Observation Registry is the authoritative, canonical store for all observation records. Every observation that the Observation Engine produces is stored as a record in the Registry. The Registry is the single source of truth for all IIOS observations.

**Responsibilities:**
- Accept new observation records submitted by the Capture pipeline
- Assign canonical observation_id on creation
- Store the complete observation record including all mandatory and optional fields
- Maintain the version chain for each observation (immutable versioning)
- Expose retrieval APIs to all authorised consumers
- Enforce read-only access to superseded versions
- Provide bulk retrieval APIs for historical analysis workloads
- Report Registry statistics: observation volume, freshness distribution, quality distribution, domain distribution

**Inputs:**
- Quality-scored, classified observation records from the Classification Engine
- Version update notifications from the Observation History Manager
- Archival instructions from the Observation Archive Manager

**Outputs:**
- Canonical observation records (to any authorised consumer)
- Registry statistics and health metrics
- Observation identifiers issued at creation time

**Dependencies:**
- Observation Catalog (type validation)
- Observation History Manager (version chain management)
- Observation Governance Manager (access control)

**Failure Handling:**
- Registry store unavailable → queue incoming observations in durable ingestion buffer; reject reads with SERVICE_UNAVAILABLE; alert monitoring system
- Version chain corruption → quarantine affected observation_ids; alert Governance Manager; do not serve corrupted versions

**Internal organisation:**
```
Observation Registry
    ├── Active Observations Index (observation_id → current record)
    ├── Version Archives (observation_id → version_chain[])
    ├── Lineage Graph (derivation relationships among observations)
    ├── Domain Index (domain → list of observation_ids)
    ├── Entity Cross-Reference (entity_id → list of observation_ids)
    ├── Type Index (type_code → list of observation_ids)
    ├── Source Cross-Reference (source_ref → list of observation_ids)
    └── Freshness Monitor (domain → freshness distribution snapshot)
```

---

#### Component 02 — Observation Catalog

**Purpose:** The Observation Catalog is the schema registry of the Observation Engine. It defines all valid observation types — their required fields, freshness SLAs, confidence floors, governance tiers, and retention policies.

**Responsibilities:**
- Maintain the authoritative list of all observation types across all 16 domains
- Define required and optional fields for each observation type
- Store freshness SLAs per type (how quickly does this observation type become stale?)
- Store confidence floors per type (minimum acceptable confidence)
- Define governance classification and retention period per type
- Support addition of new observation types via the Evolution Manager
- Provide type validation services to the Observation Validator

**Inputs:**
- Type registration requests from the Evolution Manager
- Type definition queries from the Validator, Classification Engine, Collector
- Deprecation instructions from the Governance Manager

**Outputs:**
- Type definition records (schema, constraints, SLAs, governance)
- Type validation responses
- Catalog statistics

**Catalog record structure:**

| Field | Description |
|---|---|
| type_code | Unique observation type identifier |
| type_name | Human-readable name |
| domain | Which of the 16 domains this type belongs to |
| required_fields | List of mandatory fields |
| optional_fields | List of permitted optional fields |
| freshness_sla_seconds | Time-to-stale for this observation type |
| confidence_floor | Minimum acceptable confidence |
| governance_tier | CRITICAL / HIGH / MEDIUM / LOW |
| retention_months | Retention period |
| frequency_class | TICK / REAL_TIME / INTRADAY / DAILY / PERIODIC / AD_HOC |
| observation_window | Whether this type requires an observation window specification |
| status | ACTIVE / DEPRECATED / EXPERIMENTAL |

---

### 3.2 COLLECTION CLUSTER

---

#### Component 03 — Observation Collector

**Purpose:** The Observation Collector is the domain-specific receptor that monitors managed information objects from the Information Engine and extracts observable content for each domain. Each of the 15 concrete domains has a dedicated Collector sub-component.

**Responsibilities:**
- Subscribe to the Information Engine's Distribution Service for all information types relevant to each domain
- Receive managed information objects as they arrive from the Distribution Service
- Extract observable content from each information object according to domain-specific extraction rules
- Package extracted content as candidate observation records for submission to the Observation Detector
- Maintain collection metrics (volume received, extraction success rate, extraction failures)
- Alert when expected information flows are absent (missing market data, missing macro releases)

**Collection architecture:**

```
Information Engine Distribution Layer
    │
    ├── Market Collector ──────────► Market Observation candidates
    ├── Company Collector ──────────► Company Observation candidates
    ├── Sector Collector ──────────► Sector Observation candidates
    ├── Macro Collector ──────────── Macro Observation candidates
    ├── Portfolio Collector ────────► Portfolio Observation candidates
    ├── Risk Collector ────────────► Risk Observation candidates
    ├── Order Collector ──────────── Order Observation candidates
    ├── Trade Collector ──────────── Trade Observation candidates
    ├── News Collector ──────────────News Observation candidates
    ├── Social Collector ──────────► Social Observation candidates
    ├── Alternative Collector ─────► Alternative Data Observation candidates
    ├── AI Collector ──────────────► AI Observation candidates
    ├── System Collector ──────────► System Observation candidates
    ├── Behavior Collector ────────► Behavior Observation candidates
    └── Temporal Collector ────────► Temporal Observation candidates
```

**Inputs:**
- Managed information objects pushed by the Information Engine Distribution Manager
- Collector configuration (which information types each domain collector subscribes to)

**Outputs:**
- Candidate observation records (unvalidated, unclassified) delivered to the Observation Detector

**Failure Handling:**
- Information source absent → alert; record gap in observation completeness log
- Extraction failure → quarantine source record; log extraction error; alert domain owner

---

#### Component 04 — Observation Detector

**Purpose:** The Observation Detector applies domain-specific detection rules to candidate observation records to determine which candidates represent genuine observable states. Not all information generates an observation — only information that represents a meaningful perceptible state of the world.

**Responsibilities:**
- Apply domain-specific detection rules to candidate observation records
- Determine whether each candidate represents a valid observable state
- Apply deduplication to suppress identical candidates from the same source
- Apply throttling rules to prevent observation flood from high-frequency sources
- Submit valid candidates to the Observation Validator
- Log detection statistics (candidates received, observations detected, deduplication rate)

**Detection rules by domain:**

| Domain | Example detection rules |
|---|---|
| Market | Detect: any price tick; any bar open/close; any threshold crossing; any unusual spread widening |
| Company | Detect: any filing; any earnings release; any corporate action announcement; any management change |
| Sector | Detect: sector performance divergence from prior day; sector breadth change > threshold |
| Macro | Detect: any macroeconomic release; any central bank announcement; any significant currency move |
| Portfolio | Detect: any position change; any P&L change > threshold; any drawdown level change |
| Risk | Detect: any volatility level change > threshold; any correlation regime shift |
| Order | Detect: any order state change; any order book position change |
| Trade | Detect: any fill event; any trade closure |
| News | Detect: any new article mentioning tracked entity; any volume spike |
| Temporal | Detect: expiry proximity flags; earnings season transitions; scheduled calendar events |

**Inputs:**
- Candidate observation records from the Observation Collector

**Outputs:**
- Validated candidates submitted to the Observation Validator
- Detection log (candidates assessed, detection decisions, suppressed duplicates)

---

### 3.3 CAPTURE & VALIDATION CLUSTER

---

#### Component 05 — Observation Recorder

**Purpose:** The Observation Recorder is the persistence gateway for all observation records. It receives validated, classified, quality-scored observations and writes them to the Observation Registry, ensuring durability and consistency.

**Responsibilities:**
- Receive final observation records from the Classification Engine
- Assign the observation to the correct storage tier based on domain and freshness requirements
- Write the observation to the Observation Registry with full acknowledgment
- Update the version chain for any observation that represents an update to a prior observation
- Route observations to the Observation Index Manager for indexing
- Route observations to the Observation History Manager for temporal recording
- Log all write operations in the Audit Manager

**Inputs:**
- Final, quality-scored, classified observation records from the Classification Engine

**Outputs:**
- Storage acknowledgment (observation_id, storage_tier, timestamp)
- Index update requests to the Index Manager
- Audit write records to the Audit Manager

**Failure Handling:**
- Storage failure → retry 3 times; if persistent, alert monitoring; queue in durable buffer; do not lose observations
- Index update failure → queue index updates for later processing; alert; continue recording
- Partial write → roll back; do not record partial observations; retry from full record

---

#### Component 06 — Observation Identity Manager

**Purpose:** The Identity Manager assigns and manages canonical identifiers for all observation records. It ensures global uniqueness and enables identity resolution across observations from multiple sources about the same perceived state.

**Responsibilities:**
- Generate globally unique observation_id values on demand
- Maintain source-to-canonical identity mappings
- Detect and manage observation identity conflicts (same perceived state assigned two observation_ids)
- Provide identity resolution services
- Manage entity references within observation records (validate that entity_ids are valid)

**Canonical ID format:**
```
OBS-{DOMAIN_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}
  e.g.  OBS-MKT-PRC-20260703-00014823
         OBS-CORP-EARN-20260703-00000012
         OBS-MACRO-CPI-20260703-00000003
```

---

#### Component 07 — Observation Timestamp Manager

**Purpose:** The Timestamp Manager is responsible for the precise specification of all temporal attributes of every observation record — ensuring that the distinction between observation time (when the state existed), capture time (when the IIOS perceived it), and storage time (when it was written to the Registry) is maintained rigorously.

**Responsibilities:**
- Assign the observation_timestamp from the source information object's as_of_timestamp
- Record the capture_timestamp as the moment the observation passed through the Detector
- Record the storage_timestamp as the moment the observation was written to the Registry
- Compute the observation latency (capture_timestamp − observation_timestamp)
- Detect and flag implausible timestamps (observation time in the future; observation time before the market existed)
- Maintain clock synchronisation monitoring for all system components

**Timestamp fields:**

| Field | Description |
|---|---|
| observation_timestamp | When the state existed in the real world (from source) |
| capture_timestamp | When the IIOS's Detector first identified this observation |
| storage_timestamp | When the observation was written to the Registry |
| observation_latency_ms | capture_timestamp − observation_timestamp in milliseconds |
| capture_to_storage_ms | storage_timestamp − capture_timestamp in milliseconds |

---

#### Component 08 — Observation Validator

**Purpose:** The Observation Validator confirms that each candidate observation record is structurally valid, type-conformant, and value-consistent before it proceeds to enrichment.

**Responsibilities:**
- Apply schema validation against the observation type definition from the Catalog
- Apply value range validation (prices must be positive; timestamps in valid range; percentages between −1 and +1)
- Apply cross-field consistency validation (high ≥ close ≥ low; bid ≤ ask)
- Apply entity reference validation (all entity_refs must resolve in the Entity Engine)
- Apply cross-observation consistency validation (same entity's observation should not contradict recent observations without flagging)
- Assign validation status: PASS / WARN / FAIL
- Route PASS to enrichment pipeline; WARN with reduced confidence; FAIL to quarantine

**Validation levels:**

| Level | Check | Failure consequence |
|---|---|---|
| L1 Schema | All required fields present; types correct | FAIL — reject |
| L2 Range | All values physically possible | FAIL — reject |
| L3 Consistency | Cross-field internal consistency | WARN — reduce confidence |
| L4 Entity | All entity_refs resolve | WARN — hold pending resolution |
| L5 Temporal | Observation timestamp valid; not future | FAIL — reject |
| L6 Continuity | Consistent with recent observations of the same entity | WARN — flag as anomaly |

---

### 3.4 CONTEXT & CLASSIFICATION CLUSTER

---

#### Component 09 — Observation Context Manager

**Purpose:** The Context Manager captures and attaches the state of the investment universe and the IIOS at the moment each observation was made — ensuring that every observation carries the context needed for historically accurate re-evaluation.

**Responsibilities:**
- Capture the active market regime at the observation timestamp
- Capture the active trading session
- Record concurrent significant events
- Record the prevailing VIX level and NIFTY50 level at observation time
- Capture the active F&O expiry cycle
- Build and attach a ContextRecord to every observation
- Provide context retrieval APIs for historical analysis

**ContextRecord fields:**

| Field | Description |
|---|---|
| context_id | Unique context record identifier |
| as_of_timestamp | Observation moment this context describes |
| market_regime | Active regime observation at context time |
| trading_session | PRE_MARKET / MARKET_OPEN / MARKET_CLOSE / POST_MARKET / CLOSED |
| vix_level | VIX at context time |
| nifty_level | NIFTY50 at context time |
| active_events | Significant concurrent events |
| liquidity_state | HIGH / NORMAL / LOW |
| expiry_proximity | EXPIRY_WEEK / NORMAL |
| global_context | Global risk-on / risk-off state |

---

#### Component 10 — Observation Classification Engine

**Purpose:** The Classification Engine assigns the complete classification to each observation — confirming type code, assigning domain, attaching topic tags, and establishing governance tier.

**Responsibilities:**
- Confirm or correct the declared observation type code
- Assign the observation domain (Domain 02–16)
- Assign topic tags (PRICE, VOLUME, EARNINGS, VOLATILITY, REGIME, MACRO, etc.)
- Assign entity scope tags (single entity, sector, portfolio, system-wide)
- Assign temporal classification (TICK, INTRADAY, DAILY, PERIODIC, AD_HOC)
- Confirm governance tier from Catalog definition
- Flag unusual classification results for review

---

### 3.5 QUALITY CLUSTER

---

#### Component 11 — Observation Quality Manager

**Purpose:** The Quality Manager computes the 14-dimension Observation Quality Score (OQS) for every observation and maintains quality statistics across the observation base.

**Responsibilities:**
- Apply all 14 quality dimensions to each observation (see Part VII for full framework)
- Compute the composite OQS
- Assign quality tier (EXCELLENT, GOOD, ACCEPTABLE, MARGINAL, POOR)
- Monitor quality distribution across domains and types
- Detect quality degradation trends
- Report quality metrics to monitoring and governance

**Quality tiers:**

| Tier | OQS Range | Status |
|---|---|---|
| EXCELLENT | 0.90 – 1.00 | Suitable for all analytical purposes |
| GOOD | 0.75 – 0.89 | Suitable for all analytical purposes |
| ACCEPTABLE | 0.60 – 0.74 | Usable with quality flag |
| MARGINAL | 0.40 – 0.59 | Use with explicit caution; not for high-stakes decisions |
| POOR | 0.00 – 0.39 | Do not use; quarantine for review |

---

#### Component 12 — Observation Confidence Manager

**Purpose:** The Confidence Manager assigns and maintains the confidence score for each observation — a measure of the IIOS's certainty that the observation accurately represents the true state of the world.

**Responsibilities:**
- Compute the initial confidence score from source trust tier, validation results, and completeness
- Adjust confidence based on corroboration from independent sources
- Reduce confidence as freshness decays (confidence is time-varying)
- Re-issue confidence updates when corroborating or contradicting observations arrive
- Alert when the confidence of a CRITICAL observation falls below threshold

**Confidence formula:**

$$\text{confidence}_0 = \text{base}(\text{trust\_tier}) + \text{validation\_premium} + \text{completeness\_premium}$$

$$\text{confidence}_t = \text{confidence}_0 \times \text{freshness\_decay}(t) \times \text{corroboration\_factor}$$

---

#### Component 13 — Observation Freshness Manager

**Purpose:** The Freshness Manager tracks the temporal currency of every observation in the Registry.

**Responsibilities:**
- Track the observation_timestamp for every active observation
- Apply per-type freshness SLAs from the Observation Catalog
- Compute freshness score dynamically
- Classify observations into freshness tiers
- Alert the Collector when critical observations become stale, triggering re-observation
- Report freshness distribution statistics

**Freshness tiers:**

| Tier | Condition |
|---|---|
| FRESH | Within freshness SLA for this type |
| AGING | Within 80–100% of SLA window |
| STALE | Beyond freshness SLA |
| CRITICAL_STALE | Beyond 2× SLA |
| EXPIRED | Beyond retention window |

---

### 3.6 GOVERNANCE CLUSTER

---

#### Component 14 — Observation Aggregator

**Purpose:** The Aggregator computes composite observations from collections of individual observations — producing higher-level observational summaries while preserving lineage back to the constituent observations.

**Responsibilities:**
- Aggregate tick observations into OHLCV bar observations
- Aggregate company observations into sector-level observations
- Compute rolling-window observations (moving averages, rolling volatility, rolling correlation)
- Aggregate portfolio-position observations into portfolio-snapshot observations
- Record all constituent observation_ids in the lineage of each aggregated observation
- Flag aggregated observations clearly as AGGREGATED type

---

#### Component 15 — Observation Storage Manager

**Purpose:** The Storage Manager manages the physical persistence of all observation records across a multi-tier storage architecture.

**Storage tiers:**

| Tier | Access latency | Typical content |
|---|---|---|
| HOT | < 10ms | Current session observations; intraday tick data |
| WARM | < 100ms | Recent weeks to 2-year history; bar data, daily snapshots |
| COLD | < 5 seconds | 2–7 year history |
| ARCHIVE | Minutes | Compliance records; long-term preservation |

**Tier transition rules:**

| Condition | Action |
|---|---|
| Observation age > 7 days and last access > 3 days | HOT → WARM |
| Observation age > 730 days | WARM → COLD |
| Age > retention_months for type | COLD → ARCHIVE |

---

#### Component 16 — Observation Search Engine

**Purpose:** The Search Engine provides full-text, semantic, and faceted search over the Observation Registry — enabling discovery of observations by content, entity, domain, time range, and quality tier.

**Responsibilities:**
- Index observation content (text fields from News, Social, AI domains)
- Support keyword and semantic search with relevance ranking
- Support faceted search (domain, type, entity, date range, quality tier, freshness tier)
- Return results with relevance scores and metadata
- Maintain index freshness (< 5 seconds lag for real-time domains)

---

#### Component 17 — Observation Index Manager

**Purpose:** The Index Manager maintains all indices over the observation base that enable efficient retrieval by consumers.

**Index types:**

| Index | Key | Value |
|---|---|---|
| Time-Series Index | (domain, type_code, entity_id) | Ordered list of (timestamp, observation_id) |
| Entity Index | entity_id | Set of observation_ids |
| Domain Index | domain | Set of observation_ids |
| Type Index | type_code | Set of observation_ids |
| Freshness Index | freshness_expiry_time | Set of observation_ids |
| Full-Text Index | words/tokens | Set of observation_ids (text-bearing domains) |
| Lineage Index | parent_observation_id | Set of child_observation_ids |
| Quality Index | quality_tier | Set of observation_ids |

---

#### Component 18 — Observation History Manager

**Purpose:** The History Manager manages the complete version chain for every observation — ensuring that the history of updates is preserved immutably.

**Responsibilities:**
- Create version records for every observation update
- Link versions in a strict linear chain
- Mark prior versions as SUPERSEDED — never delete
- Provide version retrieval API
- Detect version chain corruption and alert Governance Manager

---

#### Component 19 — Observation Governance Manager

**Purpose:** The Governance Manager is the policy enforcement authority for all observations. It owns the governance framework, enforces access control, manages policies, and produces governance audit reports.

**Responsibilities:**
- Own and maintain governance policy for each observation type
- Enforce access control (which consumers may access which observation types)
- Manage classification reviews
- Receive and act on escalations from the Audit Manager
- Produce governance reports for management and regulatory review
- Manage emergency governance actions (quarantine, access suspension)

---

#### Component 20 — Observation Audit Manager

**Purpose:** The Audit Manager maintains the complete, tamper-evident audit trail of all operations on observation records.

**Responsibilities:**
- Record every Create, Read, Update (via versioning), and Archive operation
- Record every governance decision
- Record every quality event
- Maintain the audit store in an append-only, tamper-evident structure
- Produce structured audit reports on request
- Alert on suspicious activity patterns

---

#### Component 21 — Observation Archive Manager

**Purpose:** The Archive Manager manages the complete lifecycle of observation records through to long-term archival and retirement.

**Responsibilities:**
- Monitor observation age against retention policies
- Initiate migration to archive storage on retention expiry
- Ensure legally required observations are retained for full regulatory period
- Compress archived observations
- Provide retrieval API for archived observations
- Manage retirement of observations beyond maximum retention with no legal hold

---

#### Component 22 — Observation Evolution Manager

**Purpose:** The Evolution Manager manages the long-term evolution of the Observation Engine's schema — the lifecycle of observation types, schemas, and governance policies.

**Responsibilities:**
- Accept new observation type proposals from domain owners and system architects
- Validate that new types are fully defined before activation
- Register new types in the Observation Catalog
- Manage schema migrations for existing types
- Deprecate obsolete types
- Publish a changelog of all schema and policy changes

---
## PART IV — OBSERVATION LIFECYCLE

### 4.1 Overview

Every observation passes through a well-defined 12-stage lifecycle. Each stage is a gate — an observation cannot advance without satisfying all requirements of the current stage. Stage transitions are recorded in the audit trail and in the observation's lineage record.

```
Stage 01: DETECTION
    │ (Observation Detector identifies an observable state from candidate records)
    │ DETECTED → Stage 02
    │ NOT_OBSERVABLE → Discard; log; do not advance
    │ DUPLICATE → Suppress; route to corroboration; do not create new observation
    ▼
Stage 02: IDENTITY ASSIGNMENT
    │ (Identity Manager assigns canonical observation_id)
    │ SUCCESS → Stage 03
    │ IDENTITY_CONFLICT → Hold in PENDING_IDENTITY; resolve before advancing
    ▼
Stage 03: TIMESTAMPING
    │ (Timestamp Manager assigns observation_timestamp, capture_timestamp)
    │ SUCCESS → Stage 04
    │ INVALID_TIMESTAMP → Reject with INVALID_TIMESTAMP reason
    │ FUTURE_TIMESTAMP → Reject; cannot observe future states
    ▼
Stage 04: VALIDATION
    │ (Observation Validator applies L1–L6 validation levels)
    │ PASS → Stage 05 (full confidence)
    │ WARN → Stage 05 (reduced confidence; flags attached)
    │ FAIL → Quarantine; alert Source and Domain owners
    ▼
Stage 05: CONTEXT ASSIGNMENT
    │ (Context Manager captures and attaches ContextRecord)
    │ SUCCESS → Stage 06
    │ CONTEXT_PARTIAL → Continue with available context; flag missing fields
    ▼
Stage 06: CLASSIFICATION
    │ (Classification Engine assigns type, domain, tags, governance tier)
    │ SUCCESS → Stage 07
    │ TYPE_CONFLICT → Escalate to Governance Manager; hold until resolved
    ▼
Stage 07: QUALITY SCORING
    │ (Quality Manager computes OQS; Confidence Manager computes confidence)
    │ OQS ≥ threshold → Stage 08
    │ OQS < minimum floor (0.25) → Quarantine; alert Governance Manager
    ▼
Stage 08: RECORDING
    │ (Observation Recorder writes to Registry; Timestamp Manager records storage_timestamp)
    │ SUCCESS → Stage 09
    │ WRITE_FAILURE → Retry 3×; alert; queue in durable buffer; do not lose
    ▼
Stage 09: INDEXING
    │ (Index Manager updates all applicable indices)
    │ SUCCESS → Stage 10
    │ INDEX_FAILURE → Queue for async retry; alert; continue to Stage 10
    ▼
Stage 10: AGGREGATION (conditional)
    │ (Aggregator checks whether this observation contributes to any aggregate)
    │ CONTRIBUTES → Update aggregated observations; extend their lineage
    │ NO_AGGREGATE → Pass directly to Stage 11
    ▼
Stage 11: ACTIVE MONITORING
    │ (Freshness Manager monitors currency; Confidence Manager monitors confidence)
    │ FRESH → Continue monitoring
    │ STALE → Alert Collector for re-observation; reduce confidence
    │ UPDATE_RECEIVED → Stage 12a (VERSION_UPDATE)
    │ RETIREMENT_TRIGGERED → Stage 12b (ARCHIVAL)
    ▼
Stage 12a: VERSION UPDATE  (triggered by update to prior observation)
    │ New version → re-enter at Stage 06 (Classification) with delta
    │ Prior version → SUPERSEDED (immutable historical record)
    ▼
Stage 12b: ARCHIVAL
    │ (Archive Manager migrates after retention period elapses)
    │ COMPRESSED → COLD or ARCHIVE storage tier
    │ LEGAL_HOLD → Retained in ARCHIVE with hold flag
    └── RETIREMENT → observation_id permanently reserved; lineage preserved
```

---

### 4.2 Lifecycle State Machine

```
                     ┌──────────────────────────────────────────────┐
                     │          OBSERVATION LIFECYCLE STATES        │
                     │                                              │
   Raw Input ──────►DETECTING──►IDENTITY_ASSIGNED──►TIMESTAMPED    │
                     │                                    │         │
                     │                             VALIDATING       │
                     │                                    │         │
                     │                          ┌─FAIL────┘         │
                     │                          │                   │
                     │                     QUARANTINED              │
                     │                          │                   │
                     │                   (Review & Remediation)     │
                     │                                              │
                     │    VALIDATING──►CONTEXT_ASSIGNED             │
                     │                       │                      │
                     │               CLASSIFYING                    │
                     │                       │                      │
                     │             QUALITY_SCORING                  │
                     │                       │                      │
                     │               RECORDING                      │
                     │                       │                      │
                     │              INDEXING                        │
                     │                       │                      │
                     │             ACTIVE◄───┘                      │
                     │              /    \                           │
                     │      SUPERSEDED  ARCHIVING                   │
                     │           │          │                        │
                     │      HISTORICAL   ARCHIVED                   │
                     │                       │                      │
                     │                   RETIRED                    │
                     └──────────────────────────────────────────────┘
```

---

### 4.3 Stage Requirements Reference

**Stage 01 — Detection Requirements**

| Requirement | Specification |
|---|---|
| Candidate validity | Candidate must pass initial plausibility check by Detector |
| Deduplication | No identical observation from same source in last 5 minutes (configurable per type) |
| Observability rule | Detection rule for this information type must return OBSERVABLE |
| Throttle check | Domain rate limit must not be exceeded |

**Stage 02 — Identity Assignment Requirements**

| Requirement | Specification |
|---|---|
| Uniqueness | observation_id must be globally unique |
| Format compliance | ID must conform to: OBS-{DOMAIN}-{TYPE}-{DATE}-{SEQ} |
| Source mapping | Source information_id mapped to observation_id in Identity Manager |
| Conflict resolution | Any conflict resolved before advancing |

**Stage 03 — Timestamping Requirements**

| Requirement | Specification |
|---|---|
| observation_timestamp present | Non-null timestamp from source record |
| observation_timestamp valid | Must be a past or current real-world timestamp; not future |
| UTC format | Timestamp in UTC ISO 8601 |
| Latency recorded | capture_timestamp − observation_timestamp recorded |

**Stage 04 — Validation Requirements**

| Requirement | Specification |
|---|---|
| L1 schema | 100% required fields present and correctly typed — MANDATORY |
| L2 range | All values within defined bounds |
| L3 consistency | Cross-field rules applied; results documented |
| L4 entity resolution | All entity_refs resolve to valid entities |
| L5 temporal | Timestamp plausible relative to entity's known history |
| L6 continuity | Not flagged as implausibly discontinuous from recent observations |

**Stage 05 — Context Assignment Requirements**

| Requirement | Specification |
|---|---|
| Context captured | ContextRecord created with all mandatory fields |
| Market regime present | Active regime observation attached |
| Session state present | Active trading session recorded |
| Context linked | context_id attached to observation record |

**Stage 06 — Classification Requirements**

| Requirement | Specification |
|---|---|
| type_code confirmed | Classification Engine confirms or corrects declared type |
| Domain assigned | Domain field set to one of Domain 02–16 |
| Tags assigned | topic_tags[], entity_tags[], and domain_tags[] populated |
| Governance tier set | governance_tier field confirmed from Catalog |

**Stage 07 — Quality Scoring Requirements**

| Requirement | Specification |
|---|---|
| All 14 dimensions computed | dimension_scores[] has 14 entries |
| OQS computed | oqs = weighted sum of dimension scores |
| Quality tier assigned | quality_tier in {EXCELLENT, GOOD, ACCEPTABLE, MARGINAL, POOR} |
| Minimum OQS | OQS ≥ 0.25 (absolute floor) |
| Confidence assigned | confidence_score in [0.0, 1.0] |

**Stage 08 — Recording Requirements**

| Requirement | Specification |
|---|---|
| Registry acknowledgment | Storage Manager returns WRITE_ACKNOWLEDGED |
| Minimum replicas | At least 2 replica copies confirmed |
| storage_timestamp recorded | Written by Timestamp Manager on acknowledgment |
| Integrity hash | SHA-256 hash of observation record stored |

**Stage 09 — Indexing Requirements**

| Requirement | Specification |
|---|---|
| Time-series index | Entry added for (domain, type_code, entity_id) |
| Entity index | Entries added for all entity_refs |
| Domain index | Entry added for domain |
| Quality index | Entry added for quality_tier |
| Full-text index | Content indexed if text-bearing observation type |

**Stage 11 — Active Monitoring Requirements**

| Requirement | Specification |
|---|---|
| Freshness tracked | Freshness Manager computing freshness dynamically |
| Confidence maintained | Confidence Manager recomputing on schedule and triggers |
| Re-observation trigger | On STALE transition: Collector receives re-observe request |

---

### 4.4 Observation Duration by Domain

| Domain | Typical ACTIVE duration | Typical retention before ARCHIVE |
|---|---|---|
| Market — Tick | Minutes to hours | 30 days (tick) |
| Market — Daily bar | Days to months | 36 months → COLD |
| Company — Earnings | Months | 84 months |
| Sector — Daily | Days to weeks | 36 months |
| Macro — Monthly indicator | Until next release | 120 months |
| Portfolio — Snapshot | Daily | 84 months (regulatory) |
| Risk — Intraday | Minutes to hours | 36 months (risk records) |
| Temporal — Calendar | Until event passes | 24 months |

---
## PART V — OBSERVATION SERVICES

The Observation Engine exposes 17 services to its consumers. Each service has a defined contract — inputs, outputs, latency targets, failure modes, and authorised consumers.

---

### 5.1 Service Registry

| Code | Name | Primary Consumer | p99 Latency |
|---|---|---|---|
| OS-01 | Collection Service | Orchestrator, Domain Collectors | N/A (async) |
| OS-02 | Capture Service | Observation Collector | < 50ms |
| OS-03 | Validation Service | Capture pipeline | < 30ms per record |
| OS-04 | Classification Service | Validation Service | < 20ms per record |
| OS-05 | Timestamp Service | Capture pipeline | < 5ms |
| OS-06 | Context Service | Classification Engine | < 20ms |
| OS-07 | Storage Service | Observation Recorder | < 30ms write; < 50ms read |
| OS-08 | Retrieval Service | All downstream engines | < 50ms point-lookup; < 500ms range |
| OS-09 | History Service | Evidence Engine, Research Lab | < 100ms |
| OS-10 | Aggregation Service | Knowledge Engine, Strategy Engine | < 200ms |
| OS-11 | Search Service | Knowledge Engine, Research Lab | < 2 seconds |
| OS-12 | Audit Service | Compliance, Management | < 1 second |
| OS-13 | Governance Service | Administrators | < 500ms |
| OS-14 | Quality Service | All consumers | < 10ms (cached) |
| OS-15 | Freshness Service | All consumers | < 10ms (cached) |
| OS-16 | Archive Service | Archive Manager | < 5 seconds |
| OS-17 | Metadata Service | All consumers | < 50ms |

---

### 5.2 Service Definitions

---

#### OS-01 — Collection Service

**Purpose:** Manages the lifecycle of domain observation collection — starting, stopping, pausing, and monitoring domain-specific Collectors.

**Inputs:**
- Collection control requests: { domain, action: START | STOP | PAUSE | RESUME, config }

**Outputs:**
- Collection status: { domain, status, observations_per_minute, last_observation_id, gaps[] }
- Collection alerts: { domain, alert_type, details }

**Consumers:** Orchestrator (scheduled start/stop at market open/close); Governance Manager (emergency pause of compromised domain)

**Failure Recovery:**
- Collector crash → restart Collector for affected domain; report gap in observation continuity log
- Information feed absent → mark domain as FEED_ABSENT; alert; continue with reduced coverage

---

#### OS-02 — Capture Service

**Purpose:** Accepts candidate observations from Collectors and submits them to the capture pipeline (Identity → Timestamp → Validation → Context → Classification → Quality → Record).

**Inputs:**
- Candidate observation package: { domain, type_hint, payload, source_ref, detected_at }

**Outputs:**
- Capture receipt: { observation_id, capture_status, estimated_processing_time }
- On completion: capture result { observation_id, validation_status, quality_score, storage_acknowledged }

**Consumers:** Observation Collectors (all domains)

**Failure Recovery:**
- Pipeline overload → buffer in priority queue; process in order; alert if queue > 50,000
- Validation failure → quarantine; alert domain owner; continue with other candidates

---

#### OS-03 — Validation Service

**Purpose:** Validates an observation record against the rules defined for its type.

**Inputs:**
- Observation candidate: { type_code, payload, source_ref }

**Outputs:**
- Validation result: { validation_status, level_reached, issues[], confidence_adjustment }

**Consumers:** Capture Service (inline); Governance Manager (re-validation workflows)

**SLA:** < 30ms per record (p99)

---

#### OS-04 — Classification Service

**Purpose:** Assigns complete classification to an observation record.

**Inputs:**
- Validated observation: { type_hint, payload, entity_refs, domain_hint }

**Outputs:**
- Classification result: { type_code, domain, topic_tags[], entity_scope, temporal_class, governance_tier }

**SLA:** < 20ms per record (p99)

---

#### OS-05 — Timestamp Service

**Purpose:** Manages all temporal attributes of observations.

**Inputs:**
- Observation with raw source timestamp: { source_timestamp, type_code }

**Outputs:**
- Timestamp record: { observation_timestamp, capture_timestamp, storage_timestamp, observation_latency_ms, validity_status }

**SLA:** < 5ms (p99)

---

#### OS-06 — Context Service

**Purpose:** Provides observation context records — either capturing a new context at the current moment or retrieving a historical context for a specified timestamp.

**Inputs:**
- Context request: { as_of_timestamp, include_regime, include_events }

**Outputs:**
- ContextRecord: { context_id, as_of_timestamp, market_regime, trading_session, vix_level, nifty_level, active_events[], liquidity_state, expiry_proximity }

**Consumers:** Classification Engine (capture pipeline); all historical retrieval consumers needing context reconstruction

**SLA:** < 20ms for current context (p99); < 100ms for historical context lookup (p99)

---

#### OS-07 — Storage Service

**Purpose:** Writes observations to and reads observations from the Observation Registry.

**Inputs (write):** Classified, quality-scored observation record
**Outputs (write):** { observation_id, storage_acknowledged, storage_tier, storage_timestamp }

**Inputs (read):** Read request: { observation_id | query }
**Outputs (read):** Observation record or set

**SLA:** < 30ms write (p99); < 50ms point-read (p99)

**Failure Recovery:**
- Write failure → retry 3×; alert; buffer in durable write-ahead log
- Read failure → return SERVICE_UNAVAILABLE; alert monitoring

---

#### OS-08 — Retrieval Service

**Purpose:** The primary structured query interface to the Observation Registry.

**Inputs:**
- Retrieval query: { query_type, filters: { domain?, type_code?, entity_id?, time_range?, quality_floor?, freshness_requirement? }, limit, include_context, include_lineage }

**Query types:**

| Type | Description |
|---|---|
| LATEST | Most recent observation of a type for an entity |
| POINT_IN_TIME | Observation as it was at a specified historical moment |
| TIME_RANGE | All observations in a time window |
| BY_ENTITY | All observations about a specific entity |
| BY_DOMAIN | All observations in a domain |
| MULTI_ENTITY | Observations about a set of entities simultaneously |
| CROSS_DOMAIN | Observations spanning multiple domains for an entity |

**SLA:**
- LATEST, POINT_IN_TIME: < 50ms (p99)
- TIME_RANGE up to 30 days: < 300ms (p99)
- TIME_RANGE up to 1 year: < 3 seconds (p99)

---

#### OS-09 — History Service

**Purpose:** Provides access to the complete version history of any observation record.

**Inputs:**
- History query: { observation_id, version_number? | as_of_timestamp?, include_delta }

**Outputs:**
- Version record: { observation_id, version_number, effective_from, effective_to, content, delta?, change_reason }

**SLA:** < 100ms (p99)

---

#### OS-10 — Aggregation Service

**Purpose:** Returns composite, aggregated observations computed from constituent observation sets.

**Inputs:**
- Aggregation request: { aggregation_type, entities[], time_range, window_size }

**Aggregation types:**

| Type | Description |
|---|---|
| TIME_AGGREGATE | Aggregate tick observations to bar observations |
| ENTITY_AGGREGATE | Aggregate company observations to sector observations |
| ROLLING_WINDOW | Rolling statistical aggregate (mean, std, min, max) over time window |
| CROSS_ENTITY | Average or sum across multiple entities simultaneously |

**Outputs:**
- Aggregated observation: { observation_id (new), aggregation_type, constituent_ids[], aggregated_payload }

**SLA:** < 200ms for up to 100 constituents (p99)

---

#### OS-11 — Search Service

**Purpose:** Provides discovery of observations by content, concept, and faceted metadata.

**Inputs:**
- Search request: { query_text?, facets: { domain?, entity?, date_range?, quality_tier?, freshness_tier? }, page, page_size }

**Outputs:**
- Search results: { hits[], total_count, query_time_ms, facet_counts }

**SLA:** < 2 seconds for full-text (p99); < 500ms for metadata-only (p99)

---

#### OS-12 — Audit Service

**Purpose:** Provides the audit trail retrieval interface.

**Inputs:**
- Audit query: { event_type?, actor?, observation_id?, time_range, page }

**Outputs:**
- Audit records: { audit_id, event_type, observation_id, actor, timestamp, outcome, details }

**SLA:** < 1 second (p99)

---

#### OS-13 — Governance Service

**Purpose:** Provides policy management and access control enforcement.

**Inputs:**
- Access query: { consumer_id, observation_id | type_code | domain }
- Policy query: { type_code, policy_category }

**Outputs:**
- Access decision: { allowed: true|false, reason }
- Policy record: { type_code, governance_tier, retention_months, access_control_list }

**SLA:** < 20ms for access decisions (p99); < 500ms for policy queries (p99)

---

#### OS-14 — Quality Service

**Purpose:** Provides quality scores and quality statistics.

**Inputs:**
- Quality query: { observation_id? | domain? | entity_id? | aggregate_flag }

**Outputs:**
- Per-observation: { observation_id, oqs, quality_tier, dimension_scores[] }
- Aggregate: { domain?, entity_id?, oqs_distribution, avg_oqs, quality_tier_counts }

**SLA:** < 10ms per observation (cached, p99)

---

#### OS-15 — Freshness Service

**Purpose:** Provides freshness status and scores.

**Inputs:**
- Freshness query: { observation_id? | type_code? | domain? }

**Outputs:**
- Per-observation: { observation_id, freshness_score, freshness_tier, time_to_stale_seconds }
- Aggregate: { stale_count, aging_count, fresh_count, critical_stale_count }

**SLA:** < 10ms (cached, p99)

---

#### OS-16 — Archive Service

**Purpose:** Provides archival operations and retrieval of archived observations.

**Inputs:**
- Archive query: { observation_id | domain, time_range, include_retired }

**Outputs:**
- Archived observation record (slower retrieval from archive tier)
- Archive status: { observation_id, archive_tier, archived_at, legal_hold }

**SLA:** < 5 seconds (p99)

---

#### OS-17 — Metadata Service

**Purpose:** Provides rich metadata about observations and the observation base.

**Inputs:**
- Metadata query: { observation_id? | domain? | aggregate_flag }

**Outputs:**
- Per-observation: { observation_id, type_code, domain, entity_refs, observation_timestamp, quality_score, confidence_score, freshness_tier, version_number, lineage_summary }
- System metadata: { total_observations, observations_by_domain, observations_by_quality_tier }

**SLA:** < 50ms (p99)

---
## PART VI — OBSERVATION PROCESSING ARCHITECTURE

### 6.1 Overview

The Observation Engine supports 15 distinct processing patterns, each optimised for a specific combination of observation velocity, volume, and analytical purpose. These patterns share the same 22 components but differ in their pipeline configurations, throughput budgets, and parallelism strategies.

---

### 6.2 Processing Pattern Taxonomy

| Pattern | Velocity | Volume | Latency | Primary domain |
|---|---|---|---|---|
| Streaming Observation | Microseconds | Extreme | < 50ms | Market ticks |
| Real-Time Observation | Milliseconds–seconds | Very high | < 200ms | Market bars, order states |
| Historical Observation | On-demand | High | < 60s | All domains |
| Scheduled Observation | Periodic | Medium | < 30 minutes | Macro, EOD, portfolio |
| Snapshot Observation | Periodic | Medium | < 5 minutes | Portfolio, risk |
| Window Observation | Rolling | Medium | < 500ms | Rolling indicators |
| Rolling Observation | Continuous | Medium | < 1 second | Moving averages, vol |
| Cross-Market Observation | Daily | Low | < 10 minutes | Global context |
| Cross-Entity Observation | Batch | Medium | < 2 minutes | Sector aggregation |
| Cross-Time Observation | On-demand | High | < 60s | Seasonality, cycles |
| Observation Correlation | Batch | Low | < 5 minutes | Correlation matrices |
| Observation Deduplication | Inline | Very high | < 5ms | All domains |
| Observation Prioritization | Inline | Very high | < 1ms | All domains |
| Observation Queue | Buffering | Very high | N/A (buffer) | All domains |
| Observation Pipeline | Orchestration | All | Varies | All domains |

---

### 6.3 Streaming Observation Pattern

The Streaming Observation Pattern is the fastest path through the Observation Engine, designed for continuous, high-throughput tick data.

```
Market tick stream (WebSocket / FIX / Exchange Feed)
    │  [< 2ms from market]
    ▼
Market Collector (subscribe → receive → extract candidate)
    │  [< 3ms]
    ▼
Observation Detector (detect → deduplicate → throttle check)
    │  [< 5ms]
    ▼
Identity Manager (fast-path: pre-registered symbols → lookup-based ID assignment)
    │  [< 2ms]
    ▼
Timestamp Manager (assign timestamps; compute latency)
    │  [< 2ms]
    ▼
Validator FAST PATH (L1 + L2 only; L3–L6 async; known types skip schema check)
    │  [< 5ms]
    ▼
Classification FAST PATH (pre-classified type; no work for known types)
    │  [< 2ms]
    ▼
Context Manager FAST PATH (latest context snapshot; no lookup)
    │  [< 2ms]
    ▼
Quality Manager FAST PATH (source-trust-based approximate score; full OQS async)
    │  [< 3ms]
    ▼
Observation Recorder (write-ahead log → async durable storage)
    │  [< 5ms]
    ▼
Index Manager (time-series index append; async full index update)
    │  [< 3ms]
    ▼
Distribution to subscribers (Real-Time push)
    │
    Total end-to-end: < 35ms (target p99: < 50ms)
```

**Streaming pattern optimisations:**
- Pre-registered symbol catalogue: Identity Manager performs a hash-table lookup, not a remote call
- L3–L6 validation runs asynchronously after write; does not block the pipeline
- Context uses the latest available snapshot rather than constructing a new one
- Quality Manager uses a fast approximate score; full OQS computed in background
- Write-ahead log ensures durability without waiting for full storage acknowledgment

---

### 6.4 Real-Time Observation Pattern

The Real-Time Pattern processes observations that are more structured than raw ticks but still require sub-second delivery — bar observations, order state changes, and risk metric updates.

```
Information Engine Distribution (OHLCV bar, order event, risk update)
    │
    ▼
Domain Collector (subscribes to Distribution; receives typed information objects)
    │
    ▼
Observation Detector (full detection rules applied; not pre-classified)
    │
    ▼
Complete pipeline (Identity → Timestamp → Validation → Context → Classification → Quality)
    │  [target < 100ms total]
    ▼
Observation Recorder (durable write with acknowledgment)
    │
    ▼
Index Manager (full index update; synchronous for operational freshness)
    │
    ▼
Aggregation trigger (does this observation contribute to a rolling aggregate?)
    │
    ▼
Distribution (push to subscribed consumers)
    │
    Target end-to-end: < 200ms (p99)
```

---

### 6.5 Historical Observation Pattern

The Historical Pattern retrieves or reconstructs observations from the Registry for analytical workloads — backtesting, research, and walk-forward testing.

```
Consumer request (domain, entity, time_range, quality_floor, include_context)
    │
    ▼
Retrieval Service (attempt to serve from Registry)
    │
    ├── FULL HIT → Return directly from Registry (warm or cold tier)
    │
    └── PARTIAL OR MISS → Acquisition pipeline
            │
            ▼
            Information Engine Retrieval (request historical information objects)
            │
            ▼
            Domain Collector (process historical objects through full pipeline)
            │
            ▼
            Retrieval Service (return combined Registry + newly processed)
    │
    ▼
Point-in-time filter applied (observations after query_time excluded — no lookahead)
    │
    ▼
Context reconstruction (historical ContextRecord attached from Context archive)
    │
    ▼
Return result set with freshness-at-query-time and quality-at-ingestion-time
```

**Critical invariant:** Historical queries must apply the capture_timestamp ≤ query_time filter. Any observation whose capture_timestamp is after the query point must be excluded.

---

### 6.6 Scheduled Observation Pattern

The Scheduled Pattern handles periodic, calendar-driven observation events — EOD market summary, macroeconomic release ingestion, and weekly/monthly aggregations.

```
Schedule trigger (cron: 15:45 market close, 08:00 pre-market, etc.)
    │
    ▼
Collection Service (trigger domain Collectors for scheduled acquisition)
    │
    ▼
Information Engine Acquisition (scheduled batch download)
    │
    ▼
Domain Collectors (process batch; full pipeline for each observation)
    │
    ▼
Aggregation Service (compute EOD aggregates, sector summaries, macro context)
    │
    ▼
Quality Manager (full OQS; full context attachment)
    │
    ▼
Registry (durable write; full indexing)
    │
    ▼
Distribution (notify scheduled-batch subscribers: Analytics, Portfolio, Learning)
    │
    ▼
Freshness Manager (reset freshness timers for all just-observed domains)
```

**Scheduled observation slots:**

| Slot | Time | Domains triggered |
|---|---|---|
| Pre-market | 08:00 | Macro, Global Market, Temporal, News |
| Market open | 09:15 | All Market, Sector, Risk |
| Mid-session | 12:00 | Portfolio snapshot, Risk, Market breadth |
| Market close | 15:30 | All Market, Sector, Portfolio |
| Post-close | 15:45 | EOD bar aggregation, Company filings, FII/DII flows |
| Evening | 18:00 | Alternative data, News volume |
| Nightly | 23:00 | Global macro (US/EU time zones), Currency close |
| Weekly | Friday 20:00 | Weekly summaries all domains |

---

### 6.7 Snapshot Observation Pattern

```
Snapshot trigger (time-based: every 30 minutes during market hours)
    │
    ▼
Portfolio Collector (read current position values from Execution Engine)
    │
    ▼
Risk Collector (read current risk metrics from Risk Engine)
    │
    ▼
Snapshot observation creation (point-in-time state record)
    │
    ▼
Context attachment (current ContextRecord)
    │
    ▼
Registry (write snapshot; preserve all prior snapshots as version chain)
    │
    ▼
Aggregation (running portfolio trajectory; running risk trajectory)
```

---

### 6.8 Window Observation Pattern

```
Window request (entity, window_type, window_size, as_of)
    │
    ▼
Retrieval Service (retrieve time-series observations for entity over window)
    │
    ▼
Aggregation Service (compute window aggregate)
    │
    ├── MOVING_AVERAGE: mean of close prices over window
    ├── ROLLING_VOLATILITY: std dev of returns over window
    ├── ROLLING_CORRELATION: pairwise correlation over window
    ├── ATR: average true range over window
    └── ROLLING_VOLUME: average volume over window
    │
    ▼
Window observation created (aggregation of window_size constituent observations)
    │
    ▼
Registry (write as new observation type: ROLLING_{TYPE}_{WINDOW}D)
```

---

### 6.9 Cross-Entity Observation Pattern

```
Cross-entity trigger (sector aggregate, portfolio aggregate, index aggregate)
    │
    ▼
Retrieval Service (retrieve latest observations for all entities in scope)
    │
    ▼
Aggregation Service (compute cross-entity aggregate)
    │
    ├── SECTOR_PERFORMANCE: weighted average return of sector constituents
    ├── SECTOR_BREADTH: proportion advancing in sector
    ├── PORTFOLIO_EXPOSURE: aggregate position-level metrics
    └── INDEX_BREADTH: advance-decline ratio for NIFTY50
    │
    ▼
Cross-entity observation created (all constituent observation_ids in lineage)
    │
    ▼
Registry (write; tag as CROSS_ENTITY in classification)
```

---

### 6.10 Observation Deduplication Pattern

Deduplication is applied inline at the Observation Detector to suppress exact duplicate observations.

```
Candidate observation arrives at Detector
    │
    ▼
Deduplication check: has an observation with identical
    (source_ref, type_code, entity_id, observation_timestamp)
    been detected in the last {type_dedup_window}?
    │
    ├── YES → Duplicate; suppress; route to corroboration store
    │          Log: duplicate_from=source_ref, suppressed_at=now
    │
    └── NO → Not a duplicate; continue to Identity Manager
```

**Deduplication windows by type:**

| Type class | Deduplication window |
|---|---|
| Tick observations | 1 second |
| Bar observations | 5 minutes |
| Company announcements | 24 hours |
| Macro releases | 48 hours |
| Governance / system observations | 1 hour |

---

### 6.11 Observation Prioritisation Pattern

Observations are prioritised in the capture queue to ensure that CRITICAL domain observations are processed first during periods of high load.

```
Priority assignment:
    Domain CRITICAL (Execution, Portfolio, Risk, Order):    Priority 1
    Domain HIGH (Market, Company, Macro):                   Priority 2
    Domain MEDIUM (Sector, News, Behavior, Temporal):       Priority 3
    Domain LOW (Social, Alternative, AI, System):           Priority 4

Queue processing:
    Pop from highest-priority non-empty queue
    Process one observation per iteration
    Rotate among equal-priority domains within the same tier
    Ensure no domain is fully starved (minimum % throughput guarantee per domain)
```

---

### 6.12 Observation Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       OBSERVATION ENGINE PIPELINE                           │
│                                                                             │
│ ┌─────────────┐  ┌────────────────┐  ┌───────────────┐  ┌───────────────┐  │
│ │  Streaming  │  │   Real-Time    │  │   Scheduled   │  │  Historical   │  │
│ │  Pipeline   │  │   Pipeline     │  │   Pipeline    │  │   Pipeline    │  │
│ │  < 50ms     │  │   < 200ms      │  │   < 30min     │  │   < 60s       │  │
│ └──────┬──────┘  └───────┬────────┘  └───────┬───────┘  └───────┬───────┘  │
│        │                 │                    │                   │          │
│        └─────────────────┴────────────────────┴───────────────────┘         │
│                                    │                                         │
│                          OBSERVATION QUEUE                                   │
│                  (Priority: CRITICAL > HIGH > MEDIUM > LOW)                  │
│                                    │                                         │
│  ┌──────────────────────────────────▼───────────────────────────────────┐    │
│  │              CAPTURE PIPELINE                                        │    │
│  │  Identity → Timestamp → Validator → Context → Classification         │    │
│  │  → Quality → Recorder → Index Manager → Aggregation → Distribution  │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│          ┌─────────────────────────┼────────────────────────┐               │
│          ▼                         ▼                        ▼               │
│  ┌───────────────┐     ┌─────────────────────┐   ┌──────────────────┐      │
│  │  Observation  │     │  Observation Index  │   │ Observation Dist │      │
│  │  Registry     │     │  Manager            │   │ ribution Layer   │      │
│  └───────────────┘     └─────────────────────┘   └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6.13 Observation Capacity Model

```
┌────────────────────────────────────────────────────────────────────┐
│             OBSERVATION ENGINE PROCESSING CAPACITY                  │
│                                                                    │
│  Streaming (tick observations)                                      │
│    Max throughput:   100,000 tick observations/second              │
│    Typical load:      15,000 tick observations/second (market hrs) │
│    Peak load:         80,000 tick observations/second (vol events) │
│    Dedup buffer:      60-second rolling window                      │
│                                                                    │
│  Real-Time (bar and event observations)                             │
│    Max throughput:   5,000 observations/second                     │
│    Typical load:       500 observations/second                     │
│                                                                    │
│  Scheduled batch                                                    │
│    EOD volume:     ~200,000 observations per night                 │
│    Window:               15:30 to 08:00 (16.5 hours)              │
│                                                                    │
│  Historical on-demand                                               │
│    Concurrent requests:   20 parallel historical pipelines        │
│    Max observations returned per request: 10,000,000              │
│                                                                    │
│  Total Registry capacity                                           │
│    Active observations:   ~50 million (across all domains)        │
│    Historical (warm+cold): ~2 billion observations                │
└────────────────────────────────────────────────────────────────────┘
```

---
## PART VII — OBSERVATION QUALITY FRAMEWORK

### 7.1 Overview

The Observation Quality Framework provides a systematic, multi-dimensional assessment of every observation's fitness for use by downstream engines. The Observation Quality Score (OQS) synthesises 14 dimensions into a single operational quality indicator. Every observation in the Registry has an OQS and a quality tier. Consumers specify a quality floor in retrieval requests; the Retrieval Service does not return observations below that floor without an explicit override.

---

### 7.2 Quality Dimension Reference

| Dim | Code | Name | Weight | Description |
|---|---|---|---|---|
| D01 | ACC | Accuracy | 0.15 | Does the observation correctly represent the true state of the world? |
| D02 | PRE | Precision | 0.10 | Is the observed value specified at the required level of numerical precision? |
| D03 | CON | Consistency | 0.10 | Is the observation internally consistent and consistent with recent related observations? |
| D04 | CMP | Completeness | 0.10 | Are all required observation fields present and non-null? |
| D05 | FRS | Freshness | 0.12 | How current is the observation relative to its defined SLA? |
| D06 | CVG | Coverage | 0.08 | Does the observation cover all entities and fields needed by the primary consumer? |
| D07 | REL | Reliability | 0.08 | What is the historical accuracy track record of the observation source for this type? |
| D08 | TRW | Trustworthiness | 0.07 | What is the assigned trust tier of the source? |
| D09 | GRN | Granularity | 0.06 | Is the observation at the required level of detail? |
| D10 | FRQ | Frequency | 0.05 | Is the observation being produced at the required frequency for this type? |
| D11 | CFD | Confidence | 0.05 | What is the computed confidence score for this observation? |
| D12 | CRX | Context Richness | 0.04 | How complete and rich is the attached context record? |
| D13 | SRC | Source Quality | 0.04 | What is the overall quality rating of the source? |
| D14 | OQS | Observation Score | — | Composite: weighted sum of all 14 dimensions |

**Note:** Weights sum to 1.04 before normalisation; after normalisation (÷1.04) they sum to exactly 1.0.

---

### 7.3 Dimension Computation Specifications

---

#### D01 — Accuracy

Accuracy is assessed through cross-source agreement, historical plausibility, and physical plausibility checks.

$$\text{acc} = w_a \cdot \text{cross\_source\_agreement} + w_b \cdot \text{historical\_plausibility} + w_c \cdot \text{physical\_plausibility}$$

Default weights: $w_a = 0.50$, $w_b = 0.35$, $w_c = 0.15$

- cross_source_agreement: proportion of independent sources that agree (within tolerance)
- historical_plausibility: probability that the observed value is consistent with recent history
- physical_plausibility: does the value satisfy physical constraints (positive prices, bounded rates, etc.)

---

#### D02 — Precision

Precision measures whether the observed value is specified at the required decimal precision for the observation type.

$$\text{pre} = \begin{cases} 1.0 & \text{if decimal places} \geq \text{required\_precision(type)} \\ \frac{\text{actual\_decimal\_places}}{\text{required\_precision(type)}} & \text{otherwise} \end{cases}$$

For example: NIFTY50 price requires precision of 2 decimal places. A value of 22345 (0 decimal places) scores precision = 0/2 = 0.0. A value of 22345.60 (2 decimal places) scores precision = 1.0.

---

#### D03 — Consistency

Consistency measures how well the observation conforms to consistency rules defined in the Catalog for its type, and how well it agrees with recent prior observations.

$$\text{con} = w_1 \cdot \text{internal\_consistency} + w_2 \cdot \text{temporal\_continuity}$$

- internal_consistency: proportion of cross-field rules that pass (e.g., high ≥ close ≥ low)
- temporal_continuity: whether the value is plausibly continuous from the last observation (detects implausible jumps)

---

#### D04 — Completeness

Completeness is the proportion of required fields present and non-null.

$$\text{cmp} = \frac{\text{required fields present and non-null}}{\text{total required fields}} + \text{optional\_bonus}$$

Optional bonus: +0.01 per optional field present, capped at +0.05.

---

#### D05 — Freshness

Freshness measures how current the observation is at the time of evaluation — a time-varying dimension.

$$\text{frs}(t) = \max\left(0,\ 1 - \frac{t - t_{\text{obs}}}{\text{SLA}(T)}\right)$$

where:
- $t$ = current evaluation time
- $t_{\text{obs}}$ = observation timestamp
- $\text{SLA}(T)$ = freshness SLA in seconds for observation type $T$

Freshness must be recomputed dynamically; it is not a static value computed once at capture.

---

#### D06 — Coverage

Coverage measures whether the observation satisfies the consumer's informational requirements.

$$\text{cvg} = \frac{\text{consumer-required fields covered}}{\text{consumer-required fields total}}$$

Coverage is consumer-context-specific. The Retrieval Service uses the requesting consumer's registered coverage profile.

---

#### D07 — Reliability

Reliability is the rolling 90-day accuracy rate of the source for this observation type.

$$\text{rel} = \frac{\text{confirmed accurate observations from source for type}}{\text{total observations from source for type}} \text{ (rolling 90 days)}$$

---

#### D08 — Trustworthiness

Trustworthiness is a function of the source's assigned trust tier.

| Trust tier | Score |
|---|---|
| AUTHORITATIVE | 1.00 |
| RELIABLE | 0.85 |
| STANDARD | 0.70 |
| PROVISIONAL | 0.55 |
| UNRELIABLE | 0.30 |

---

#### D09 — Granularity

Granularity assesses whether the observation is at the resolution required by consumers.

$$\text{grn} = \begin{cases} 1.0 & \text{observation granularity} \leq \text{required\_granularity} \\ 0.5 & \text{one granularity level coarser than required} \\ 0.1 & \text{more than one level coarser} \end{cases}$$

For example: if a consumer requires 1-minute bars and only 5-minute bars are available, granularity = 0.5.

---

#### D10 — Frequency

Frequency measures whether observations of this type are being produced at the required rate.

$$\text{frq} = \min\left(1.0,\ \frac{\text{actual\_observations\_in\_period}}{\text{expected\_observations\_in\_period}}\right)$$

---

#### D11 — Confidence

Confidence is the composite confidence score from the Confidence Manager.

$$\text{cfd} = \text{confidence\_score} \in [0.0, 1.0]$$

---

#### D12 — Context Richness

Context Richness measures how complete the attached ContextRecord is.

$$\text{crx} = \frac{\text{context fields populated}}{\text{total context fields}}$$

A ContextRecord with all fields (regime, session, VIX, NIFTY, events, liquidity, expiry, global) populated scores 1.0.

---

#### D13 — Source Quality

Source Quality is the overall quality rating of the observation source — a composite of its reliability, uptime, and trust tier.

$$\text{src} = 0.50 \cdot \text{reliability} + 0.30 \cdot \text{trustworthiness} + 0.20 \cdot \text{uptime\_score}$$

---

### 7.4 Composite OQS Formula

$$\text{OQS} = \frac{\sum_{i=1}^{13} w_i \cdot d_i}{\sum_{i=1}^{13} w_i}$$

(Normalised so that OQS ∈ [0.0, 1.0] regardless of whether all optional dimensions are present.)

---

### 7.5 Quality Tier Boundaries

| Tier | OQS Range | Operational Meaning |
|---|---|---|
| EXCELLENT | [0.90, 1.00] | All dimensions healthy; suitable for highest-stakes analytical use |
| GOOD | [0.75, 0.90) | Most dimensions healthy; suitable for all operational use |
| ACCEPTABLE | [0.60, 0.75) | Some dimensions degraded; usable with quality awareness |
| MARGINAL | [0.40, 0.60) | Multiple dimensions degraded; not for high-stakes decisions |
| POOR | [0.00, 0.40) | Widespread quality failure; quarantine; do not use |

---

### 7.6 Quality Monitoring Reference

**Per-domain quality dashboard:**

| Metric | Update frequency | Alert threshold |
|---|---|---|
| Mean OQS by domain | Every 30 minutes | < 0.75 for any domain |
| % POOR by domain | Every 30 minutes | > 5% for any CRITICAL domain |
| Mean OQS trend | Daily | Decline > 0.05 over 7 days |
| Staleness count | Every 5 minutes | Any CRITICAL observation STALE |
| Corroboration gaps | Hourly | < 2 sources corroborating CRITICAL observations |

---

### 7.7 Quality Improvement Guidance

| Dimension failing | Common root cause | Recommended remediation |
|---|---|---|
| Accuracy (ACC) | Source error; feed quality degradation | Cross-source corroboration; source reliability review |
| Precision (PRE) | Rounding in source data; unit conversion errors | Review source data format; check unit conversion factors |
| Consistency (CON) | Source data entry error; format change in source | Cross-field validation tightening; source escalation |
| Completeness (CMP) | Source not providing all fields; parse failure | Update extraction rules; contact source provider |
| Freshness (FRS) | Stale data; acquisition job failure | Investigate acquisition; escalate source outage |
| Coverage (CVG) | Consumer needs fields not in standard observation | Add optional fields to Catalog; enrich observation record |
| Reliability (REL) | Source track record deteriorating | Trust tier review; source replacement evaluation |
| Context Richness (CRX) | Context Manager failure; missing regime data | Investigate Context Manager; check regime observation availability |

---
## PART VIII — OBSERVATION GOVERNANCE

### 8.1 Governance Philosophy

Observation governance is the system of policies, responsibilities, and controls that ensures observations are managed as analytical assets of the IIOS — not merely technical records. Governance answers the questions that operational design cannot: who is responsible for the quality of this observation type? who can access it? how long must it be preserved? who is accountable when an observation is wrong?

The Observation Engine's governance framework is built on 11 dimensions. Each dimension addresses a distinct governance concern. Together, they provide comprehensive coverage of all governance obligations across all 16 observation domains.

---

### 8.2 Governance Dimension Reference

| Dim | Code | Name | Description |
|---|---|---|---|
| G01 | OWN | Ownership | Each observation type has a designated owner responsible for quality and policy |
| G02 | CLS | Classification | Security and confidentiality classification assigned to each type |
| G03 | NAM | Naming Standards | Canonical naming conventions for observation types, fields, and IDs |
| G04 | MTD | Metadata Standards | Standards for the metadata fields attached to every observation |
| G05 | RET | Retention | How long observations must be preserved before archiving |
| G06 | VER | Versioning | Policy for how observation version histories are managed |
| G07 | AUD | Auditability | All operations on observations must produce audit trail entries |
| G08 | SEC | Security | Access control and authentication requirements |
| G09 | CPL | Compliance | Regulatory requirements applicable to each observation type |
| G10 | QCT | Quality Control | Standards for quality assessment and minimum quality thresholds |
| G11 | HIS | Historical Preservation | Requirements for preserving historical observations for replay and audit |

---

### 8.3 Governance Tier Matrix

| Domain | Tier | Justification |
|---|---|---|
| Market — Price, Volume, Depth | CRITICAL | Execution decisions depend directly on price observations |
| Order Observation | CRITICAL | Order state affects live positions; errors have immediate financial consequences |
| Trade Observation | CRITICAL | Trade records are regulatory compliance records; 7-year retention |
| Portfolio Observation | CRITICAL | Portfolio state is the source of truth for P&L and regulatory reporting |
| Risk Observation | CRITICAL | Risk observations feed the kill-switch logic |
| Company — Corporate Actions | CRITICAL | Incorrect corporate action observations affect position valuations |
| Macro — Monetary Policy | HIGH | Central bank rate decisions affect all asset pricing models |
| Company — Earnings | HIGH | Earnings observations drive valuation models and strategy decisions |
| Sector Observation | HIGH | Sector rotations are key regime inputs |
| Behavior Observation | HIGH | Institutional flow observations are key market context signals |
| Temporal Observation | HIGH | Expiry and calendar observations affect derivatives strategies |
| News Observation | MEDIUM | News presence informs context but is not a direct decision input |
| Social Observation | MEDIUM | Social mentions are supplementary context |
| Alternative Data | MEDIUM | Useful supplementary signals; not primary inputs |
| AI Observation | MEDIUM | Model outputs are analytical inputs; subject to model risk |
| System Observation | MEDIUM | Internal system health monitoring |

---

### 8.4 Ownership Responsibility Matrix

| Role | Responsibilities |
|---|---|
| Domain Owner | Responsible for the quality and governance of all observation types in their domain. Approves new types, schema changes, and governance classification changes. Signs off on retention policies. |
| Observation Steward | Day-to-day quality monitoring for a set of observation types. Escalates quality issues. Conducts monthly source reliability reviews. |
| Consumer System | Uses observations for authorised purposes only. Reports quality anomalies. Does not re-distribute without permission. |
| Observation Engineer | Implements and maintains collection and capture pipelines. Deploys schema changes approved by Domain Owner. |
| Governance Manager | Enforces governance policies. Conducts governance reviews. Escalates violations. Produces compliance reports. |
| Audit Manager | Maintains audit trail. Responds to internal and external audit requests. Alerts on suspicious access patterns. |

---

### 8.5 Naming Standards

**Observation type codes:** `{DOMAIN_CODE}-{CATEGORY_CODE}-{SPECIFIC_CODE}`

Examples:
- `MKT-PRC-QUOTE` — Market Price Quote
- `MKT-PRC-OHLCV-1M` — Market Price 1-Minute Bar
- `CORP-EARN-QUARTERLY` — Company Quarterly Earnings
- `MACRO-MON-REPO` — Macroeconomic Monetary Repo Rate
- `PORT-SNAP-EOD` — Portfolio End-of-Day Snapshot
- `RISK-VOL-REALISED` — Risk Realised Volatility
- `ORD-STATE-CHANGE` — Order State Change
- `TRD-FILL-COMPLETE` — Trade Fill Completed

**Observation ID format:** `OBS-{DOMAIN_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`

**Field naming convention:**
- All field names: lowercase_with_underscores
- Timestamps: end in `_timestamp` or `_date`
- Percentages: named as `xxx_pct` and stored as decimal (0.05 = 5%)
- Monetary values: named as `xxx_inr` or `xxx_usd` to specify currency
- Counts: named as `xxx_count`
- Ratios: named as `xxx_ratio`
- Scores: named as `xxx_score`

---

### 8.6 Metadata Standards

Every observation record MUST contain the following standard metadata fields:

| Field | Type | Required | Description |
|---|---|---|---|
| observation_id | string | MANDATORY | Canonical identifier |
| observation_type | string | MANDATORY | Type code from Catalog |
| domain | string | MANDATORY | One of 16 domains |
| entity_refs | array | MANDATORY | At least one canonical entity_id |
| observation_timestamp | datetime | MANDATORY | UTC ISO 8601 |
| capture_timestamp | datetime | MANDATORY | UTC ISO 8601 |
| storage_timestamp | datetime | MANDATORY | UTC ISO 8601 |
| source_ref | string | MANDATORY | information_id of source |
| context_id | string | MANDATORY | ContextRecord reference |
| observation_quality_score | float | MANDATORY | OQS in [0.0, 1.0] |
| quality_tier | string | MANDATORY | EXCELLENT/GOOD/ACCEPTABLE/MARGINAL/POOR |
| observation_confidence | float | MANDATORY | Confidence in [0.0, 1.0] |
| freshness_tier | string | MANDATORY | FRESH/AGING/STALE/CRITICAL_STALE/EXPIRED |
| version_number | integer | MANDATORY | ≥ 1 |
| governance_tier | string | MANDATORY | CRITICAL/HIGH/MEDIUM/LOW |
| status | string | MANDATORY | ACTIVE/SUPERSEDED/ARCHIVED/RETIRED |
| lineage_id | string | MANDATORY | Reference to lineage record |
| validation_status | string | MANDATORY | PASS/WARN/FAIL |
| collection_domain | string | MANDATORY | Which domain Collector produced this |
| aggregation_type | string | OPTIONAL | If aggregated: AGGREGATED; else absent |

---

### 8.7 Retention Policy Reference

| Domain | Minimum retention | Archive after | Legal hold |
|---|---|---|---|
| Order observations | 7 years | 7 years | Yes |
| Trade observations | 7 years | 7 years | Yes |
| Portfolio observations | 7 years | 7 years | Yes |
| Risk observations | 3 years | 3 years | Yes |
| Market — tick | 90 days | 30 days hot; 60 days warm | No |
| Market — daily bar | 36 months | 18 months warm; 36 months cold | No |
| Company — earnings | 84 months | 84 months | Yes |
| Company — corporate actions | 84 months | 84 months | Yes |
| Macro observations | 120 months | 60 months cold | No |
| Sector observations | 36 months | 36 months | No |
| News observations | 12 months | 12 months | No |
| Social observations | 12 months | 12 months | No |
| AI observations | 24 months | 24 months | No |
| System observations | 90 days | 90 days | No |
| Temporal observations | 24 months | 24 months | No |

---

### 8.8 Security Classification

| Level | Description | Access |
|---|---|---|
| PUBLIC | Non-sensitive observations | No restriction |
| INTERNAL | IIOS internal use only | Authenticated IIOS components only |
| RESTRICTED | Limited to specific consumer roles | Role-based access control; audit all reads |
| CONFIDENTIAL | Commercially sensitive | Named consumers only; encrypted at rest; full audit |

**Mandatory CONFIDENTIAL classification:**
- Trade observations (execution details)
- Portfolio observations (position details)
- Order observations (order strategy details)

---

### 8.9 Compliance Requirements

| Requirement | Affected domains | Control |
|---|---|---|
| SEBI OATS | Order, Trade observations | Tamper-evident audit trail; 5-year minimum retention; on-demand export |
| PMLA | Order, Trade, Portfolio | 10-year retention capability; beneficial ownership tracing |
| Income Tax Act | Trade, Portfolio | 7-year retention; complete and accurate trade history |
| Data localisation | All India-market observations | Stored on India-resident infrastructure or compliant cloud region |

---

### 8.10 Quality Control Standards

| Standard | Specification |
|---|---|
| Minimum OQS for operational use | 0.60 |
| Minimum OQS for CRITICAL domains | 0.70 |
| Absolute minimum OQS (below = quarantine) | 0.25 |
| Minimum confidence for execution-related observations | 0.80 |
| Maximum STALE observations in CRITICAL domain | 0 (any STALE triggers immediate re-observation request) |
| Maximum quarantine rate | 2% of total daily observations |
| Source reliability review threshold | Rolling 90-day accuracy < 0.80 |

---

### 8.11 Historical Preservation Standards

| Standard | Specification |
|---|---|
| Lineage records | PERMANENT — never archived or retired |
| Point-in-time query support | All historical observations must support PIT queries |
| Regime annotation | All historical observations must carry the regime context active at observation time |
| Version chain | Every version of every observation must be preserved |
| Audit trail | Observation audit records preserved for 7 years minimum |
| Context records | ContextRecords preserved for the lifetime of the observations they describe |

---

### 8.12 Governance Review Cycle

| Review | Frequency | Participants | Output |
|---|---|---|---|
| Quality review | Weekly | Observation Stewards | Quality trend report; remediation actions |
| Source reliability review | Monthly | Domain Owners | Trust tier adjustments; source warnings |
| Schema review | Quarterly | Domain Owners, Observation Engineers | Schema changes approved |
| Retention audit | Annually | Domain Owners, Legal | Retention policies confirmed |
| Security classification review | Annually | Governance Manager, Security | Classification updates |
| Full governance audit | Annually | All stakeholders | Governance health assessment |

---
## PART IX — OBSERVATION CONSTITUTION

### 9.1 Purpose

The Observation Constitution defines the non-negotiable rules that govern all observations in the IIOS. These rules are architectural invariants — they may not be bypassed by any component, consumer, or operational procedure. Constitutional rules may only be superseded by a formal governance decision with full stakeholder approval and a documented record.

Rules are organised into six categories: Identity (OC-A), Immutability (OC-B), Temporality (OC-C), Integrity (OC-D), Governance (OC-E), and Intelligence (OC-F).

---

### 9.2 Category OC-A — Identity Rules

**OC-A-001** Every observation MUST have a globally unique canonical observation_id assigned by the Identity Manager at the moment of capture. No two observations may share the same observation_id.

**OC-A-002** The observation_id MUST be assigned by the Identity Manager. No component may self-assign an observation_id.

**OC-A-003** The observation_id MUST conform to the canonical format: `OBS-{DOMAIN_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`.

**OC-A-004** A retired observation_id MUST NOT be reused. Retired IDs are permanently reserved.

**OC-A-005** Every observation MUST reference at least one valid entity via its entity_refs[] field. Observations without an entity reference are not permitted.

**OC-A-006** All entity_ids in an observation's entity_refs[] MUST be valid, resolvable entity identifiers in the Entity Engine at the time the observation is captured.

**OC-A-007** Every observation MUST declare an observation type code. The type code MUST be a valid type registered in the Observation Catalog.

**OC-A-008** Every observation MUST declare its domain. The domain MUST be one of Domain 02–16 (concrete domains). Observations may not be assigned to Domain 01 (Observation Root).

**OC-A-009** The source reference in every observation MUST be a valid, traceable reference to the information object or data record from which the observation was derived.

**OC-A-010** Identity conflicts (same perceived state receiving two observation_ids) MUST be detected and resolved before any downstream distribution.

---

### 9.3 Category OC-B — Immutability Rules

**OC-B-001** An ACTIVE observation MUST NOT be modified in place. All corrections or updates MUST create a new version via the History Manager.

**OC-B-002** A SUPERSEDED observation MUST NOT be modified, deleted, or altered. It is an immutable historical record.

**OC-B-003** A RETIRED observation's lineage record MUST be preserved permanently. Lineage is never retired.

**OC-B-004** The audit trail for an observation MUST be append-only. Existing audit records MUST NOT be modified or deleted.

**OC-B-005** The observation lineage graph MUST be append-only. Lineage records documenting derivation and transformation steps MUST NOT be modified after creation.

**OC-B-006** The original source reference that gave rise to an observation MUST be preserved permanently in the observation's lineage record.

**OC-B-007** No component may write directly to the Observation Registry's storage layer. All writes MUST go through the Observation Recorder's controlled interface.

**OC-B-008** A version chain for an observation MUST be a strict linear sequence. Branching of version chains is prohibited.

**OC-B-009** Once an observation has been distributed to a consumer, the observation content it received MUST be retrievable in identical form from the Registry at any future time (via the version history).

**OC-B-010** The context record attached to an observation MUST be preserved for as long as the observation itself is preserved.

---

### 9.4 Category OC-C — Temporality Rules

**OC-C-001** Every observation MUST have an observation_timestamp specifying the moment the observed state existed in the real world.

**OC-C-002** Every observation MUST have a capture_timestamp specifying the moment the IIOS detected and captured the observation.

**OC-C-003** The observation_timestamp MUST be in UTC and conform to ISO 8601 format: `YYYY-MM-DDTHH:MM:SS.sssZ`.

**OC-C-004** The observation_timestamp MUST NOT be in the future. Observations of future states are forecasts, not observations, and are a distinct observation sub-type with explicit FORECAST classification.

**OC-C-005** The capture_timestamp MUST NOT precede the observation_timestamp. The IIOS cannot capture an observation before the observed state occurred.

**OC-C-006** Point-in-time queries MUST return only observations whose capture_timestamp is on or before the query time. Any observation captured after the query time MUST be excluded. This is the fundamental look-ahead prevention rule.

**OC-C-007** Freshness scores MUST be recomputed dynamically based on elapsed time from the observation_timestamp. A static freshness score computed at capture time MUST NOT be treated as current.

**OC-C-008** Time-series observations for the same entity and type MUST be stored in non-decreasing timestamp order. Out-of-order observations MUST be re-ordered before storage or flagged with an OUT_OF_ORDER flag.

**OC-C-009** Duplicate observations (same entity, type, source, and observation_timestamp) MUST be detected and deduplicated. The duplicate MUST be preserved in the corroboration store, not as a separate Registry entry.

**OC-C-010** Historical revisions (e.g., restated earnings) MUST be recorded as a new version with the revision ingestion timestamp. The original observation MUST be preserved with its original timestamp.

**OC-C-011** The observation latency (capture_timestamp − observation_timestamp) MUST be recorded for every observation and used in the Timeliness quality dimension.

**OC-C-012** All context records MUST capture the state of the investment universe at the observation_timestamp — not at the capture_timestamp or storage_timestamp.

---

### 9.5 Category OC-D — Integrity Rules

**OC-D-001** Every observation MUST have an Observation Quality Score (OQS) computed before it is distributed to any consumer.

**OC-D-002** Observations with OQS < 0.25 (the absolute quality floor) MUST be quarantined. They MUST NOT be distributed to any operational consumer.

**OC-D-003** Observations with OQS in [0.25, 0.40) (POOR tier) MUST be flagged with QUALITY_POOR in all retrieval responses.

**OC-D-004** No observation used as an input to a trade decision MUST have OQS below the operational quality floor (default: 0.60).

**OC-D-005** Quality scores MUST be recomputed when corroborating or contradicting observations arrive, or when freshness degrades across a tier boundary.

**OC-D-006** Every observation MUST have a complete lineage record from its source information object to its current state.

**OC-D-007** Every observation MUST have an attached ContextRecord describing the investment universe state at the observation_timestamp.

**OC-D-008** Observations MUST NOT contain interpretations, predictions, signals, recommendations, or conclusions. The content of an observation MUST be limited to what was directly perceived.

**OC-D-009** Observations MUST NOT contain embedded references to strategies, trade decisions, or risk assessments. These are products of downstream engines, not observations.

**OC-D-010** Every observation's schema MUST conform to the type definition in the Observation Catalog. Observations with fields not defined in the Catalog for their type MUST NOT be admitted to the Registry.

**OC-D-011** Aggregated observations MUST list all constituent observation_ids in their lineage record.

**OC-D-012** Every observation MUST declare its confidence score. An observation without a confidence score MUST NOT be distributed.

**OC-D-013** An observation source whose reliability drops below 0.70 over 90 days MUST have its trust tier reduced and all subsequent observations confidence-penalised.

**OC-D-014** Physical integrity of stored observations MUST be verified through cryptographic hashing. Observations failing integrity checks MUST be quarantined immediately.

**OC-D-015** The Observation Validator MUST apply all six validation levels (L1–L6) to all non-streaming observations before storage.

---

### 9.6 Category OC-E — Governance Rules

**OC-E-001** Every observation type MUST have a designated Domain Owner. Observation types without an owner MUST NOT be activated.

**OC-E-002** Every observation MUST carry a governance tier assignment from the moment of capture.

**OC-E-003** Access control MUST be enforced at the Retrieval Service layer. No observation MUST be returned to an unauthorised consumer regardless of the query method.

**OC-E-004** All observations classified as CONFIDENTIAL MUST be encrypted at rest with AES-256 minimum.

**OC-E-005** Every Create, Read, Update (via versioning), and Archive operation on an observation MUST be recorded in the audit trail.

**OC-E-006** The audit trail MUST be append-only. No audit record MUST be modified or deleted.

**OC-E-007** Audit records for observations MUST be retained for a minimum of 7 years.

**OC-E-008** Observations under a legal hold MUST NOT be archived or retired regardless of retention policy expiry.

**OC-E-009** Governance policies MUST be documented, versioned, and accessible to all stakeholders.

**OC-E-010** A governance review MUST be triggered when: a new observation type is added; a source's trust tier changes; a schema migration is required; a retention period changes.

**OC-E-011** Failed access attempts (unauthorised reads) MUST be recorded in the audit trail with the same completeness as successful reads.

**OC-E-012** The Governance Manager MUST approve all new observation type additions and schema changes before they take effect.

**OC-E-013** Retention policy expiry MUST trigger archival. Observations MUST NOT be archived before their retention period has elapsed except by explicit governance exception.

**OC-E-014** No observation may be permanently deleted before its retention period has elapsed. Data destruction before retention expiry is prohibited.

**OC-E-015** All observation access control lists MUST be reviewed at least annually.

---

### 9.7 Category OC-F — Intelligence Rules

**OC-F-001** The Observation Engine MUST support point-in-time query semantics for all historical observations. Look-ahead bias is a fatal architectural failure.

**OC-F-002** All observations provided to the Evidence Engine MUST be clearly labelled with their observation_timestamp and capture_timestamp, enabling the Evidence Engine to enforce its own look-ahead prevention.

**OC-F-003** Historical observation streams provided for backtesting MUST use the capture_timestamp ≤ backtest_date filter, not the observation_timestamp alone.

**OC-F-004** Survivorship bias correction MUST be available for all historical observation streams. The Observation Registry MUST preserve observations for entities that have been delisted, merged, or dissolved.

**OC-F-005** All historical observations MUST carry regime annotation — the market regime observation that was ACTIVE at the observation_timestamp.

**OC-F-006** The Observation Engine MUST detect and flag any observation that could introduce look-ahead bias into the analytical pipeline. Detection of potential look-ahead MUST halt the relevant analytical process and alert the requesting consumer.

**OC-F-007** Observations of AI model outputs MUST record the model_id, model_version, and training_cutoff_date in the observation's lineage, enabling assessment of model staleness.

**OC-F-008** Observations MUST be consumable by the Evidence Engine without transformation. The Observation Engine's output format MUST be the Evidence Engine's input format.

**OC-F-009** Cross-entity observations (sector aggregates, portfolio aggregates) MUST list all constituent entity_ids and their individual observation_ids in the lineage record.

**OC-F-010** The Observation Engine MUST detect and alert when critical observations are absent — when an expected observation for a critical entity and type has not arrived within the expected interval.

**OC-F-011** Observations of market states during extreme events (VIX > 40, circuit breakers triggered) MUST be flagged with an EXTREME_MARKET_CONDITIONS flag so that downstream engines can apply appropriate treatment.

**OC-F-012** No observation MUST be labelled as "significant", "important", "major", "minor", "bullish", "bearish", "positive", or "negative". These are interpretive labels and are prohibited in observations.

**OC-F-013** The Observation Engine MUST provide the ability for the Evidence Engine to query: "all observations about entity X in the 30 minutes before event Y" — a temporal proximity query. This capability is mandatory.

**OC-F-014** Observations of the same entity from multiple independent sources MUST be corroborated. The corroboration result MUST be recorded in the observation confidence score.

**OC-F-015** The Observation Engine MUST support observation replay — the ability to re-process historical observation streams through current detection and classification rules, producing a refreshed view of historical observations.

---
## PART X — OBSERVATION READINESS CHECKLIST

### 10.1 Purpose

The Observation Readiness Checklist is the operational verification framework applied to every observation before it is designated ACTIVE and released for consumption. It defines the minimum criteria that an observation MUST satisfy in 14 sections. An observation fails readiness if any MANDATORY criterion is not met. Failed observations are rejected back to the quarantine state pending remediation.

The checklist is executed automatically by the Validation Service and Readiness Service as part of the 12-stage lifecycle. The readiness result is stored with the observation record.

---

### 10.2 Section R01 — Captured

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R01-01 | Observation has a source | source_ref is non-null and resolvable | MANDATORY |
| R01-02 | Source is registered | source_ref references a registered source in the Source Registry | MANDATORY |
| R01-03 | Source is active | source status is ACTIVE at observation_timestamp | MANDATORY |
| R01-04 | Capture latency within SLA | (capture_timestamp − observation_timestamp) ≤ SLA(type) | MANDATORY |
| R01-05 | Raw payload preserved | raw observation payload stored in lineage before any processing | RECOMMENDED |
| R01-06 | Collection domain recorded | collection_domain field non-null | MANDATORY |

---

### 10.3 Section R02 — Timestamped

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R02-01 | observation_timestamp present | non-null | MANDATORY |
| R02-02 | observation_timestamp in valid format | ISO 8601 UTC | MANDATORY |
| R02-03 | observation_timestamp not in future | observation_timestamp ≤ NOW() + 5s tolerance | MANDATORY |
| R02-04 | capture_timestamp present | non-null | MANDATORY |
| R02-05 | capture_timestamp ≥ observation_timestamp | no negative latency | MANDATORY |
| R02-06 | storage_timestamp present | non-null; system-assigned at write time | MANDATORY |
| R02-07 | All timestamps UTC | timezone = UTC on all three timestamps | MANDATORY |

---

### 10.4 Section R03 — Validated

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R03-01 | L1 structural validation passed | all mandatory fields present and correctly typed | MANDATORY |
| R03-02 | L2 physical validation passed | values satisfy domain constraints (positive prices, bounded rates) | MANDATORY |
| R03-03 | L3 referential validation passed | all foreign key references resolvable | MANDATORY |
| R03-04 | L4 cross-field consistency passed | all cross-field rules satisfied (high ≥ close ≥ low, etc.) | MANDATORY |
| R03-05 | L5 historical plausibility passed | value within historical range tolerance | RECOMMENDED |
| R03-06 | L6 schema conformance passed | schema version matches Catalog definition | MANDATORY |
| R03-07 | validation_status field set | one of PASS / WARN / FAIL | MANDATORY |

---

### 10.5 Section R04 — Context Assigned

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R04-01 | context_id present | non-null | MANDATORY |
| R04-02 | ContextRecord exists | context_id resolves to a valid ContextRecord | MANDATORY |
| R04-03 | Regime assigned | context.regime non-null | MANDATORY |
| R04-04 | Session context assigned | context.session non-null | MANDATORY |
| R04-05 | Market state captured | context.market_state non-null | MANDATORY |
| R04-06 | Calendar context captured | context.calendar non-null for all trading-relevant types | RECOMMENDED |
| R04-07 | ContextRecord timestamp matches | context.context_timestamp within 60 seconds of observation_timestamp | MANDATORY |

---

### 10.6 Section R05 — Classified

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R05-01 | Observation type assigned | observation_type non-null and valid in Catalog | MANDATORY |
| R05-02 | Domain assigned | domain non-null and valid (Domain 02–16) | MANDATORY |
| R05-03 | Governance tier assigned | governance_tier non-null | MANDATORY |
| R05-04 | Security classification assigned | security_classification non-null | MANDATORY |
| R05-05 | Entity refs present | entity_refs non-empty | MANDATORY |
| R05-06 | Entity refs valid | all entity_ids resolve in Entity Engine | MANDATORY |
| R05-07 | Freshness tier assigned | freshness_tier non-null | MANDATORY |

---

### 10.7 Section R06 — Quality Scored

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R06-01 | OQS computed | observation_quality_score non-null, in [0.0, 1.0] | MANDATORY |
| R06-02 | quality_tier assigned | non-null, consistent with OQS | MANDATORY |
| R06-03 | All 13 quality dimensions scored | no dimension score is null | MANDATORY |
| R06-04 | confidence_score computed | observation_confidence non-null, in [0.0, 1.0] | MANDATORY |
| R06-05 | OQS ≥ quarantine floor | OQS ≥ 0.25 to proceed; else quarantine | MANDATORY |
| R06-06 | Quality dimension scores consistent | no dimension score inconsistency with OQS | RECOMMENDED |
| R06-07 | Quality review flags applied | quality-relevant flags set (LOW_CONFIDENCE, POOR_FRESHNESS, etc.) | MANDATORY |

---

### 10.8 Section R07 — Recorded

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R07-01 | Stored in Observation Registry | observation is retrievable by its observation_id | MANDATORY |
| R07-02 | storage_timestamp set | system-assigned at write; non-null | MANDATORY |
| R07-03 | version_number set | ≥ 1 | MANDATORY |
| R07-04 | status set | ACTIVE | MANDATORY |
| R07-05 | Lineage record created | lineage_id non-null; lineage record exists | MANDATORY |
| R07-06 | Audit record created | at minimum one CREATE event in audit trail | MANDATORY |
| R07-07 | Physical integrity hash computed | integrity_hash non-null | MANDATORY |

---

### 10.9 Section R08 — Indexed

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R08-01 | Primary index entry created | retrievable by observation_id | MANDATORY |
| R08-02 | Entity index entry created | retrievable by entity_id | MANDATORY |
| R08-03 | Type index entry created | retrievable by observation_type | MANDATORY |
| R08-04 | Temporal index entry created | retrievable by observation_timestamp range | MANDATORY |
| R08-05 | Domain index entry created | retrievable by domain | MANDATORY |
| R08-06 | Full-text indexed if applicable | news/social observations searchable by content | RECOMMENDED |
| R08-07 | PIT index entry created | retrievable with point-in-time query by capture_timestamp | MANDATORY |

---

### 10.10 Section R09 — Aggregated (If Applicable)

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R09-01 | Aggregation type declared | aggregation_type field set to AGGREGATED | MANDATORY if aggregated |
| R09-02 | Constituent list complete | all contributing observation_ids listed in lineage | MANDATORY if aggregated |
| R09-03 | Aggregation method documented | method (mean, median, etc.) in lineage | MANDATORY if aggregated |
| R09-04 | Count of constituents | n_constituents field non-null and ≥ 2 | MANDATORY if aggregated |
| R09-05 | Weighting declared | weight scheme declared if weighted | RECOMMENDED if aggregated |
| R09-06 | Missing data handling declared | how missing constituents were treated | RECOMMENDED if aggregated |
| R09-07 | Not applicable flag | aggregation_type = NOT_APPLICABLE for atomic observations | RECOMMENDED |

---

### 10.11 Section R10 — Governed

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R10-01 | Domain owner resolvable | observation_type has active Domain Owner | MANDATORY |
| R10-02 | Access control active | retrieval constraints enforced for observation_type | MANDATORY |
| R10-03 | Retention policy assigned | retention schedule resolvable for domain | MANDATORY |
| R10-04 | Regulatory flags applied | regulatory_flags set appropriately | MANDATORY |
| R10-05 | Legal hold check passed | legal hold status checked and applied | MANDATORY |
| R10-06 | Classification consistent | security_classification consistent with governance_tier | MANDATORY |
| R10-07 | Data localisation compliant | India-market observations stored on compliant infrastructure | MANDATORY |

---

### 10.12 Section R11 — Audited

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R11-01 | CREATE audit record exists | one CREATE event in audit trail at storage_timestamp | MANDATORY |
| R11-02 | Audit record contains actor | actor_id or system_id identified | MANDATORY |
| R11-03 | Audit record contains timestamp | audit_timestamp non-null | MANDATORY |
| R11-04 | Audit record tamper-evident | audit record has integrity hash | MANDATORY |
| R11-05 | Audit trail append-only verification | latest audit record consistent with append-only constraint | MANDATORY |
| R11-06 | Audit record retention period set | audit retention ≥ 7 years | MANDATORY |

---

### 10.13 Section R12 — Distributed

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R12-01 | Distribution queue entry created | observation_id in distribution queue for all subscribed consumers | MANDATORY |
| R12-02 | OQS floor checked before distribution | OQS ≥ consumer's registered quality floor | MANDATORY |
| R12-03 | Freshness checked before distribution | freshness_tier is not EXPIRED | MANDATORY |
| R12-04 | Distribution timestamp recorded | distribution_timestamp non-null | MANDATORY |
| R12-05 | Delivery confirmation required for CRITICAL | consumer acknowledged delivery for CRITICAL governance tier | MANDATORY |
| R12-06 | Distribution audit record created | DISTRIBUTE event in audit trail | MANDATORY |

---

### 10.14 Section R13 — Freshness Monitored

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R13-01 | Freshness SLA registered | SLA(type) resolvable for observation_type | MANDATORY |
| R13-02 | Freshness tier assigned at distribution | freshness_tier assigned based on elapsed time | MANDATORY |
| R13-03 | Freshness alert configured | alert registered for STALE on CRITICAL observations | MANDATORY |
| R13-04 | Absence alert configured | alert registered for late arrival for CRITICAL types | MANDATORY |
| R13-05 | Freshness monitoring interval set | monitoring cadence ≤ SLA(type) / 2 | MANDATORY |
| R13-06 | Freshness trend tracked | freshness tier history tracked for SLA performance reporting | RECOMMENDED |

---

### 10.15 Section R14 — Evidence Engine Ready

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R14-01 | PIT query semantics verified | observation correctly excluded when capture_timestamp > query_time | MANDATORY |
| R14-02 | Regime annotation present | regime_at_observation non-null in ContextRecord | MANDATORY |
| R14-03 | Survivorship bias flag set | is_surviving_entity flag set for market observations | MANDATORY |
| R14-04 | Temporal proximity query support | observation indexed for temporal proximity queries | MANDATORY |
| R14-05 | Look-ahead bias flag absent | no look-ahead_bias flag set | MANDATORY |
| R14-06 | Replayable | observation can be replayed through current classification rules | MANDATORY |
| R14-07 | Evidence format compliant | observation conforms to Evidence Engine input contract | MANDATORY |

---

### 10.16 Use-Case Readiness Matrix

| Use case | R01 | R02 | R03 | R04 | R05 | R06 | R07 | R08 | R09 | R10 | R11 | R12 | R13 | R14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Real-time execution | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | — |
| Backtesting | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | — | ✅ |
| Risk management | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | — |
| Regulatory compliance | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | — | ✅ | ✅ | — | — | — |
| Knowledge Engine input | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Strategy research | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ |
| Audit investigation | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | — | ✅ | ✅ | — | — | — |

Legend: ✅ = required for this use case; — = not required

---
---

## SUPPLEMENT A — OBSERVATION TYPE CATALOGUE

### A.1 Purpose

The Observation Type Catalogue is the authoritative registry of all observation types in the IIOS Observation Engine. Every type specifies its canonical code, required fields, freshness SLA, minimum confidence floor, governance tier, retention period, and access classification.

---

### A.2 Market Domain Types

| Type code | Name | Key required fields | Freshness SLA | Min confidence | Gov tier | Retention |
|---|---|---|---|---|---|---|
| MKT-PRC-QUOTE | Real-time quote | entity_id, price, bid, ask, timestamp | 1 s | 0.90 | CRITICAL | 90 days |
| MKT-PRC-OHLCV-1M | 1-minute OHLCV bar | entity_id, open, high, low, close, volume, bar_start | 120 s | 0.85 | CRITICAL | 90 days |
| MKT-PRC-OHLCV-5M | 5-minute OHLCV bar | entity_id, open, high, low, close, volume, bar_start | 360 s | 0.85 | CRITICAL | 180 days |
| MKT-PRC-OHLCV-1D | Daily OHLCV bar | entity_id, open, high, low, close, volume, bar_date | 1 h | 0.90 | CRITICAL | 36 months |
| MKT-VOL-DAILY | Daily traded volume | entity_id, volume, trade_count, bar_date | 1 h | 0.85 | HIGH | 36 months |
| MKT-DEPTH-L2 | Level-2 order book depth | entity_id, bid_levels, ask_levels, timestamp | 5 s | 0.80 | CRITICAL | 30 days |
| MKT-OI-DAILY | Open interest (daily) | entity_id, open_interest, change_oi, bar_date | 1 h | 0.85 | HIGH | 36 months |
| MKT-IV-DAILY | Implied volatility | entity_id, iv, iv_rank, iv_percentile, bar_date | 1 h | 0.80 | HIGH | 24 months |
| MKT-VWAP-INTRADAY | Intraday VWAP | entity_id, vwap, total_volume, timestamp | 300 s | 0.85 | HIGH | 30 days |
| MKT-IDX-SPOT | Index spot value | entity_id, index_value, change_pct, timestamp | 5 s | 0.95 | CRITICAL | 36 months |

---

### A.3 Company Domain Types

| Type code | Name | Key required fields | Freshness SLA | Min confidence | Gov tier | Retention |
|---|---|---|---|---|---|---|
| CORP-EARN-QUARTERLY | Quarterly earnings | entity_id, revenue, net_income, eps, quarter_end | 24 h | 0.90 | HIGH | 84 months |
| CORP-EARN-ANNUAL | Annual earnings | entity_id, revenue, net_income, eps, fiscal_year | 24 h | 0.90 | HIGH | 84 months |
| CORP-DIV-ANNOUNCEMENT | Dividend announcement | entity_id, dividend_type, amount_inr, ex_date | 24 h | 0.95 | CRITICAL | 84 months |
| CORP-SPLIT-EVENT | Stock split | entity_id, split_ratio, record_date | 24 h | 1.00 | CRITICAL | 84 months |
| CORP-BONUS-ISSUE | Bonus issue | entity_id, bonus_ratio, record_date | 24 h | 1.00 | CRITICAL | 84 months |
| CORP-RATING | Credit rating | entity_id, rating_agency, rating, outlook, rating_date | 48 h | 0.90 | HIGH | 84 months |
| CORP-OWNERSHIP | Ownership pattern | entity_id, promoter_pct, fii_pct, dii_pct, report_date | 24 h | 0.90 | HIGH | 84 months |

---

### A.4 Macro Domain Types

| Type code | Name | Key required fields | Freshness SLA | Min confidence | Gov tier | Retention |
|---|---|---|---|---|---|---|
| MACRO-MON-REPO | RBI repo rate | rate_pct, effective_date, rbi_policy_date | 6 h | 0.99 | HIGH | 120 months |
| MACRO-MON-CRR | Cash reserve ratio | crr_pct, effective_date | 24 h | 0.99 | HIGH | 120 months |
| MACRO-INF-CPI | CPI inflation | cpi_value, yoy_change_pct, reference_month | 24 h | 0.95 | HIGH | 120 months |
| MACRO-INF-WPI | WPI inflation | wpi_value, yoy_change_pct, reference_month | 24 h | 0.95 | HIGH | 120 months |
| MACRO-GDP-QTR | GDP quarterly | gdp_growth_pct, gdp_value_crore, quarter_end | 24 h | 0.95 | HIGH | 120 months |
| MACRO-CAL-HOLIDAY | Market holiday | holiday_date, exchange, description | 7 days | 1.00 | HIGH | 36 months |
| MACRO-VIX-INDIA | India VIX | vix_value, vix_change_pct, timestamp | 60 s | 0.95 | CRITICAL | 36 months |
| MACRO-FX-USDINR | USD/INR FX rate | fx_rate, bid, ask, timestamp | 30 s | 0.90 | HIGH | 36 months |

---

### A.5 Portfolio Domain Types

| Type code | Name | Key required fields | Freshness SLA | Min confidence | Gov tier | Retention |
|---|---|---|---|---|---|---|
| PORT-SNAP-EOD | End-of-day snapshot | portfolio_id, positions[], nav, pnl_realised_inr, date | 2 h | 0.99 | CRITICAL | 7 years |
| PORT-SNAP-INTRADAY | Intraday snapshot | portfolio_id, positions[], nav, unrealised_pnl_inr, timestamp | 300 s | 0.95 | CRITICAL | 90 days |
| PORT-PNL-DAILY | Daily P&L | portfolio_id, realised_inr, unrealised_inr, net_inr, date | 2 h | 0.99 | CRITICAL | 7 years |

---

### A.6 Risk Domain Types

| Type code | Name | Key required fields | Freshness SLA | Min confidence | Gov tier | Retention |
|---|---|---|---|---|---|---|
| RISK-EXP-ENTITY | Entity exposure | entity_id, exposure_inr, exposure_pct, timestamp | 60 s | 0.95 | CRITICAL | 36 months |
| RISK-EXP-SECTOR | Sector exposure | sector_id, exposure_inr, exposure_pct, timestamp | 60 s | 0.95 | CRITICAL | 36 months |
| RISK-DD-REALTIME | Drawdown real-time | portfolio_id, current_dd_pct, peak_nav, trough_nav, timestamp | 60 s | 0.99 | CRITICAL | 36 months |
| RISK-VAR-DAILY | Daily VaR | portfolio_id, var_95_pct, var_99_pct, method, date | 2 h | 0.95 | CRITICAL | 36 months |

---

### A.7 Order and Trade Domain Types

| Type code | Name | Key required fields | Freshness SLA | Min confidence | Gov tier | Retention |
|---|---|---|---|---|---|---|
| ORD-STATE-CHANGE | Order state change | order_id, entity_id, old_state, new_state, timestamp | 5 s | 0.99 | CRITICAL | 7 years |
| ORD-PLACED | Order placed | order_id, entity_id, order_type, qty, price_inr, timestamp | 5 s | 0.99 | CRITICAL | 7 years |
| ORD-CANCELLED | Order cancelled | order_id, reason, cancelled_at | 5 s | 0.99 | CRITICAL | 7 years |
| TRD-FILL-COMPLETE | Trade fill | trade_id, order_id, entity_id, fill_qty, fill_price_inr, timestamp | 5 s | 1.00 | CRITICAL | 7 years |
| TRD-PARTIAL-FILL | Partial trade fill | trade_id, order_id, entity_id, fill_qty, fill_price_inr, remaining_qty, timestamp | 5 s | 1.00 | CRITICAL | 7 years |

---
## SUPPLEMENT B — COMPONENT INTERFACE REFERENCE

### B.1 Purpose

This supplement provides the operational interface specification for all 22 components of the Observation Engine. Each entry documents the primary method, its input parameters, output, p99 latency target, and failure mode.

---

### B.2 Cluster 1 — Observation Registry and Catalog

**OC-01 — Observation Catalog**

| Attribute | Specification |
|---|---|
| Primary method | lookup_type(type_code) |
| Input | type_code: string |
| Output | ObservationTypeDefinition |
| p99 latency | < 5 ms |
| Failure mode | Return TYPE_NOT_FOUND if type_code unknown; never throw |

---

**OC-02 — Observation Registry**

| Attribute | Specification |
|---|---|
| Primary method | store(observation: ObservationRecord) |
| Input | observation: ObservationRecord with all mandatory fields |
| Output | observation_id: string |
| p99 latency | < 50 ms |
| Failure mode | If mandatory fields missing, raise ObservationValidationError |

---

**OC-03 — Source Registry**

| Attribute | Specification |
|---|---|
| Primary method | get_source(source_id) |
| Input | source_id: string |
| Output | SourceRecord |
| p99 latency | < 5 ms |
| Failure mode | Return SOURCE_NOT_FOUND; do not throw |

---

**OC-04 — Entity Reference Manager**

| Attribute | Specification |
|---|---|
| Primary method | resolve_entity(entity_id) |
| Input | entity_id: string |
| Output | EntityReference |
| p99 latency | < 5 ms |
| Failure mode | ENTITY_NOT_FOUND returned; observation quarantined |

---

### B.3 Cluster 2 — Collection Domain

**OC-05 — Market Data Collector**

| Attribute | Specification |
|---|---|
| Primary method | start_collection(config: CollectionConfig) |
| Input | config: CollectionConfig |
| Output | collection_handle: CollectionHandle |
| p99 latency | < 500 ms to first observation |
| Failure mode | COLLECTION_FAILED on source unavailability; exponential backoff |

---

**OC-06 — Company Event Collector**

| Attribute | Specification |
|---|---|
| Primary method | poll_events(since_timestamp) |
| Input | since_timestamp: datetime |
| Output | List[RawObservationPayload] |
| p99 latency | < 2000 ms |
| Failure mode | Return empty list on source failure; alert |

---

**OC-07 — Macro Data Collector**

| Attribute | Specification |
|---|---|
| Primary method | poll_macro(since_timestamp) |
| Input | since_timestamp: datetime |
| Output | List[RawObservationPayload] |
| p99 latency | < 2000 ms |
| Failure mode | Return empty list; schedule retry at next interval |

---

**OC-08 — Alternative Data Collector**

| Attribute | Specification |
|---|---|
| Primary method | fetch_alternative(feed_id, since_timestamp) |
| Input | feed_id: string, since_timestamp: datetime |
| Output | List[RawObservationPayload] |
| p99 latency | < 5000 ms |
| Failure mode | Mark feed DEGRADED; skip and alert |

---

### B.4 Cluster 3 — Capture and Validation

**OC-09 — Observation Validator**

| Attribute | Specification |
|---|---|
| Primary method | validate(payload, type_def) |
| Input | payload: RawObservationPayload, type_def: ObservationTypeDefinition |
| Output | ValidationResult |
| p99 latency | < 10 ms |
| Failure mode | Always returns result; never throws; on fatal failure returns FAIL |

---

**OC-10 — Timestamp Service**

| Attribute | Specification |
|---|---|
| Primary method | assign_timestamps(payload) |
| Input | payload: RawObservationPayload |
| Output | TimestampedPayload |
| p99 latency | < 1 ms |
| Failure mode | System time failure → log and use NTP fallback; never use local wall clock alone |

---

**OC-11 — Identity Manager**

| Attribute | Specification |
|---|---|
| Primary method | assign_id(domain, type_code, date) |
| Input | domain: string, type_code: string, date: date |
| Output | observation_id: string |
| p99 latency | < 5 ms |
| Failure mode | ID assignment failure → fatal; halt observation pipeline until resolved |

---

**OC-12 — Deduplication Service**

| Attribute | Specification |
|---|---|
| Primary method | check_duplicate(fingerprint) |
| Input | fingerprint: ObservationFingerprint |
| Output | DuplicateCheckResult |
| p99 latency | < 5 ms |
| Failure mode | On dedup service failure, admit observation with DEDUP_SKIPPED flag |

---

### B.5 Cluster 4 — Context and Classification

**OC-13 — Context Manager**

| Attribute | Specification |
|---|---|
| Primary method | get_context(observation_timestamp) |
| Input | observation_timestamp: datetime |
| Output | ContextRecord |
| p99 latency | < 20 ms |
| Failure mode | Return degraded context record with CONTEXT_PARTIAL flag; never block |

---

**OC-14 — Observation Classifier**

| Attribute | Specification |
|---|---|
| Primary method | classify(observation) |
| Input | observation: PartialObservationRecord |
| Output | ClassificationResult |
| p99 latency | < 10 ms |
| Failure mode | On classification failure, set type to UNKNOWN; quarantine |

---

**OC-15 — Entity Linker**

| Attribute | Specification |
|---|---|
| Primary method | link_entities(observation) |
| Input | observation: PartialObservationRecord |
| Output | LinkedObservation |
| p99 latency | < 15 ms |
| Failure mode | Unresolvable entity → quarantine observation with ENTITY_LINK_FAILED flag |

---

**OC-16 — Source Tracker**

| Attribute | Specification |
|---|---|
| Primary method | record_source_event(source_id, event_type, timestamp) |
| Input | source_id, event_type, timestamp |
| Output | None |
| p99 latency | < 5 ms |
| Failure mode | Silent failure; queue event for async retry |

---

### B.6 Cluster 5 — Quality Services

**OC-17 — Quality Scorer**

| Attribute | Specification |
|---|---|
| Primary method | compute_oqs(observation) |
| Input | observation: ObservationRecord |
| Output | OQSResult |
| p99 latency | < 20 ms |
| Failure mode | On partial failure, use available dimensions; note degraded quality in OQS flags |

---

**OC-18 — Confidence Manager**

| Attribute | Specification |
|---|---|
| Primary method | compute_confidence(observation) |
| Input | observation: ObservationRecord |
| Output | ConfidenceScore: float in [0.0, 1.0] |
| p99 latency | < 10 ms |
| Failure mode | On failure, assign default_confidence(type); flag CONFIDENCE_DEFAULT |

---

**OC-19 — Corroboration Service**

| Attribute | Specification |
|---|---|
| Primary method | corroborate(observation_id, corroborating_obs) |
| Input | observation_id: string, corroborating_obs: ObservationRecord |
| Output | CorroborationResult |
| p99 latency | < 30 ms |
| Failure mode | On failure, proceed without corroboration; note LOW_CORROBORATION |

---

**OC-20 — Freshness Monitor**

| Attribute | Specification |
|---|---|
| Primary method | get_freshness_tier(observation_id, eval_timestamp) |
| Input | observation_id: string, eval_timestamp: datetime |
| Output | FreshnessTier enum |
| p99 latency | < 5 ms |
| Failure mode | On failure, return FRESHNESS_UNKNOWN; consumer treats as STALE |

---

### B.7 Cluster 6 — Governance and Observation Engine Management

**OC-21 — History Manager**

| Attribute | Specification |
|---|---|
| Primary method | create_version(existing_id, updated_observation) |
| Input | existing_id: string, updated_observation: ObservationRecord |
| Output | new_observation_id: string |
| p99 latency | < 50 ms |
| Failure mode | On failure, reject update; preserve existing version |

---

**OC-22 — Audit Logger**

| Attribute | Specification |
|---|---|
| Primary method | log_event(observation_id, event_type, actor_id, detail) |
| Input | observation_id, event_type, actor_id, detail |
| Output | audit_record_id: string |
| p99 latency | < 5 ms |
| Failure mode | On audit logger failure → CRITICAL alert; block operation (audit integrity is non-negotiable) |

---
## SUPPLEMENT C — PROCESSING PIPELINE PATTERNS

### C.1 Purpose

This supplement details four foundational pipeline patterns used by the Observation Engine. Each pattern is described with its architectural flow, trigger, components involved, and applicable observation types.

---

### C.2 Pattern P-01 — Point-in-Time Observation Pipeline

**Purpose:** Ensure every observation is fully timestamped and anchored to a PIT record so historical consumers can reconstruct the observation universe as it existed at any moment in the past.

**Trigger:** Any new observation reaching the Observation Recorder.

**Flow:**

```
Raw Payload
    |
    v
[Timestamp Service]
 - assign observation_timestamp (from payload or source clock)
 - assign capture_timestamp (system clock, NTP-validated)
    |
    v
[Identity Manager]
 - assign observation_id: OBS-{DOMAIN}-{TYPE}-{DATE}-{SEQ}
    |
    v
[Observation Validator]
 - L1: structural check
 - L3: referential check (resolve entity_ids, source_ref)
 - L6: schema check
    |
    v
[Observation Recorder]
 - write to Registry with storage_timestamp
 - create lineage record
 - write PIT index entry (capture_timestamp → observation_id)
    |
    v
[Audit Logger]
 - CREATE event written to audit trail
```

**PIT query semantics:**
All PIT queries use the filter: `capture_timestamp ≤ query_timestamp`. This ensures observations whose source was not yet available (e.g., restated earnings released after the fact) are not visible at the original observation date — preventing look-ahead bias.

---

### C.3 Pattern P-02 — Cross-Domain Corroboration Pipeline

**Purpose:** Validate CRITICAL observations through cross-source and cross-domain corroboration before they achieve full GOOD or EXCELLENT quality tier.

**Trigger:** A CRITICAL observation is stored with OQS < 0.85.

**Flow:**

```
New CRITICAL observation stored (OQS < 0.85)
    |
    v
[Corroboration Service]
 - search Observation Registry for:
   * same entity + same type + same timestamp window (±tolerance)
   * different source_ref
    |
    v
  [If corroborating observations found]
        |
        v
  [Confidence Manager]
  - update confidence using cross-source agreement formula
        |
        v
  [Quality Scorer]
  - recompute OQS with updated confidence dimension
        |
        v
  [History Manager]
  - create new version with updated OQS and confidence
  - supersede previous version
        |
        v
  [Distribution Service]
  - re-distribute updated observation to subscribed consumers

  [If no corroborating observations found]
        |
        v
  [Corroboration Service]
  - set AWAITING_CORROBORATION flag
  - schedule corroboration timeout check
  - after timeout: set UNCONFIRMED flag; distribute as UNCONFIRMED
```

---

### C.4 Pattern P-03 — Deduplication Pipeline

**Purpose:** Prevent the same observed state from being stored as multiple distinct observations in the Registry.

**Trigger:** Any new raw payload arrives before identity assignment.

**Flow:**

```
Raw Payload arrives
    |
    v
[Deduplication Service]
 - compute fingerprint:
   * entity_id + observation_type + source_id + timestamp_bucket
 - query dedup bloom filter
    |
    v
  [If duplicate detected]
        |
        v
  [Corroboration Service]
  - store as corroborating observation (not a new Registry entry)
  - update corroboration count on primary observation
  - update confidence on primary observation

  [If no duplicate]
        |
        v
  Continue to main observation pipeline (Stages 1–12)
```

**Timestamp bucketing:** Observations with observation_timestamp within the tolerance window for their type (e.g., ±1 second for tick data; ±5 minutes for daily data) are treated as the same temporal event for dedup purposes.

---

### C.5 Pattern P-04 — Aggregation Pipeline

**Purpose:** Produce aggregated observations (e.g., sector aggregates, portfolio snapshots, daily summary bars) from a set of constituent atomic observations.

**Trigger:** Scheduled aggregation job (e.g., end-of-day bar computation) or consumer request for a derived aggregate.

**Flow:**

```
Aggregation request (type, entity_set, time_range)
    |
    v
[Retrieval Service]
 - fetch all constituent observations matching:
   * entity_id IN entity_set
   * observation_type = constituent_type
   * observation_timestamp IN time_range
   * capture_timestamp ≤ aggregation_run_timestamp (PIT-safe)
    |
    v
[Aggregation Service]
 - apply aggregation function (OHLCV sum/max/min, mean, etc.)
 - record: n_constituents, missing_count, aggregation_method
    |
    v
[Identity Manager]
 - assign new observation_id for aggregate

[Context Manager]
 - assign context at aggregation_timestamp

[Quality Scorer]
 - compute OQS: note reduced accuracy if n_missing > 0
    |
    v
[Observation Recorder]
 - store aggregate with aggregation_type = AGGREGATED
 - lineage: list all constituent observation_ids
 - link to all constituent observations
    |
    v
[Distribution Service]
 - distribute aggregate to subscribed consumers
```

**Missing constituent handling:**
If > 20% of expected constituents are missing, the aggregate is flagged with INCOMPLETE_AGGREGATION and its OQS is capped at 0.70 regardless of other dimensions.

---
## SUPPLEMENT D — QUALITY FRAMEWORK REFERENCE

### D.1 Dimension Weight Table

| Dimension | Code | Weight (raw) | Weight (normalised) |
|---|---|---|---|
| Accuracy | ACC | 0.15 | 14.42% |
| Precision | PRE | 0.10 | 9.62% |
| Consistency | CON | 0.10 | 9.62% |
| Completeness | CMP | 0.10 | 9.62% |
| Freshness | FRS | 0.12 | 11.54% |
| Coverage | CVG | 0.08 | 7.69% |
| Reliability | REL | 0.08 | 7.69% |
| Trustworthiness | TRW | 0.07 | 6.73% |
| Granularity | GRN | 0.06 | 5.77% |
| Frequency | FRQ | 0.05 | 4.81% |
| Confidence | CFD | 0.05 | 4.81% |
| Context Richness | CRX | 0.04 | 3.85% |
| Source Quality | SRC | 0.04 | 3.85% |
| **Total** | | **1.04** | **100.00%** |

---

### D.2 Representative OQS by Scenario

| Scenario | ACC | PRE | CON | CMP | FRS | OQS (approx.) | Tier |
|---|---|---|---|---|---|---|---|
| Live NSE tick from primary feed | 0.95 | 1.00 | 0.95 | 1.00 | 1.00 | ~0.96 | EXCELLENT |
| NSE daily OHLCV (EOD batch) | 0.95 | 1.00 | 0.95 | 1.00 | 0.90 | ~0.94 | EXCELLENT |
| Earnings report — single source | 0.85 | 0.90 | 0.90 | 0.95 | 0.95 | ~0.88 | GOOD |
| NSE tick via fallback feed | 0.80 | 0.90 | 0.85 | 0.95 | 0.95 | ~0.85 | GOOD |
| Earnings report — no corroboration | 0.75 | 0.90 | 0.85 | 0.90 | 0.90 | ~0.83 | GOOD |
| VIX reading — 15 min delayed | 0.90 | 1.00 | 0.95 | 1.00 | 0.65 | ~0.82 | GOOD |
| News observation — single publisher | 0.70 | 0.80 | 0.80 | 0.85 | 0.95 | ~0.78 | GOOD |
| Social observation — low-trust source | 0.55 | 0.70 | 0.65 | 0.75 | 0.90 | ~0.65 | ACCEPTABLE |
| Macro indicator — 2 days stale | 0.90 | 1.00 | 0.95 | 0.95 | 0.30 | ~0.65 | ACCEPTABLE |
| AI model output — model stale | 0.65 | 0.80 | 0.70 | 0.90 | 0.50 | ~0.63 | ACCEPTABLE |
| Alternative data — unverified | 0.45 | 0.60 | 0.55 | 0.65 | 0.80 | ~0.52 | MARGINAL |
| Tick data — feed outage recovery | 0.70 | 0.90 | 0.60 | 0.70 | 0.20 | ~0.50 | MARGINAL |
| Macro — 1 week stale | 0.90 | 1.00 | 0.95 | 0.95 | 0.05 | ~0.48 | MARGINAL |
| Unverified social — no source | 0.30 | 0.40 | 0.35 | 0.40 | 0.80 | ~0.35 | POOR |
| Corrupted tick payload | 0.10 | 0.20 | 0.10 | 0.40 | 1.00 | ~0.25 | POOR |

---

### D.3 Monitoring Dashboard Metrics

The Quality Monitoring Service exposes the following metrics in the IIOS telemetry stream:

| Metric | Description | Alert condition |
|---|---|---|
| oqs_mean_by_domain | Rolling 30-min mean OQS per domain | < 0.75 for any domain |
| oqs_p10_by_domain | 10th percentile OQS per domain | < 0.60 for CRITICAL domain |
| poor_obs_pct | % of observations in POOR tier (rolling 1 h) | > 2% |
| quarantine_rate | % of observations quarantined (rolling 1 h) | > 1% |
| staleness_count_critical | Count of STALE observations in CRITICAL domains | > 0 |
| stale_critical_types | List of CRITICAL types currently STALE | Any entry |
| corroboration_gap_critical | CRITICAL observations with < 2 corroborating sources | > 0 |
| dedup_rate | % of arrivals rejected as duplicates (rolling 1 h) | > 5% (potential feed loop) |
| validation_fail_rate | % of observations failing validation (rolling 1 h) | > 1% |
| context_partial_rate | % of observations with CONTEXT_PARTIAL flag (rolling 1 h) | > 2% |

---

### D.4 Quality Improvement Guidance Reference

| Symptom | Likely root cause | Investigation | Remediation |
|---|---|---|---|
| ACC degrading across domain | Source feed quality issue | Check source reliability; cross-source divergence | Escalate to source provider; switch to fallback |
| FRS degrading for multiple types | Acquisition job failure or lag | Check job scheduler; check source latency | Restart acquisition job; escalate source |
| CMP declining for specific type | Source stopped providing field | Check source API changelog | Update extraction rule; add field fallback |
| CON failing cross-field rules | Schema change in source format | Inspect raw payloads for format changes | Update parser; validate against new schema |
| TRW declining for source | Trust tier review found issues | Review source accuracy track record | Reduce trust tier; apply confidence penalty |
| CRX declining | Context Manager latency spike | Check Context Manager health | Scale Context Manager; pre-warm regime observations |
| SRC declining | Multiple source health issues | Dashboard: source health scores | Source rotation; add backup sources |
| Low corroboration rate | Second source unavailable | Check second source SLA and connectivity | Onboard backup source for critical types |

---
## SUPPLEMENT E — GOVERNANCE DECISION RECORDS

### GDR-001 — Observation Immutability

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Should observations be mutable (allowing in-place correction) or immutable (requiring a new version for every change)?

**Decision:** Observations are immutable once admitted to the ACTIVE state. Corrections create new versions via the History Manager. The original observation is preserved in SUPERSEDED state.

**Rationale:**
1. Analytical reproducibility requires that the state of knowledge at any historical moment can be reconstructed exactly. A mutable store cannot guarantee this.
2. Point-in-time query semantics require stable historical records. An observation that was correct at 14:30:00 must remain visible with its 14:30:00 content.
3. Regulatory compliance (SEBI, PMLA) requires tamper-evident records. Immutability provides a stronger audit foundation than a mutation log.
4. Downstream consumers (backtesting, Evidence Engine) require stable historical replay. Mutable observations break replay reproducibility.

**Consequence accepted:** Corrections are more expensive (new version created, old superseded). This cost is deliberately accepted to preserve analytical integrity.

---

### GDR-002 — Purity Enforcement (No Interpretation in Observations)

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Should observations be permitted to contain interpretation, scores, labels, signals, or recommendations?

**Decision:** No. Observations are strictly limited to the directly perceived state of the world. No interpretation, conclusion, signal, prediction, label, or recommendation may appear in an observation.

**Rationale:**
1. Separation of concerns: the Observation Engine perceives; the Evidence Engine interprets; the Knowledge Engine concludes. Violating this boundary creates coupling that is extremely difficult to unwind.
2. Reusability: a pure observation is usable by any downstream consumer with any analytical approach. An observation contaminated with interpretation from one analytical model is not usable by a different model.
3. Auditability: when an observation contains both raw data and an interpretation, it is impossible to audit which errors in downstream outputs arose from the data and which arose from the embedded interpretation.
4. Bias prevention: interpretive labels in observations would propagate the biases of whatever model produced the label throughout the analytical pipeline.

**Consequence accepted:** Downstream engines must perform their own interpretation. This is deliberate — they are designed for that purpose.

---

### GDR-003 — Mandatory Context Records

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Should context records be optional (attached only when useful) or mandatory (required for every observation)?

**Decision:** Mandatory. Every observation MUST have an attached ContextRecord.

**Rationale:**
1. Without context, an observation is inherently ambiguous. A VIX reading of 35 means different things during a normal market day vs during a circuit-breaker event. The context disambiguates.
2. Historical analytical quality depends on context. Backtesting that ignores the market regime in which historical trades occurred produces regime-blind results.
3. Making context optional creates a two-tier observation population — contextualized and decontextualized — that is difficult to query uniformly.
4. The cost of context enrichment at capture time is lower than the cost of reconstructing context analytically years later.

**Consequence accepted:** Context Manager must be always available. This is a hard dependency. Context Manager has its own high-availability design.

---

### GDR-004 — Capture Timestamp Separation from Observation Timestamp

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Is one timestamp sufficient, or must two (observation_timestamp and capture_timestamp) be maintained for every observation?

**Decision:** Two timestamps are mandatory: observation_timestamp (when the state existed in the world) and capture_timestamp (when the IIOS detected and recorded it).

**Rationale:**
1. The distinction between "when it happened" and "when we knew about it" is fundamental to look-ahead bias prevention. Using only observation_timestamp in PIT queries would admit observations whose source was not available until later — introducing look-ahead.
2. Corporate events (earnings, dividends) are often announced days after the relevant date. The observation_timestamp is the announcement date; the capture_timestamp is when the IIOS ingested the announcement.
3. Delayed data feeds are common. A data feed may deliver yesterday's closing prices at market open today. capture_timestamp records the actual availability of the data.
4. Audit and compliance require traceability of when the IIOS had knowledge of a fact — this is the capture_timestamp, not the observation_timestamp.

**Consequence accepted:** All queries, backtesting pipelines, and evidence queries must specify which timestamp they are filtering on. This is explicitly required by OC-C-006.

---

### GDR-005 — Source Trust Tier Architecture

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Should source quality be a binary reliable/unreliable flag, or a graduated trust tier?

**Decision:** Graduated 5-tier trust architecture: AUTHORITATIVE → RELIABLE → STANDARD → PROVISIONAL → UNRELIABLE.

**Rationale:**
1. Binary classification cannot capture the real spectrum of source quality. A newly onboarded provider whose reliability is unknown is not equivalent to a known-unreliable source — the former is PROVISIONAL, not UNRELIABLE.
2. Graduated tiers allow proportional confidence penalisation. An AUTHORITATIVE source contributes full confidence weight; a PROVISIONAL source contributes a reduced weight without being excluded entirely.
3. Trust tiers enable automated decision-making in the Confidence Manager and Quality Scorer without requiring manual human review of every observation.
4. The five tiers map to the five practical states a source can be in over its operational lifecycle.

**Consequence accepted:** Trust tier reviews must be scheduled and conducted. Degrading a source's trust tier requires governance approval. This is the correct trade-off: trust changes have systemic consequences and must be deliberate.

---

### GDR-006 — Observation Purity: No Deletion Policy

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** When an observation is found to be incorrect, should it be deleted from the Registry?

**Decision:** No observation may be deleted before its retention period has elapsed. Incorrect observations are SUPERSEDED by corrected versions. Both the incorrect and correct versions are preserved.

**Rationale:**
1. The historical record of what the IIOS believed at any moment — including observations it later found to be incorrect — is itself analytically valuable. Understanding past errors enables model improvement.
2. Deleting incorrect observations would break the audit trail and version chain, making it impossible to reconstruct the state of IIOS knowledge at arbitrary historical moments.
3. Regulatory compliance requires that original records be preserved even if superseded by corrections.
4. Downstream engines that consumed the original observation before the correction need to be able to identify what they consumed — this requires the original to remain accessible in SUPERSEDED state.

**Consequence accepted:** Storage grows permanently. This is explicitly accepted and budgeted for. Data volume projections are included in the capacity model.

---
## SUPPLEMENT F — ANTI-PATTERN REFERENCE

### F.1 Purpose

This supplement catalogs the most common anti-patterns that undermine the architectural integrity of the Observation Engine. Each anti-pattern is described with its observable symptoms, root cause, architectural harm, and required remediation.

---

### AP-01 — The Interpreted Observation

**Description:** An observation that contains an analytical judgement embedded in its content — e.g., "price is elevated relative to fair value", "earnings were disappointing", "volume is unusually high".

**Symptom:** Observation fields contain qualitative labels, sentiment scores, or signal indicators alongside raw observed values.

**Root cause:** Developers conflating the Observation Engine (perception) with the Evidence Engine (interpretation) or the Knowledge Engine (conclusion).

**Architectural harm:** Downstream engines receive pre-interpreted observations that force them to accept the analytical model embedded in the observation. Different consumers may require different interpretations of the same raw observation. Analytical independence is destroyed.

**Remediation:** Strip all interpretive content from the observation. Store raw values only. Move any analytical scoring to the Evidence Engine or Knowledge Engine as appropriate. If analytical labels are required for certain consumers, create a separate Evidence Engine output that references the observation by observation_id.

---

### AP-02 — The Timestampless Observation

**Description:** An observation recorded without an observation_timestamp — or with only a relative timestamp ("3 days ago", "this morning").

**Symptom:** observation_timestamp is null, approximate, or relative rather than an absolute UTC datetime.

**Root cause:** Acquisition pipeline not enforcing timestamp extraction from the source. Developer assumed the ingestion time is "close enough" to the observation time.

**Architectural harm:** PIT queries cannot work correctly. Historical analysis cannot anchor the observation to the correct moment. Look-ahead bias is introduced if the capture timestamp is used as a proxy.

**Remediation:** Every acquisition pipeline MUST extract an explicit observation_timestamp from the source payload. If the source does not provide a timestamp, the observation MUST be flagged with TIMESTAMP_INFERRED and assigned the capture_timestamp as a best-effort approximation with confidence penalised.

---

### AP-03 — The Sourceless Observation

**Description:** An observation that does not have a valid source reference — either source_ref is null, or it references a source not registered in the Source Registry.

**Symptom:** source_ref is null or unresolvable; lineage record has no source entry.

**Root cause:** Ad-hoc observation creation bypassing the Source Registry and the Observation Validator.

**Architectural harm:** Traceability is broken. Quality scoring is impossible without a source trust tier. Regulatory audit cannot trace observations to their origin. Source reliability tracking cannot function.

**Remediation:** All observations MUST pass through the Observation Validator (L3 referential check). Source Registry MUST be queried at validation time. Any observation with an unresolvable source_ref MUST be quarantined with INVALID_SOURCE status.

---

### AP-04 — The Look-Ahead Observation

**Description:** An observation used in a historical analysis with a capture_timestamp that post-dates the analysis moment — the IIOS is using information it did not yet have at that moment.

**Symptom:** Backtesting results dramatically outperform live performance. Historical analytical outputs reference observations not yet captured at the relevant historical time.

**Root cause:** Historical queries filtering only on observation_timestamp, ignoring capture_timestamp. The correct filter is: `capture_timestamp ≤ analysis_moment`.

**Architectural harm:** All historical analysis, backtesting, and model training that uses look-ahead observations is invalid. Strategies selected based on look-ahead-contaminated analysis will fail in live trading.

**Remediation:** Enforce OC-C-006 at the Retrieval Service layer. All PIT queries must use the `capture_timestamp ≤ query_time` filter. Backtesting pipelines must use the Retrieval Service's PIT query interface — never direct Registry queries.

---

### AP-05 — The Aggregation Identity Theft

**Description:** An aggregated observation stored with the same observation_id as one of its constituent atomic observations, overwriting the original.

**Symptom:** Atomic observations disappear from the Registry when aggregates are created. Lineage chains are broken.

**Root cause:** Aggregation pipeline reusing atomic observation IDs rather than requesting new IDs from the Identity Manager.

**Architectural harm:** Original atomic observations are lost. Historical queries return aggregate values at timestamps where atomic values should appear. Version chains are broken. Downstream engines relying on atomic granularity fail silently.

**Remediation:** The Identity Manager MUST assign a new observation_id for every aggregated observation. Aggregation pipelines MUST use the Identity Manager for ID assignment. The Observation Recorder MUST reject aggregates with IDs that match existing atomic observation IDs.

---

### AP-06 — The Staleness Blindspot

**Description:** A consumer system using observations without checking freshness, silently accepting STALE or EXPIRED observations as current.

**Symptom:** Consumer decisions are based on observations whose freshness_tier is STALE or EXPIRED. The consumer has no quality floor check in its retrieval request.

**Root cause:** Consumer system not specifying a quality floor or freshness floor in retrieval requests. Retrieval Service permitting unconstrained queries.

**Architectural harm:** Execution decisions based on stale market data. Risk assessments based on stale risk observations. Potentially significant financial harm.

**Remediation:** The Retrieval Service MUST enforce minimum quality floors specified in every consumer's registered profile. Consumers MUST specify their freshness requirements. The Freshness Monitor MUST alert and halt distribution of CRITICAL observations that have become STALE.

---

### AP-07 — The Context Desert

**Description:** Observations stored without a ContextRecord — either because the Context Manager was temporarily unavailable and the system admitted observations without context, or because a pipeline bypassed context enrichment.

**Symptom:** context_id is null or points to a default/empty ContextRecord with no regime, session, or market state information.

**Root cause:** Context Manager failure causing the observation pipeline to admit observations rather than pause. Or: observation pipeline that bypasses the Context Manager for "efficiency".

**Architectural harm:** Historical analysis without context is regime-blind. The Evidence Engine cannot perform regime-aware analysis on decontextualized observations. The value of context is cumulative — a large cohort of decontextualized observations degrades all downstream analytical quality.

**Remediation:** Observations MUST NOT be admitted to the Registry with null or default context records. When the Context Manager is unavailable, the observation pipeline MUST enter a degraded-context mode, storing observations with CONTEXT_PARTIAL flag and re-enriching when Context Manager recovers.

---

### AP-08 — The Mutation Mirage

**Description:** An observation that has been modified in-place in the Registry storage layer, bypassing the History Manager and the versioning system.

**Symptom:** An observation's content has changed since it was last retrieved, but no new version exists in the version chain. The original content is gone.

**Root cause:** Direct database writes bypassing the Observation Recorder and History Manager. Developer or operational process treating the Registry like a mutable database.

**Architectural harm:** The fundamental architectural invariant of immutability is violated. Historical replays will produce different results at different times. Audit trails are broken. Downstream consumers that cached the observation will have divergent state from the Registry.

**Remediation:** Database access to the Observation Registry MUST be restricted to the Observation Recorder only. All other access is read-only. Write permissions at the database layer must enforce this. Periodic integrity audits must detect any in-place modifications by comparing observation content hashes.

---

### AP-09 — The Deduplication Dropout

**Description:** The same observation arriving twice from the same source being stored as two distinct observations in the Registry rather than being deduplicated.

**Symptom:** Duplicate observation_ids exist for the same entity, type, source, and timestamp. Corroboration counts are inflated by self-corroboration.

**Root cause:** Deduplication Service failure or bypass. Feed delivering duplicate payloads and the dedup bloom filter not catching them.

**Architectural harm:** Query results for an entity at a timestamp return multiple apparently distinct observations. Aggregations count the same event twice. Confidence scores are inflated by self-corroboration. Portfolio state calculations may double-count events.

**Remediation:** Deduplication Service MUST be in the observation pipeline before Identity assignment. Bloom filter false-positive rate must be monitored. Periodic deduplication audits must identify Registry duplicates and merge them, with the earlier identity retained and the later one superseded.

---

### AP-10 — The Schema Drift

**Description:** An observation type's actual schema in the Registry has diverged from its definition in the Observation Catalog, because observations were admitted without enforcing the Catalog schema.

**Symptom:** Retrieval Service returns observations for a type with unexpected fields, missing fields, or different data types than the Catalog specifies. Consumers fail with field parse errors.

**Root cause:** Schema changes deployed to the acquisition pipeline without updating the Catalog definition. Or: Observation Validator's L6 schema check is disabled or misconfigured.

**Architectural harm:** Consumers cannot rely on observation schemas. Quality scoring breaks for fields that have changed type. Downstream engines built against the Catalog contract fail silently or crash.

**Remediation:** The Observation Catalog MUST be updated before any schema change is deployed to acquisition pipelines. The Observation Validator's L6 schema check MUST be mandatory. Schema migration must follow the governed process (reviewed and approved by the Domain Owner).

---
## SUPPLEMENT G — OBSERVATION ENGINE GLOSSARY

### G.1 Purpose

This glossary defines all terms specific to the Observation Engine architecture. Terms are listed alphabetically. Where a term overlaps with IIOS-wide terminology, the Observation Engine–specific usage is noted.

---

**Absence Alert**
An alert triggered when an expected observation for a CRITICAL type and entity has not arrived within the expected interval. Absence is an observable signal in itself.

**Acquisition Pipeline**
The automated collection, extraction, and delivery system that retrieves raw data from external or internal sources and delivers it as raw payloads to the Observation Capture Service. Each acquisition pipeline operates on a schedule or trigger defined in the Source Registry.

**Aggregated Observation**
An observation computed from multiple constituent atomic observations. Aggregated observations carry an aggregation_type = AGGREGATED field and list all constituent observation_ids in their lineage record.

**Atomic Observation**
An observation of a single measurable quantity for a single entity at a single moment in time. Atomic observations are the elemental unit of the Registry.

**Audit Trail**
The append-only sequence of audit records documenting every operation performed on every observation. The audit trail is the primary evidence base for compliance, governance, and error investigation.

**Capture Latency**
The elapsed time between the observation_timestamp (when the state existed in the world) and the capture_timestamp (when the IIOS detected and recorded it). A key component of the Timeliness quality dimension.

**Capture Timestamp**
The moment the IIOS detected and captured an observation. Always UTC. Must be ≥ observation_timestamp. Used in PIT queries to prevent look-ahead bias.

**Classification**
The process of assigning an observation to a type, domain, governance tier, and security classification. Performed by the Observation Classifier.

**Confidence Score**
A value in [0.0, 1.0] expressing the degree of certainty that an observation accurately represents the observed state. Computed by the Confidence Manager from source trust tier, cross-source agreement, and historical accuracy.

**Context Record (ContextRecord)**
A structured record capturing the state of the investment universe at the observation_timestamp — regime, trading session, market state, VIX level, expiry status, calendar context, and global context. Mandatory for every observation.

**Corroboration**
The process of comparing an observation with independently-sourced observations of the same entity, type, and approximate timestamp. Corroboration increases confidence and improves OQS accuracy dimension.

**Corroboration Count**
The number of independent sources that have produced a confirming observation for a given observation. A CRITICAL observation with corroboration_count ≥ 2 is considered corroborated.

**Cross-Source Agreement**
The proportion of independent sources that agree (within a tolerance) on the observed value. Used in the accuracy dimension of OQS computation.

**Deduplication**
The process of detecting that a newly arrived raw payload represents the same observed state as an already-stored observation, and routing it to the Corroboration Store rather than creating a new Registry entry.

**Domain**
A classification of observations by the type of entity and data they describe. The Observation Engine has 16 domains: Domain 01 (abstract root), Domains 02–16 (concrete). Each observation belongs to exactly one concrete domain.

**Evidence Engine**
The IIOS component downstream of the Observation Engine that assembles observations into structured evidence for the Knowledge Engine. The Observation Engine provides the perceptual layer; the Evidence Engine provides the reasoning layer.

**Freshness**
A time-varying property of an observation reflecting how current it is relative to its SLA at any moment of evaluation. Freshness degrades as time elapses since the observation_timestamp. One of the 14 OQS dimensions.

**Freshness SLA**
The maximum elapsed time (in seconds) after which an observation of a given type is considered STALE. Defined per observation type in the Observation Catalog.

**Freshness Tier**
A classification of an observation's freshness: FRESH → AGING → STALE → CRITICAL_STALE → EXPIRED. Computed dynamically by the Freshness Monitor.

**Governance Tier**
A classification of the operational and regulatory importance of an observation type: CRITICAL → HIGH → MEDIUM → LOW. Determines retention requirements, access control strictness, audit depth, and monitoring intensity.

**History Manager**
The component responsible for creating new versions of observations when corrections are required. Ensures immutability of the existing version and creates a linear version chain.

**Identity Manager**
The component responsible for assigning canonical observation_ids. Ensures global uniqueness. Never allows ID reuse.

**Immutability**
The architectural invariant that ACTIVE and SUPERSEDED observations cannot be modified in place. All corrections create new versions. See GDR-001.

**Interpreted Observation**
An anti-pattern (AP-01). An observation that contains analytical labels, signals, or conclusions rather than raw observed values. Prohibited by OC-D-008.

**Lineage**
The record of an observation's derivation — its source information object, transformation steps, aggregation constituents, and version history. Lineage is preserved permanently.

**Lineage Record**
A structured document associated with each observation_id, containing: source_ref, transformation_steps[], constituent_ids[], version_history[], and review_events[].

**Look-Ahead Bias**
An error in historical analysis caused by using information that was not yet available at the time being analysed. Prevented architecturally by the PIT query filter: `capture_timestamp ≤ query_time`.

**Market Domain**
Observation Domain 03. Covers all market price, volume, depth, volatility, and index observations.

**Observation**
A directly perceived, factual record of a measurable state of an entity or the market at a specific moment in time. Observations do not contain interpretation, prediction, conclusion, or recommendation.

**Observation Catalog**
The authoritative registry of all observation type definitions, including canonical codes, required fields, freshness SLAs, confidence floors, governance tiers, and schema definitions.

**Observation Confidence**
See Confidence Score.

**Observation Engine**
The perceptual layer of the IIOS. Responsible for detecting, capturing, validating, contextualising, classifying, scoring, storing, and distributing observations to downstream engines.

**Observation Quality Score (OQS)**
A single value in [0.0, 1.0] summarising the quality of an observation across 13 weighted dimensions. Computed by the Quality Scorer. Mandatory before distribution.

**Observation Record**
The complete structured document stored in the Observation Registry for each observation, comprising: identity fields, content fields, quality fields, context fields, governance fields, lifecycle fields, and lineage reference.

**Observation Registry**
The central store of all observations in the IIOS. The single source of truth for all observation state. Provides PIT query semantics across its full history.

**Observation Type**
A precise classification of an observation within its domain — e.g., MKT-PRC-OHLCV-1M, CORP-EARN-QUARTERLY. Each type has a canonical code and a schema definition in the Observation Catalog.

**Observation Validator**
The component that applies six levels of validation (L1–L6) to every incoming observation payload before it is admitted to the Registry.

**OQS**
See Observation Quality Score.

**PIT Query (Point-in-Time Query)**
A historical query that retrieves observations as they were known at a specific historical moment, using the filter `capture_timestamp ≤ query_timestamp`. Prevents look-ahead bias.

**Purity**
The architectural property of an observation containing only directly perceived factual content — no interpretation, labelling, prediction, signal, or recommendation. See OC-D-008 and GDR-002.

**Quality Tier**
A classification derived from OQS: EXCELLENT → GOOD → ACCEPTABLE → MARGINAL → POOR.

**Quarantine**
A lifecycle state for observations that fail quality, validation, or governance checks. Quarantined observations are not distributed to consumers.

**Regime**
The prevailing market regime at the observation_timestamp — e.g., BULL_QUIET, BEAR_VOLATILE, CHOPPY_NEUTRAL. Captured in the ContextRecord. Used for regime-aware historical analysis.

**Retention Period**
The minimum duration that an observation must be preserved before archival. Defined per domain in the governance policy.

**Source Registry**
The authoritative registry of all observation sources, including their trust tier, active status, reliability history, and acquisition configuration.

**Source Trust Tier**
A 5-level classification of source quality: AUTHORITATIVE → RELIABLE → STANDARD → PROVISIONAL → UNRELIABLE. Determines the trustworthiness quality dimension score and confidence penalisation.

**SUPERSEDED**
A lifecycle state for observations that have been replaced by a newer, corrected version. Superseded observations are preserved in the Registry but are excluded from default active queries.

**Survivorship Bias**
An analytical error caused by excluding observations of entities that have been delisted, merged, or dissolved from historical datasets. Prevented by the Observation Engine through preservation of all observations, including those for inactive entities.

**Version Chain**
The linear sequence of versions of an observation, from the original (version_number = 1) through all corrections. Each version except the latest is in SUPERSEDED state.

---
## OPERATIONAL RUNBOOK APPENDIX

### OR-01 — Startup Sequence

This section documents the required startup sequence for the Observation Engine. Components must be started in dependency order. Starting components out of order will result in observation pipeline failures.

**Pre-startup checklist:**

| Step | Action | Verification |
|---|---|---|
| 1 | Confirm Observation Registry database is accessible | Registry health check returns OK |
| 2 | Confirm Source Registry is populated with all active sources | Source count ≥ expected count |
| 3 | Confirm Observation Catalog version is current | Catalog version matches deployed version |
| 4 | Confirm Context Manager is available | Context Manager health check returns OK |
| 5 | Confirm Identity Manager sequence continuity | Last sequence number is consistent with Registry |
| 6 | Confirm Audit Logger write access | Test audit write succeeds |

**Startup order:**

```
Step 1:  Audit Logger                    — must be ready before any other component writes
Step 2:  Observation Catalog             — required by Identity Manager and Validator
Step 3:  Source Registry                 — required by Validator (L3) and Source Tracker
Step 4:  Entity Reference Manager        — required by Validator (L3) and Entity Linker
Step 5:  Identity Manager                — required by Observation Recorder
Step 6:  Observation Registry            — storage layer; required by Recorder and Retrieval
Step 7:  Deduplication Service           — must be ready before first observation arrives
Step 8:  Timestamp Service               — required by Capture Service
Step 9:  Context Manager                 — required by Context Enricher
Step 10: Observation Validator           — required by Capture Service
Step 11: Confidence Manager              — required by Quality Scorer
Step 12: Corroboration Service           — required by Quality Scorer
Step 13: Quality Scorer                  — required by Readiness Service
Step 14: Freshness Monitor               — required by Distribution Service
Step 15: Observation Recorder            — required by Capture Service (write path)
Step 16: History Manager                 — required for versioning operations
Step 17: Market Data Collector           — primary collection domain; start streaming
Step 18: Company Event Collector         — periodic polling; start scheduler
Step 19: Macro Data Collector            — periodic polling; start scheduler
Step 20: Alternative Data Collector      — periodic polling; start scheduler
Step 21: Observation Classifier          — must be ready before classification stage
Step 22: Entity Linker                   — must be ready before linking stage
Step 23: Source Tracker                  — starts recording source events
Step 24: Retrieval Service               — open for consumer queries
Step 25: Distribution Service            — open for observation delivery
Step 26: Quality Monitoring Service      — start quality dashboard
Step 27: Governance Manager              — activate governance checks
Step 28: Completeness Monitor            — activate absence alerts
```

**Post-startup verification:**

| Check | Expected result |
|---|---|
| Retrieval Service health | Returns HTTP 200 with status=HEALTHY |
| Quality Monitoring dashboard | All domain mean OQS > 0.75 |
| Market Data Collector status | All active symbols streaming |
| First observation PIT query | Returns results for today's timestamps |
| Audit trail integrity | Last audit record is consistent with startup |

---

### OR-02 — Graceful Shutdown Sequence

**Pre-shutdown checklist:**

| Step | Action |
|---|---|
| 1 | Set Distribution Service to DRAINING mode (no new distributions accepted) |
| 2 | Wait for in-flight distribution confirmations from CRITICAL consumers |
| 3 | Set Collectors to STOPPING mode (stop new acquisition) |
| 4 | Wait for in-flight observation captures to complete |
| 5 | Flush Deduplication Service bloom filter state to disk |

**Shutdown order (reverse of startup):**

```
Step 1:  Market Data Collector            — stop streaming; flush pending payloads
Step 2:  Company/Macro/Alternative Collectors — stop polling; flush pending payloads
Step 3:  Distribution Service             — drain queue; confirm all critical deliveries
Step 4:  Quality Monitoring Service       — flush metrics; write final quality report
Step 5:  Completeness Monitor             — write absence alert summary
Step 6:  Governance Manager               — write governance event log
Step 7:  Source Tracker                   — flush source event buffer
Step 8:  Freshness Monitor                — write freshness summary
Step 9:  Corroboration Service            — flush pending corroboration queue
Step 10: Retrieval Service                — stop accepting new queries; drain in-flight
Step 11: Observation Recorder             — flush write buffer; confirm all writes committed
Step 12: Observation Validator            — drain validation queue
Step 13: Identity Manager                 — write sequence state to disk
Step 14: Deduplication Service            — write bloom filter state to disk
Step 15: Context Manager                  — flush context cache
Step 16: Audit Logger                     — write SHUTDOWN event; flush audit buffer
Step 17: Observation Registry             — checkpoint; verify storage consistency
```

---

### OR-03 — Recovery Procedures

**Scenario: Observation Registry storage failure**

| Step | Action |
|---|---|
| 1 | Immediately halt all Observation Recorder writes |
| 2 | Buffer incoming observations in the capture queue (max capacity: 10 minutes of typical volume) |
| 3 | Diagnose storage failure: disk full / connection failure / process failure |
| 4 | Recover storage (restore from backup, repair disk, restart database process) |
| 5 | Verify Registry integrity: run hash checks on most recent observations |
| 6 | Resume Observation Recorder; drain capture queue |
| 7 | Alert consumers of the outage window; they should re-query for observations they missed |
| 8 | Write outage event to audit trail |

---

**Scenario: Context Manager unavailable**

| Step | Action |
|---|---|
| 1 | Context Enricher switches to DEGRADED_CONTEXT mode |
| 2 | Observations captured with CONTEXT_PARTIAL flag and a minimal stub ContextRecord |
| 3 | Alert ops team of Context Manager failure |
| 4 | When Context Manager recovers, run Context Backfill job: for all observations with CONTEXT_PARTIAL in the outage window, compute and apply full ContextRecords |
| 5 | Trigger OQS recomputation for affected observations (context richness dimension improves) |
| 6 | Re-distribute updated observations to subscribed consumers |

---

**Scenario: Primary data feed failure (Market Data Collector)**

| Step | Action |
|---|---|
| 1 | Market Data Collector detects feed disconnection (within 5 seconds) |
| 2 | Switches to secondary feed automatically |
| 3 | All market observations produced during failover carry a SECONDARY_FEED flag |
| 4 | Secondary feed observations have trust tier RELIABLE (not AUTHORITATIVE) |
| 5 | Freshness Monitor maintains STALE alerts if secondary feed latency exceeds SLA |
| 6 | When primary feed reconnects, validate that gap observations were captured via secondary |
| 7 | Reconcile any gaps through manual backfill or acceptance of gap with MISSING_DATA flag |

---

**Scenario: Identity Manager sequence gap**

| Step | Action |
|---|---|
| 1 | On startup, Identity Manager detects a gap in the sequence (last ID in Registry > last ID in sequence state file) |
| 2 | Immediately halt observation capture |
| 3 | Reconstruct the last assigned sequence number from the Registry (query max sequence per domain/type/date) |
| 4 | Resume sequence from the reconstructed maximum + 1 |
| 5 | Log the sequence recovery event in the audit trail |
| 6 | Alert ops team; investigation of root cause is required |

---

**Scenario: Quality scoring service failure**

| Step | Action |
|---|---|
| 1 | Observation pipeline switches to QUALITY_DEGRADED mode |
| 2 | Observations are captured and stored with quality_tier = UNKNOWN and observation_quality_score = null |
| 3 | Observations with UNKNOWN quality tier are not distributed to consumers requiring quality floors |
| 4 | When Quality Scorer recovers, run Quality Backfill job: compute OQS for all UNKNOWN-tier observations in the failure window |
| 5 | Update distribution queue to release held observations that now meet consumer quality floors |

---

### OR-04 — Performance Targets

| Metric | Target | Measurement point |
|---|---|---|
| Observation capture latency (p50) | < 10 ms | Timestamp Service to Observation Recorder commit |
| Observation capture latency (p99) | < 100 ms | Timestamp Service to Observation Recorder commit |
| OQS computation latency (p99) | < 20 ms | Quality Scorer |
| PIT query latency (p99) | < 50 ms | Retrieval Service |
| Distribution latency, CRITICAL (p99) | < 5 ms | Distribution Service |
| Full validation pipeline latency (p99) | < 200 ms | Capture Service to Registry store |
| Context enrichment latency (p99) | < 20 ms | Context Manager |
| Corroboration check latency (p99) | < 30 ms | Corroboration Service |
| Audit write latency (p99) | < 5 ms | Audit Logger |
| Identity assignment latency (p99) | < 5 ms | Identity Manager |

---

### OR-05 — Capacity Reference

| Metric | Value |
|---|---|
| Market tick observations per trading day | ~2,000,000 (500 symbols × 4,000 ticks/day avg) |
| OHLCV bar observations per trading day | ~75,000 (500 symbols × 150 intervals/day) |
| Company/macro/alternative observations per day | ~10,000 |
| Total daily observation volume | ~2,100,000 |
| Registry storage per observation (avg) | ~2 KB |
| Daily Registry growth (uncompressed) | ~4.2 GB |
| Daily Registry growth (compressed, 3:1 ratio) | ~1.4 GB |
| Deduplication bloom filter size | 100 MB (supports 500M observations with 0.1% FPR) |
| Audit trail daily growth | ~500 MB |
| Lineage record daily growth | ~200 MB |
| Total daily storage (all components) | ~2.1 GB compressed |
| Annual storage budget (compressed) | ~766 GB |

---
---

## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | OBSERVATION ENGINE ARCHITECTURE |
| Document code | IIOS-OE-ARCH-001 |
| Version | 1.0 |
| Status | RATIFIED |
| Part I — Observation Philosophy | 20 conceptual distinctions + 10 design principles |
| Part II — Observation Domains | 16 domains (1 abstract, 15 concrete) |
| Part III — Components | 22 components across 6 clusters |
| Part IV — Observation Lifecycle | 12 stages; 5 lifecycle states |
| Part V — Observation Services | 17 services (OS-01 through OS-17) |
| Part VI — Processing Patterns | 15 processing patterns |
| Part VII — Quality Framework | 14 OQS dimensions; 5 quality tiers |
| Part VIII — Governance | 11 governance dimensions |
| Part IX — Observation Constitution | 70 constitutional rules across 6 categories |
| Part X — Readiness Checklist | 14 sections; 7 use cases |
| Supplement A — Type Catalogue | 35+ observation type definitions across 7 domains |
| Supplement B — Component Interfaces | 22 component interface specifications |
| Supplement C — Pipeline Patterns | 4 detailed pipeline patterns with flow diagrams |
| Supplement D — Quality Reference | Weight table; 15 calibration scenarios; monitoring metrics |
| Supplement E — Governance Decisions | 6 governance decision records (GDR-001 through GDR-006) |
| Supplement F — Anti-Patterns | 10 anti-patterns (AP-01 through AP-10) |
| Supplement G — Glossary | 40+ alphabetically ordered terms |
| Operational Runbook | 5 sections; startup/shutdown; 5 recovery procedures |
| Constitutional rules — OC-A (Identity) | 10 rules |
| Constitutional rules — OC-B (Immutability) | 10 rules |
| Constitutional rules — OC-C (Temporality) | 12 rules |
| Constitutional rules — OC-D (Integrity) | 15 rules |
| Constitutional rules — OC-E (Governance) | 15 rules |
| Constitutional rules — OC-F (Intelligence) | 15 rules (total: 77 rules, 70 numbered + 7 sub-clauses) |
| Readiness checklist criteria | 98 individual criteria across 14 sections |

---

### Master Compliance Checklist

| Section | Included | Verified |
|---|---|---|
| Part I — Observation Philosophy | ✅ | ✅ |
| Part II — Observation Domains | ✅ | ✅ |
| Part III — Components | ✅ | ✅ |
| Part IV — Lifecycle | ✅ | ✅ |
| Part V — Services | ✅ | ✅ |
| Part VI — Processing Patterns | ✅ | ✅ |
| Part VII — Quality Framework | ✅ | ✅ |
| Part VIII — Governance | ✅ | ✅ |
| Part IX — Observation Constitution | ✅ | ✅ |
| Part X — Readiness Checklist | ✅ | ✅ |
| Supplement A — Type Catalogue | ✅ | ✅ |
| Supplement B — Component Interfaces | ✅ | ✅ |
| Supplement C — Pipeline Patterns | ✅ | ✅ |
| Supplement D — Quality Reference | ✅ | ✅ |
| Supplement E — Governance Decisions | ✅ | ✅ |
| Supplement F — Anti-Patterns | ✅ | ✅ |
| Supplement G — Glossary | ✅ | ✅ |
| Operational Runbook | ✅ | ✅ |

---

### Governing Documents

| Document | Code | Relationship |
|---|---|---|
| IIOS Architecture Overview | IIOS-ARCH-000 | Parent: this document is a subordinate architecture |
| INFORMATION_ENGINE_ARCHITECTURE.md | IIOS-IE-ARCH-001 | Upstream: provides information objects that become observation sources |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | IIOS-KE-ARCH-001 | Downstream: consumes observations via Evidence Engine |
| ENTITY_ENGINE_ARCHITECTURE.md | IIOS-EE-ARCH-001 | Referenced: provides canonical entity identifiers |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | IIOS-RE-ARCH-001 | Referenced: provides relationship context |
| EVENT_ENGINE_ARCHITECTURE.md | IIOS-EVE-ARCH-001 | Referenced: observations feed event detection |
| DATABASE_PERSISTENCE_ARCHITECTURE.md | IIOS-DB-ARCH-001 | Underlying: persistence layer for the Observation Registry |

---

### Architectural Impact Statement

The Observation Engine is the sole perceptual layer of the IIOS. It defines the boundary between the external world and the analytical intelligence of the system. Every observation that any downstream engine — the Evidence Engine, the Knowledge Engine, the Risk Engine, the Execution Engine — uses as a basis for reasoning, decision-making, or action was first captured, validated, contextualised, and quality-scored by the Observation Engine.

The architectural invariants established in this document — immutability, purity, mandatory context, dual-timestamp PIT semantics, mandatory OQS — are not implementation preferences. They are existential properties of the IIOS. A system that violates any of these invariants is not an implementation of this architecture: it is a different, less analytically rigorous system.

The observation that enters the Registry at 09:15:23 and powers a position decision at 09:15:28 will be the same observation that appears in a regulatory audit five years later, that proves or disproves the validity of a strategy in backtesting, and that anchors the causal explanation of a historical outcome. The engineering discipline this document encodes exists to make those five-year-later guarantees holdable on the basis of five-second-earlier engineering decisions.

---

### Version History

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1 | Architecture inception | IIOS Architecture Board | Initial draft: domains, components, lifecycle |
| 0.5 | First review cycle | IIOS Architecture Board | Added quality framework, constitution |
| 0.9 | Pre-ratification review | All domain owners | Added supplements, anti-patterns, glossary |
| 1.0 | Ratification | IIOS Architecture Board | Ratified; all 10 parts and supplements complete |

---

*This document is RATIFIED. No component of the IIOS Observation Engine may be designed, implemented, or operated in a manner inconsistent with the architecture defined herein. Proposed changes must be submitted as Architecture Change Requests to the IIOS Architecture Board.*

*End of OBSERVATION_ENGINE_ARCHITECTURE.md*

---