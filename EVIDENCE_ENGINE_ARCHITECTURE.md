# EVIDENCE ENGINE ARCHITECTURE

**Document Code:** IIOS-EVE-ENG-ARCH-001  
**Version:** 1.0  
**Status:** RATIFIED  
**Classification:** INTERNAL — IIOS Core Architecture  
**Date:** 2026-07-03  
**Author:** IIOS Architecture Board

---

## DOCUMENT PURPOSE

This document is the authoritative engineering architecture specification for the Evidence Engine of the Investment Intelligence Operating System (IIOS). It defines the complete design of the second cognitive layer — the component responsible for transforming observations into structured, weighted, confidence-scored, and traceable evidence that supports hypothesis formation and reasoning.

The Evidence Engine never predicts. It never decides. It never executes. It evaluates — determining whether observations constitute valid, reliable evidence, how strongly each piece of evidence speaks, how consistent the body of evidence is, and how that evidence has evolved over time.

---

## POSITION IN THE IIOS COGNITIVE STACK

```
┌─────────────────────────────────────────────────────────────────┐
│                    IIOS COGNITIVE STACK                         │
│                                                                 │
│  Layer 7 │  INTELLIGENCE ENGINE    │  Acts                      │
│  Layer 6 │  DECISION ENGINE        │  Decides                   │
│  Layer 5 │  REASONING ENGINE       │  Reasons                   │
│  Layer 4 │  HYPOTHESIS ENGINE      │  Hypothesises              │
│  Layer 3 │  KNOWLEDGE ENGINE       │  Knows                     │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Layer 2 │  EVIDENCE ENGINE        │  Evaluates    ◄ THIS DOC   │
│  Layer 1 │  OBSERVATION ENGINE     │  Perceives                 │
│  Layer 0 │  INFORMATION ENGINE     │  Acquires                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## INFORMATION FLOW

```
INFORMATION ENGINE
       │
       │  Information Objects (structured, quality-scored)
       ▼
OBSERVATION ENGINE
       │
       │  Observations (timestamped, contextualised, OQS-scored,
       │                immutable, PIT-queryable)
       ▼
┌─────────────────────────────────────────────────────────┐
│               EVIDENCE ENGINE  (this document)          │
│                                                         │
│  Intake → Qualify → Weight → Score → Correlate →       │
│  Fuse → Conflict-Check → Store → Distribute            │
│                                                         │
│  Output: Evidence Records                               │
│   - evidence_id                                         │
│   - supporting_observations[]                           │
│   - evidence_type                                       │
│   - weight                                              │
│   - confidence_score                                    │
│   - reliability_score                                   │
│   - independence_score                                  │
│   - EQS (Evidence Quality Score)                        │
│   - conflict_status                                     │
│   - context_id                                          │
│   - lineage_id                                          │
└─────────────────────────────────────────────────────────┘
       │
       │  Evidence Records (weighted, confidence-scored,
       │                    conflict-checked, governed)
       ▼
KNOWLEDGE ENGINE / HYPOTHESIS ENGINE
```

---

## AUTHORITATIVE PARENT DOCUMENTS

| Document | Code | Role |
|---|---|---|
| INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md | IIOS-SYS-000 | System root |
| MASTER_KNOWLEDGE_ARCHITECTURE.md | IIOS-MKA-001 | Knowledge layer spec |
| ENGINEERING_STANDARDS.md | IIOS-ENG-STD-001 | Engineering standards |
| CORE_FRAMEWORK_ARCHITECTURE.md | IIOS-CFA-001 | Core framework |
| DATABASE_PERSISTENCE_ARCHITECTURE.md | IIOS-DB-ARCH-001 | Persistence layer |
| AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md | IIOS-BP-001 | System blueprint |
| INFORMATION_ONTOLOGY.md | IIOS-ONT-INFO-001 | Information ontology |
| ENTITY_ONTOLOGY.md | IIOS-ONT-ENT-001 | Entity ontology |
| RELATIONSHIP_ONTOLOGY.md | IIOS-ONT-REL-001 | Relationship ontology |
| EVENT_ONTOLOGY.md | IIOS-ONT-EVT-001 | Event ontology |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | IIOS-KE-ARCH-001 | Knowledge engine spec |
| ENTITY_ENGINE_ARCHITECTURE.md | IIOS-EE-ARCH-001 | Entity engine spec |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | IIOS-RE-ARCH-001 | Relationship engine spec |
| EVENT_ENGINE_ARCHITECTURE.md | IIOS-EVE-ARCH-001 | Event engine spec |
| INFORMATION_ENGINE_ARCHITECTURE.md | IIOS-IE-ARCH-001 | Information engine spec |
| OBSERVATION_ENGINE_ARCHITECTURE.md | IIOS-OE-ARCH-001 | Observation engine spec (direct input) |

---

## TABLE OF CONTENTS

```
PART I     — Evidence Philosophy
PART II    — Evidence Model
PART III   — Core Components
PART IV    — Evidence Lifecycle
PART V     — Evidence Services
PART VI    — Evidence Processing Pipelines
PART VII   — Evidence Quality Framework
PART VIII  — Evidence Governance
PART IX    — Evidence Constitution
PART X     — Evidence Readiness Checklist

SUPPLEMENT A  — Evidence Taxonomy
SUPPLEMENT B  — Evidence Weighting Reference
SUPPLEMENT C  — Evidence Confidence Reference
SUPPLEMENT D  — Evidence Conflict Matrix
SUPPLEMENT E  — Evidence Lineage Examples
SUPPLEMENT F  — Evidence Anti-Pattern Reference
SUPPLEMENT G  — Operational Runbook
SUPPLEMENT H  — Evidence Engine Glossary

DOCUMENT FOOTER
```

---
## PART I — EVIDENCE PHILOSOPHY

### 1.1 What Is Evidence?

Evidence is the evaluated, weighted, and confidence-scored transformation of one or more observations into a structured assertion that a particular state, condition, or pattern is present in the investment universe. Evidence answers a more sophisticated question than observation: not merely "what did we perceive?" but "does what we perceived constitute a meaningful, reliable, and contextually appropriate signal in the direction of some potential truth?"

Evidence is the bridge between perception and reasoning. It does not contain conclusions, predictions, or decisions — those belong to higher cognitive layers. But it transforms raw perceptions into evaluated facts that are capable of contributing to a body of reasoning.

In the IIOS architecture, evidence is always:
- Derived from one or more validated observations
- Evaluated for weight, confidence, and reliability
- Contextualised at the moment of evaluation
- Checked for conflict with other evidence
- Assessed for independence from correlated sources
- Preserved with full lineage to its source observations
- Never interpreted beyond what the observations directly support

---

### 1.2 Why Evidence Exists

Intelligence — the capacity to form well-grounded views and make sound decisions — requires more than raw data. A price tick, taken alone, is not evidence of anything beyond the fact that a transaction occurred at a specific price. Ten thousand price ticks arranged in a pattern, evaluated against historical norms, contextualised within the current regime, weighted by source reliability, and compared with competing observations begin to constitute evidence of a trend, a regime shift, a breakout, or a reversal.

The Evidence Engine exists because:
1. Observations are atomic — they describe one thing at one moment. Reasoning requires evaluated, fused, and weighted inputs.
2. Not all observations deserve equal weight. A corporate action reported by an authoritative regulatory source deserves more weight than the same event reported by a secondary news source.
3. Observations can conflict. Two sources may report different values for the same market state. Conflict must be detected and adjudicated before observations are presented as evidence to reasoning systems.
4. Evidence must be traceable. If a trading decision is later questioned, the evidence it was based on must be auditable from the decision back through hypothesis → evidence → observations → information → source.
5. Evidence ages differently from observations. An observation is a fact about a moment in time. Its freshness decays, but the fact itself is unchanging. Evidence is an evaluation of that observation's current relevance, which can evolve as new observations arrive, as the market regime changes, and as corroborating or contradicting evidence accumulates.

---

### 1.3 The Conceptual Hierarchy

Understanding the Evidence Engine requires precise clarity about the conceptual hierarchy above and below it.

---

#### 1.3.1 Raw Data

The unprocessed byte streams, feed messages, API payloads, document fragments, and sensor readings that arrive from external sources. Raw data has no semantics — it is a physical signal, nothing more. Raw data is transformed into information by the Information Engine.

---

#### 1.3.2 Information

Parsed, structured, quality-scored representations of raw data. Information answers "what was the raw signal?" in a form the system can process. Information is the output of the Information Engine and the input to the Observation Engine. Information is not yet situated in the investment universe — it has no entity reference, no context, no evaluation.

---

#### 1.3.3 Observation

A directly perceived, factual record of a measurable state of an entity or the market at a specific moment in time. Observations are produced by the Observation Engine from information. An observation captures "what the IIOS perceived" — a price level, a volume print, an earnings figure, a VIX reading — anchored in time, entity-referenced, contextualised, and quality-scored. Observations are strictly non-interpretive: they record what was detected, not what it means.

---

#### 1.3.4 Measurement

A quantitative observation with a well-defined unit, precision, and instrument. Every measurement is an observation, but not every observation is a measurement. A news headline is an observation but not a measurement. NIFTY50 at 22,345.60 is a measurement (unit: INR, precision: 2 decimal places, instrument: NSE real-time feed).

---

#### 1.3.5 Fact

A validated observation that has been confirmed across independent sources, whose accuracy confidence is sufficiently high that it can be treated as true for analytical purposes. Facts are a special subset of observations with high corroboration and low uncertainty. The Evidence Engine does not produce facts — it assesses whether observations approach the confidence threshold of a fact.

---

#### 1.3.6 Evidence

An evaluated, weighted, and confidence-scored transformation of one or more observations into an analytical input that speaks to the presence, absence, or degree of a condition. Evidence is the output of the Evidence Engine. Evidence does not conclude — it supports, contradicts, or remains neutral toward a potential hypothesis.

---

#### 1.3.7 Signal

A pattern in observations or evidence that, by convention or prior validation, is associated with a particular market condition or entity state. Signals are produced by Signal Engines (pattern recognition systems operating on evidence). Signals are not produced by the Evidence Engine — evidence is the input to signal generation, not a signal itself.

---

#### 1.3.8 Indicator

A derived quantitative measure — typically computed from a sequence of observations — whose value is interpreted as an indicator of a market condition. Moving averages, RSI, Bollinger Bands, VIX percentile rank are indicators. Indicators are computed from observations; they are not themselves evidence. However, the observation of an indicator value (e.g., the 14-day RSI reading) becomes an observation that the Evidence Engine can then evaluate as evidence.

---

#### 1.3.9 Knowledge

Validated, organised, interconnected conclusions about the investment universe. Knowledge is produced by the Knowledge Engine from evidence and hypotheses. Knowledge is what the IIOS "knows" to be true at a given confidence level. Evidence is a lower-level construct — it is what the IIOS "sees" that supports or contradicts knowledge.

---

#### 1.3.10 Reasoning

The process of drawing inferences from evidence toward conclusions. Reasoning is the domain of the Reasoning Engine and Hypothesis Engine — not the Evidence Engine. The Evidence Engine provides the evaluated inputs on which reasoning operates. It does not itself reason.

---

#### 1.3.11 Hypothesis

A structured, testable, probabilistic assertion about the investment universe that the IIOS holds tentatively until confirmed or refuted by evidence. Hypotheses are the output of the Hypothesis Engine. The Evidence Engine does not form hypotheses — it provides the evidence that the Hypothesis Engine uses to form and score them.

---

#### 1.3.12 Prediction

A probabilistic assertion about a future state of the investment universe. Predictions are produced by the Intelligence Engine, not the Evidence Engine. Evidence speaks to what is currently observed and what has been historically observed. It does not speak to what will be observed.

---

#### 1.3.13 Decision

A commitment to a course of action — to trade, to hedge, to hold, to exit. Decisions are produced by the Decision Engine. Evidence contributes to decisions through the chain: Evidence → Knowledge → Hypothesis → Reasoning → Decision.

---

#### 1.3.14 Conviction

The degree of confidence with which the IIOS holds a decision. Conviction emerges from the combined weight of the evidence supporting a hypothesis, the consistency of the reasoning chain, and the historical track record of similar evidence bodies. Conviction is computed at the Decision Engine level.

---

#### 1.3.15 Probability

A quantitative expression of uncertainty. The Evidence Engine assigns confidence scores to evidence — these are probabilistic assessments of the reliability of each evidence item. The aggregation of evidence confidence scores into a hypothesis probability is the domain of the Hypothesis Engine.

---

#### 1.3.16 Correlation

The statistical relationship between two or more evidence items. Correlated evidence must not be treated as independent — the Independence Engine detects evidence correlation and adjusts effective weights accordingly. Treating correlated evidence as independent inflates apparent certainty.

---

#### 1.3.17 Causation

A directional, mechanistic relationship between a cause and an effect. The Evidence Engine detects correlation but does not assert causation. Causal claims belong to the Reasoning Engine, which uses evidence of temporal precedence, mechanism, and dose-response to argue for causal relationships.

---

### 1.4 Types of Evidence

#### 1.4.1 Supporting Evidence

Evidence that increases the probability that a particular hypothesis, condition, or assertion is true. Supporting evidence confirms, reinforces, or corroborates a claim. The Evidence Engine computes a support vector for each piece of evidence relative to all active hypotheses.

#### 1.4.2 Contradicting Evidence

Evidence that decreases the probability that a particular hypothesis, condition, or assertion is true. Contradicting evidence challenges, weakens, or refutes a claim. The Evidence Engine detects and flags contradicting evidence through the Conflict Manager.

#### 1.4.3 Neutral Evidence

Evidence that neither increases nor decreases the probability of a hypothesis. Neutral evidence is relevant to the domain but does not speak to the specific hypothesis being evaluated. The Evidence Engine retains neutral evidence in the store — it may become relevant as hypotheses evolve.

#### 1.4.4 Independent Evidence

Evidence derived from sources that have no statistical or structural relationship to each other. Independent evidence has higher combined weight than correlated evidence of the same strength. Independence is assessed by the Independence Engine using source correlation analysis.

#### 1.4.5 Correlated Evidence

Evidence derived from sources that share a common upstream dependency, methodology, or data pipeline. Correlated evidence must be identified and its effective independence weight reduced. Failing to detect correlated evidence leads to overconfidence.

#### 1.4.6 Primary Evidence

Evidence derived directly from authoritative, first-party observations (exchange feeds, regulatory filings, official government statistics). Primary evidence carries the highest baseline weight and confidence.

#### 1.4.7 Secondary Evidence

Evidence derived from secondary sources (news reports, analyst commentary, aggregated data services). Secondary evidence carries a reduced baseline weight and must be corroborated by primary evidence before achieving high confidence.

#### 1.4.8 Derived Evidence

Evidence computed from one or more other pieces of evidence through a defined derivation function (e.g., trend evidence derived from a sequence of price observations; regime evidence derived from a combination of volatility, breadth, and momentum evidence). Derived evidence carries a derivation lineage.

#### 1.4.9 Composite Evidence

Evidence that fuses multiple independent evidence items into a single higher-order evidence record. Composite evidence is produced by the Evidence Aggregator and carries a fusion score indicating the coherence of its constituents.

---

### 1.5 Why Evidence Is Probabilistic

Evidence in financial markets is never absolute. The following properties of investment markets make absolute evidence impossible:

**Market incompleteness:** No set of observations, however comprehensive, can fully describe the state of a complex adaptive market at any moment.

**Measurement uncertainty:** Even the most reliable market data sources have measurement error, latency, and precision limitations.

**Source heterogeneity:** Different sources observe the same underlying truth through different instruments, with different methodologies, biases, and error profiles.

**Regime dependence:** The same observation may constitute strong evidence in one market regime and weak or irrelevant evidence in another.

**Temporal decay:** Evidence freshness decays with time. An earnings observation from three months ago is weaker evidence of current company health than a today's earnings release.

**Survivorship effects:** The evidence set available for analysis is systematically biased toward surviving entities and complete histories. Missing evidence must be accounted for.

Because evidence is probabilistic, the Evidence Engine never makes binary assertions ("this is true" or "this is false"). It assigns confidence scores, weights, and reliability measures that allow higher cognitive layers to make nuanced, calibrated probabilistic assessments.

---

### 1.6 Evidence as Foundation for Intelligence

The Evidence Engine occupies a uniquely important architectural position. It is the last cognitive layer that operates purely on perception — on what the IIOS has observed. Every higher layer — knowledge, hypotheses, reasoning, decisions — must ultimately trace its lineage back through evidence to observation. If the evidence is weak, biased, or poorly evaluated, every layer above it will be contaminated.

Ten architectural properties follow from this foundational role:

1. **Completeness:** Every observation relevant to an active hypothesis must be evaluated. Missing evidence is itself evidence.
2. **Traceability:** Every evidence record must be traceable through observation to information to raw source.
3. **Calibration:** Confidence scores must be calibrated — a 0.80 confidence should be correct 80% of the time historically.
4. **Independence awareness:** The Evidence Engine must explicitly model source correlations and reduce effective weight for correlated evidence.
5. **Conflict transparency:** Conflicting evidence must not be silently resolved. Conflicts must be preserved, flagged, and made visible to reasoning systems.
6. **Freshness management:** Evidence has a temporal dimension. Stale evidence must be marked and weighted accordingly.
7. **Context sensitivity:** Evidence strength is context-dependent. The same observation may be stronger evidence in a volatile regime than a quiet one.
8. **Immutability:** Evidence records are immutable once committed. Revisions create new versions with full version chains.
9. **Auditability:** Every evaluation step — qualification, weighting, confidence scoring — must be recorded in the audit trail.
10. **Purity:** Evidence records must not contain predictions, conclusions, signals, recommendations, or decisional content. They record evaluation results only.

---
## PART II — EVIDENCE MODEL

### 2.1 Evidence Model Architecture

The Evidence Model defines the complete taxonomy of evidence categories in the IIOS. Like the Observation Model, it is organised as a hierarchy with an abstract Evidence Root and 22 concrete evidence categories. Every concrete evidence category maps to one or more observation domains in the Observation Engine.

Evidence records carry a canonical evidence_id in the format:
`EVD-{CATEGORY_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`

---

### 2.2 Evidence Root (Abstract)

**Code:** EVD-ROOT  
**Type:** Abstract base  
**Description:** The conceptual parent of all evidence categories. Evidence Root defines the mandatory fields that every evidence record must carry, regardless of category:

| Mandatory field | Description |
|---|---|
| evidence_id | Canonical identifier |
| evidence_type | Category code from Evidence Catalog |
| domain | One of 22 evidence domains |
| hypothesis_relevance[] | Hypotheses this evidence speaks to |
| supporting_observations[] | observation_ids that constitute this evidence |
| weight | Assigned weight in [0.0, 1.0] |
| confidence_score | ECS — Evidence Confidence Score |
| reliability_score | ERS — Evidence Reliability Score |
| independence_score | Independence from correlated evidence |
| eqs | Evidence Quality Score (composite) |
| evidence_timestamp | UTC — when this evidence was evaluated |
| context_id | ContextRecord at evaluation time |
| conflict_status | NONE / WARNING / CONFLICT |
| conflict_refs[] | evidence_ids of conflicting evidence |
| lineage_id | Full lineage to observations and sources |
| status | ACTIVE / SUPERSEDED / ARCHIVED / RETIRED |
| version_number | ≥ 1 |
| governance_tier | CRITICAL / HIGH / MEDIUM / LOW |

---

### 2.3 Market Evidence

**Code:** EVD-MKT  
**Sources:** Market observation domain (price, volume, depth, volatility, open interest, index)

Market evidence is the most time-sensitive category. It is derived from continuously streaming market observations and must be evaluated, weighted, and distributed within the latency constraints of real-time operations. Market evidence includes:

- **Price Level Evidence:** Evidence derived from absolute price observations — where is price relative to historical ranges, support/resistance levels, or index composition.
- **Price Movement Evidence:** Evidence derived from sequences of price observations — trend direction, momentum, acceleration, reversal patterns.
- **Volume Evidence:** Evidence derived from traded volume observations — volume relative to average, volume at price, volume-price divergence.
- **Order Book Evidence:** Evidence derived from Level-2 depth observations — imbalance, queue exhaustion, large order detection.
- **Volatility Evidence:** Evidence derived from realised and implied volatility observations — volatility regime, volatility surface shape, volatility term structure.
- **Open Interest Evidence:** Evidence derived from options and futures OI observations — directional positioning, gamma exposure concentration.
- **Index Evidence:** Evidence derived from index observations — market breadth, sector contribution, index rebalancing signals.

---

### 2.4 Company Evidence

**Code:** EVD-CORP  
**Sources:** Company observation domain (earnings, corporate actions, ratings, ownership, filings)

Company evidence is episodic rather than continuous — it arrives on the cadence of corporate reporting cycles, regulatory filings, and event-driven announcements. Company evidence includes:

- **Earnings Evidence:** Evidence derived from quarterly and annual earnings observations — EPS surprise, revenue growth, margin trends.
- **Corporate Action Evidence:** Evidence derived from dividend, split, bonus, and buyback observations — capital allocation signals.
- **Credit Evidence:** Evidence derived from credit rating observations — solvency risk, credit trajectory.
- **Ownership Evidence:** Evidence derived from promoter, FII, and DII ownership observations — smart money positioning, ownership momentum.
- **Filing Evidence:** Evidence derived from regulatory filing observations — auditor changes, related-party transactions, pledging.

---

### 2.5 Financial Evidence

**Code:** EVD-FIN  
**Sources:** Financial statement observations, accounting metrics, ratio computations

Financial evidence derives from the quantitative outputs of financial analysis applied to company observations. It is the domain of fundamental investment analysis:

- **Valuation Evidence:** P/E, P/B, EV/EBITDA, DCF-implied value relative to current price observations.
- **Quality Evidence:** Return on equity, return on assets, asset turnover, operating leverage.
- **Growth Evidence:** Revenue growth trajectory, earnings growth, free cash flow growth.
- **Leverage Evidence:** Debt-to-equity, interest coverage, debt maturity profile.
- **Liquidity Evidence:** Current ratio, quick ratio, cash conversion cycle.

---

### 2.6 Technical Evidence

**Code:** EVD-TECH  
**Sources:** Technical indicator observations computed from market price and volume history

Technical evidence is derived from indicator observations — computed values such as moving averages, oscillators, and pattern recognition outputs applied to price and volume histories:

- **Trend Evidence:** Moving average crossovers, directional movement, trend consistency.
- **Momentum Evidence:** RSI, MACD, rate-of-change observations as evidence of trend strength.
- **Mean Reversion Evidence:** Price deviation from moving averages, Bollinger Band position.
- **Pattern Evidence:** Classical chart pattern observations (head and shoulders, triangle, flag).
- **Volume-Price Evidence:** VWAP deviation, accumulation/distribution.

---

### 2.7 Fundamental Evidence

**Code:** EVD-FUND  
**Sources:** Macroeconomic observations, sector observations, company financial observations

Fundamental evidence is the evidence domain that speaks to intrinsic value, economic conditions, and sector dynamics. It bridges company-level financial evidence and macroeconomic evidence:

- **Intrinsic Value Evidence:** Observations supporting or contradicting a view that an entity is trading at a discount or premium to intrinsic value.
- **Competitive Position Evidence:** Market share, pricing power, moat-related observations.
- **Industry Cycle Evidence:** Where in the industry cycle a sector is, based on capacity utilisation, pricing, and volume observations.

---

### 2.8 Macro Evidence

**Code:** EVD-MACRO  
**Sources:** Macroeconomic observation domain (monetary policy, inflation, GDP, FX, rates)

Macro evidence covers the broad economic environment that determines the available alpha in all other evidence categories:

- **Monetary Policy Evidence:** RBI rate decisions, liquidity conditions, credit growth as evidence for the rate cycle phase.
- **Inflation Evidence:** CPI, WPI trends as evidence for the inflationary environment.
- **Growth Evidence:** GDP growth, PMI, industrial production as evidence for the economic growth trajectory.
- **Currency Evidence:** INR/USD, DXY movements as evidence for FX risk and global capital flows.
- **Global Evidence:** Federal Reserve policy, ECB policy, global PMI as evidence for international headwinds/tailwinds.

---

### 2.9 Sector Evidence

**Code:** EVD-SECT  
**Sources:** Sector observation domain, sector rotation observations

Sector evidence captures relative performance, rotation, and structural trends across NSE/BSE sector indices:

- **Sector Rotation Evidence:** Relative strength of sectors, money flow between sectors.
- **Sector Breadth Evidence:** Advance/decline within a sector, sector participation in market moves.
- **Sector Catalyst Evidence:** Sector-specific regulatory, policy, or commodity price observations.

---

### 2.10 Relationship Evidence

**Code:** EVD-REL  
**Sources:** Relationship observation domain, relationship engine outputs

Relationship evidence captures observations about how entities relate to each other — correlations, common ownership, supply chain dependencies, peer pricing:

- **Correlation Evidence:** Statistical co-movement between entity price observations.
- **Peer Evidence:** Relative valuation and performance within a peer group.
- **Supply Chain Evidence:** Input/output price and volume relationships.
- **Common Factor Evidence:** Shared sensitivity to macro or sector factors.

---

### 2.11 Event Evidence

**Code:** EVD-EVT  
**Sources:** Event observation domain, event engine outputs

Event evidence captures the evidential content of discrete events — earnings releases, policy decisions, corporate announcements, index rebalances:

- **Pre-Event Evidence:** Observations in the run-up to a scheduled event as evidence for directional positioning.
- **Event Confirmation Evidence:** The event observation itself as confirmation of expected or unexpected outcomes.
- **Post-Event Evidence:** Observations after an event as evidence for market reaction and follow-through.

---

### 2.12 Behavioral Evidence

**Code:** EVD-BEH  
**Sources:** Behavior observation domain, flow observations, institutional positioning

Behavioral evidence captures what market participants are actually doing — their positioning, flows, and revealed preferences:

- **Institutional Flow Evidence:** FII/DII net buying/selling as evidence of smart money positioning.
- **Options Positioning Evidence:** Put/call ratio, skew, max pain levels as evidence of market participant expectations.
- **Short Interest Evidence:** Short positions as evidence for bearish conviction among market participants.

---

### 2.13 Sentiment Evidence

**Code:** EVD-SENT  
**Sources:** News observation domain, social observation domain, analyst observation domain

Sentiment evidence captures the prevailing emotional and cognitive disposition of market participants:

- **News Sentiment Evidence:** Sentiment scores from financial news observations.
- **Social Sentiment Evidence:** Aggregated social media sentiment for entities.
- **Analyst Consensus Evidence:** Analyst rating and target price observations as evidence for the sell-side consensus.

---

### 2.14 Liquidity Evidence

**Code:** EVD-LIQ  
**Sources:** Order book observations, trading volume observations, spread observations

Liquidity evidence captures the capacity of the market to absorb orders without significant price impact:

- **Spread Evidence:** Bid-ask spread observations as evidence for transaction cost and market maker confidence.
- **Depth Evidence:** Available volume at various price levels as evidence for short-term price support/resistance.
- **Market Impact Evidence:** Historical evidence of how large orders have moved prices for an entity.

---

### 2.15 Volatility Evidence

**Code:** EVD-VOL  
**Sources:** Volatility observation domain (realised, implied, term structure)

Volatility evidence captures the risk and uncertainty environment:

- **Realised Volatility Evidence:** Historical price variation as evidence for the statistical risk of an entity.
- **Implied Volatility Evidence:** Options market's implied uncertainty as evidence for expected forward volatility.
- **Volatility Surface Evidence:** IV term structure and skew as evidence for the market's directional and magnitude expectations.

---

### 2.16 Flow Evidence

**Code:** EVD-FLOW  
**Sources:** Order flow observations, institutional flow observations, derivative flow observations

Flow evidence captures directional and volume evidence from order flow:

- **Net Order Flow Evidence:** Buy-initiated vs. sell-initiated flow as evidence for directional pressure.
- **Block Trade Evidence:** Large block transactions as evidence for institutional conviction.
- **Dark Pool Evidence:** Off-exchange flow relative to on-exchange flow.

---

### 2.17 Alternative Data Evidence

**Code:** EVD-ALT  
**Sources:** Alternative data observation domain (satellite, mobile, web traffic, credit card)

Alternative data evidence provides non-traditional, often high-frequency signals:

- **Consumer Activity Evidence:** Credit card spending, web traffic, app download observations as evidence for business performance.
- **Physical Activity Evidence:** Satellite imagery (parking lots, factory lights) as evidence for operational intensity.
- **Supply Chain Evidence:** Shipping, logistics, and inventory observations as evidence for business cycle positioning.

---

### 2.18 Risk Evidence

**Code:** EVD-RISK  
**Sources:** Risk observation domain (VaR, drawdown, exposure, stress test results)

Risk evidence captures the current risk posture of the portfolio and individual entities:

- **Portfolio Risk Evidence:** Current drawdown, VaR, exposure concentration as evidence for portfolio risk level.
- **Tail Risk Evidence:** Stress test observations as evidence for extreme scenario resilience.
- **Liquidity Risk Evidence:** Observations about market liquidity and portfolio liquidation capacity.

---

### 2.19 Portfolio Evidence

**Code:** EVD-PORT  
**Sources:** Portfolio observation domain (positions, P&L, exposure snapshots)

Portfolio evidence captures the current state and trajectory of the portfolio:

- **Position Evidence:** Current positions as evidence for portfolio exposure and concentration.
- **P&L Evidence:** Realised and unrealised P&L observations as evidence for strategy performance.
- **Attribution Evidence:** P&L attribution by strategy, sector, and entity.

---

### 2.20 Cross-Asset Evidence

**Code:** EVD-XAST  
**Sources:** Cross-asset observation domain (equity, rates, credit, currency, commodities)

Cross-asset evidence captures the inter-market context:

- **Risk-Off/Risk-On Evidence:** Equity-bond, equity-gold, USD-emerging market relationships as evidence for global risk appetite.
- **Commodity-Equity Evidence:** Oil price movements as evidence for energy sector and transport sector dynamics.
- **Rate-Equity Evidence:** Yield curve shape and movement as evidence for equity valuation and rotation.

---

### 2.21 Cross-Market Evidence

**Code:** EVD-XMKT  
**Sources:** Cross-market observation domain (NSE, BSE, SGX Nifty, global indices)

Cross-market evidence captures relationships across geographies:

- **SGX Nifty Pre-Open Evidence:** SGX Nifty futures as evidence for NSE opening direction.
- **Correlation with Global Indices:** Nikkei, S&P 500, DAX movements as evidence for global market context.
- **ADR Premium/Discount Evidence:** Indian ADR observations as evidence for foreign investor sentiment.

---

### 2.22 AI-Generated Evidence

**Code:** EVD-AI  
**Sources:** AI observation domain (model output observations, anomaly detection observations)

AI-generated evidence is derived from the outputs of statistical and machine learning models:

- **Anomaly Evidence:** Model-detected statistical anomalies in price, volume, or options data as evidence for unusual market conditions.
- **Pattern Recognition Evidence:** Model-detected recurring patterns as evidence for historical analogue conditions.
- **Regime Classification Evidence:** Model-assigned regime probabilities as evidence for current market regime.

Note: AI-generated evidence carries a mandatory model_id, model_version, and training_cutoff_date in its lineage. Evidence based on a stale model is flagged with MODEL_STALE.

---

### 2.23 Composite Evidence

**Code:** EVD-COMP  
**Sources:** Multiple evidence categories fused by the Evidence Aggregator

Composite evidence is a higher-order evidence record produced by fusing two or more evidence items from different categories. Composite evidence enables multi-factor analysis:

- **Confluence Evidence:** Multiple independent evidence items converging on the same conclusion direction.
- **Divergence Evidence:** Evidence items pulling in opposite directions — flagged as conflicted composite.
- **Thematic Evidence:** A structured collection of evidence items evaluating a specific investment theme.

---

### 2.24 Historical Evidence

**Code:** EVD-HIST  
**Sources:** Historical observation registry via PIT queries

Historical evidence is evidence evaluated at a historical point in time — used for backtesting, research, and historical analysis. Historical evidence MUST use PIT-safe query semantics (capture_timestamp ≤ historical_analysis_time) to prevent look-ahead bias.

---
## PART III — CORE COMPONENTS

### 3.1 Component Architecture Overview

The Evidence Engine is composed of 23 components organised into 5 operational clusters. Each cluster owns a distinct phase of the evidence lifecycle.

```
┌────────────────────────────────────────────────────────────────────┐
│                  EVIDENCE ENGINE COMPONENTS                        │
│                                                                    │
│  Cluster 1: Registry & Catalog                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Evidence Registry│  │ Evidence Catalog │  │ Identity Manager │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                    │
│  Cluster 2: Intake & Qualification                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │ Ev. Collector │  │ Ev. Builder   │  │ Ev. Validator         │  │
│  └───────────────┘  └───────────────┘  └───────────────────────┘  │
│                                                                    │
│  Cluster 3: Evaluation Engines                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │ Weight Eng  │  │ Confidence  │  │ Reliability │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │ Independence│  │ Correlation │  │ Aggregator  │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
│  ┌───────────────────────────┐                                    │
│  │ Conflict Manager          │                                    │
│  └───────────────────────────┘                                    │
│                                                                    │
│  Cluster 4: Context & Metadata                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Context Mgr  │  │ Lineage Mgr  │  │ Metadata Manager       │   │
│  └──────────────┘  └──────────────┘  └────────────────────────┘   │
│  ┌──────────────────────────────┐                                  │
│  │ Version Manager              │                                  │
│  └──────────────────────────────┘                                  │
│                                                                    │
│  Cluster 5: Storage, Search & Governance                           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐    │
│  │ Search Engine│  │ Storage Mgr  │  │ History Manager       │    │
│  └──────────────┘  └──────────────┘  └───────────────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐    │
│  │ Governance   │  │ Audit Manager│  │ Evolution Manager     │    │
│  └──────────────┘  └──────────────┘  └───────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 EC-01 — Evidence Registry

**Purpose:** The central store and authoritative source of truth for all evidence records in the IIOS. Every evidence record, regardless of category, is registered here before being distributed to consumers.

**Responsibilities:**
- Maintain the complete, versioned, immutable collection of all evidence records.
- Enforce evidence immutability — no in-place modifications; all changes create new versions.
- Provide point-in-time query semantics across the full historical evidence base.
- Enforce access control on all reads and writes.
- Maintain evidence status lifecycle (ACTIVE → SUPERSEDED → ARCHIVED → RETIRED).

**Inputs:** Evidence records from the Evidence Recorder (write path). Query requests from the Evidence Retrieval Service (read path).

**Outputs:** Evidence records on retrieval; storage confirmation on write.

**Dependencies:** Database Persistence Engine; Identity Manager; Audit Manager.

**Failure Modes:** Storage failure; replication lag; write conflicts on concurrent updates.

**Recovery:** Write queue buffering during storage failure; automatic failover to replica; consistency reconciliation on recovery.

**Monitoring:** Write latency (p99); storage capacity; replication health; query throughput.

**Scalability:** Horizontal partitioning by evidence_type and evidence_timestamp; read replicas for analytical queries.

**Engineering Notes:** The Registry distinguishes between operational access (ACTIVE evidence, recent history) and analytical access (full historical evidence). Separate storage tiers optimise for each access pattern.

---

### 3.3 EC-02 — Evidence Catalog

**Purpose:** The schema and definition authority for all evidence types. Defines what each evidence type means, what fields it must carry, what observation types it can be derived from, and what quality thresholds apply.

**Responsibilities:**
- Maintain the authoritative definition of every evidence type code.
- Define mandatory and optional fields for each type.
- Specify derivation rules (which observation types can produce which evidence types).
- Define weight ranges and confidence floors for each type.
- Govern schema evolution — changes approved by Domain Owner.

**Inputs:** Schema change requests (governance-approved). Type lookup requests from validators and classifiers.

**Outputs:** Evidence type definitions; schema validation schemas; derivation rule specifications.

**Dependencies:** Evidence Governance Manager.

**Failure Modes:** Schema corruption; version desync between Catalog and deployed validators.

**Recovery:** Catalog is maintained in a version-controlled store; rollback on corruption; version validation on startup.

**Monitoring:** Catalog version consistency; schema validation success rate.

**Engineering Notes:** The Catalog is the reference contract for all Evidence Engine components. It must be readable with sub-5ms latency under any load.

---

### 3.4 EC-03 — Evidence Identity Manager

**Purpose:** Assigns canonical, globally unique evidence_ids to every new evidence record. Maintains the identity sequence for each evidence type.

**Responsibilities:**
- Generate evidence_id in canonical format: `EVD-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`.
- Maintain per-type, per-date sequence counters.
- Persist sequence state to survive restarts without gaps.
- Detect and prevent identity conflicts.

**Inputs:** Identity assignment requests from Evidence Builder.

**Outputs:** Canonical evidence_id.

**Dependencies:** Evidence Catalog (for type code validation).

**Failure Modes:** Sequence state loss on crash; identity conflicts during concurrent assignment.

**Recovery:** Sequence recovery from Registry scan (find max existing sequence per type/date) on startup; atomic sequence increment prevents concurrent conflicts.

**Monitoring:** Sequence continuity; assignment latency (p99 < 5ms).

**Engineering Notes:** Identity assignment is an atomic, synchronous operation. It must never be retried with a different ID for the same evidence record.

---

### 3.5 EC-04 — Evidence Collector

**Purpose:** Receives validated observations from the Observation Engine and presents them to the Evidence Builder as candidates for evidence evaluation.

**Responsibilities:**
- Subscribe to the Observation Engine's Distribution Service for relevant observation types.
- Filter observations by quality floor (OQS ≥ configurable minimum before evidence evaluation begins).
- Present observations to the Evidence Builder in priority order (by governance tier and freshness).
- Maintain a collection queue for burst handling.

**Inputs:** Observation records from Observation Engine Distribution Service.

**Outputs:** Qualified observation candidates to Evidence Builder.

**Dependencies:** Observation Engine (Distribution Service); Evidence Catalog (for observation-to-evidence type mapping).

**Failure Modes:** Observation feed disconnection; queue overflow under burst load.

**Recovery:** Queue replay from Observation Registry on reconnection; circuit breaker on persistent overload.

**Monitoring:** Queue depth; observation intake rate; OQS rejection rate.

**Engineering Notes:** The Evidence Collector enforces a quality gate at the very start — no observation with OQS below the minimum enters the evidence pipeline. This prevents weak observations from contaminating the evidence store.

---

### 3.6 EC-05 — Evidence Builder

**Purpose:** Constructs an Evidence Candidate record from one or more qualified observations. The Builder determines whether observations can form evidence — not whether the evidence is strong, but whether it is structurally valid.

**Responsibilities:**
- Map one or more observations to an evidence type using the Catalog derivation rules.
- Assemble the Evidence Candidate record (all structural fields populated).
- Request context from the Context Manager.
- Request lineage record from the Lineage Manager.
- Pass the candidate to the Validator.

**Inputs:** Qualified observations from Evidence Collector.

**Outputs:** Evidence Candidate records to Evidence Validator.

**Dependencies:** Evidence Catalog; Context Manager; Lineage Manager; Identity Manager.

**Failure Modes:** Cannot map observation to any evidence type (no matching derivation rule); missing observation fields; context unavailable.

**Recovery:** Unclassified observations are held in a triage queue; flagged for manual review if unresolvable.

**Monitoring:** Candidate construction success rate; derivation rule hit rate; triage queue depth.

**Engineering Notes:** The Builder is a pure structural assembly component. It does not evaluate weight, confidence, or quality — those are for downstream evaluation components. The Builder's only quality gate is structural completeness.

---

### 3.7 EC-06 — Evidence Validator

**Purpose:** Applies multi-level validation to Evidence Candidate records before they proceed to evaluation. Analogous to the Observation Validator, but operating on evidence rather than raw observations.

**Responsibilities:**
- L1: Structural check — all mandatory fields present and correctly typed.
- L2: Referential check — all observation_ids resolvable in the Observation Registry.
- L3: Derivation validity — evidence type derivation is consistent with the Catalog.
- L4: Temporal consistency — evidence_timestamp is not in the future; all observation timestamps are ≤ evidence_timestamp.
- L5: Context validity — context_id is non-null and resolves to a valid ContextRecord.
- L6: Schema conformance — candidate conforms to the Catalog schema for its type.

**Inputs:** Evidence Candidate records from Evidence Builder.

**Outputs:** Validated candidates to Weighting Engine; rejected candidates to quarantine with failure reason.

**Dependencies:** Evidence Catalog; Observation Registry; Context Manager.

**Failure Modes:** Validation service failure → fallback to structural-only validation with PARTIAL_VALIDATION flag.

**Recovery:** Failed candidates retained in quarantine store; re-validation on manual trigger.

**Monitoring:** Validation pass rate; failure reason distribution; quarantine rate.

**Engineering Notes:** The Validator is the Evidence Engine's first quality gate. Structurally invalid evidence must not proceed to evaluation, where it might contaminate weights and scores.

---

### 3.8 EC-07 — Evidence Weighting Engine

**Purpose:** Assigns a numerical weight to each piece of evidence reflecting its analytical importance relative to other evidence of the same or similar type.

**Responsibilities:**
- Compute the base weight from the evidence type's weight range in the Catalog.
- Apply source-quality modifier: primary evidence > secondary evidence.
- Apply regime-sensitivity modifier: adjust weight for current market context.
- Apply recency modifier: recent evidence receives higher weight for fast-changing conditions.
- Produce a final weight in [0.0, 1.0] with a derivation record.

**Inputs:** Validated evidence candidates; current ContextRecord; Evidence Catalog weight specifications.

**Outputs:** Weighted evidence records; weight derivation audit records.

**Dependencies:** Evidence Catalog; Context Manager; source quality data from Observation Engine.

**Failure Modes:** Weight computation failure → assign default weight for type; flag as DEFAULT_WEIGHT.

**Recovery:** Default weight assignment with degraded flag; scheduled weight recomputation when service recovers.

**Monitoring:** Weight distribution by type; default weight rate; weight computation latency.

**Engineering Notes:** Weights must be calibrated periodically against historical outcomes. A weight that consistently under- or over-predicts evidence relevance should be recalibrated by the Evidence Evolution Manager.

---

### 3.9 EC-08 — Evidence Confidence Engine

**Purpose:** Assigns a confidence score to each evidence record, reflecting the degree of certainty that the evidence accurately represents the condition it is asserting.

**Responsibilities:**
- Inherit base confidence from the source observation's OQS and confidence score.
- Adjust for derivation complexity (more derivation steps → more uncertainty propagation).
- Adjust for cross-source agreement on the underlying observations.
- Adjust for historical accuracy of this evidence type for this entity and regime.
- Produce an Evidence Confidence Score (ECS) in [0.0, 1.0].

**Inputs:** Weighted evidence records; corroboration data from Corroboration Service; historical accuracy records.

**Outputs:** Evidence records with ECS; confidence derivation audit records.

**Dependencies:** Weighting Engine; Corroboration Service; Evidence History Manager.

**Failure Modes:** Confidence computation failure → assign base confidence from OQS; flag as CONFIDENCE_DERIVED_PARTIAL.

**Recovery:** Partial confidence with flag; scheduled recomputation.

**Monitoring:** ECS distribution by type; confidence degradation rate; calibration accuracy.

**Engineering Notes:** ECS must be calibrated — a 0.80 ECS should historically correspond to approximately 80% probability that the evidence correctly represents the condition. Calibration is the responsibility of the Evolution Manager.

---

### 3.10 EC-09 — Evidence Reliability Engine

**Purpose:** Assesses the long-term track record of this evidence type from this source for this entity type, producing an Evidence Reliability Score (ERS).

**Responsibilities:**
- Compute the rolling 90-day accuracy of this evidence type for this source — how often did evidence of this type from this source, at this confidence level, correctly support the hypothesis it spoke to?
- Produce an ERS in [0.0, 1.0].
- Maintain the reliability history in the Evidence History Manager.
- Trigger trust tier review when ERS drops below 0.70.

**Inputs:** Evidence records; historical evidence outcome records from Evidence History Manager.

**Outputs:** Evidence Reliability Scores; reliability alerts.

**Dependencies:** Evidence History Manager; Evidence Governance Manager.

**Failure Modes:** Insufficient history (< 30 days) → assign provisional ERS = 0.70 with PROVISIONAL_RELIABILITY flag.

**Recovery:** Provisional reliability until sufficient history accumulates.

**Monitoring:** ERS by type/source; sources with declining ERS; provisional reliability rate.

**Engineering Notes:** ERS is computed asynchronously — it does not block the evidence pipeline. Each evidence record is tagged with the current ERS at the time of evaluation.

---

### 3.11 EC-10 — Evidence Independence Engine

**Purpose:** Assesses whether a new evidence record is statistically independent from other evidence records already in the active evidence set. Dependent evidence must not be treated as independent by reasoning systems.

**Responsibilities:**
- Compute pairwise source correlation for all active evidence sharing a common entity or hypothesis.
- Detect evidence derived from common upstream information sources (e.g., two "independent" news sources both reprinting the same wire report).
- Compute an independence score for each evidence record relative to the current evidence set.
- Adjust effective evidence weight to reflect reduced independence (correlated evidence gets lower effective weight).

**Inputs:** New evidence record; current active evidence set for the same entity/hypothesis; source correlation matrix.

**Outputs:** Independence-adjusted evidence records; correlation flags.

**Dependencies:** Evidence Registry (active evidence query); source correlation data.

**Failure Modes:** Correlation check failure → assign independence_score = 0.50 (neutral) with INDEPENDENCE_CHECK_SKIPPED.

**Recovery:** Scheduled independence recheck for flagged evidence.

**Monitoring:** Independence score distribution; high-correlation detection rate; effective weight reduction due to correlation.

**Engineering Notes:** This is the most analytically important correction in the Evidence Engine. Overconfidence caused by correlated evidence is a primary source of systematic trading error. The Independence Engine must be always-on.

---

### 3.12 EC-11 — Evidence Correlation Engine

**Purpose:** Identifies and records statistical correlations between evidence items — relationships that may provide additional signal when the Evidence Aggregator forms composite evidence.

**Responsibilities:**
- Compute rolling correlations between evidence series for the same entity (e.g., price momentum evidence vs. volume evidence).
- Identify leading/lagging relationships between evidence types.
- Record correlation records in the Evidence Registry for use by the Aggregator and Hypothesis Engine.

**Inputs:** Active evidence series from Evidence Registry; time-series correlation analysis requests.

**Outputs:** Correlation records; lead/lag relationship records.

**Dependencies:** Evidence Registry; statistical analysis services.

**Failure Modes:** Insufficient time series data for correlation computation.

**Recovery:** Flag evidence as CORRELATION_PENDING until sufficient history accumulates.

**Monitoring:** Correlation computation coverage; correlation stability.

---

### 3.13 EC-12 — Evidence Aggregator

**Purpose:** Fuses multiple evidence records from different categories into composite evidence records that express a multi-dimensional view of an entity or market condition.

**Responsibilities:**
- Identify evidence items that speak to the same hypothesis from different categories.
- Apply independence-adjusted weighting to each constituent evidence item.
- Compute a fusion score reflecting the coherence of the evidence set.
- Produce Composite Evidence records with full constituent lineage.
- Detect and flag divergent composites (evidence items pulling in opposite directions).

**Inputs:** Evidence records from multiple categories; independence scores; weights.

**Outputs:** Composite Evidence records (EVD-COMP) with fusion scores.

**Dependencies:** Independence Engine; Weighting Engine; Evidence Registry.

**Failure Modes:** Fusion computation failure → preserve constituent evidence; skip composite generation; alert.

**Recovery:** Individual evidence records remain valid; composite re-attempted on next cycle.

**Monitoring:** Composite generation rate; fusion score distribution; divergent composite rate.

---

### 3.14 EC-13 — Evidence Conflict Manager

**Purpose:** Detects, records, and adjudicates conflicts between evidence records that speak to the same hypothesis in opposing directions.

**Responsibilities:**
- Maintain a real-time conflict detection scan over active evidence for the same entity and hypothesis context.
- Classify conflicts: MINOR (small weight difference), MODERATE, MAJOR (strongly opposing high-confidence evidence).
- Adjudicate conflicts where possible — determine whether one piece of evidence should be weighted down based on recency, reliability, or quality.
- Preserve unresolved conflicts as CONFLICT status in both evidence records.
- Alert the Hypothesis Engine of active major conflicts.

**Inputs:** Active evidence set; new evidence arrivals.

**Outputs:** Conflict records; conflict status updates on evidence records; conflict alerts.

**Dependencies:** Evidence Registry; Evidence Weighting Engine; Evidence Reliability Engine.

**Failure Modes:** Conflict detection failure → evidence proceeds without conflict status; alert ops.

**Recovery:** Batch conflict scan as recovery step.

**Monitoring:** Active conflict count; conflict resolution rate; MAJOR conflict alert count.

**Engineering Notes:** Conflicts must never be silently resolved. The Hypothesis Engine must see the conflict and decide how to handle it in the context of its hypothesis evaluation.

---
### 3.15 EC-14 — Evidence Context Manager

**Purpose:** Enriches every evidence record with a ContextRecord describing the state of the investment universe at the evidence_timestamp.

**Responsibilities:**
- Fetch the ContextRecord from the Observation Engine's Context Store for the evidence_timestamp.
- Attach regime, session, market state, VIX level, expiry calendar, and global context.
- Compute a context_richness score for the evidence record.
- Handle degraded context gracefully (CONTEXT_PARTIAL flag).

**Inputs:** Evidence candidates requiring context assignment; evidence_timestamp.

**Outputs:** Context-enriched evidence records; context_richness scores.

**Dependencies:** Observation Engine (Context Manager); ContextRecord store.

**Failure Modes:** Context Manager unavailable → CONTEXT_PARTIAL; evidence held for re-enrichment.

**Recovery:** Re-enrichment job runs when Context Manager recovers.

**Monitoring:** Context enrichment success rate; context_richness score distribution; CONTEXT_PARTIAL rate.

**Engineering Notes:** Context is not optional. Evidence evaluated without context is regime-blind. The system must accept a brief delay rather than store context-free evidence.

---

### 3.16 EC-15 — Evidence Lineage Manager

**Purpose:** Creates and maintains the lineage records for all evidence — the complete chain from evidence back through constituent observations, derivation steps, and source information objects.

**Responsibilities:**
- Create a lineage record at evidence creation time: list constituent observation_ids, derivation function, source information_ids.
- Maintain lineage across versioning — new versions extend the lineage chain.
- Support lineage traversal queries: "show me the full lineage of evidence EVD-MKT-TREND-…".
- Maintain lineage records permanently (lineage is never archived or deleted).

**Inputs:** Evidence records at creation time; version events from Version Manager.

**Outputs:** Lineage records in the Evidence Registry.

**Dependencies:** Evidence Registry; Observation Registry (for lineage traversal back to observation level).

**Failure Modes:** Lineage write failure → fatal for evidence creation; evidence must not be stored without lineage.

**Recovery:** Lineage write retry; evidence creation held until lineage is committed.

**Monitoring:** Lineage record count; lineage write success rate; lineage traversal latency.

**Engineering Notes:** The lineage record is the evidentiary foundation for auditability. A trading decision traceable back through evidence to observations to sources is an auditable decision. This is non-negotiable.

---

### 3.17 EC-16 — Evidence Metadata Manager

**Purpose:** Manages the metadata fields attached to every evidence record beyond the core analytical fields.

**Responsibilities:**
- Assign and validate metadata fields: creation_timestamp, creator_system, processing_pipeline, schema_version, tags[].
- Maintain metadata schema consistency with the Evidence Catalog.
- Support metadata-driven queries (e.g., find all evidence created by pipeline X in the last 30 days).

**Inputs:** Evidence records at creation time.

**Outputs:** Metadata-enriched evidence records.

**Dependencies:** Evidence Catalog.

**Failure Modes:** Metadata enrichment failure → proceed with minimal metadata; flag as METADATA_PARTIAL.

**Monitoring:** Metadata completeness score; METADATA_PARTIAL rate.

---

### 3.18 EC-17 — Evidence Version Manager

**Purpose:** Manages the version lifecycle of evidence records — creating new versions when evidence is updated, corrections are made, or re-evaluations are triggered by new information.

**Responsibilities:**
- On evidence update: create a new version via the History Manager; supersede the previous version.
- Enforce linear version chains — no branching.
- Record the reason for the new version (CORRECTION / RE_EVALUATION / CONTEXT_UPDATE / OBSERVATION_UPDATE).
- Preserve all previous versions permanently.

**Inputs:** Version requests from Evidence Confidence Engine, Evolution Manager, or re-evaluation pipelines.

**Outputs:** New version evidence records; SUPERSEDED status updates on old versions.

**Dependencies:** Evidence History Manager; Evidence Identity Manager.

**Failure Modes:** Version creation failure → reject update; preserve existing version.

**Recovery:** Version creation retry; persistent failure alerts ops.

**Monitoring:** Version creation rate; re-evaluation trigger frequency; reason distribution.

---

### 3.19 EC-18 — Evidence Search Engine

**Purpose:** Provides full-text, structured, and semantic search across the evidence store, enabling the Hypothesis Engine and Knowledge Engine to retrieve relevant evidence quickly.

**Responsibilities:**
- Maintain inverted indexes over evidence_type, entity_id, hypothesis_relevance[], context fields, and tags.
- Support temporal proximity queries: "evidence about entity X in the 2 hours before event Y".
- Support quality-filtered queries: "evidence with EQS ≥ 0.75 about entity X".
- Support conflict-filtered queries: "evidence in CONFLICT status about entity X".

**Inputs:** Query requests from Evidence Retrieval Service; index update events from Evidence Recorder.

**Outputs:** Ranked evidence record lists matching query criteria.

**Dependencies:** Evidence Registry; Evidence Catalog.

**Failure Modes:** Index corruption → rebuild from Registry; degraded search performance during rebuild.

**Recovery:** Incremental index rebuild from Registry.

**Monitoring:** Query latency (p99 < 50ms); index freshness; index rebuild duration.

---

### 3.20 EC-19 — Evidence Storage Manager

**Purpose:** Manages the physical storage lifecycle of evidence records — hot tier (recent, frequently accessed), warm tier (historical, periodically accessed), cold tier (archival).

**Responsibilities:**
- Govern tier transitions based on age and access frequency.
- Enforce retention policies by domain.
- Manage compression for warm and cold tiers.
- Provide transparent access across tiers (consumers do not need to know which tier).

**Inputs:** Evidence records from Recorder; tier transition policies from Governance Manager; retrieval requests.

**Outputs:** Tiered stored evidence; retrieval responses across tiers.

**Dependencies:** Database Persistence Engine; Evidence Governance Manager.

**Failure Modes:** Tier transition failure → evidence remains in current tier; alert.

**Monitoring:** Tier occupancy; tier transition latency; retrieval latency by tier.

---

### 3.21 EC-20 — Evidence History Manager

**Purpose:** Preserves the complete history of every evidence record — all versions, all evaluation events, and all outcome records.

**Responsibilities:**
- Store all superseded evidence versions with their full content.
- Record evidence outcome events (when the hypothesis the evidence supported was confirmed or refuted).
- Support historical replay queries — "what evidence existed about entity X at timestamp T?"
- Maintain outcome records for reliability calibration.

**Inputs:** Version events from Version Manager; outcome records from external feedback loops.

**Outputs:** Historical evidence records; outcome records for Reliability Engine.

**Dependencies:** Evidence Registry; Evidence Version Manager.

**Failure Modes:** History write failure → alert; evidence creation holds until history is committed.

**Recovery:** History write retry; consistent commit of history and primary record.

**Monitoring:** History write success rate; outcome record rate; replay query latency.

---

### 3.22 EC-21 — Evidence Governance Manager

**Purpose:** Enforces governance policies across all evidence — ownership, naming, retention, access, and compliance.

**Responsibilities:**
- Maintain the evidence governance policy registry.
- Enforce evidence type ownership assignments.
- Review and approve schema changes to the Evidence Catalog.
- Enforce retention schedules — trigger archival and retirement.
- Produce governance reports.
- Conduct governance reviews on schedule.

**Inputs:** Governance policy requests; schema change requests; retention schedule triggers.

**Outputs:** Governance approvals; policy enforcement events; governance reports.

**Dependencies:** Evidence Catalog; Evidence Storage Manager.

**Failure Modes:** Governance Manager failure → freeze schema changes and archival; continue evidence creation with existing policies.

**Monitoring:** Policy compliance rate; governance review completion; schema change approval latency.

---

### 3.23 EC-22 — Evidence Audit Manager

**Purpose:** Records every operation on every evidence record in an append-only, tamper-evident audit trail.

**Responsibilities:**
- Record CREATE, READ, UPDATE (via versioning), ARCHIVE, RETIRE operations on all evidence records.
- Record all query access to evidence records classified as RESTRICTED or CONFIDENTIAL.
- Maintain the audit trail as append-only (no modification, no deletion).
- Support on-demand audit export.

**Inputs:** Operation events from all Evidence Engine components.

**Outputs:** Audit records; audit reports.

**Dependencies:** Audit storage (append-only; separate from Evidence Registry).

**Failure Modes:** Audit write failure → CRITICAL; block the triggering operation until audit is committed.

**Recovery:** Persistent audit failure alerts ops immediately; no evidence operations permitted until resolved.

**Monitoring:** Audit write latency (p99 < 5ms); audit record count; tamper detection.

---

### 3.24 EC-23 — Evidence Evolution Manager

**Purpose:** Manages the long-term evolution of the evidence system — recalibrating weights and confidence scores, detecting drift, retiring stale evidence types, and promoting experimental evidence types.

**Responsibilities:**
- Monitor weight calibration: compare assigned weights against historical predictive accuracy; trigger recalibration when drift exceeds threshold.
- Monitor confidence calibration: compare ECS values against historical outcome rates.
- Detect evidence type drift — when an evidence type that historically worked well begins to lose predictive relevance.
- Propose weight adjustments, type retirements, and new type additions for governance approval.
- Execute approved evolution changes with full version tracking.

**Inputs:** Historical outcome records from History Manager; calibration analysis results.

**Outputs:** Calibration proposals; approved calibration updates; evolution reports.

**Dependencies:** Evidence History Manager; Evidence Governance Manager; Evidence Weighting Engine.

**Failure Modes:** Evolution computation failure → retain existing calibration; alert.

**Recovery:** Re-run evolution computation on next scheduled cycle.

**Monitoring:** Calibration error by type; drift detection alerts; evidence type retirement rate.

**Engineering Notes:** The Evolution Manager is the only component authorised to propose changes to evidence weights and type definitions. All proposals require governance approval before taking effect. This prevents automated drift from silently degrading evidence quality.

---
## PART IV — EVIDENCE LIFECYCLE

### 4.1 Lifecycle Overview

The Evidence Lifecycle defines the complete journey of an evidence record from its origination (as one or more observations) through evaluation, storage, and eventual retirement. The lifecycle has 14 stages organised into 4 phases.

```
PHASE A — INTAKE
  Stage 1:  Observation Intake
  Stage 2:  Evidence Candidate Formation
  Stage 3:  Validation

PHASE B — EVALUATION
  Stage 4:  Qualification
  Stage 5:  Weight Assignment
  Stage 6:  Confidence Assignment
  Stage 7:  Context Assignment
  Stage 8:  Correlation Analysis
  Stage 9:  Conflict Analysis

PHASE C — STORAGE & DISTRIBUTION
  Stage 10: Storage
  Stage 11: Distribution

PHASE D — PERSISTENCE
  Stage 12: Historical Preservation
  Stage 13: Evolution
  Stage 14: Archive / Retirement
```

---

### 4.2 Stage 1 — Observation Intake

**Trigger:** Observation Distribution Service delivers a qualified observation.

**Process:**
```
Observation arrives from Observation Engine
       │
       ▼
[Evidence Collector]
 - Check OQS ≥ minimum for evidence (default: 0.60)
 - Check freshness_tier ≠ EXPIRED
       │
       ├─── OQS below floor or EXPIRED ──► Reject; log; do not create evidence candidate
       │
       ▼
Queue observation for Evidence Builder
```

**Stage output:** Qualified observation in evidence intake queue.

**Quality gate:** OQS ≥ configured minimum (default 0.60); freshness_tier not EXPIRED.

**Monitoring:** Rejection rate; intake queue depth; intake throughput.

---

### 4.3 Stage 2 — Evidence Candidate Formation

**Trigger:** Evidence Builder dequeues a qualified observation.

**Process:**
```
Qualified observation dequeued
       │
       ▼
[Evidence Builder]
 - Look up derivation rules in Evidence Catalog
 - Identify evidence type(s) this observation can contribute to
       │
       ├── No matching type ──► Triage queue; alert
       │
       ▼
Assemble Evidence Candidate:
 - evidence_type assigned
 - supporting_observations[] = [observation_id]
 - evidence_timestamp = NOW()
 - status = CANDIDATE
       │
       ▼
[Context Manager]
 - attach ContextRecord at evidence_timestamp
       │
       ▼
[Lineage Manager]
 - create lineage record: source obs_ids, derivation rule
       │
       ▼
Pass to Evidence Validator
```

**Stage output:** Evidence Candidate record with context and lineage.

---

### 4.4 Stage 3 — Validation

**Trigger:** Evidence Candidate arrives at Evidence Validator.

**Process:**
```
Evidence Candidate
       │
       ▼
[Evidence Validator]
 L1: Structural check (mandatory fields)
       │
       ▼
 L2: Referential check (all obs_ids resolvable)
       │
       ▼
 L3: Derivation validity (type consistent with Catalog)
       │
       ▼
 L4: Temporal consistency (timestamps valid)
       │
       ▼
 L5: Context validity (context_id resolves)
       │
       ▼
 L6: Schema conformance
       │
       ├── Any L1–L4 or L6 fail ──► QUARANTINE; log failure reason
       ├── L5 fail only ──► CONTEXT_PARTIAL flag; continue
       │
       ▼
validation_status = PASS (or WARN for L5)
```

**Stage output:** Validated evidence candidate (status: VALIDATED) or quarantined candidate (status: QUARANTINE).

---

### 4.5 Stage 4 — Qualification

**Trigger:** Validated candidate proceeds.

**Process:**
The Evidence Qualification step determines whether the observation data constitutes a valid basis for evidence of the assigned type. It is a semantic check — not merely structural:

- Does the observation value meet the minimum threshold to constitute evidence of this type? (e.g., a price movement of 0.01% is not evidence of a significant trend even if the observation is structurally valid)
- Is the observation from a source type that is permitted to produce evidence of this type?
- Is the evidence period consistent with the type's minimum time window?

**Stage output:** QUALIFIED evidence candidate (ready for evaluation) or DISQUALIFIED (with disqualification reason, held in triage).

---

### 4.6 Stage 5 — Weight Assignment

**Trigger:** Qualified candidate.

**Process:**
```
[Evidence Weighting Engine]
 base_weight = Catalog.weight_range(type).midpoint
 source_modifier = f(source_trust_tier)
 regime_modifier = f(context.regime, type.regime_sensitivity)
 recency_modifier = f(observation_age, type.recency_decay)
 weight = normalise(base × source_modifier × regime_modifier × recency_modifier)
```

**Stage output:** Weight-assigned evidence record.

---

### 4.7 Stage 6 — Confidence Assignment

**Trigger:** Weight-assigned evidence.

**Process:**
```
[Evidence Confidence Engine]
 base_confidence = source_observation.observation_confidence
 corroboration_modifier = f(corroboration_count, corroboration_agreement)
 derivation_uncertainty = f(derivation_steps, derivation_complexity)
 historical_accuracy_modifier = f(ERS, type, source)
 ECS = normalise(base × corroboration_modifier × (1 - derivation_uncertainty) × historical_accuracy_modifier)
```

**Stage output:** ECS-assigned evidence record.

---

### 4.8 Stage 7 — Context Assignment

**Trigger:** Confidence-scored evidence (may already have context from Stage 2; this stage enriches further).

**Process:**
The Context Manager enriches the evidence with full investment context — not just the market state, but the regime-specific interpretation context, the event calendar context, and the portfolio-level context if applicable. Context is finalised at this stage.

**Stage output:** Fully context-enriched evidence record.

---

### 4.9 Stage 8 — Correlation Analysis

**Trigger:** Context-enriched evidence.

**Process:**
```
[Independence Engine]
 active_evidence = Registry.get_active(entity_id, hypothesis_context)
 pairwise_correlation = compute(new_evidence, active_evidence)
 independence_score = 1.0 - max(pairwise_correlation)
 effective_weight = weight × independence_score
```

**Stage output:** Independence-adjusted evidence with correlation flags.

---

### 4.10 Stage 9 — Conflict Analysis

**Trigger:** Independence-adjusted evidence.

**Process:**
```
[Conflict Manager]
 opposing_evidence = Registry.get_active(entity_id, same_hypothesis, opposing_direction)
 if opposing_evidence is not empty:
     severity = classify_conflict(weight, ECS, opposing_evidence.weight, opposing_evidence.ECS)
     set conflict_status = MINOR / MODERATE / MAJOR
     record conflict_refs[]
     notify Hypothesis Engine if severity = MAJOR
```

**Stage output:** Conflict-assessed evidence record (status may be updated to CONFLICT).

---

### 4.11 Stage 10 — Storage

**Trigger:** Conflict-assessed evidence.

**Process:**
```
[Identity Manager]
 evidence_id = assign(category, type, date)

[Evidence Recorder]
 write evidence record to Registry (ACTIVE status)
 write lineage record (permanent)
 write audit record (CREATE event)

[Search Engine]
 index new evidence record
```

**Stage output:** Stored, indexed, audited evidence record.

---

### 4.12 Stage 11 — Distribution

**Trigger:** Evidence stored.

**Process:**
```
[Distribution Service]
 for each subscribed consumer (Hypothesis Engine, Knowledge Engine, etc.):
     check consumer.evidence_quality_floor ≤ evidence.EQS
     check consumer.freshness_requirement ≤ evidence.freshness_tier
     if pass: add to consumer delivery queue
     record DISTRIBUTE audit event
```

**Stage output:** Evidence distributed to eligible consumers.

---

### 4.13 Stage 12 — Historical Preservation

After distribution, evidence records are managed by the History Manager for long-term preservation:

- Original evidence records preserved permanently in version history.
- Evidence outcomes (hypothesis confirmation/refutation) linked to evidence records.
- Historical evidence available for backtesting and replay via PIT queries.
- Survivorship bias correction maintained — evidence for retired entities preserved.

---

### 4.14 Stages 13–14 — Evolution and Archive/Retirement

**Evolution (Stage 13):** The Evolution Manager reviews evidence records periodically for calibration accuracy. If weight or confidence scores have drifted from historical accuracy, re-evaluation creates new versions. Evolution events are governance-approved.

**Archive (Stage 14):** Evidence records older than their active retention period transition to the warm tier (governed by Storage Manager). After the retention period, they transition to cold storage. Legal hold prevents archival. Retirement permanently removes evidence from active queries (status = RETIRED); the record itself remains in cold storage permanently.

---

### 4.15 Evidence State Machine

```
          ┌─────────────────────────────────────────────┐
          │           EVIDENCE STATE MACHINE            │
          └─────────────────────────────────────────────┘

                        ┌──────────┐
          Observation   │ CANDIDATE│
          arrives  ────►│          │
                        └────┬─────┘
                             │ Builder assembles
                             ▼
                        ┌──────────┐
                        │VALIDATED │◄─── Validator PASS
                        └────┬─────┘
                             │ Validator FAIL
                             ▼
                        ┌──────────┐
                        │QUARANTINE│  (retained; re-validate possible)
                        └──────────┘

                             │ Qualification PASS
                             ▼
                        ┌──────────────┐
                        │  QUALIFIED   │
                        └──────┬───────┘
                               │ Evaluation complete
                               ▼
                        ┌──────────────┐
                        │    ACTIVE    │◄─── stored, indexed, distributed
                        └──────┬───────┘
                               │
                 ┌─────────────┼──────────────┐
                 ▼             ▼              ▼
          ┌──────────┐  ┌──────────┐   ┌──────────┐
          │SUPERSEDED│  │ ARCHIVED │   │ RETIRED  │
          │(version  │  │(warm/cold│   │(permanent│
          │ replaced)│  │ storage) │   │ end-of-  │
          └──────────┘  └──────────┘   │ life)    │
                                       └──────────┘
```

---
## PART V — EVIDENCE SERVICES

### 5.1 Service Architecture Overview

The Evidence Engine exposes 17 services. Services are the operational interfaces through which components and external consumers interact with evidence. Each service owns a defined function, has an SLA, and has a defined failure handling strategy.

| Service | Code | Function |
|---|---|---|
| Evidence Collection Service | ES-01 | Receives observations; feeds intake pipeline |
| Evidence Validation Service | ES-02 | Multi-level evidence candidate validation |
| Evidence Qualification Service | ES-03 | Semantic qualification of evidence candidates |
| Evidence Weight Service | ES-04 | Evidence weight computation |
| Evidence Confidence Service | ES-05 | ECS computation |
| Evidence Reliability Service | ES-06 | ERS computation and tracking |
| Evidence Correlation Service | ES-07 | Independence and correlation analysis |
| Evidence Conflict Resolution Service | ES-08 | Conflict detection and adjudication |
| Evidence Context Service | ES-09 | Context enrichment |
| Evidence Search Service | ES-10 | Query and search |
| Evidence Retrieval Service | ES-11 | Structured evidence retrieval |
| Evidence Governance Service | ES-12 | Policy enforcement |
| Evidence Audit Service | ES-13 | Audit trail management |
| Evidence Analytics Service | ES-14 | Aggregate analytics |
| Evidence Evolution Service | ES-15 | Calibration and evolution |
| Evidence Archive Service | ES-16 | Archival and lifecycle management |
| Evidence Health Service | ES-17 | System health monitoring |

---

### 5.2 ES-01 — Evidence Collection Service

**Purpose:** Acts as the primary intake interface, receiving observation records from the Observation Engine and routing them into the evidence pipeline.

**Inputs:** Observation records via Observation Engine Distribution Service subscription.

**Outputs:** Qualified observation candidates to the Evidence Builder queue.

**Consumers:** Evidence Builder (EC-05).

**Dependencies:** Observation Engine (Distribution Service); Evidence Catalog (derivation rule lookup).

**Failure Handling:** On observation feed disconnection, reconnect with exponential backoff; replay missed observations from Observation Registry on reconnection.

**Recovery:** Full queue replay from Observation Registry using PIT query semantics.

**Performance Expectations:**
- Intake throughput: ≥ 10,000 observations/second sustained
- Intake queue depth alert threshold: > 5 minutes of average volume
- OQS rejection rate alert threshold: > 5%
- p99 latency from observation receipt to queue entry: < 10ms

---

### 5.3 ES-02 — Evidence Validation Service

**Purpose:** Applies the 6-level validation protocol to all Evidence Candidate records before they proceed to evaluation.

**Inputs:** Evidence Candidate records from Evidence Builder.

**Outputs:** Validated candidates to qualification pipeline; quarantined candidates with failure reason.

**Consumers:** Evidence Qualification Service (ES-03).

**Dependencies:** Evidence Catalog; Observation Registry; Context Manager.

**Failure Handling:** On partial validator failure, apply available levels; flag PARTIAL_VALIDATION; alert.

**Recovery:** Re-validation batch for PARTIAL_VALIDATION records when full service restores.

**Performance Expectations:**
- Validation throughput: ≥ 5,000 candidates/second
- p99 validation latency: < 15ms
- Quarantine rate alert threshold: > 2% of candidates

---

### 5.4 ES-03 — Evidence Qualification Service

**Purpose:** Applies semantic qualification tests to determine whether a validated candidate constitutes actionable evidence.

**Inputs:** Validated evidence candidates.

**Outputs:** QUALIFIED evidence candidates; DISQUALIFIED candidates with disqualification reason.

**Consumers:** Evidence Weight Service (ES-04).

**Dependencies:** Evidence Catalog (qualification rules); ContextRecord.

**Failure Handling:** On qualification failure, route to DISQUALIFIED with QUALIFICATION_FAILED reason.

**Recovery:** Batch re-qualification on rule update.

**Performance Expectations:**
- p99 qualification latency: < 20ms
- Disqualification rate alert: > 10% (may indicate source quality issue)

---

### 5.5 ES-04 — Evidence Weight Service

**Purpose:** Computes weights for all qualified evidence records.

**Inputs:** Qualified evidence records; current ContextRecord.

**Outputs:** Weighted evidence records; weight derivation audit records.

**Consumers:** Evidence Confidence Service (ES-05).

**Dependencies:** Evidence Catalog (weight ranges); Context Service (ES-09).

**Failure Handling:** On weight computation failure, assign default weight with DEFAULT_WEIGHT flag.

**Recovery:** Weight recomputation on next evaluation cycle.

**Performance Expectations:**
- p99 weight computation latency: < 15ms
- Default weight rate alert: > 1%

---

### 5.6 ES-05 — Evidence Confidence Service

**Purpose:** Computes Evidence Confidence Scores (ECS) for all weighted evidence.

**Inputs:** Weighted evidence records; corroboration data; historical reliability records.

**Outputs:** ECS-assigned evidence records.

**Consumers:** Evidence Reliability Service (ES-06).

**Dependencies:** Evidence Reliability Service; corroboration data from Observation Engine.

**Failure Handling:** Assign base confidence from observation OQS; flag CONFIDENCE_PARTIAL.

**Recovery:** Full confidence recomputation when corroboration and reliability data are available.

**Performance Expectations:**
- p99 ECS computation latency: < 20ms
- CONFIDENCE_PARTIAL rate alert: > 2%

---

### 5.7 ES-06 — Evidence Reliability Service

**Purpose:** Computes and maintains Evidence Reliability Scores (ERS) based on rolling 90-day outcome history.

**Inputs:** Evidence records; outcome records from History Manager.

**Outputs:** ERS values attached to evidence records; reliability trend reports.

**Consumers:** Evidence Confidence Service (ES-05); Evolution Service (ES-15).

**Dependencies:** Evidence History Manager; Evidence Evolution Service.

**Failure Handling:** Assign provisional ERS = 0.70; flag PROVISIONAL_RELIABILITY.

**Recovery:** Full ERS computation from history after recovery.

**Performance Expectations:**
- ERS computation runs asynchronously; no latency SLA on the evidence creation path
- ERS recalibration frequency: daily for all evidence types with ≥ 30 outcomes

---

### 5.8 ES-07 — Evidence Correlation Service

**Purpose:** Computes pairwise independence scores and correlation maps between evidence records sharing an entity or hypothesis.

**Inputs:** New evidence records; active evidence set from Registry.

**Outputs:** Independence-adjusted evidence records; correlation maps.

**Consumers:** Evidence Aggregator (EC-12); Hypothesis Engine (external consumer).

**Dependencies:** Evidence Registry; statistical correlation services.

**Failure Handling:** Assign independence_score = 0.50 (neutral); flag INDEPENDENCE_CHECK_SKIPPED.

**Recovery:** Batch independence recomputation.

**Performance Expectations:**
- p99 independence check latency: < 30ms
- Correlation map update frequency: on every new evidence arrival and on every new active evidence set change

---

### 5.9 ES-08 — Evidence Conflict Resolution Service

**Purpose:** Detects conflicts between evidence records and adjudicates or escalates them.

**Inputs:** New evidence records; active evidence set.

**Outputs:** Conflict records; conflict_status updates on evidence records; major conflict alerts.

**Consumers:** Evidence Aggregator (EC-12); Hypothesis Engine (external consumer).

**Dependencies:** Evidence Registry; Evidence Weighting Engine.

**Failure Handling:** Evidence proceeds without conflict assessment; flag CONFLICT_CHECK_SKIPPED; alert.

**Recovery:** Batch conflict scan on service recovery.

**Performance Expectations:**
- p99 conflict detection latency: < 25ms
- MAJOR conflict alert delivery: < 100ms from detection

---

### 5.10 ES-09 — Evidence Context Service

**Purpose:** Enriches evidence records with investment context from the Observation Engine's context store.

**Inputs:** Evidence candidates at Stage 2 and Stage 7.

**Outputs:** Context-enriched evidence records; context_richness scores.

**Consumers:** All evaluation services.

**Dependencies:** Observation Engine Context Manager; ContextRecord store.

**Failure Handling:** CONTEXT_PARTIAL flag; stub context attached; re-enrichment queued.

**Recovery:** Re-enrichment job on Context Manager recovery.

**Performance Expectations:**
- p99 context enrichment latency: < 20ms
- CONTEXT_PARTIAL rate alert: > 2%

---

### 5.11 ES-10 — Evidence Search Service

**Purpose:** Full-text, structured, and semantic search over the evidence store.

**Inputs:** Search queries from consumers.

**Outputs:** Ranked evidence record lists.

**Consumers:** Hypothesis Engine; Knowledge Engine; Analytics dashboards.

**Dependencies:** Evidence Search Engine (EC-18); Evidence Registry.

**Failure Handling:** On search failure, fall back to unindexed Registry scan (high latency); alert.

**Recovery:** Index rebuild from Registry.

**Performance Expectations:**
- p99 search latency: < 50ms
- Index freshness: < 1 second behind Registry

---

### 5.12 ES-11 — Evidence Retrieval Service

**Purpose:** Structured retrieval of evidence records with quality filtering, PIT semantics, and access control enforcement.

**Inputs:** Structured retrieval requests (entity_id, type, time_range, quality_floor, PIT_timestamp).

**Outputs:** Evidence record lists conforming to request parameters.

**Consumers:** Hypothesis Engine; Knowledge Engine; Risk Engine.

**Dependencies:** Evidence Registry; Evidence Search Engine; access control lists.

**Failure Handling:** Return partial results with PARTIAL_RESULTS flag if sub-query fails.

**Recovery:** Full retrieval on service recovery.

**Performance Expectations:**
- p99 retrieval latency: < 50ms
- PIT query support: mandatory on all retrieval requests

---

### 5.13 ES-12 through ES-17 — Governance, Audit, Analytics, Evolution, Archive, Health

**ES-12 — Evidence Governance Service:** Enforces policies; approves schema changes; conducts governance reviews. p99 policy enforcement latency < 10ms.

**ES-13 — Evidence Audit Service:** Append-only audit trail management. All evidence operations audited. p99 audit write latency < 5ms. Audit failure blocks triggering operation.

**ES-14 — Evidence Analytics Service:** Aggregate analytics over the evidence store — evidence counts, quality distributions, conflict rates, freshness distributions. Used by operational dashboards. Refresh frequency: every 15 minutes.

**ES-15 — Evidence Evolution Service:** Calibration analysis and evidence weight/confidence recalibration. Runs daily. Proposals require governance approval before deployment.

**ES-16 — Evidence Archive Service:** Governs tier transitions (hot → warm → cold), retention enforcement, and legal hold management. Runs on scheduled triggers.

**ES-17 — Evidence Health Service:** Monitors all 16 other services and all 23 components. Publishes health metrics to the IIOS telemetry system. Alerts on: service degradation, quality floor breaches, major conflicts, calibration drift, intake queue overflow.

---
## PART VI — EVIDENCE PROCESSING PIPELINES

### 6.1 Pipeline Architecture Overview

The Evidence Engine operates 15 distinct processing pipelines. Each pipeline is optimised for a specific evidence evaluation pattern.

```
┌──────────────────────────────────────────────────────────────────┐
│              EVIDENCE PROCESSING PIPELINE MAP                    │
│                                                                  │
│  INTAKE PIPELINES                                                │
│  ├── P-01: Real-Time Evidence Pipeline                           │
│  ├── P-02: Streaming Evidence Pipeline                           │
│  └── P-03: Historical Evidence Pipeline                          │
│                                                                  │
│  CROSS-DOMAIN PIPELINES                                          │
│  ├── P-04: Cross-Market Evidence Pipeline                        │
│  ├── P-05: Cross-Asset Evidence Pipeline                         │
│  └── P-06: Multi-Observation Fusion Pipeline                     │
│                                                                  │
│  QUALITY PIPELINES                                               │
│  ├── P-07: Evidence Deduplication Pipeline                       │
│  ├── P-08: Evidence Correlation Pipeline                         │
│  ├── P-09: Evidence Conflict Resolution Pipeline                 │
│  └── P-10: Evidence Validation Pipeline                          │
│                                                                  │
│  ANALYTICAL PIPELINES                                            │
│  ├── P-11: Evidence Ranking Pipeline                             │
│  ├── P-12: Evidence Prioritization Pipeline                      │
│  └── P-13: Evidence Evolution Pipeline                           │
│                                                                  │
│  DISTRIBUTION & STORAGE                                          │
│  ├── P-14: Evidence Distribution Pipeline                        │
│  └── P-15: Evidence Storage Pipeline                             │
└──────────────────────────────────────────────────────────────────┘
```

---

### 6.2 P-01 — Real-Time Evidence Pipeline

**Purpose:** Process market observations in real time — from observation receipt to distributed evidence in under 200ms.

**Trigger:** Real-time market observations from Observation Engine (MKT-PRC-QUOTE, MKT-IDX-SPOT, MKT-DEPTH-L2).

**Latency target:** Observation receipt → Evidence distributed: p99 < 200ms.

**Flow:**

```
Market observation arrives (OQS ≥ 0.75, freshness = FRESH)
       │
       ▼
[ES-01 Evidence Collection Service]
 - OQS gate (≥ 0.75 for real-time path)
 - Priority queue (CRITICAL governance tier observations first)
       │
       ▼
[EC-05 Evidence Builder] — parallel construction of all applicable types
       │
       ▼
[ES-02 Validation] — L1+L2+L4 only (streamlined for real-time)
       │
       ▼
[ES-03 Qualification] — real-time qualification rules
       │
       ▼
[ES-04 Weight Service]  [ES-05 Confidence Service]  (parallel)
       │
       ▼
[ES-07 Correlation Service] — check against last 60s evidence set only
       │
       ▼
[ES-08 Conflict Resolution] — check against active evidence
       │
       ▼
[ES-09 Context Service]
       │
       ▼
[EC-03 Identity Manager] → [EC-01 Registry write] → [EC-22 Audit]
       │
       ▼
[ES-11 Retrieval + ES-10 Index update] (parallel with distribution)
       │
       ▼
[ES-11 Distribution] → Hypothesis Engine, Knowledge Engine
```

**Notes:** Full L3/L5/L6 validation runs asynchronously after distribution for real-time evidence. Any retroactive failure triggers a SUPERSEDE event.

---

### 6.3 P-02 — Streaming Evidence Pipeline

**Purpose:** Process continuous high-frequency observations (tick data, order book updates, intraday indicators) into evidence windows.

**Trigger:** Continuous streaming observation feeds.

**Flow:**

```
Streaming observations → Evidence Collection Service
       │
       ▼
[Rolling Window Accumulator]
 - accumulate observations in sliding time window (configurable: 30s, 1min, 5min)
 - compute window-level evidence:
     * price trend evidence (linear regression over window)
     * volume evidence (window total vs. average)
     * volatility evidence (realised vol over window)
       │
       ▼
[Standard evaluation pipeline: Weight → Confidence → Correlation → Conflict]
       │
       ▼
[Distribution] — time-windowed evidence distributed to consumers
```

**Window types supported:**
- Tumbling windows (non-overlapping)
- Sliding windows (overlapping by configurable step)
- Session windows (grouped by trading session: pre-open, open, afternoon, close)

---

### 6.4 P-03 — Historical Evidence Pipeline

**Purpose:** Evaluate historical observations as evidence for backtesting, research, and historical regime analysis.

**Trigger:** Backtesting requests; historical analysis requests.

**Critical constraint:** All observation queries MUST use PIT semantics: `capture_timestamp ≤ analysis_timestamp`. Look-ahead is a fatal pipeline failure.

**Flow:**

```
Historical analysis request: {entity_id, time_range, as_of_timestamp}
       │
       ▼
[ES-11 Retrieval Service]
 - PIT query: capture_timestamp ≤ as_of_timestamp
 - Retrieve observations for time_range
       │
       ▼
[Historical Evidence Builder]
 - Apply historical derivation rules
 - Reconstruct historical context (regime, session as of as_of_timestamp)
       │
       ▼
[Historical Evaluation Pipeline]
 - Weight, confidence, correlation, conflict — using historical context
       │
       ▼
[Historical Evidence Records]
 - Stored with HISTORICAL_ANALYSIS flag
 - Linked to requesting analysis job
```

---

### 6.5 P-04 — Cross-Market Evidence Pipeline

**Purpose:** Produce cross-market evidence by combining observations across NSE, BSE, SGX Nifty, and global indices.

**Trigger:** Scheduled (every 5 minutes during live trading) and on major cross-market events.

**Flow:**

```
Retrieve: NSE index observation + BSE index observation + SGX Nifty observation
       │
       ▼
[Cross-Market Builder]
 - Compute premium/discount: SGX Nifty vs. NSE previous close
 - Compute NSE-BSE divergence
 - Compute global index correlation context
       │
       ▼
[EVD-XMKT evidence records created]
       │
       ▼
Standard evaluation pipeline → Distribution
```

---

### 6.6 P-05 — Cross-Asset Evidence Pipeline

**Purpose:** Produce cross-asset evidence by combining observations from equity, rates, currency, and commodity domains.

**Trigger:** Scheduled (every 15 minutes) and on significant cross-asset moves.

**Flow:**

```
Retrieve: NIFTY50 + India 10Y yield + USD/INR + Gold + Brent Crude observations
       │
       ▼
[Cross-Asset Builder]
 - Compute equity-rate relationship (rate-equity evidence)
 - Compute risk-off/risk-on signal (equity + gold + bond)
 - Compute energy-market nexus (Brent + energy sector OHLCV)
       │
       ▼
[EVD-XAST evidence records created]
       │
       ▼
Standard evaluation → Distribution
```

---

### 6.7 P-06 — Multi-Observation Fusion Pipeline

**Purpose:** Fuse multiple observations of the same entity from different sources or different time points into a single composite evidence record with higher confidence than any single observation.

**Trigger:** When multiple qualifying observations are available for the same entity and evidence type within the fusion window.

**Flow:**

```
Observations for entity X, type OHLCV-1D from sources: NSE, BSE, yfinance
       │
       ▼
[Fusion Builder]
 - Check for consistency across sources (cross-source agreement)
 - Compute agreement score
 - Compute fused value (weighted average by source trust tier)
       │
       ▼
[EVD-COMP record with fusion_score]
 - n_constituents = 3
 - constituent_observation_ids listed in lineage
 - confidence boosted by cross-source corroboration
```

---

### 6.8 P-07 — Evidence Deduplication Pipeline

**Purpose:** Prevent the same observation from producing duplicate evidence records.

**Trigger:** Runs in-line on every new evidence candidate before identity assignment.

**Flow:**

```
New evidence candidate
       │
       ▼
[Dedup fingerprint computation]
 fingerprint = hash(entity_id + evidence_type + source_observation_id + temporal_bucket)
       │
       ▼
[Bloom filter check]
       │
       ├── Match found: DUPLICATE
       │       │
       │       ▼
       │   Add to corroboration count of primary evidence
       │   Do NOT create new evidence record
       │
       ▼
No match: Continue to identity assignment
```

---

### 6.9 P-08 — Evidence Correlation Pipeline

**Purpose:** Compute and maintain the correlation map between all active evidence items for the same entity.

**Trigger:** On every new evidence arrival; updated continuously during trading hours.

**Flow:**

```
New evidence arrives (entity X)
       │
       ▼
[Retrieve active evidence set for entity X]
       │
       ▼
[Compute pairwise correlations]
 - Source independence check (same upstream source?)
 - Statistical correlation (evidence value time series)
 - Derivation overlap check (same observations used?)
       │
       ▼
[Update independence scores for all affected evidence]
       │
       ▼
[Update effective weights (weight × independence_score)]
```

---

### 6.10 P-09 — Evidence Conflict Resolution Pipeline

**Purpose:** Detect and adjudicate conflicts between evidence records speaking to the same hypothesis in opposing directions.

**Trigger:** On new evidence arrival; on periodic batch scan.

**Flow:**

```
New evidence arrives (entity X, hypothesis Y, direction POSITIVE)
       │
       ▼
[Retrieve active evidence for entity X, hypothesis Y, direction NEGATIVE]
       │
       ▼
[Conflict severity assessment]
 weight_diff = abs(new.effective_weight - opposing.effective_weight)
 confidence_product = new.ECS × opposing.ECS
 severity = MINOR if weight_diff > 0.3 else MODERATE if weight_diff > 0.1 else MAJOR
       │
       ▼
[Set conflict_status on both evidence records]
       │
       ▼
[If MAJOR: notify Hypothesis Engine immediately]
       │
       ▼
[Adjudication attempt]
 - If one evidence has ERS < 0.60 → weight that evidence down; flag RELIABILITY_DOWNWEIGHTED
 - If recency strongly favours one → recency-adjust weight
 - If conflict persists: preserve as ACTIVE CONFLICT
```

---

### 6.11 P-10 through P-15 — Remaining Pipelines

**P-10 — Evidence Validation Pipeline:**
Full 6-level validation run as a batch over all recently admitted evidence. Complements the in-line real-time validation. Runs every 5 minutes.

**P-11 — Evidence Ranking Pipeline:**
Ranks evidence by EQS × weight × freshness × independence for each active hypothesis. Produces ranked evidence lists for Hypothesis Engine consumption. Updates on every evidence change event.

**P-12 — Evidence Prioritization Pipeline:**
Prioritises evidence delivery to consumers based on governance tier (CRITICAL first) and freshness (FRESH first). Manages the distribution queue priority.

**P-13 — Evidence Evolution Pipeline:**
Runs daily. Retrieves 90-day outcome history; computes calibration accuracy by type; identifies weight and confidence drift; produces recalibration proposals for governance approval.

**P-14 — Evidence Distribution Pipeline:**
Manages the delivery of evidence to all subscribed consumers. Enforces quality floors. Confirms delivery for CRITICAL evidence. Records DISTRIBUTE audit events.

**P-15 — Evidence Storage Pipeline:**
Manages write path to Registry, index update, audit write, and lineage record creation as a single transaction. Ensures all-or-nothing storage — partial writes are rolled back.

---
## PART VII — EVIDENCE QUALITY FRAMEWORK

### 7.1 Overview

The Evidence Quality Framework defines how the quality of every evidence record is assessed, expressed, and maintained. Every evidence record must have a composite Evidence Quality Score (EQS) computed from 16 quality dimensions before distribution. The EQS is the primary quality indicator used by consumers to filter their retrieval requests.

---

### 7.2 Quality Dimension Reference

| Dim | Code | Name | Weight | Description |
|---|---|---|---|---|
| D01 | STR | Strength | 0.15 | How strongly does the evidence speak to the hypothesis? |
| D02 | WT | Weight | 0.12 | Assigned analytical weight relative to evidence category |
| D03 | ECS | Confidence | 0.12 | Evidence Confidence Score |
| D04 | ERS | Reliability | 0.10 | Evidence Reliability Score (90-day track record) |
| D05 | IND | Independence | 0.10 | Independence from correlated evidence |
| D06 | CON | Consistency | 0.08 | Consistency with related evidence of same type |
| D07 | FRS | Freshness | 0.08 | How current is the evidence? |
| D08 | TRW | Trustworthiness | 0.07 | Trust tier of underlying observation source |
| D09 | CVG | Coverage | 0.06 | Coverage of required analytical dimensions |
| D10 | CRX | Context Richness | 0.05 | Completeness of attached context record |
| D11 | LIN | Lineage | 0.05 | Completeness and depth of lineage chain |
| D12 | STA | Stability | 0.04 | Historical consistency of this evidence type's evaluation |
| D13 | IMP | Importance | 0.04 | Governance tier weight of the entity and evidence type |
| D14 | FUS | Fusion Score | 0.03 | If composite: coherence of constituent evidence |
| D15 | CFT | Conflict Status | 0.02 | Penalty for active conflicts |
| D16 | OBS | Observation Quality | 0.02 | Inherited from underlying OQS |

**Weights sum to 1.13 raw; normalised (÷1.13) to sum to 1.0.**

---

### 7.3 Quality Dimension Specifications

**D01 — Strength**

Strength measures how decisively the evidence speaks to the hypothesis domain it belongs to. It is computed from the signal-to-noise ratio in the underlying observations:

$$\text{STR} = \frac{|\text{signal value}| - \text{noise\_floor}(\text{type})}{\text{signal\_range}(\text{type})}$$

Clamped to [0.0, 1.0]. For example: if a 14-day RSI reading of 72 is "strong" evidence of overbought condition relative to a neutral reading of 50 and a noise floor of ±5, strength would be computed as (72 − 55) / (100 − 55) ≈ 0.38. A reading of 85 would score 0.67.

**D02 — Weight**

The analytically assigned weight (from ES-04) expressed as a quality dimension. Weight reflects the prior belief about this evidence type's relevance to its domain.

$$\text{WT} = \text{assigned\_weight} \in [0.0, 1.0]$$

**D03 — Confidence (ECS)**

The Evidence Confidence Score from ES-05.

$$\text{ECS} = f(\text{source OQS},\ \text{corroboration},\ \text{derivation complexity},\ \text{historical accuracy})$$

**D04 — Reliability (ERS)**

The Evidence Reliability Score from ES-06.

$$\text{ERS} = \frac{\text{confirmed correct evidence outcomes}}{\text{total evidence outcomes (rolling 90 days)}}$$

**D05 — Independence**

$$\text{IND} = 1.0 - \max_{j \neq i}(\text{correlation}(e_i, e_j)) \text{ for active evidence set}$$

High pairwise correlation → low independence → lower effective contribution to evidence body.

**D06 — Consistency**

Consistency measures whether this evidence record is consistent with recent prior evidence of the same type for the same entity:

$$\text{CON} = 1.0 - \frac{|\text{current value} - \text{rolling mean}|}{\text{rolling std dev} \times \text{k\_sigma}}$$

where k_sigma = 3 (flag inconsistency beyond 3 standard deviations).

**D07 — Freshness**

$$\text{FRS}(t) = \max\left(0,\ 1 - \frac{t - t_{\text{evidence}}}{\text{SLA}(\text{type})}\right)$$

Evidence freshness decays with time since evidence_timestamp.

**D08 — Trustworthiness**

Inherited from the trust tier of the source observation's source:

| Trust tier | TRW score |
|---|---|
| AUTHORITATIVE | 1.00 |
| RELIABLE | 0.85 |
| STANDARD | 0.70 |
| PROVISIONAL | 0.55 |
| UNRELIABLE | 0.30 |

**D09 — Coverage**

The proportion of the evidence template's required analytical dimensions that are populated:

$$\text{CVG} = \frac{\text{populated required dimensions}}{\text{total required dimensions}}$$

**D10 — Context Richness**

$$\text{CRX} = \frac{\text{context fields populated}}{\text{total context fields}}$$

Full context (regime, session, market state, VIX, events, calendar) = 1.0.

**D11 — Lineage Completeness**

$$\text{LIN} = \frac{\text{lineage depth achieved}}{\text{target lineage depth for type}}$$

A lineage tracing back from evidence → observation → information → raw source = 1.0. Evidence with incomplete lineage scores < 1.0.

**D12 — Stability**

Stability measures the historical variance of this evidence type's evaluation outcomes:

$$\text{STA} = 1 - \frac{\text{historical ECS standard deviation for type}}{\text{ECS range}}$$

Consistently reliable evidence (low historical variance) scores high stability.

**D13 — Importance**

$$\text{IMP} = f(\text{governance\_tier}) = \begin{cases} 1.00 & \text{CRITICAL} \\ 0.80 & \text{HIGH} \\ 0.60 & \text{MEDIUM} \\ 0.40 & \text{LOW} \end{cases}$$

**D14 — Fusion Score**

For composite evidence: coherence score of all constituent evidence items. For atomic evidence: D14 = 1.0 by default.

$$\text{FUS} = \frac{\sum_{i} w_i \cdot d_i}{\sum_{i} w_i} \quad \text{(weighted agreement across constituents)}$$

**D15 — Conflict Status Penalty**

$$\text{CFT} = \begin{cases} 1.0 & \text{conflict\_status = NONE} \\ 0.7 & \text{conflict\_status = MINOR} \\ 0.4 & \text{conflict\_status = MODERATE} \\ 0.1 & \text{conflict\_status = MAJOR} \end{cases}$$

**D16 — Inherited Observation Quality**

$$\text{OBS} = \text{mean}(\text{OQS of constituent observations})$$

---

### 7.4 Composite EQS Formula

$$\text{EQS} = \frac{\sum_{i=1}^{16} w_i \cdot d_i}{\sum_{i=1}^{16} w_i}$$

EQS ∈ [0.0, 1.0].

---

### 7.5 EQS Quality Tier Boundaries

| Tier | EQS Range | Operational Meaning |
|---|---|---|
| EXCELLENT | [0.90, 1.00] | All dimensions healthy; highest analytical value |
| GOOD | [0.75, 0.90) | Most dimensions healthy; suitable for all analytical use |
| ACCEPTABLE | [0.60, 0.75) | Some dimensions degraded; use with quality awareness |
| MARGINAL | [0.40, 0.60) | Multiple dimensions degraded; not for high-stakes hypotheses |
| POOR | [0.00, 0.40) | Widespread quality failure; quarantine; do not use |

---

### 7.6 Evidence Strength vs. Evidence Quality

A critical distinction:

**Evidence Strength** (D01) measures how decisively the evidence speaks to its hypothesis — a very strong RSI reading is high-strength evidence of momentum.

**Evidence Quality** (EQS) measures how trustworthy and well-evaluated the evidence is — even a high-strength signal can be low-quality if it comes from an unreliable source with poor lineage.

Both dimensions are independently important. A high-strength, low-quality evidence item should not override a moderate-strength, high-quality evidence item.

---

### 7.7 EQS Monitoring Reference

| Metric | Alert threshold |
|---|---|
| Mean EQS by evidence category | < 0.75 for any CRITICAL category |
| POOR evidence rate | > 2% of daily evidence |
| MAJOR conflict rate | > 1% of CRITICAL entity evidence |
| Independence floor breach | Mean independence score < 0.60 for any entity |
| Freshness degradation | Any CRITICAL evidence STALE |
| Confidence calibration error | RMSE > 0.05 between ECS and historical outcomes |

---
## PART VIII — EVIDENCE GOVERNANCE

### 8.1 Governance Philosophy

Evidence governance defines the policies, responsibilities, and controls that ensure evidence records are managed as analytical assets with institutional-grade integrity. The Evidence Engine is the second-to-last firewall against analytical error — only observations are below it. Governance failures here propagate into every layer above.

---

### 8.2 Governance Dimension Reference

| Dim | Code | Name | Description |
|---|---|---|---|
| G01 | OWN | Ownership | Each evidence type has a designated Domain Owner |
| G02 | NAM | Naming Standards | Canonical codes, field naming conventions |
| G03 | MTD | Metadata Standards | Mandatory metadata for every evidence record |
| G04 | VER | Versioning | Immutable evidence; all changes create new versions |
| G05 | RET | Retention | Minimum retention periods by evidence category |
| G06 | CPL | Compliance | Regulatory requirements by evidence category |
| G07 | SEC | Security | Classification and encryption requirements |
| G08 | INT | Integrity | Hash verification; tamper detection |
| G09 | LIN | Lineage | End-to-end traceability requirements |
| G10 | AUD | Auditability | Append-only audit trail for all operations |
| G11 | REV | Review | Governance review cycle |
| G12 | APP | Approval | Change approval process |
| G13 | ESC | Escalation | Conflict and quality escalation procedures |
| G14 | REC | Recovery | Evidence recovery after failure |
| G15 | MON | Monitoring | Continuous quality and health monitoring |
| G16 | QCT | Quality Control | Minimum quality standards |

---

### 8.3 Governance Tier Matrix

| Evidence Category | Gov Tier | Justification |
|---|---|---|
| EVD-MKT (CRITICAL types: price, depth) | CRITICAL | Drives real-time execution decisions |
| EVD-RISK | CRITICAL | Feeds kill-switch and risk controls |
| EVD-PORT | CRITICAL | Portfolio state; regulatory reporting |
| EVD-CORP (corporate actions, dividends) | CRITICAL | Affects position valuations; legal compliance |
| EVD-FIN | HIGH | Fundamental investment analysis inputs |
| EVD-MACRO (monetary policy) | HIGH | System-wide pricing model inputs |
| EVD-TECH | HIGH | Strategy decision inputs |
| EVD-FUND | HIGH | Valuation model inputs |
| EVD-BEH | HIGH | Smart money flow indicators |
| EVD-VOL | HIGH | Risk regime indicators |
| EVD-SECT | MEDIUM | Sector rotation context |
| EVD-SENT | MEDIUM | Supplementary context |
| EVD-LIQ | MEDIUM | Market microstructure context |
| EVD-ALT | MEDIUM | Alternative signal inputs |
| EVD-AI | MEDIUM | Model output evidence; subject to model risk |
| EVD-FLOW | MEDIUM | Order flow context |
| EVD-REL | MEDIUM | Relationship context |
| EVD-EVT | MEDIUM | Event context |
| EVD-XAST | HIGH | Cross-asset regime inputs |
| EVD-XMKT | HIGH | Cross-market context |
| EVD-COMP | Inherits highest constituent tier | |
| EVD-HIST | Inherits from original type | |

---

### 8.4 Ownership Responsibility Matrix

| Role | Responsibilities |
|---|---|
| Domain Owner | Owns all evidence types in their domain. Approves schema changes, weight changes, and governance classification changes. Signs off on retention policies. |
| Evidence Steward | Day-to-day quality monitoring. Escalates quality issues. Conducts monthly calibration reviews. Reports to Domain Owner. |
| Evidence Engineer | Implements and maintains evidence pipelines. Deploys approved schema changes. |
| Governance Manager | Enforces governance policies system-wide. Conducts governance reviews. Issues compliance reports. Escalates violations. |
| Audit Manager | Maintains audit trail. Responds to audit requests. Alerts on anomalous access patterns. |
| Evidence Consumer | Authorised consumer of evidence via registered access profile. Reports quality anomalies. |

---

### 8.5 Naming Standards

**Evidence type code format:** `{CATEGORY_CODE}-{DOMAIN_CODE}-{SPECIFIC_CODE}`

Examples:
- `EVD-MKT-TREND-1D` — Market Trend Evidence, 1-Day
- `EVD-CORP-EARN-Q` — Corporate Earnings Evidence, Quarterly
- `EVD-MACRO-MON-REPO` — Macroeconomic Monetary Repo Rate Evidence
- `EVD-TECH-MOM-RSI14` — Technical Momentum Evidence, 14-day RSI
- `EVD-RISK-DD-CURRENT` — Risk Drawdown Evidence, Current
- `EVD-COMP-CONF-BULL` — Composite Confluence Evidence, Bullish

**Evidence ID format:** `EVD-{CAT}-{TYPE}-{YYYYMMDD}-{SEQ:08d}`

**Field naming convention:**
- Scores: `xxx_score` in [0.0, 1.0]
- Weights: `xxx_weight` in [0.0, 1.0]
- Timestamps: `xxx_timestamp` in UTC ISO 8601
- Counts: `xxx_count`
- Flags: `is_xxx` (boolean), `has_xxx` (boolean)
- Status codes: UPPERCASE_UNDERSCORE

---

### 8.6 Metadata Standards

Every evidence record MUST contain:

| Field | Type | Required |
|---|---|---|
| evidence_id | string | MANDATORY |
| evidence_type | string | MANDATORY |
| category | string | MANDATORY |
| entity_refs[] | array | MANDATORY (≥ 1 entity) |
| supporting_observations[] | array | MANDATORY (≥ 1 observation) |
| evidence_timestamp | datetime UTC | MANDATORY |
| creation_timestamp | datetime UTC | MANDATORY |
| storage_timestamp | datetime UTC | MANDATORY |
| context_id | string | MANDATORY |
| weight | float [0,1] | MANDATORY |
| confidence_score | float [0,1] | MANDATORY |
| reliability_score | float [0,1] | MANDATORY |
| independence_score | float [0,1] | MANDATORY |
| eqs | float [0,1] | MANDATORY |
| quality_tier | string | MANDATORY |
| conflict_status | string | MANDATORY |
| conflict_refs[] | array | CONDITIONAL |
| lineage_id | string | MANDATORY |
| version_number | integer ≥ 1 | MANDATORY |
| governance_tier | string | MANDATORY |
| status | string | MANDATORY |
| schema_version | string | MANDATORY |

---

### 8.7 Retention Policy Reference

| Category | Minimum retention | Archive after | Legal hold? |
|---|---|---|---|
| EVD-MKT intraday | 90 days | 30 days hot | No |
| EVD-MKT daily | 36 months | 12 months warm | No |
| EVD-CORP corporate actions | 84 months | 84 months | Yes |
| EVD-FIN | 84 months | 36 months warm | No |
| EVD-RISK | 36 months | 12 months warm | Yes |
| EVD-PORT | 7 years | 7 years | Yes |
| EVD-MACRO | 120 months | 60 months | No |
| EVD-TECH | 36 months | 18 months | No |
| EVD-SENT | 12 months | 12 months | No |
| EVD-ALT | 24 months | 24 months | No |
| EVD-AI | 36 months | 24 months | No |
| EVD-HIST | Same as original category | | |
| Lineage records | PERMANENT | Never archived | Permanent |
| Audit records | 7 years minimum | 7 years | Yes |

---

### 8.8 Compliance Requirements

| Requirement | Affected categories | Control |
|---|---|---|
| SEBI OATS audit trail | EVD-PORT, EVD-RISK (when linked to trades) | Tamper-evident audit trail; 5-year minimum |
| PMLA lineage | All CRITICAL evidence | End-to-end lineage to source observable |
| Data localisation | All India-market evidence | Stored on India-resident infrastructure |
| Model risk governance | EVD-AI | Model ID, version, training cutoff in lineage |

---

### 8.9 Security Classification

| Level | Description | Evidence categories |
|---|---|---|
| PUBLIC | Non-sensitive | None (all evidence is at least INTERNAL) |
| INTERNAL | IIOS-internal use | All MEDIUM-tier evidence |
| RESTRICTED | Role-based access | HIGH-tier evidence; full audit on all reads |
| CONFIDENTIAL | Named consumer only; encrypted at rest | CRITICAL-tier evidence |

All CONFIDENTIAL evidence is encrypted at rest using AES-256 minimum.

---

### 8.10 Governance Review Cycle

| Review | Frequency | Output |
|---|---|---|
| Quality review | Weekly | Quality trend report; remediation actions |
| Calibration review | Monthly | Weight and confidence calibration assessment |
| Schema review | Quarterly | Schema change approvals |
| Retention audit | Annually | Retention policy confirmation |
| Security review | Annually | Classification updates |
| Full governance audit | Annually | Complete governance health assessment |

---
## PART IX — EVIDENCE CONSTITUTION

### 9.1 Purpose

The Evidence Constitution defines the non-negotiable architectural rules for all evidence in the IIOS. These rules may not be bypassed by any component, service, consumer, or operational procedure. Constitutional violations are architectural failures — not bugs to be fixed pragmatically, but invariants to be restored immediately.

---

### 9.2 Category EC-A — Identity Rules

**EC-A-001** Every evidence record MUST have a globally unique canonical evidence_id assigned by the Identity Manager at the moment of creation.

**EC-A-002** The evidence_id MUST conform to the canonical format: `EVD-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`.

**EC-A-003** A retired evidence_id MUST NOT be reused. Retired IDs are permanently reserved.

**EC-A-004** Every evidence record MUST reference at least one valid entity via entity_refs[].

**EC-A-005** All entity_ids in entity_refs[] MUST be resolvable in the Entity Engine at the time the evidence is created.

**EC-A-006** Every evidence record MUST declare an evidence type code. The code MUST be registered in the Evidence Catalog.

**EC-A-007** Every evidence record MUST declare its category (one of the 22 concrete evidence categories).

**EC-A-008** Every evidence record MUST reference at least one supporting observation via supporting_observations[].

**EC-A-009** All observation_ids in supporting_observations[] MUST be resolvable in the Observation Registry.

**EC-A-010** Two evidence records may share no observation_ids as primary constituents (deduplication prevents duplicate primary evidence).

---

### 9.3 Category EC-B — Validity Rules

**EC-B-001** Evidence MUST NOT be created from observations with OQS below the minimum quality floor (default: 0.60).

**EC-B-002** Evidence MUST NOT be created from EXPIRED observations.

**EC-B-003** Evidence MUST pass all 6 validation levels before storage in the Registry.

**EC-B-004** Evidence with validation_status = FAIL MUST be quarantined. Quarantined evidence MUST NOT be distributed.

**EC-B-005** Evidence MUST have an evidence_timestamp that is not in the future.

**EC-B-006** Evidence MUST have an evidence_timestamp that is ≥ the latest observation_timestamp of its supporting observations.

**EC-B-007** The derivation of an evidence record from its supporting observations MUST be consistent with the derivation rules in the Evidence Catalog.

**EC-B-008** Evidence MUST be qualified (semantically, not just structurally) before proceeding to weight assignment.

**EC-B-009** Evidence with EQS < 0.25 (absolute floor) MUST be quarantined. It MUST NOT be distributed to any operational consumer.

**EC-B-010** Evidence MUST NOT contain any claim that is not directly derivable from its supporting observations. No hypothetical or inferred content.

**EC-B-011** Evidence of type EVD-AI MUST declare the model_id, model_version, and training_cutoff_date in its lineage record.

**EC-B-012** Evidence derived from a stale AI model (training_cutoff_date > MODEL_STALENESS_THRESHOLD days ago) MUST be flagged with MODEL_STALE. Consumers must be informed.

---

### 9.4 Category EC-C — Lineage Rules

**EC-C-001** Every evidence record MUST have a complete, traceable lineage chain from evidence → observations → information → raw source.

**EC-C-002** Lineage records MUST be created before the evidence record is stored in the Registry. Evidence without lineage MUST NOT be stored.

**EC-C-003** Lineage records are PERMANENT. They MUST NOT be archived, retired, or deleted.

**EC-C-004** The lineage of a composite evidence record MUST list all constituent evidence_ids and their respective observation_ids.

**EC-C-005** The lineage chain MUST include the derivation function used at each step.

**EC-C-006** When an evidence record is versioned (creating a new version), the new version's lineage MUST extend the previous version's lineage — not replace it.

**EC-C-007** Lineage traversal queries MUST be supported: "show the full provenance of evidence EVD-xxx-yyy-zzz". This capability MUST be always-on.

**EC-C-008** Lineage MUST capture the evidence_timestamp and the capture_timestamp of each constituent observation, enabling PIT audit of the evidence's temporal validity.

**EC-C-009** Lineage MUST record which ContextRecord was active at evidence creation time.

**EC-C-010** Lineage MUST capture the version of the Evidence Catalog schema used to derive the evidence type.

---

### 9.5 Category EC-D — Traceability Rules

**EC-D-001** Every evidence record MUST support the query "show me all decisions that were influenced by this evidence" — reverse traceability from evidence to decision.

**EC-D-002** The Evidence Audit Trail MUST record all access events for RESTRICTED and CONFIDENTIAL evidence — every read, not just writes.

**EC-D-003** All weight assignments, confidence computations, and quality scores MUST be recorded with their derivation rationale in the audit trail.

**EC-D-004** All calibration changes (weight updates, confidence recalibrations) MUST be logged with the evidence records they affect.

**EC-D-005** The audit trail MUST be append-only and tamper-evident.

**EC-D-006** Audit records MUST be retained for a minimum of 7 years.

**EC-D-007** Bulk access to evidence (e.g., backtesting retrievals of thousands of records) MUST be logged as a single access event with the query parameters, not as individual record reads.

**EC-D-008** Failed access attempts (unauthorised reads) MUST be logged with the same completeness as successful reads.

**EC-D-009** The identity of the requesting consumer MUST be captured in every audit record.

**EC-D-010** All conflict detection and resolution events MUST be recorded in the audit trail.

---

### 9.6 Category EC-E — Confidence and Weight Rules

**EC-E-001** Every evidence record MUST have a computed weight before distribution. Evidence without a weight MUST NOT be distributed.

**EC-E-002** Every evidence record MUST have a computed ECS before distribution. Evidence without an ECS MUST NOT be distributed.

**EC-E-003** Every evidence record MUST have a computed ERS before distribution (provisional ERS is permitted if insufficient history exists, but must be flagged).

**EC-E-004** The EQS MUST be computed from all 16 quality dimensions before distribution.

**EC-E-005** Weights MUST be calibrated at least monthly. Weight calibration updates MUST be governance-approved.

**EC-E-006** ECS calibration MUST be validated quarterly. An ECS that is systematically overconfident (historical accuracy < ECS − 0.05) MUST trigger recalibration.

**EC-E-007** Correlated evidence MUST have its effective weight reduced by the Independence Engine. Treating correlated evidence as independent is prohibited.

**EC-E-008** No evidence from an UNRELIABLE source (ERS < 0.50 for 90 days) MUST be distributed without a RELIABILITY_WARNING flag.

**EC-E-009** Evidence weights for the same type MUST be consistent across entities in the same regime — differential weighting for the same type in the same regime is not permitted without governance approval.

**EC-E-010** The Independence Engine MUST be always-on. No evidence pipeline may bypass independence scoring.

**EC-E-011** Weights MUST NOT be hand-coded for production pipelines. All weights MUST be derived from the Evidence Catalog and modulated by calibrated modifiers.

**EC-E-012** A weight of exactly 0.0 or exactly 1.0 is only permitted for evidence types that the Catalog explicitly classifies as binary (fully disqualified or absolutely certain). Continuous types MUST have weights in (0.0, 1.0).

---

### 9.7 Category EC-F — Independence and Conflict Rules

**EC-F-001** The pairwise independence of all active evidence for the same entity and hypothesis context MUST be assessed before the evidence body is presented to the Hypothesis Engine.

**EC-F-002** Two evidence records derived from the same observation (or overlapping observation sets) MUST be flagged as CORRELATED and their combined effective weight must not exceed the weight of a single independent evidence item.

**EC-F-003** Evidence from different sources that ultimately derive from the same data vendor MUST be flagged as POTENTIALLY_CORRELATED.

**EC-F-004** A conflict (opposing evidence for the same hypothesis) MUST be detected within 30 seconds of the conflicting evidence being stored.

**EC-F-005** A MAJOR conflict MUST be reported to all subscribed consumers (Hypothesis Engine, Knowledge Engine, Evidence Health Service) within 100ms of detection.

**EC-F-006** Conflicts MUST NOT be silently resolved. Both the supporting and contradicting evidence records MUST remain ACTIVE in the Registry with conflict_status set.

**EC-F-007** Only the Conflict Manager may adjudicate a conflict. Adjudication reduces the effective weight of one side but does not remove either evidence record.

**EC-F-008** An adjudicated conflict MUST be recorded in the audit trail with the adjudication rationale.

**EC-F-009** Evidence that has been downweighted by adjudication MUST carry an ADJUDICATED flag and the reason.

**EC-F-010** The Hypothesis Engine MUST be informed of all active MAJOR conflicts affecting its active hypotheses. The Evidence Engine MUST maintain a subscription mechanism for this purpose.

**EC-F-011** A MINOR conflict that is not adjudicated within 24 hours MUST be escalated to MODERATE status.

**EC-F-012** A MODERATE conflict that is not adjudicated within 72 hours MUST be escalated to MAJOR status.

**EC-F-013** Conflict escalation events MUST be recorded in the audit trail.

**EC-F-014** The Conflict Manager MUST provide the reason for every adjudication decision, enabling audit review.

**EC-F-015** Evidence in MAJOR CONFLICT status for more than 7 days without resolution MUST trigger a governance review.

---

### 9.8 Category EC-G — Governance Rules

**EC-G-001** Every evidence type MUST have a designated Domain Owner. Evidence types without an owner MUST NOT be activated.

**EC-G-002** Access control MUST be enforced at the Evidence Retrieval Service. No evidence MUST be returned to an unauthorised consumer.

**EC-G-003** All CONFIDENTIAL evidence MUST be encrypted at rest with AES-256 minimum.

**EC-G-004** All evidence schema changes MUST be reviewed and approved by the Domain Owner before deployment.

**EC-G-005** Evidence MUST NOT be permanently deleted before its retention period has elapsed.

**EC-G-006** Evidence under a legal hold MUST NOT be archived or retired regardless of retention expiry.

**EC-G-007** A governance review MUST be triggered when: a new evidence type is added; a source's trust tier changes; a schema migration is required; ERS drops below 0.65 for any CRITICAL evidence type; a retention period changes.

**EC-G-008** Weight recalibration proposals from the Evolution Manager MUST be reviewed and approved by the Domain Owner before deployment.

**EC-G-009** All governance decisions MUST be recorded in Governance Decision Records (GDRs).

**EC-G-010** Every quarterly governance audit MUST assess EQS calibration accuracy for all CRITICAL and HIGH evidence types.

---

### 9.9 Category EC-H — Historical Preservation Rules

**EC-H-001** Historical evidence MUST support PIT query semantics: filter by `creation_timestamp ≤ analysis_timestamp`. Look-ahead is a fatal architectural failure.

**EC-H-002** Evidence provided to backtesting pipelines MUST use PIT-safe evidence retrieval. No backtesting pipeline may query evidence by evidence_timestamp alone.

**EC-H-003** All superseded versions of evidence MUST be preserved permanently in the History Manager.

**EC-H-004** Survivorship bias correction MUST be applied to historical evidence streams: evidence for retired entities MUST remain accessible.

**EC-H-005** Evidence recalibrations (new versions from Evolution Manager) MUST record the original weight and confidence at each historical point. The original historical evaluation must remain reconstructable.

**EC-H-006** Regime annotations MUST be preserved with all historical evidence to enable regime-aware historical analysis.

**EC-H-007** The Evidence Engine MUST support evidence replay — re-evaluating historical observations through current derivation and evaluation rules, producing a refreshed view of historical evidence quality.

**EC-H-008** Outcome records (hypothesis confirmed/refuted by evidence) MUST be preserved permanently and linked to the evidence records that supported the hypothesis.

**EC-H-009** The History Manager MUST provide the ability to reconstruct the complete body of evidence that existed at any historical timestamp. This capability MUST be always-on.

**EC-H-010** Historical evidence retrieval for the same entity and time window MUST produce deterministic results — given the same query parameters, the same evidence records MUST always be returned.

---
## PART X — EVIDENCE READINESS CHECKLIST

### 10.1 Purpose

The Evidence Readiness Checklist defines the minimum criteria that every evidence record MUST satisfy before it is designated ACTIVE and released for consumption. The checklist has 15 sections. An evidence record fails readiness if any MANDATORY criterion in any section is not met. Failed records are held in QUARANTINE pending remediation.

---

### 10.2 Section R01 — Evidence Created

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R01-01 | Evidence record has evidence_id | Non-null, canonical format | MANDATORY |
| R01-02 | evidence_id assigned by Identity Manager | Not self-assigned | MANDATORY |
| R01-03 | Evidence type is registered in Catalog | type resolves in Evidence Catalog | MANDATORY |
| R01-04 | At least one supporting observation linked | supporting_observations[] non-empty | MANDATORY |
| R01-05 | All supporting observations resolvable | All obs_ids resolve in Observation Registry | MANDATORY |
| R01-06 | Creation timestamp set | creation_timestamp non-null, UTC | MANDATORY |

---

### 10.3 Section R02 — Validated

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R02-01 | L1 structural validation passed | All mandatory fields present and typed correctly | MANDATORY |
| R02-02 | L2 referential validation passed | All obs_ids resolvable; source_ref valid | MANDATORY |
| R02-03 | L3 derivation validity passed | Type consistent with derivation rules | MANDATORY |
| R02-04 | L4 temporal consistency passed | evidence_timestamp ≥ max(obs timestamps) | MANDATORY |
| R02-05 | L5 context validity passed | context_id resolves | MANDATORY |
| R02-06 | L6 schema conformance passed | Conforms to Catalog schema version | MANDATORY |
| R02-07 | validation_status = PASS or WARN | Not FAIL | MANDATORY |

---

### 10.4 Section R03 — Weighted

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R03-01 | weight computed | Non-null, in [0.0, 1.0] | MANDATORY |
| R03-02 | Weight derivation recorded | weight_derivation_record non-null | MANDATORY |
| R03-03 | Regime modifier applied | Context-sensitive weight adjustment confirmed | MANDATORY |
| R03-04 | Source quality modifier applied | Source trust tier reflected in weight | MANDATORY |
| R03-05 | Weight is not default | DEFAULT_WEIGHT flag absent for non-fallback cases | RECOMMENDED |

---

### 10.5 Section R04 — Confidence Assigned

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R04-01 | ECS computed | confidence_score non-null, in [0.0, 1.0] | MANDATORY |
| R04-02 | ECS derivation recorded | confidence_derivation non-null | MANDATORY |
| R04-03 | Corroboration considered | corroboration_modifier applied (or AWAITING flag) | MANDATORY |
| R04-04 | ERS used in ECS computation | ERS referenced | MANDATORY |
| R04-05 | CONFIDENCE_PARTIAL flag absent unless justified | No unjustified partial confidence | RECOMMENDED |

---

### 10.6 Section R05 — Context Assigned

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R05-01 | context_id present | Non-null | MANDATORY |
| R05-02 | ContextRecord resolvable | context_id resolves to valid ContextRecord | MANDATORY |
| R05-03 | Regime assigned | context.regime non-null | MANDATORY |
| R05-04 | Session context assigned | context.session non-null | MANDATORY |
| R05-05 | Market state captured | context.market_state non-null | MANDATORY |
| R05-06 | Context timestamp consistent | context.timestamp within 60s of evidence_timestamp | MANDATORY |
| R05-07 | CONTEXT_PARTIAL flag reviewed | If present, re-enrichment scheduled | MANDATORY |

---

### 10.7 Section R06 — Conflict Checked

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R06-01 | Conflict check executed | CONFLICT_CHECK_SKIPPED flag absent | MANDATORY |
| R06-02 | conflict_status field set | One of NONE/MINOR/MODERATE/MAJOR | MANDATORY |
| R06-03 | MAJOR conflict triggers alert | Hypothesis Engine notified | MANDATORY |
| R06-04 | Conflict refs recorded | conflict_refs[] populated if conflict_status ≠ NONE | MANDATORY |
| R06-05 | Evidence not suppressed by conflict | Both conflicting evidence records remain ACTIVE | MANDATORY |

---

### 10.8 Section R07 — Correlation Checked

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R07-01 | Independence check executed | INDEPENDENCE_CHECK_SKIPPED absent | MANDATORY |
| R07-02 | independence_score computed | Non-null, in [0.0, 1.0] | MANDATORY |
| R07-03 | Effective weight adjusted | effective_weight = weight × independence_score | MANDATORY |
| R07-04 | CORRELATED flag set if applicable | Correctly applied | MANDATORY |
| R07-05 | Correlation map updated | Active evidence correlation map reflects new evidence | RECOMMENDED |

---

### 10.9 Section R08 — Stored

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R08-01 | Stored in Evidence Registry | Retrievable by evidence_id | MANDATORY |
| R08-02 | storage_timestamp set | Non-null | MANDATORY |
| R08-03 | version_number = 1 (new evidence) | Confirmed | MANDATORY |
| R08-04 | status = ACTIVE | Confirmed | MANDATORY |
| R08-05 | Storage is atomic | Evidence + lineage + audit committed together | MANDATORY |
| R08-06 | Physical integrity hash set | integrity_hash non-null | MANDATORY |

---

### 10.10 Section R09 — Indexed

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R09-01 | Primary index entry created | Retrievable by evidence_id | MANDATORY |
| R09-02 | Entity index entry created | Retrievable by entity_id | MANDATORY |
| R09-03 | Type index entry created | Retrievable by evidence_type | MANDATORY |
| R09-04 | Temporal index entry created | Retrievable by evidence_timestamp range | MANDATORY |
| R09-05 | PIT index entry created | Retrievable by creation_timestamp ≤ query_time | MANDATORY |
| R09-06 | Hypothesis relevance index | Retrievable by hypothesis_relevance[] | RECOMMENDED |

---

### 10.11 Section R10 — Versioned

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R10-01 | version_number assigned | ≥ 1 | MANDATORY |
| R10-02 | Version chain intact | If v > 1: previous version in SUPERSEDED state | MANDATORY |
| R10-03 | Version reason recorded | For v > 1: reason for new version in lineage | MANDATORY |
| R10-04 | Version chain is linear | No branching | MANDATORY |
| R10-05 | All versions preserved | No versions deleted or overwritten | MANDATORY |

---

### 10.12 Section R11 — Governed

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R11-01 | Domain owner resolvable | Evidence type has active Domain Owner | MANDATORY |
| R11-02 | governance_tier assigned | Non-null | MANDATORY |
| R11-03 | Access control active | Retrieval constraints enforced | MANDATORY |
| R11-04 | Retention policy assigned | Retention schedule resolvable for category | MANDATORY |
| R11-05 | Legal hold check passed | Legal hold applied if applicable | MANDATORY |
| R11-06 | Security classification assigned | Non-null | MANDATORY |

---

### 10.13 Section R12 — Audited

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R12-01 | CREATE audit record exists | One CREATE event in audit trail | MANDATORY |
| R12-02 | Audit record has actor | system_id or creator_pipeline non-null | MANDATORY |
| R12-03 | Audit record is tamper-evident | integrity_hash on audit record | MANDATORY |
| R12-04 | Audit trail is append-only | No modification to existing audit records | MANDATORY |
| R12-05 | Audit retention ≥ 7 years | Confirmed | MANDATORY |

---

### 10.14 Section R13 — Historically Preserved

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R13-01 | Lineage record created and permanent | lineage_id resolves; lineage_is_permanent = true | MANDATORY |
| R13-02 | PIT query support confirmed | Evidence excluded when creation_timestamp > query_time | MANDATORY |
| R13-03 | Regime annotation present | Context.regime non-null in ContextRecord | MANDATORY |
| R13-04 | Survivorship bias flag set | is_entity_active flag recorded | MANDATORY |
| R13-05 | Evidence outcome linkable | outcome_linkage field available for future outcome records | RECOMMENDED |

---

### 10.15 Section R14 — Traceable

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R14-01 | Full lineage traversal available | Evidence → obs → info → source chain traversable | MANDATORY |
| R14-02 | Derivation steps documented | All derivation functions recorded in lineage | MANDATORY |
| R14-03 | Weight derivation recorded | weight_derivation_record complete | MANDATORY |
| R14-04 | Confidence derivation recorded | confidence_derivation complete | MANDATORY |
| R14-05 | Forward traceability available | Decision linkage queryable (async) | RECOMMENDED |

---

### 10.16 Section R15 — Ready for Hypothesis Engine

| # | Criterion | PASS condition | Mandatory? |
|---|---|---|---|
| R15-01 | EQS ≥ consumer's quality floor | EQS ≥ Hypothesis Engine's registered quality floor | MANDATORY |
| R15-02 | Freshness tier ≠ EXPIRED | Evidence is not expired | MANDATORY |
| R15-03 | Conflict status visible | conflict_status field correctly set | MANDATORY |
| R15-04 | Independence score declared | independence_score non-null | MANDATORY |
| R15-05 | PIT semantics verified | Evidence correctly excluded for prior PIT queries | MANDATORY |
| R15-06 | Evidence format compliant | Conforms to Hypothesis Engine input contract | MANDATORY |
| R15-07 | Distribution record created | DISTRIBUTE audit event written | MANDATORY |

---

### 10.17 Multi-Level Readiness Matrix

| Use case | R01 | R02 | R03 | R04 | R05 | R06 | R07 | R08 | R09 | R10 | R11 | R12 | R13 | R14 | R15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Real-time hypothesis evaluation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| Backtesting | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Knowledge Engine input | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Risk management | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — |
| Regulatory compliance | ✅ | ✅ | — | — | — | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Strategy research | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | — |
| Audit investigation | ✅ | — | — | — | — | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |

Legend: ✅ = required; — = not required for this use case

---
## SUPPLEMENT A — EVIDENCE TAXONOMY

### A.1 Purpose

The Evidence Taxonomy is the complete hierarchical classification of all evidence types in the IIOS. Each entry specifies its canonical code, parent category, evidence temporal nature, derivation level, and minimum EQS requirement.

---

### A.2 Primary Taxonomy Table

| Type code | Name | Category | Temporal | Derivation | Min EQS |
|---|---|---|---|---|---|
| EVD-MKT-TREND-1D | 1-Day price trend | EVD-MKT | CONTINUOUS | COMPUTED | 0.70 |
| EVD-MKT-TREND-5D | 5-Day price trend | EVD-MKT | CONTINUOUS | COMPUTED | 0.70 |
| EVD-MKT-TREND-20D | 20-Day price trend | EVD-MKT | CONTINUOUS | COMPUTED | 0.70 |
| EVD-MKT-MOM-RSI14 | RSI-14 momentum | EVD-MKT | CONTINUOUS | COMPUTED | 0.70 |
| EVD-MKT-VOL-RV10 | 10-day realised volatility | EVD-MKT | CONTINUOUS | COMPUTED | 0.70 |
| EVD-MKT-VOL-IV | Implied volatility level | EVD-MKT | CONTINUOUS | OBSERVED | 0.75 |
| EVD-MKT-DEPTH-IMB | Order book imbalance | EVD-MKT | REAL-TIME | COMPUTED | 0.75 |
| EVD-MKT-OI-CHANGE | Open interest change | EVD-MKT | DAILY | COMPUTED | 0.70 |
| EVD-MKT-VWAP-DEV | VWAP deviation | EVD-MKT | INTRADAY | COMPUTED | 0.70 |
| EVD-CORP-EARN-Q | Quarterly earnings | EVD-CORP | EPISODIC | OBSERVED | 0.80 |
| EVD-CORP-EARN-SURP | Earnings surprise | EVD-CORP | EPISODIC | COMPUTED | 0.75 |
| EVD-CORP-DIV-ANN | Dividend announcement | EVD-CORP | EPISODIC | OBSERVED | 0.85 |
| EVD-CORP-ACT-SPLIT | Stock split | EVD-CORP | EPISODIC | OBSERVED | 0.90 |
| EVD-CORP-RATE-CHG | Rating change | EVD-CORP | EPISODIC | OBSERVED | 0.80 |
| EVD-CORP-OWN-FII | FII ownership change | EVD-CORP | PERIODIC | OBSERVED | 0.80 |
| EVD-FIN-PE-CURR | Current P/E ratio | EVD-FIN | DAILY | COMPUTED | 0.75 |
| EVD-FIN-ROE-TTM | TTM Return on equity | EVD-FIN | QUARTERLY | COMPUTED | 0.75 |
| EVD-FIN-DEBT-EQ | Debt to equity | EVD-FIN | QUARTERLY | COMPUTED | 0.75 |
| EVD-TECH-MA-CROSS | Moving average crossover | EVD-TECH | CONTINUOUS | COMPUTED | 0.65 |
| EVD-TECH-BB-POS | Bollinger Band position | EVD-TECH | CONTINUOUS | COMPUTED | 0.65 |
| EVD-TECH-MACD | MACD crossover | EVD-TECH | CONTINUOUS | COMPUTED | 0.65 |
| EVD-MACRO-REPO-RATE | RBI repo rate level | EVD-MACRO | EPISODIC | OBSERVED | 0.85 |
| EVD-MACRO-REPO-TREND | Repo rate direction | EVD-MACRO | PERIODIC | COMPUTED | 0.80 |
| EVD-MACRO-CPI-MOM | CPI month-on-month | EVD-MACRO | MONTHLY | COMPUTED | 0.80 |
| EVD-MACRO-VIX-IND | India VIX level | EVD-MACRO | REAL-TIME | OBSERVED | 0.85 |
| EVD-MACRO-VIX-REGIME | VIX regime | EVD-MACRO | REAL-TIME | COMPUTED | 0.80 |
| EVD-SECT-RS | Sector relative strength | EVD-SECT | DAILY | COMPUTED | 0.70 |
| EVD-SECT-ROT | Sector rotation signal | EVD-SECT | WEEKLY | COMPUTED | 0.70 |
| EVD-BEH-FII-FLOW | FII net flow | EVD-BEH | DAILY | OBSERVED | 0.80 |
| EVD-BEH-DII-FLOW | DII net flow | EVD-BEH | DAILY | OBSERVED | 0.80 |
| EVD-BEH-OI-PCR | Put-Call ratio | EVD-BEH | INTRADAY | COMPUTED | 0.75 |
| EVD-SENT-NEWS | News sentiment | EVD-SENT | CONTINUOUS | COMPUTED | 0.60 |
| EVD-SENT-ANALYST | Analyst consensus | EVD-SENT | PERIODIC | OBSERVED | 0.70 |
| EVD-RISK-DD-CURR | Current drawdown | EVD-RISK | REAL-TIME | COMPUTED | 0.85 |
| EVD-RISK-VAR-1D | 1-Day VaR | EVD-RISK | DAILY | COMPUTED | 0.80 |
| EVD-XMKT-SGX-PREM | SGX Nifty premium | EVD-XMKT | PRE-MARKET | COMPUTED | 0.80 |
| EVD-XAST-RO-SIGNAL | Risk-on/off signal | EVD-XAST | DAILY | COMPUTED | 0.75 |
| EVD-AI-ANOMALY | Model-detected anomaly | EVD-AI | CONTINUOUS | INFERRED | 0.65 |
| EVD-AI-REGIME | AI regime classification | EVD-AI | CONTINUOUS | INFERRED | 0.70 |
| EVD-COMP-BULL-CONF | Bullish confluence | EVD-COMP | CONTINUOUS | FUSED | 0.75 |
| EVD-COMP-BEAR-CONF | Bearish confluence | EVD-COMP | CONTINUOUS | FUSED | 0.75 |

**Derivation levels:**
- OBSERVED: direct from single observation
- COMPUTED: formula applied to observation(s)
- INFERRED: model output from multiple observations
- FUSED: composite of multiple evidence items

---

## SUPPLEMENT B — EVIDENCE WEIGHTING REFERENCE

### B.1 Base Weight Ranges by Category

| Category | Base weight range | Typical modifiers |
|---|---|---|
| EVD-MKT (CRITICAL) | [0.70, 0.95] | Regime (+/−0.10); source trust (−0.15 for fallback) |
| EVD-CORP (CRITICAL events) | [0.75, 1.00] | Source authoritativeness (+0.10); corroboration (+0.05) |
| EVD-FIN | [0.60, 0.85] | Data age (−0.05 per quarter old); analyst consensus (+0.05) |
| EVD-TECH | [0.50, 0.80] | Regime sensitivity (VOLATILE: +0.10; QUIET: −0.05) |
| EVD-FUND | [0.60, 0.85] | Cycle alignment (+0.10 if all fundamental factors aligned) |
| EVD-MACRO | [0.70, 0.95] | Policy certainty (+0.10 for unanimous committee) |
| EVD-SECT | [0.55, 0.80] | Regime correlation (+0.05) |
| EVD-BEH | [0.65, 0.90] | FII weight > DII weight (FII has higher systematic importance) |
| EVD-SENT | [0.40, 0.65] | Corroboration (+0.10); single source cap at 0.55 |
| EVD-ALT | [0.45, 0.70] | Proven track record (+0.15); unproven cap at 0.55 |
| EVD-RISK | [0.80, 1.00] | CRITICAL tier: risk evidence highest base weight |
| EVD-AI | [0.45, 0.70] | Model freshness: stale model (−0.20); validated model (+0.10) |
| EVD-COMP | Inherits weighted average | Plus fusion_score modifier |
| EVD-XMKT | [0.65, 0.85] | Pre-market timing premium (+0.10 before open) |
| EVD-XAST | [0.60, 0.80] | Cross-asset coherence (+0.10 if all assets aligned) |

---

### B.2 Regime Sensitivity Modifier Table

| Evidence category | BULL_QUIET | BULL_VOLATILE | BEAR_QUIET | BEAR_VOLATILE | CHOPPY |
|---|---|---|---|---|---|
| EVD-MKT-TREND | +0.05 | 0.00 | +0.05 | 0.00 | −0.10 |
| EVD-TECH-MOM | +0.05 | −0.05 | +0.05 | −0.05 | −0.15 |
| EVD-MACRO-VIX | −0.05 | +0.10 | −0.05 | +0.15 | +0.05 |
| EVD-BEH-FII | 0.00 | +0.05 | 0.00 | +0.05 | 0.00 |
| EVD-CORP-EARN | 0.00 | +0.05 | 0.00 | +0.10 | 0.00 |
| EVD-SENT-NEWS | −0.10 | +0.05 | −0.05 | +0.05 | −0.10 |

---
## SUPPLEMENT C — EVIDENCE CONFIDENCE REFERENCE

### C.1 Confidence Tier Definitions

| ECS Range | Tier | Meaning |
|---|---|---|
| [0.90, 1.00] | VERY_HIGH | Multiple authoritative corroborating sources; high historical accuracy |
| [0.75, 0.90) | HIGH | Corroborated from authoritative sources; good historical accuracy |
| [0.60, 0.75) | MODERATE | Single authoritative source or corroborated secondary sources |
| [0.45, 0.60) | LOW | Single secondary source; limited corroboration |
| [0.00, 0.45) | VERY_LOW | Unverified; unreliable source; insufficient history |

---

### C.2 Confidence Modifier Reference

| Modifier | Effect on ECS | Condition |
|---|---|---|
| Authoritative primary source | +0.10 | Source trust tier = AUTHORITATIVE |
| Corroborated by 2+ independent sources | +0.10 | corroboration_count ≥ 2, agreement > 95% |
| Corroborated by 1 independent source | +0.05 | corroboration_count = 1, agreement > 90% |
| No corroboration available | −0.05 | corroboration_count = 0 for CRITICAL type |
| Single secondary source only | −0.10 | source_trust_tier = STANDARD, no corroboration |
| High historical accuracy (ERS > 0.85) | +0.05 | Rolling 90-day ERS > 0.85 |
| Low historical accuracy (ERS < 0.60) | −0.15 | Rolling 90-day ERS < 0.60 |
| Derived evidence (3+ steps) | −0.05 | derivation_steps > 3 |
| AI model stale | −0.20 | training_cutoff_date > 90 days |
| CONTEXT_PARTIAL flag | −0.05 | Context enrichment incomplete |
| Historical plausibility fail | −0.10 | Value outside 5-sigma historical range |

---

### C.3 Representative ECS by Evidence Scenario

| Scenario | ECS | Tier |
|---|---|---|
| NSE OHLCV from primary feed, corroborated BSE | 0.95 | VERY_HIGH |
| RBI rate decision from official source, same-day | 0.95 | VERY_HIGH |
| Corporate action (dividend) from NSE official | 0.90 | HIGH |
| Earnings report — 2 authoritative sources | 0.88 | HIGH |
| FII flow — NSE SEBI data | 0.85 | HIGH |
| Technical indicator (RSI) from verified OHLCV | 0.78 | HIGH |
| News sentiment — multiple verified publishers | 0.72 | MODERATE |
| Earnings report — single secondary source | 0.65 | MODERATE |
| Analyst consensus — 5+ analysts | 0.68 | MODERATE |
| Social sentiment — aggregated | 0.55 | LOW |
| Alternative data — unproven track record | 0.50 | LOW |
| AI anomaly — stale model | 0.40 | VERY_LOW |
| Single unverified news source | 0.38 | VERY_LOW |

---

## SUPPLEMENT D — EVIDENCE CONFLICT MATRIX

### D.1 Conflict Classification Matrix

| Supporting ECS | Opposing ECS | Supporting weight | Opposing weight | Severity |
|---|---|---|---|---|
| ≥ 0.85 | ≥ 0.85 | ≥ 0.70 | ≥ 0.70 | MAJOR |
| ≥ 0.75 | ≥ 0.75 | ≥ 0.60 | ≥ 0.60 | MODERATE |
| ≥ 0.60 | ≥ 0.75 | any | ≥ 0.70 | MODERATE |
| ≥ 0.85 | 0.40–0.60 | ≥ 0.70 | any | MINOR |
| any | < 0.40 | any | any | MINOR (opposing weak) |
| < 0.40 | ≥ 0.85 | any | ≥ 0.70 | MODERATE (supporting weak) |

---

### D.2 Conflict Adjudication Rules

| Condition | Adjudication action |
|---|---|
| One side has ERS < 0.60 | Downweight that side by 30%; flag RELIABILITY_DOWNWEIGHTED |
| One side is > 5× more recent | Downweight older side by 20%; flag RECENCY_DOWNWEIGHTED |
| One side is AUTHORITATIVE; other is STANDARD | Downweight STANDARD side by 20%; flag SOURCE_DOWNWEIGHTED |
| One side has independence_score < 0.40 | Downweight correlated side by 25%; flag CORRELATION_DOWNWEIGHTED |
| No clear adjudication basis | Preserve both at full weight; flag UNRESOLVED_CONFLICT |

---

### D.3 Conflict Resolution Timeline

| Severity | Detection SLA | Notification SLA | Adjudication deadline | Escalation if unresolved |
|---|---|---|---|---|
| MINOR | 60 seconds | N/A (no immediate notification) | 24 hours | Escalate to MODERATE |
| MODERATE | 30 seconds | Alert to Evidence Health Service | 72 hours | Escalate to MAJOR |
| MAJOR | < 30 seconds | Immediate alert to Hypothesis Engine | 7 days | Governance review |

---

### D.4 Conflict Impact on EQS

Conflict status is applied as the D15 dimension in EQS:

| conflict_status | EQS impact |
|---|---|
| NONE | No impact (CFT factor = 1.0) |
| MINOR | CFT = 0.70 (−30% on conflict dimension) |
| MODERATE | CFT = 0.40 |
| MAJOR | CFT = 0.10 (evidence almost unusable until conflict resolved) |

Note: A MAJOR conflict on a HIGH-weight evidence item effectively reduces its contribution to a hypothesis body to near-zero until the conflict is adjudicated. This is deliberate — the Hypothesis Engine must not act on deeply conflicted evidence.

---
## SUPPLEMENT E — EVIDENCE LINEAGE EXAMPLES

### E.1 Purpose

This supplement illustrates the lineage structure for representative evidence types, demonstrating the full chain from evidence → observations → information → source.

---

### E.2 Example 1 — Market Trend Evidence (EVD-MKT-TREND-20D)

```
EVIDENCE
  evidence_id:    EVD-MKT-TREND-20D-20260703-00000001
  evidence_type:  EVD-MKT-TREND-20D
  entity:         RELIANCE.NS
  weight:         0.72
  ECS:            0.88
  EQS:            0.83

  LINEAGE
  ├── derivation_function: linear_regression(close_prices, 20_days)
  ├── derivation_steps: 2
  │
  ├── OBSERVATION [20 items]
  │   ├── OBS-MKT-PRC-OHLCV-1D-20260614-00000042
  │   │     close: 3,245.00
  │   │     source: NSE official feed
  │   │     OQS: 0.94
  │   │
  │   ├── OBS-MKT-PRC-OHLCV-1D-20260615-00000038
  │   │     close: 3,267.50
  │   │     ...
  │   └── [... 18 more daily OHLCV observations ...]
  │
  └── INFORMATION (source of each observation)
      ├── INFO-NSE-OHLCV-20260614-00000042
      │     source: NSE data feed (AUTHORITATIVE)
      └── [... 19 more information objects ...]
```

---

### E.3 Example 2 — Corporate Earnings Surprise Evidence (EVD-CORP-EARN-SURP)

```
EVIDENCE
  evidence_id:    EVD-CORP-EARN-SURP-20260703-00000015
  evidence_type:  EVD-CORP-EARN-SURP
  entity:         TATAMOTORS.NS
  weight:         0.78
  ECS:            0.82
  EQS:            0.79

  LINEAGE
  ├── derivation_function: (actual_EPS - consensus_EPS) / abs(consensus_EPS)
  ├── derivation_steps: 2
  │
  ├── OBSERVATION 1 — Actual Earnings
  │   OBS-CORP-EARN-Q-20260703-00000003
  │     actual_EPS: 18.45
  │     source: BSE filing (AUTHORITATIVE)
  │     OQS: 0.93
  │
  ├── OBSERVATION 2 — Analyst Consensus
  │   OBS-CORP-CONS-EPS-20260703-00000001
  │     consensus_EPS: 15.20
  │     analyst_count: 12
  │     source: Bloomberg consensus (RELIABLE)
  │     OQS: 0.85
  │
  └── COMPUTED VALUE
      EPS_surprise_pct: (18.45 - 15.20) / 15.20 = +21.4%
      Strength (D01): 0.84 (large positive surprise)
```

---

### E.4 Example 3 — Composite Bullish Confluence Evidence (EVD-COMP-BULL-CONF)

```
EVIDENCE
  evidence_id:    EVD-COMP-BULL-CONF-20260703-00000007
  evidence_type:  EVD-COMP-BULL-CONF
  entity:         NIFTY50
  fusion_score:   0.78
  ECS:            0.81
  EQS:            0.77

  LINEAGE — 4 constituent evidence items
  ├── EVD-MKT-TREND-20D-20260703-00000001   weight: 0.72  ECS: 0.88  direction: +
  ├── EVD-MKT-MOM-RSI14-20260703-00000002   weight: 0.65  ECS: 0.75  direction: +
  ├── EVD-BEH-FII-FLOW-20260703-00000003    weight: 0.80  ECS: 0.85  direction: +
  └── EVD-MACRO-VIX-REGIME-20260703-00000004 weight: 0.70  ECS: 0.82  direction: +
      (VIX below 20 = favourable regime)

  FUSION COMPUTATION
  independence_scores: [0.95, 0.70, 0.90, 0.85]  (RSI correlated with trend: 0.70)
  weighted_agreement: 0.78
  direction_coherence: 1.00 (all four point positive)
  fusion_score: 0.78

  CONFLICT STATUS: NONE
```

---

## SUPPLEMENT F — EVIDENCE ANTI-PATTERN REFERENCE

### F.1 Purpose

This supplement catalogs the most damaging evidence anti-patterns — the recurring design or operational failures that undermine evidence quality and analytical integrity.

---

### AP-01 — The Interpretive Evidence

**Description:** An evidence record that contains analytical conclusions, trading signals, price targets, or buy/sell recommendations embedded in its content.

**Symptom:** Evidence fields contain labels like "BULLISH", "BUY", "STRONG UPTREND", or embedded signal scores.

**Root cause:** Developers conflating the Evidence Engine (evaluation) with the Signal Engine (signal generation) or Decision Engine (decision).

**Architectural harm:** Downstream engines receive evidence that has already been interpreted, forcing them to accept the embedded analysis. Evidence reusability is destroyed. Different reasoning models cannot apply their own interpretation.

**Remediation:** Strip all conclusory content from evidence. Evidence records contain evaluated, weighted, scored facts — not recommendations. Move all signal and decision content to the appropriate downstream engine.

---

### AP-02 — The Confidence Inflation Anti-Pattern

**Description:** Treating correlated evidence sources as independent, artificially inflating apparent confidence.

**Symptom:** Evidence body appears to show five independent confirming signals; on investigation, all five derive from the same underlying data provider or methodology.

**Root cause:** Independence Engine disabled or bypassed; source correlation not tracked.

**Architectural harm:** Overconfidence in evidence body leads to overconfident hypotheses, overconvicted decisions, and outsized position sizing. One of the most dangerous analytical errors in quantitative investment.

**Remediation:** Independence Engine MUST be always-on. All evidence creation pipelines must pass through independence scoring. Source correlation matrix must be maintained and updated continuously.

---

### AP-03 — The Silent Conflict

**Description:** Conflicting evidence exists in the store but has not been detected or flagged, because the Conflict Manager was bypassed or failed.

**Symptom:** Strong opposing evidence for the same hypothesis exists simultaneously but neither has a conflict_status set. The Hypothesis Engine sees a falsely clean evidence picture.

**Root cause:** Conflict detection disabled; conflict manager failure not detected; new evidence admitted without conflict scan.

**Architectural harm:** The Hypothesis Engine forms a hypothesis on the basis of what it believes is a clean evidence picture. In reality, the evidence is strongly conflicted. The hypothesis is formed with false confidence.

**Remediation:** Conflict detection MUST run on every new evidence arrival. Conflict Manager failures MUST be detected and MUST block evidence admission until resolved. Periodic batch conflict scans provide a safety net.

---

### AP-04 — The Stale Evidence Blindspot

**Description:** Evidence continues to be treated as current and high-quality despite being significantly past its freshness SLA, because freshness monitoring is not enforced.

**Symptom:** Evidence with evidence_timestamp 4 hours ago is being presented to the Hypothesis Engine with EQS = 0.85 despite having a 30-minute freshness SLA for its type.

**Root cause:** Freshness score not recomputed dynamically; static EQS not updated after initial computation.

**Architectural harm:** Hypothesis Engine forms views based on stale evidence. Market conditions may have changed significantly since the evidence was evaluated. Decisions based on stale evidence fail in live markets.

**Remediation:** Freshness (D07 in EQS) must be recomputed dynamically. EQS must be recomputed when freshness crosses a tier boundary. STALE CRITICAL evidence must trigger immediate alerts and re-evaluation requests.

---

### AP-05 — The Look-Ahead Evidence

**Description:** Historical evidence provided to backtesting pipelines was evaluated with observations whose capture_timestamp post-dates the analysis moment, introducing look-ahead bias.

**Symptom:** Backtesting results dramatically outperform live trading results on identical strategies.

**Root cause:** Historical evidence retrieval using observation_timestamp filter only, not capture_timestamp ≤ analysis_timestamp filter.

**Architectural harm:** Strategies selected on the basis of look-ahead-contaminated evidence backtests will fail in live trading. The backtest is not a valid simulation of the live trading environment.

**Remediation:** All historical evidence retrieval MUST use PIT-safe semantics: filter by creation_timestamp ≤ analysis_timestamp. The Retrieval Service must enforce this for all historical queries. Backtesting frameworks must use the Retrieval Service PIT interface exclusively.

---

### AP-06 — The Derivation Black Box

**Description:** An evidence record exists in the Registry with a weight and ECS but no derivation record — no record of how the weight was computed, what modifiers were applied, or which components produced the ECS.

**Symptom:** An analyst asks "why does this evidence have weight 0.82 and ECS 0.75?" — no answer is possible.

**Root cause:** Weight and confidence computation proceeding without recording derivation rationale.

**Architectural harm:** Auditability is broken. Weight calibration is impossible without derivation records. Regulatory audit requests cannot be satisfied. Governance reviews cannot assess whether weights are appropriately calibrated.

**Remediation:** Every weight and confidence computation MUST produce a derivation record. Derivation records are stored in the audit trail. Evidence MUST NOT be distributed without derivation records.

---

### AP-07 — The Orphaned Evidence

**Description:** Evidence records in the Registry that cannot be traced back to any observation — either the supporting_observations[] list is empty, or the observation_ids do not resolve.

**Symptom:** evidence.supporting_observations[] is empty or contains unresolvable IDs.

**Root cause:** Evidence created without proper lineage wiring; observation deletion (which is prohibited) removing the foundation of existing evidence.

**Architectural harm:** Lineage is broken. The evidence cannot be audited. Its accuracy cannot be assessed. It cannot be included in reliable backtesting.

**Remediation:** Evidence MUST NOT be stored without at least one resolvable supporting observation (EC-A-008). Observations MUST NOT be deleted before their retention period (preventing orphaning). Periodic orphan audits must detect and quarantine orphaned evidence.

---

### AP-08 — The Weight Anchoring Error

**Description:** Evidence weights are anchored to values set at system inception and never recalibrated, even as market conditions and evidence predictive power change.

**Symptom:** Evidence type that historically predicted hypothesis outcomes with 80% accuracy now predicts with 55% accuracy, but its weight has not been reduced.

**Root cause:** Evolution Manager disabled or inactive; governance approval cycle too slow; calibration reviews not conducted.

**Architectural harm:** The evidence body has systematically miscalibrated weights. Hypotheses formed on this evidence have inflated confidence that does not reflect reality. Decision quality deteriorates over time.

**Remediation:** Evolution Manager MUST run monthly calibration assessments. ERS monitoring MUST alert when rolling accuracy drops > 15% below assigned weight. Governance MUST approve recalibration proposals within 14 days.

---

### AP-09 — The Composite Masquerade

**Description:** A composite evidence record masquerades as having five independent inputs when its five constituent evidence items are all derived from the same source observation.

**Symptom:** composite_evidence.n_constituents = 5; fusion_score = 0.95; but all five constituents share the same underlying observation_ids.

**Root cause:** Fusion logic not checking constituent independence; deduplication not applied at the constituent level of composition.

**Architectural harm:** The composite appears to represent strong, multiply-confirmed evidence. In reality, it is the same observation expressed five different ways. Hypothesis Engine is misled into high confidence.

**Remediation:** Composite evidence MUST check that constituent evidence items are independent (no shared underlying observation_ids). If constituents are correlated, the fusion_score is penalised. Independence Engine must be applied at the composite level as well as the individual evidence level.

---

### AP-10 — The Version Collapse

**Description:** Instead of creating a new version when evidence is corrected, the existing evidence record is modified in place, destroying the historical record.

**Symptom:** An evidence record's weight or ECS has changed since it was cached by the Hypothesis Engine, but no version history exists.

**Root cause:** Direct database writes bypassing the History Manager and Version Manager.

**Architectural harm:** Historical replay produces different results. The Hypothesis Engine's cache and the Registry have diverged. Audit trail is broken. Calibration history is corrupted.

**Remediation:** Database access to the Evidence Registry is READ-ONLY for all components except the Evidence Recorder and Version Manager. All write paths MUST go through the Version Manager for existing evidence. Periodic integrity audits detect in-place modifications.

---
## SUPPLEMENT G — OPERATIONAL RUNBOOK

### G.1 Startup Sequence

**Pre-startup checklist:**

| Step | Action | Verification |
|---|---|---|
| 1 | Confirm Evidence Registry accessible | Registry health check returns OK |
| 2 | Confirm Evidence Catalog is current | Catalog version matches deployed version |
| 3 | Confirm Observation Engine is healthy | OE health endpoint returns HEALTHY |
| 4 | Confirm Identity Manager sequence continuity | Last sequence consistent with Registry |
| 5 | Confirm Audit Logger write access | Test audit write succeeds |
| 6 | Confirm Context Manager (via OE) is accessible | Context enrichment test succeeds |

**Startup order:**

```
Step 1:  Audit Logger (EC-22)            — must be first; all operations require audit
Step 2:  Evidence Catalog (EC-02)        — required by all downstream components
Step 3:  Evidence Identity Manager (EC-03) — required by Evidence Builder
Step 4:  Evidence Registry (EC-01)       — storage layer
Step 5:  Evidence Lineage Manager (EC-15)— required for evidence creation
Step 6:  Evidence Validator (EC-06)      — required before evaluation
Step 7:  Evidence Weighting Engine (EC-07)
Step 8:  Evidence Confidence Engine (EC-08)
Step 9:  Evidence Reliability Engine (EC-09)
Step 10: Evidence Independence Engine (EC-10)
Step 11: Evidence Correlation Engine (EC-11)
Step 12: Evidence Conflict Manager (EC-13)
Step 13: Evidence Context Manager (EC-14)
Step 14: Evidence Version Manager (EC-17)
Step 15: Evidence Aggregator (EC-12)
Step 16: Evidence Search Engine (EC-18)
Step 17: Evidence Storage Manager (EC-19)
Step 18: Evidence History Manager (EC-20)
Step 19: Evidence Builder (EC-05)
Step 20: Evidence Collector (EC-04)      — subscribe to Observation Engine
Step 21: Evidence Retrieval Service (ES-11) — open for consumer queries
Step 22: Evidence Governance Manager (EC-21) — activate governance checks
Step 23: Evidence Evolution Manager (EC-23) — schedule calibration checks
Step 24: Evidence Health Service (ES-17) — begin health monitoring
```

**Post-startup verification:**

| Check | Expected result |
|---|---|
| Evidence Collector subscription | Observation Engine delivering observations |
| First evidence record created | Retrievable by evidence_id within 2 minutes |
| Audit trail health | First audit records visible |
| Quality monitoring dashboard | All category mean EQS > 0.70 |
| Conflict scan | No pre-existing unscanned conflicts |

---

### G.2 Graceful Shutdown Sequence

```
Step 1:  Halt Evidence Collector — stop accepting new observations
Step 2:  Drain evidence construction queue — process all in-flight candidates
Step 3:  Flush Conflict Manager queue — complete all pending conflict scans
Step 4:  Flush Distribution queue — deliver all pending distributions
Step 5:  Evidence Evolution Manager — complete any in-progress calibration
Step 6:  Evidence Storage Manager — flush write buffer; checkpoint
Step 7:  Evidence Search Engine — flush index updates
Step 8:  Evidence Audit Logger — flush audit buffer; write SHUTDOWN event
Step 9:  Evidence Registry — checkpoint; verify storage consistency
```

---

### G.3 Recovery Procedures

**Scenario: Evidence Registry failure**

| Step | Action |
|---|---|
| 1 | Halt Evidence Recorder writes immediately |
| 2 | Buffer new evidence candidates in construction queue (max 10 min of volume) |
| 3 | Diagnose storage failure |
| 4 | Restore from backup; verify Registry integrity |
| 5 | Resume Evidence Recorder; drain construction queue |
| 6 | Run conflict scan over newly stored evidence |
| 7 | Alert consumers of outage window |

---

**Scenario: Observation Engine feed disconnection**

| Step | Action |
|---|---|
| 1 | Evidence Collector detects feed disconnect (< 30 seconds) |
| 2 | Enter EVIDENCE_GAP state; alert Evidence Health Service |
| 3 | Flag all evidence for affected entity types as EVIDENCE_GAP_POSSIBLE |
| 4 | On reconnect: replay missed observations from Observation Registry (PIT query) |
| 5 | Re-evaluate evidence for the gap period |
| 6 | Notify Hypothesis Engine of evidence gap and recovery |

---

**Scenario: Confidence Engine failure**

| Step | Action |
|---|---|
| 1 | Evidence pipeline switches to CONFIDENCE_DEGRADED mode |
| 2 | Evidence stored with confidence inherited from observation OQS; CONFIDENCE_PARTIAL flag |
| 3 | CONFIDENCE_PARTIAL evidence held from CRITICAL consumers until fully scored |
| 4 | On recovery: run confidence backfill job for all CONFIDENCE_PARTIAL evidence |
| 5 | Re-evaluate EQS; re-distribute updated evidence to consumers |

---

**Scenario: Conflict Manager failure**

| Step | Action |
|---|---|
| 1 | CONFLICT_CHECK_SKIPPED flag applied to all new evidence |
| 2 | Evidence proceeds to storage with CONFLICT_UNKNOWN status |
| 3 | Alert Hypothesis Engine: conflict data unavailable |
| 4 | Hypothesis Engine reduces confidence in all hypothesis evaluations during outage |
| 5 | On recovery: run batch conflict scan over all evidence stored during outage |
| 6 | Update conflict_status on affected evidence; notify Hypothesis Engine |

---

**Scenario: Independence Engine failure**

| Step | Action |
|---|---|
| 1 | INDEPENDENCE_CHECK_SKIPPED flag applied to all new evidence |
| 2 | independence_score defaulted to 0.50 (neutral) |
| 3 | Alert Hypothesis Engine: independence data may be inaccurate |
| 4 | On recovery: run batch independence recomputation |

---

### G.4 Performance Targets

| Metric | Target | Measurement point |
|---|---|---|
| Evidence construction latency (p50) | < 50ms | Observation receipt to evidence candidate |
| Evidence evaluation latency (p99) | < 200ms | Observation receipt to evidence distributed |
| OQS gate check latency (p99) | < 5ms | Evidence Collector |
| Weight computation latency (p99) | < 15ms | Weighting Engine |
| Confidence computation latency (p99) | < 20ms | Confidence Engine |
| Independence check latency (p99) | < 30ms | Independence Engine |
| Conflict detection latency (p99) | < 30ms | Conflict Manager |
| Registry write latency (p99) | < 50ms | Evidence Recorder → Registry |
| Retrieval query latency (p99) | < 50ms | Retrieval Service |
| Distribution latency, CRITICAL (p99) | < 100ms | Distribution Service |
| Audit write latency (p99) | < 5ms | Audit Logger |

---

### G.5 Capacity Reference

| Metric | Value |
|---|---|
| Estimated daily evidence records | ~500,000 |
| CRITICAL evidence records per day | ~50,000 |
| Evidence record size (avg) | ~3 KB |
| Daily evidence storage (uncompressed) | ~1.5 GB |
| Daily evidence storage (compressed 3:1) | ~500 MB |
| Lineage record daily growth | ~200 MB |
| Audit trail daily growth | ~100 MB |
| Conflict records per day | ~5,000 |
| Annual storage budget | ~290 GB compressed |

---
## SUPPLEMENT H — EVIDENCE ENGINE GLOSSARY

### H.1 Purpose

This glossary defines all terms specific to the Evidence Engine architecture. Terms are listed alphabetically.

---

**Adjudication**
The process by which the Conflict Manager determines which of two conflicting evidence records deserves a reduced effective weight, based on recency, source reliability, and independence. Adjudication produces an ADJUDICATED flag and must be recorded in the audit trail.

**Alternative Data Evidence**
Evidence derived from non-traditional data sources — satellite imagery, mobile geolocation, credit card spending, web traffic. Category code: EVD-ALT. Carries higher uncertainty than primary market evidence.

**Behavioral Evidence**
Evidence derived from observed market participant behaviour — institutional flows, short interest, options positioning. Category code: EVD-BEH.

**Calibration**
The process of verifying that assigned confidence scores and weights are statistically accurate — that a 0.80 ECS corresponds to approximately 80% historical accuracy for evidence of that type from that source. Managed by the Evidence Evolution Manager.

**Capture Timestamp**
The UTC timestamp at which the IIOS captured and recorded the underlying observation. Used in PIT query semantics to prevent look-ahead bias in historical analysis.

**Composite Evidence**
An evidence record fusing two or more constituent evidence items from different categories into a higher-order analytical input. Category code: EVD-COMP. Carries a fusion_score.

**Confidence Score (ECS)**
The Evidence Confidence Score — a value in [0.0, 1.0] expressing the degree of certainty that an evidence record correctly represents the condition it is asserting. Computed by the Confidence Engine from source quality, corroboration, derivation complexity, and historical accuracy.

**Conflict Manager**
The component responsible for detecting, classifying, and adjudicating conflicts between evidence records that speak to the same hypothesis in opposing directions.

**Conflict Status**
The field on an evidence record indicating whether it is in conflict with opposing evidence: NONE / MINOR / MODERATE / MAJOR. Affects the EQS conflict dimension (D15).

**Context Record (ContextRecord)**
A structured record capturing the state of the investment universe at the evidence_timestamp — regime, session, market state, VIX, events, calendar. Mandatory for every evidence record.

**Conviction**
The degree of confidence with which the IIOS holds a decision. Conviction is computed at the Decision Engine level from the combined weight, consistency, and reliability of the evidence body supporting a hypothesis.

**Corroboration**
Independent confirmation of an underlying observation by multiple sources. Corroboration increases ECS and the accuracy quality dimension.

**Derived Evidence**
Evidence computed from one or more other pieces of evidence through a defined derivation function. Carries a derivation lineage documenting the derivation steps.

**Disqualification**
The semantic rejection of an evidence candidate during the Qualification stage. A disqualified candidate was structurally valid but did not meet the semantic threshold to constitute evidence of its type.

**ECS**
See Confidence Score.

**EQS**
Evidence Quality Score — the composite quality indicator for an evidence record, computed from 16 weighted quality dimensions. EQS ∈ [0.0, 1.0].

**ERS**
Evidence Reliability Score — the rolling 90-day track record of an evidence type from a specific source. Computed by the Reliability Engine.

**Evidence**
An evaluated, weighted, and confidence-scored transformation of one or more observations into an analytical input that speaks to the presence, absence, or degree of a condition. Evidence does not conclude — it supports, contradicts, or remains neutral toward a hypothesis.

**Evidence Builder**
The component that constructs an Evidence Candidate record from one or more qualified observations, applying derivation rules from the Evidence Catalog.

**Evidence Catalog**
The authoritative registry of all evidence type definitions — codes, schemas, derivation rules, weight ranges, and confidence floors.

**Evidence Collector**
The component that subscribes to the Observation Engine's distribution service and receives qualified observations for evidence evaluation.

**Evidence Quality Score**
See EQS.

**Evidence Registry**
The central store of all evidence records in the IIOS. The single source of truth for all evidence state.

**Evidence Timestamp**
The UTC timestamp at which the evidence was evaluated. Not the same as the underlying observation timestamp. Used with creation_timestamp to support PIT queries on evidence.

**Evolution Manager**
The component responsible for the long-term calibration of evidence weights and confidence scores, detecting drift and proposing recalibration.

**Freshness SLA**
The maximum elapsed time after which an evidence record of a given type is considered STALE. Defined per type in the Evidence Catalog.

**Governance Decision Record (GDR)**
A documented record of a governance decision affecting the Evidence Engine — why immutability is required, why independence scoring is mandatory, etc.

**History Manager**
The component that preserves all versions of evidence records and all outcome records, enabling historical replay and calibration.

**Hypothesis**
A structured, testable, probabilistic assertion about the investment universe. Hypotheses are formed by the Hypothesis Engine from evidence. The Evidence Engine does not form hypotheses — it provides evaluated evidence to the Hypothesis Engine.

**Identity Manager**
The component responsible for assigning canonical, globally unique evidence_ids.

**Independence Engine**
The component that assesses whether evidence records are statistically independent of each other and reduces effective weight for correlated evidence.

**Independence Score**
A value in [0.0, 1.0] measuring the statistical independence of an evidence record from other active evidence for the same entity and hypothesis context.

**Lineage**
The complete, traceable chain from evidence → constituent observations → information objects → raw sources. Lineage is preserved permanently.

**Lineage Manager**
The component that creates and maintains evidence lineage records.

**Look-Ahead Bias**
An analytical error caused by using evidence that was evaluated with observations not yet captured at the time being analysed. Prevented by PIT query semantics.

**Purity**
The architectural property of an evidence record containing only evaluated, weighted, confidence-scored facts — no interpretations, conclusions, signals, or recommendations. Analogous to purity in the Observation Engine but at the evaluation layer.

**Qualification**
The semantic validation of an evidence candidate — determining whether the observation data meets the threshold to constitute actionable evidence of the assigned type, beyond mere structural validity.

**Quarantine**
A lifecycle state for evidence candidates that fail validation or qualification. Quarantined evidence is not distributed to consumers.

**Regime**
The prevailing market regime at the evidence_timestamp — e.g., BULL_QUIET, BEAR_VOLATILE. Captured in the ContextRecord. Used for regime-sensitive weight modifiers.

**Reliability Score**
See ERS.

**Strength**
The D01 quality dimension — how decisively the evidence speaks to its hypothesis domain, independent of how trustworthy or well-corroborated it is.

**SUPERSEDED**
A lifecycle state for evidence records that have been replaced by a newer, corrected version. Superseded records are preserved in the History Manager.

**Trust Tier**
A 5-level classification of source quality (AUTHORITATIVE / RELIABLE / STANDARD / PROVISIONAL / UNRELIABLE) inherited from the Observation Engine's Source Registry.

**Version Chain**
The linear sequence of versions of an evidence record, from the original (version_number = 1) through all recalibrations and corrections. No branching permitted.

**Weight**
A value in [0.0, 1.0] assigned by the Weighting Engine indicating the analytical importance of an evidence record relative to other evidence of the same type.

---
## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | EVIDENCE ENGINE ARCHITECTURE |
| Document code | IIOS-EVE-ENG-ARCH-001 |
| Version | 1.0 |
| Status | RATIFIED |
| Part I — Evidence Philosophy | 20 conceptual distinctions; 9 types of evidence; 10 foundational properties |
| Part II — Evidence Model | 22 evidence categories (1 abstract root, 21 concrete) |
| Part III — Core Components | 23 components across 5 clusters |
| Part IV — Evidence Lifecycle | 14 stages across 4 phases; complete state machine |
| Part V — Evidence Services | 17 services (ES-01 through ES-17) |
| Part VI — Processing Pipelines | 15 pipelines with ASCII flow diagrams |
| Part VII — Quality Framework | 16 EQS dimensions; 5 quality tiers; formulas |
| Part VIII — Governance | 16 governance dimensions; tier matrix; review cycle |
| Part IX — Evidence Constitution | 80 constitutional rules across 8 categories (EC-A through EC-H) |
| Part X — Readiness Checklist | 15 sections; 7-use-case readiness matrix |
| Supplement A — Evidence Taxonomy | 40+ evidence types with derivation level and min EQS |
| Supplement B — Weighting Reference | Weight ranges by category; regime sensitivity modifier table |
| Supplement C — Confidence Reference | ECS tiers; 11 modifiers; 13 calibration scenarios |
| Supplement D — Conflict Matrix | Classification matrix; adjudication rules; timeline; EQS impact |
| Supplement E — Lineage Examples | 3 detailed lineage examples (trend, earnings surprise, composite) |
| Supplement F — Anti-Patterns | 10 anti-patterns (AP-01 through AP-10) |
| Supplement G — Operational Runbook | Startup (24 steps); shutdown; 5 recovery procedures; performance targets; capacity |
| Supplement H — Glossary | 45+ alphabetically ordered terms |
| Constitutional rules — EC-A (Identity) | 10 rules |
| Constitutional rules — EC-B (Validity) | 12 rules |
| Constitutional rules — EC-C (Lineage) | 10 rules |
| Constitutional rules — EC-D (Traceability) | 10 rules |
| Constitutional rules — EC-E (Confidence/Weight) | 12 rules |
| Constitutional rules — EC-F (Independence/Conflict) | 15 rules |
| Constitutional rules — EC-G (Governance) | 10 rules |
| Constitutional rules — EC-H (Historical Preservation) | 10 rules |
| Readiness checklist criteria | ~100 individual criteria across 15 sections |

---

### Master Compliance Checklist

| Section | Included | Verified |
|---|---|---|
| Part I — Evidence Philosophy | ✅ | ✅ |
| Part II — Evidence Model | ✅ | ✅ |
| Part III — Core Components | ✅ | ✅ |
| Part IV — Lifecycle | ✅ | ✅ |
| Part V — Services | ✅ | ✅ |
| Part VI — Processing Pipelines | ✅ | ✅ |
| Part VII — Quality Framework | ✅ | ✅ |
| Part VIII — Governance | ✅ | ✅ |
| Part IX — Evidence Constitution | ✅ | ✅ |
| Part X — Readiness Checklist | ✅ | ✅ |
| Supplement A — Evidence Taxonomy | ✅ | ✅ |
| Supplement B — Weighting Reference | ✅ | ✅ |
| Supplement C — Confidence Reference | ✅ | ✅ |
| Supplement D — Conflict Matrix | ✅ | ✅ |
| Supplement E — Lineage Examples | ✅ | ✅ |
| Supplement F — Anti-Patterns | ✅ | ✅ |
| Supplement G — Operational Runbook | ✅ | ✅ |
| Supplement H — Glossary | ✅ | ✅ |

---

### Governing Documents

| Document | Code | Relationship |
|---|---|---|
| IIOS Architecture Overview | IIOS-SYS-000 | System root |
| OBSERVATION_ENGINE_ARCHITECTURE.md | IIOS-OE-ARCH-001 | Direct upstream: provides observations |
| INFORMATION_ENGINE_ARCHITECTURE.md | IIOS-IE-ARCH-001 | Upstream (Layer 0) |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | IIOS-KE-ARCH-001 | Downstream: consumes evidence |
| ENTITY_ENGINE_ARCHITECTURE.md | IIOS-EE-ARCH-001 | Referenced: entity identity resolution |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | IIOS-RE-ARCH-001 | Referenced: relationship evidence context |
| EVENT_ENGINE_ARCHITECTURE.md | IIOS-EVE-ARCH-001 | Referenced: event evidence context |
| DATABASE_PERSISTENCE_ARCHITECTURE.md | IIOS-DB-ARCH-001 | Underlying: persistence for Evidence Registry |

---

### Architectural Impact Statement

The Evidence Engine occupies the most analytically critical position in the IIOS cognitive stack. It is the last layer that operates purely on perception — the last layer before reasoning begins. Every hypothesis the Hypothesis Engine forms, every conclusion the Knowledge Engine reaches, every decision the Decision Engine makes, traces its ultimate analytical foundation through evidence.

If evidence weights are miscalibrated, hypotheses will be systematically biased. If evidence independence is not tracked, overconfidence will persistently corrupt the system's self-assessment. If conflicts are silently resolved, the system will act on false certainty. If look-ahead bias enters the historical evidence pipeline, every backtested strategy becomes fiction.

The architectural invariants established in this document — immutability, purity, mandatory independence assessment, conflict transparency, PIT semantics, permanent lineage — are the minimum necessary conditions for the IIOS to be a trustworthy analytical system. They are not engineering preferences. They are the conditions under which the system's outputs can be trusted, audited, and staked real capital against.

Evidence is the bridge between what the IIOS perceives and what it reasons. The quality of that bridge determines the quality of everything above it.

---

### Version History

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1 | Architecture inception | IIOS Architecture Board | Initial draft: model, components, lifecycle |
| 0.5 | First review | IIOS Architecture Board | Added quality framework, constitution |
| 0.9 | Pre-ratification | All domain owners | Added supplements, anti-patterns, glossary |
| 1.0 | Ratification | IIOS Architecture Board | Ratified; all 10 parts and supplements A–H complete |

---

*This document is RATIFIED. No component of the IIOS Evidence Engine may be designed, implemented, or operated in a manner inconsistent with the architecture defined herein. Proposed changes must be submitted as Architecture Change Requests to the IIOS Architecture Board.*

*End of EVIDENCE_ENGINE_ARCHITECTURE.md*

---## SUPPLEMENT I — GOVERNANCE DECISION RECORDS

### GDR-EV-001 — Mandatory Independence Assessment

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Should independence assessment be optional (applied only for high-stakes hypotheses) or mandatory for every evidence record?

**Decision:** Independence assessment is mandatory for every evidence record before distribution.

**Rationale:**
1. Correlated evidence is the primary cause of systematic overconfidence in quantitative investment systems. A system that correctly assigns ECS = 0.80 to five correlated evidence items but treats them as five independent confirmations will compute a combined confidence of 1 − (0.20^5) ≈ 0.9997 — almost certainty — when the correct combined confidence (accounting for correlation = 1.0) is simply 0.80.
2. The cost of independence assessment (< 30ms per evidence item) is negligible compared to the cost of a decision made with false certainty.
3. Making independence optional creates a two-tier evidence population — assessed and unassessed — that is impossible to reason about coherently. A Hypothesis Engine receiving a mix cannot know which evidence items have been independence-adjusted.
4. Market regime changes alter correlation structures. Evidence that was independent in a low-volatility regime may become highly correlated during a crisis (correlation goes to 1.0 in crises). Independence must be re-assessed continuously.

**Consequence accepted:** All evidence creation pipelines depend on the Independence Engine. Independence Engine failure triggers a INDEPENDENCE_CHECK_SKIPPED flag rather than blocking evidence creation — but the flag must cause the Hypothesis Engine to reduce its confidence in all affected hypotheses.

---

### GDR-EV-002 — Conflict Preservation (No Silent Adjudication)

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** When the Conflict Manager detects a conflict, should it silently resolve it (suppress the weaker evidence) or preserve both evidence records with a conflict flag?

**Decision:** Both conflicting evidence records are preserved at full weight with conflict_status set. Silent suppression is prohibited.

**Rationale:**
1. A conflict between two high-quality evidence items is itself analytically valuable information. The Hypothesis Engine needs to know that the evidence picture is mixed. If the weaker side is silently suppressed, the Hypothesis Engine forms a view based on apparent certainty that does not exist.
2. The "weaker" evidence may be correct. Adjudication downweights one side but does not remove it — the Hypothesis Engine retains access to the full conflicted picture.
3. Historical analysis requires that all conflicts be preserved. A strategy that failed may have failed because strong contradicting evidence was available but silently suppressed. That failure cannot be diagnosed retrospectively if the suppression was not recorded.
4. Audit and compliance require that all evidence used in decisions is traceable. Silently suppressed evidence cannot appear in audit trails.

**Consequence accepted:** Hypothesis Engine must handle conflicted evidence bodies. It is explicitly designed to do so — conflicted evidence is one of the inputs to its uncertainty quantification.

---

### GDR-EV-003 — Immutable Evidence Records

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Should evidence records be mutable (correctable in place) or immutable (requiring new versions for all changes)?

**Decision:** Evidence records are immutable once stored as ACTIVE. All corrections, recalibrations, or re-evaluations create new versions with full version chains.

**Rationale:**
1. Decisions were made on the basis of evidence as it existed at a point in time. That point-in-time evidence must be reconstructable. A mutable store makes historical reconstruction impossible.
2. Calibration is an ongoing process. Weights and confidence scores will be recalibrated as the system learns. Each recalibration should produce a new version — the original evaluation is preserved, and the evolution of the system's evidence assessment is fully auditable.
3. Regulatory compliance requires that evidence used in trading decisions is immutable. A regulator may ask "what evidence existed on date X that supported trade Y?" — this must be answerable with certainty.
4. Multiple components may simultaneously be using the same evidence record. In-place modification would create race conditions and consistency violations.

**Consequence accepted:** Storage grows with every recalibration. This is deliberately accepted — the version history is itself an analytical asset.

---

### GDR-EV-004 — Mandatory Lineage to Source

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Must evidence lineage trace all the way back to the raw source (information object and raw data), or is lineage to the observation level sufficient?

**Decision:** Lineage must trace all the way from evidence → observations → information → raw source. Observation-level lineage alone is insufficient.

**Rationale:**
1. The quality of an observation depends on the quality of its source information object. An observation with OQS = 0.90 from an information object that was itself derived from an unreliable raw source requires traceability all the way back to assess the true quality chain.
2. Regulatory compliance (PMLA, SEBI) requires traceability of trading decisions back to the underlying data sources.
3. When a data source is found to have been systematically inaccurate, the system must be able to identify all evidence records derived from that source — this requires lineage to the source level.
4. Research and forensic analysis of past decisions requires the ability to re-evaluate what the IIOS would have concluded if a specific source had not been trusted — only possible with full lineage.

**Consequence accepted:** Lineage records are more complex and consume more storage. Lineage records are permanent and never archived. This cost is explicitly accepted.

---

### GDR-EV-005 — Evidence Does Not Contain Conclusions

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** May evidence records embed analytical conclusions, signals, or trading recommendations for the convenience of downstream consumers?

**Decision:** No. Evidence records contain evaluated, weighted, scored facts — never conclusions, signals, predictions, or recommendations.

**Rationale:**
1. Evidence is a shared analytical resource used by multiple consumers (Hypothesis Engine, Knowledge Engine, Research) with potentially different analytical frameworks. Embedding conclusions from one framework contaminate the evidence for all other frameworks.
2. The separation between evidence (evaluation) and hypothesis (interpretation) is architecturally fundamental. Violating it creates feedback loops where evidence appears to confirm hypotheses it helped form.
3. If evidence contained trading signals, a regulatory audit of a trading decision would find the analytical conclusion embedded in the evidentiary foundation — it would be impossible to assess whether the decision was based on evidence or on a conclusion embedded in evidence.
4. Different market regimes require different interpretations of the same evidence. A bearish RSI in a bull regime may be a minor correction signal; the same RSI in a bear regime may confirm a downtrend. Embedding a single interpretation in the evidence destroys regime sensitivity.

**Consequence accepted:** Downstream consumers must perform their own interpretation. This is the correct architectural assignment of responsibilities.

---

### GDR-EV-006 — PIT Semantics Mandatory for Historical Evidence

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Is it sufficient to filter historical evidence by evidence_timestamp, or must all historical queries use the creation_timestamp ≤ analysis_timestamp filter?

**Decision:** All historical queries must use creation_timestamp ≤ analysis_timestamp (PIT semantics). Filtering by evidence_timestamp alone is prohibited for historical analysis.

**Rationale:**
1. Evidence is created when the IIOS becomes aware of a condition — not when the condition existed. A quarterly earnings report may be for Q1 (observation_timestamp = March 31) but be filed and captured on April 15. Evidence derived from this report has evidence_timestamp = April 15. If a historical analysis of March 31 filters by evidence_timestamp, it would correctly exclude the earnings evidence. But if it filters by observation_timestamp, it might include pre-April 15 placeholder evidence, creating a subtle look-ahead.
2. More critically: evidence recalibrations (new versions) have creation_timestamps at the time of recalibration. A backtest that does not filter by creation_timestamp would see post-event recalibrations as if they were available before the event — a severe form of look-ahead.
3. The correct question for historical analysis is: "what evidence had the IIOS created and stored by timestamp T?" — creation_timestamp ≤ T is the correct filter for this question.

**Consequence accepted:** Historical queries are slightly more complex (must specify analysis_timestamp). This complexity is mandatory and is enforced at the Retrieval Service layer.

---
## SUPPLEMENT J — EVIDENCE CALIBRATION METHODOLOGY

### J.1 Overview

Evidence calibration is the systematic process of verifying that the confidence scores and weights assigned to evidence records correspond to empirically observed accuracy over time. This supplement defines the calibration methodology in sufficient detail for the Evidence Evolution Manager to implement it and for governance to audit it.

---

### J.2 The Calibration Problem

An evidence record with ECS = 0.80 is asserting that, when conditions match this evidence type and source profile, the condition being evaluated is correct approximately 80% of the time. This assertion must be testable.

The calibration problem has three dimensions:

1. **Binning accuracy** — Do records with ECS in [0.70, 0.80) show approximately 75% historical accuracy?
2. **Weight proportionality** — Do high-weight records contribute proportionally more predictive value to hypothesis outcomes than low-weight records of the same type?
3. **Regime sensitivity** — Do calibration parameters shift appropriately across regimes?

---

### J.3 Calibration Data Requirements

To calibrate evidence record r, the following data must be available:

| Requirement | Description |
|---|---|
| Outcome record | The actual outcome of the condition that evidence r evaluated |
| Matching criteria | The set of conditions defining "similar" records (same type, same source tier, similar regime) |
| Minimum sample | At least 50 completed outcome records per calibration bin |
| Maximum staleness | No calibration uses outcome records older than 2 years |
| Look-ahead compliance | All outcome records must postdate their evidence_timestamp by the appropriate evaluation horizon |

---

### J.4 Calibration Procedure

#### J.4.1 Evidence Type Calibration

For each evidence type T and source tier S:

1. Retrieve all evidence records of type T from source tier S with OUTCOME_AVAILABLE status.
2. Group into ECS bins: [0.0–0.2), [0.2–0.4), [0.4–0.6), [0.6–0.8), [0.8–1.0].
3. For each bin, compute: observed_accuracy = count(correct outcomes) / count(total outcomes).
4. Compute calibration error: CE = |assigned_midpoint − observed_accuracy|.
5. If CE > 0.10 for any bin, flag the type for RECALIBRATION.
6. If CE > 0.20 for any bin, escalate to governance as CALIBRATION_BREACH.

#### J.4.2 Regime-Sensitive Calibration

The above procedure is repeated separately for each regime class:
- BULL_QUIET / BULL_VOLATILE
- BEAR_QUIET / BEAR_VOLATILE
- RANGE_QUIET / RANGE_VOLATILE
- CRISIS

Regime-specific calibration parameters override the type-level defaults when a sufficient sample (≥ 50) is available for that regime.

#### J.4.3 Temporal Drift Detection

Calibration is performed on a rolling 90-day window. Drift is detected by comparing:
- CE(current 90 days) vs CE(prior 90 days)
- If ΔCE > 0.05 and direction is worsening, trigger DRIFT_ALERT.
- If ΔCE > 0.10, trigger DRIFT_ESCALATION to Evidence Constitution governance.

---

### J.5 Reliability Score (ERS) Computation

The ERS for evidence type T from source S is computed monthly:

$$ERS(T, S) = w_A \cdot Acc + w_C \cdot Cons + w_F \cdot Fresh + w_V \cdot Vol$$

Where:

| Variable | Meaning | Weight |
|---|---|---|
| Acc | Empirical accuracy over rolling 90d (% of outcomes correctly predicted) | 0.40 |
| Cons | Consistency of ECS calibration across bins | 0.25 |
| Fresh | Average freshness of evidence at consumption time | 0.20 |
| Vol | 1 − coefficient_of_variation(ECS) — score stability | 0.15 |

ERS bounds: [0.0, 1.0]. ERS < 0.55 triggers SOURCE_TIER_REVIEW.

---

### J.6 Calibration Governance

| Trigger | Response | Governance level |
|---|---|---|
| CE > 0.10 for any bin | Automatic recalibration proposed; requires human approval | MEDIUM |
| CE > 0.20 for any bin | Mandatory recalibration; evidence type suspended pending approval | HIGH |
| Drift ΔCE > 0.05 | DRIFT_ALERT; 14-day remediation window | MEDIUM |
| Drift ΔCE > 0.10 | DRIFT_ESCALATION; 7-day remediation window; potential source downgrade | HIGH |
| ERS < 0.55 | Source tier review; evidence distribution rate reduction | HIGH |
| ERS < 0.40 | Source potentially downgraded; immediate governance review | CRITICAL |

---

### J.7 Weight Recalibration

Weight recalibration is distinct from confidence recalibration. Weights express relative analytical importance within a type; confidence expresses absolute accuracy.

Weight recalibration procedure:

1. Compute contribution score C(r) = correlation(weight(r), outcome_accuracy(r)) over the calibration window.
2. If rank correlation < 0.50, weight assignment rules for type T are not performing — flag for review.
3. If high-weight records consistently outperform low-weight records, weights are validated.
4. Regime-specific weight modifiers are recalibrated separately.

---

### J.8 Calibration Audit Trail

Every calibration event must produce an audit record containing:

- calibration_id (UUID)
- calibration_timestamp (UTC)
- evidence_type
- source_tier
- regime (if regime-specific)
- n_records_sampled
- ce_by_bin (JSON)
- ers_before / ers_after
- recalibration_applied (boolean)
- governance_approval_id (if required)
- calibrator_version (software version of Evolution Manager)

Calibration audit records are permanent and may not be modified or deleted.

---

## SUPPLEMENT K — EVIDENCE ENGINE PERFORMANCE BENCHMARKS

### K.1 Design Performance Targets

The following are the design performance targets for a compliant Evidence Engine implementation. These are not aspirational goals — they are contractual targets that a deployed Evidence Engine must meet before accepting live evidence production traffic.

| Metric | Target | Measurement Condition |
|---|---|---|
| Single evidence ingestion latency (p50) | ≤ 50ms | Single observation input, standard type |
| Single evidence ingestion latency (p99) | ≤ 200ms | Single observation input, standard type |
| Composite evidence assembly latency (p50) | ≤ 150ms | 3-observation composite |
| Composite evidence assembly latency (p99) | ≤ 500ms | 3-observation composite |
| Qualification throughput | ≥ 500 candidates/sec | Mixed type distribution |
| Distribution fan-out latency (p99) | ≤ 100ms | 10 concurrent consumers |
| EQS computation latency (p99) | ≤ 20ms | All 16 dimensions |
| ECS computation latency (p99) | ≤ 25ms | Standard modifier chain |
| Independence assessment latency (p99) | ≤ 30ms | Against 1,000 active records |
| Conflict detection latency (p99) | ≤ 40ms | Against 500 active records |
| Retrieval — single record by ID | ≤ 5ms | Post-cache |
| Retrieval — entity query (100 results) | ≤ 50ms | Post-index-warm |
| Retrieval — time-range query (1,000 results) | ≤ 200ms | Post-index-warm |
| Full pipeline (observation → ACTIVE) | ≤ 300ms | p99, single type |

---

### K.2 Capacity Targets

| Capacity Metric | Target |
|---|---|
| Active evidence records (hot tier) | ≤ 2,000,000 |
| Evidence records per day (peak) | ≤ 200,000 |
| Distinct evidence types active concurrently | ≤ 100 |
| Consumer subscriptions concurrently active | ≤ 50 |
| Conflict checks per second (peak) | ≤ 5,000 |
| Independence assessments per second (peak) | ≤ 5,000 |
| Lineage records per evidence record (average) | ≤ 10 |

---

### K.3 Availability and Resilience Targets

| Target | Requirement |
|---|---|
| Uptime SLA | 99.9% (≤ 8.76 hours/year downtime) |
| Recovery Time Objective (RTO) | ≤ 15 minutes |
| Recovery Point Objective (RPO) | ≤ 60 seconds |
| Warm restart with state recovery | ≤ 5 minutes |
| Maximum queue depth before backpressure | 10,000 candidates |
| Backpressure activation latency | ≤ 500ms |

---

### K.4 Quality SLA

| Quality Metric | Target |
|---|---|
| Mis-typed evidence rate | < 0.1% (of all evidence produced) |
| EQS below ACCEPTABLE tier (0.60) in production | < 5% |
| Calibration breach events per quarter | 0 (any breach is an incident) |
| Conflict detection false negative rate | < 1% |
| Lineage completeness | 100% (no evidence without full lineage) |
| Evidence records without valid ECS | 0 |

---

### K.5 Degraded Mode Performance

When operating in DEGRADED mode (one or more non-critical components unavailable):

| Degraded Component | Degraded Behaviour | Performance Impact |
|---|---|---|
| Independence Engine unavailable | Evidence flagged INDEPENDENCE_CHECK_SKIPPED; distributed at reduced effective weight | +0ms (skip); distributed at weight × 0.7 |
| Reliability Engine unavailable | ECS computed without ERS modifier; RELIABILITY_UNVERIFIED flag | ECS capped at 0.80 |
| Evolution Manager unavailable | No recalibration; no drift detection; CALIBRATION_STALE flag after 7 days | ERS treated as last known value |
| Conflict Manager unavailable | Evidence distributed; CONFLICT_CHECK_SKIPPED flag | p99 latency unchanged; consumers warned |
| History Manager unavailable | Evidence not versioned; creation blocked for already-versioned types | New evidence only (version_number=1) accepted |

---
## SUPPLEMENT L — EVIDENCE ENGINE INTEGRATION CONTRACTS

### L.1 Overview

The Evidence Engine has formal integration contracts with every system it communicates with. These contracts define the exact protocol, payload schema, error handling, and SLA for each integration point. Any change to a contract requires Architecture Board approval.

---

### L.2 Contract with the Observation Engine (Upstream)

**Direction:** Observation Engine → Evidence Engine  
**Channel:** Event bus subscription (evidence-qualified-observations topic)  
**Protocol:** Publish-subscribe; at-least-once delivery with deduplication by observation_id

| Field | Type | Required | Notes |
|---|---|---|---|
| observation_id | UUID | Yes | Canonical ID from Observation Engine |
| symbol | String | Yes | Canonical entity symbol |
| observation_type | String | Yes | From Observation Engine taxonomy |
| observation_timestamp | UTC datetime | Yes | PIT anchor |
| capture_timestamp | UTC datetime | Yes | When IIOS captured this |
| observation_quality_score | Float [0,1] | Yes | OQS from Observation Engine |
| source_trust_tier | Enum | Yes | AUTHORITATIVE/RELIABLE/STANDARD/PROVISIONAL/UNRELIABLE |
| data_payload | JSON object | Yes | Type-specific observation fields |
| context | JSON object | Yes | regime, session, vix, events |

**SLA:**  
- Observation Engine must deliver observations within 500ms of creation.  
- Evidence Engine must acknowledge within 2,000ms.  
- Unacknowledged observations are retried up to 3 times with exponential backoff (1s, 2s, 4s).  
- After 3 failures, observation is logged to DEAD_LETTER_QUEUE.

**Error conditions handled by Evidence Engine:**  
- Duplicate observation_id → silently deduplicated; no error.  
- Invalid schema → rejected with SCHEMA_VALIDATION_FAILED; dead-lettered.  
- Unknown observation_type → rejected with UNKNOWN_TYPE; dead-lettered.  
- OQS below floor (< 0.30) → accepted but immediately quarantined.

---

### L.3 Contract with the Hypothesis Engine (Downstream)

**Direction:** Evidence Engine → Hypothesis Engine  
**Channel:** Event bus publication (evidence-distribution topic) + on-demand retrieval API  
**Protocol:** Publish-subscribe for real-time; REST/gRPC for historical retrieval

**Real-time distribution payload:**

| Field | Type | Notes |
|---|---|---|
| evidence_id | String | Canonical evidence ID |
| evidence_type | String | Category and type |
| symbol | String | Canonical entity |
| evidence_timestamp | UTC datetime | When evaluated |
| status | Enum | Must be ACTIVE for distribution |
| weight | Float [0,1] | Analytically assigned weight |
| effective_weight | Float [0,1] | After independence adjustment |
| ecs | Float [0,1] | Evidence Confidence Score |
| eqs | Float [0,1] | Evidence Quality Score |
| eqs_tier | Enum | EXCELLENT/GOOD/ACCEPTABLE/MARGINAL/POOR |
| conflict_status | Enum | NONE/MINOR/MODERATE/MAJOR |
| independence_score | Float [0,1] | From Independence Engine |
| context | JSON object | regime, session, vix, events at evidence_timestamp |
| lineage_summary | JSON object | Root observation_ids (not full lineage) |

**SLA:**  
- Evidence Engine must publish ACTIVE evidence within 200ms of lifecycle transition to ACTIVE.  
- Hypothesis Engine must acknowledge within 1,000ms.  
- Evidence Engine does not retry distribution; the Hypothesis Engine must poll for gaps.

**On-demand retrieval API — endpoints:**

| Endpoint | Description | Max response time |
|---|---|---|
| GET /evidence/{evidence_id} | Single record by ID | 10ms |
| GET /evidence/entity/{symbol} | All active evidence for symbol | 100ms |
| GET /evidence/type/{type} | All active evidence for type | 100ms |
| GET /evidence/hypothesis/{hypothesis_id} | Evidence linked to a hypothesis | 150ms |
| GET /evidence/history?symbol=X&from=T1&to=T2 | PIT historical query | 300ms |

---

### L.4 Contract with the Knowledge Engine (Downstream)

**Direction:** Evidence Engine → Knowledge Engine  
**Channel:** Separate subscription topic (evidence-for-knowledge topic)  
**Protocol:** Publish-subscribe; at-least-once with deduplication

The Knowledge Engine receives the same payload as the Hypothesis Engine but additionally receives:
- Full lineage_graph (not summary) — required for Knowledge Engine's provenance tracing.
- version_chain summary — required for the Knowledge Engine's temporal consistency checks.
- calibration_metadata — ERS, calibration_timestamp, drift_status.

The Knowledge Engine must not make trading decisions from evidence — it uses evidence to update its knowledge graph only.

---

### L.5 Contract with the Research Layer (Downstream)

**Direction:** Evidence Engine → Research Layer  
**Channel:** Batch export API  
**Protocol:** REST; pull-based; bulk export with PIT compliance

The Research Layer is the only consumer permitted to receive ARCHIVED and RETIRED evidence records (for historical analysis). All other consumers receive only ACTIVE evidence.

Research Layer queries must include:
- analysis_timestamp: the PIT anchor for creation_timestamp filtering.
- date_range: the evidence_timestamp range.
- type_filter: one or more evidence types.

The Research Layer must acknowledge the PIT compliance requirement in every request header.

---

### L.6 Contract with the System Monitor (Telemetry)

**Direction:** Evidence Engine → System Monitor  
**Protocol:** Internal event bus (telemetry topic)  
**Frequency:** Per-evidence for lifecycle events; aggregated every 30 seconds for metrics

**Lifecycle events published (each evidence record):**

| Event | Trigger |
|---|---|
| EVIDENCE_CREATED | Candidate created |
| EVIDENCE_VALIDATED | Structural validation passed |
| EVIDENCE_QUALIFIED | Semantic qualification passed |
| EVIDENCE_ACTIVE | Lifecycle transitioned to ACTIVE |
| EVIDENCE_QUARANTINED | Any quarantine transition |
| EVIDENCE_CONFLICT_DETECTED | Conflict Manager detection |
| EVIDENCE_SUPERSEDED | Version supersession |

**Aggregate metrics (every 30 seconds):**

| Metric | Description |
|---|---|
| evidence_throughput | Records transitioned to ACTIVE in last 30s |
| pipeline_latency_p50/p99 | Full pipeline latency percentiles |
| queue_depth | Current candidate queue depth |
| quarantine_rate | % of candidates quarantined in last 5 minutes |
| conflict_rate | % of active records in conflict |
| eqs_distribution | Histogram of EQS tiers |
| ecs_distribution | Histogram of ECS tiers |

---

### L.7 Breaking Change Policy

A breaking change to any integration contract is any modification that:
- Removes a required field from a payload.
- Changes the type or format of an existing field.
- Changes the enum values for a status or tier field.
- Removes an API endpoint.
- Changes a delivery guarantee (e.g., from at-least-once to at-most-once).
- Reduces an SLA (e.g., increases maximum response time).

Breaking changes require:
1. Architecture Board approval (minimum 5-business-day review).
2. A migration plan with backward-compatibility period (minimum 30 days).
3. Notification to all registered consumers 30 days before activation.
4. A consumer acceptance test confirming the consumer can handle the new contract.

Additive changes (new optional fields, new optional endpoints) do not require approval but must be documented in the contract changelog within 3 business days.

---
## SUPPLEMENT M — EVIDENCE ENGINE FAILURE MODE ANALYSIS

### M.1 Critical Failure Modes

The following table enumerates the critical failure modes of the Evidence Engine, their detection mechanism, immediate response, and recovery procedure.

| ID | Failure Mode | Detection | Immediate Response | Recovery |
|---|---|---|---|---|
| FM-01 | Evidence Registry unavailable | Health check failure; write errors | Halt evidence creation; activate emergency buffer | Restart Registry; replay buffer; verify no gap |
| FM-02 | Independence Engine crash | Component health timeout | Flag all new evidence INDEPENDENCE_CHECK_SKIPPED; reduce effective weight by 30% | Restart; re-assess all evidence produced during outage |
| FM-03 | Confidence Engine crash | Component health timeout | Halt ECS computation; halt evidence distribution | Restart; recompute ECS for all CANDIDATE records in queue |
| FM-04 | Conflict Manager crash | Component health timeout | Continue distribution; flag all evidence CONFLICT_CHECK_SKIPPED | Restart; run retroactive conflict scan on last 60 minutes of evidence |
| FM-05 | Dead letter queue overflow | Queue depth > 10,000 | Alert CRITICAL; throttle observation ingestion by 50% | Diagnose dead letter causes; drain queue; restore ingestion rate |
| FM-06 | Calibration drift breach | CE > 0.20 in any bin | Suspend evidence type; alert governance | Recalibrate with governance approval; reinstate after validation |
| FM-07 | Lineage Manager failure | Write error on lineage creation | Halt evidence creation for affected records; queue for retry | Restore Lineage Manager; replay queued records |
| FM-08 | Version chain corruption | Integrity check failure | Quarantine affected evidence_id chain | Restore from audit log; rebuild version chain |
| FM-09 | EQS computation divergence | EQS > 1.0 or < 0.0 | Quarantine evidence record; alert | Investigate dimension computation; fix and reprocess |
| FM-10 | Distribution backpressure | Consumer queue > 10,000 | Activate backpressure; throttle creation | Identify slow consumer; apply consumer-specific rate limit |

---

### M.2 Cascade Risk Assessment

The Evidence Engine's downstream consumers (Hypothesis Engine, Knowledge Engine) depend on a continuous stream of ACTIVE evidence. A prolonged outage of the Evidence Engine will cause hypothesis formation to stall and knowledge updates to cease. The cascade risk assessment below quantifies the acceptable outage duration before downstream impact becomes severe.

| Duration | Downstream Impact |
|---|---|
| 0–2 minutes | Consumers continue with cached active evidence; no decision degradation |
| 2–10 minutes | Active evidence becomes stale; Hypothesis Engine applies staleness penalty; conviction scores reduce |
| 10–30 minutes | Hypotheses begin expiring; Decision Engine confidence below ACTIONABLE threshold; trading paused automatically |
| 30–60 minutes | RTO exceeded; emergency escalation required |
| > 60 minutes | Full system audit required before resuming evidence production |

---

### M.3 Non-Recoverable Failure Conditions

The following conditions represent non-recoverable failures that require human intervention before the Evidence Engine may resume:

1. **Evidence Registry corruption** — any evidence record with missing lineage, missing ECS, or version chain break. Full audit required before restart.
2. **Calibration fraud** — calibration records showing impossible values (CE < −0.05 or CE > 1.05). Indicates data tampering. Security review required.
3. **PIT breach** — any evidence record created with look-ahead evidence (creation_timestamp < evidence_timestamp). Full evidence purge for affected records required.
4. **Constitutional rule persistent violation** — any CRITICAL constitutional rule (EC-A, EC-B, EC-C) violated more than once in a 24-hour window. Architecture review required.

---

*End of EVIDENCE_ENGINE_ARCHITECTURE.md — IIOS-EVE-ENG-ARCH-001 v1.0 RATIFIED*

---