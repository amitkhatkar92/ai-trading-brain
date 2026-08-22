# HYPOTHESIS ENGINE ARCHITECTURE

**Document Code:** IIOS-HYP-ENG-ARCH-001  
**Version:** 1.0  
**Status:** RATIFIED  
**Classification:** INTERNAL — ARCHITECTURE  
**Layer:** Cognitive Layer 3 of 5  
**Predecessor Layer:** Evidence Engine (IIOS-EVE-ENG-ARCH-001)  
**Successor Layer:** Reasoning Engine (IIOS-RSN-ENG-ARCH-001)

---

## Document Purpose and Scope

This document defines the complete engineering architecture of the Hypothesis Engine — the third cognitive layer of the Investment Intelligence Operating System (IIOS). The Hypothesis Engine receives evaluated, weighted, confidence-scored evidence from the Evidence Engine and constructs structured, testable, ranked explanations of observed market conditions. These explanations — hypotheses — are the analytical inputs to the Reasoning Engine.

**Scope:**
- All components of the Hypothesis Engine
- The complete hypothesis lifecycle from evidence intake to retirement
- All processing pipelines, services, quality frameworks, and governance structures
- Constitutional rules governing hypothesis integrity
- Operational procedures

**Out of scope:**
- Implementation code of any form
- Database schema definitions
- API contracts
- Trade signals, trade recommendations, or trade decisions
- Prediction mechanisms of any kind

**Fundamental Constraint:** The Hypothesis Engine constructs explanations of observed conditions. It does not predict future states. It does not decide courses of action. It does not execute. Any component, process, or rule that would cause the Hypothesis Engine to produce a prediction, decision, or recommendation is a constitutional violation.

---

## Parent Documents

| Document | Code | Role |
|---|---|---|
| Investment Intelligence Operating System | IIOS-SYS-000 | System root |
| Master Knowledge Architecture | IIOS-MKA-001 | Knowledge framework |
| Engineering Standards | IIOS-ENG-STD-001 | Engineering constraints |
| Core Framework Architecture | IIOS-FWK-001 | Framework constraints |
| Database Persistence Architecture | IIOS-DB-ARCH-001 | Persistence layer |
| AI Trading Brain Engineering Blueprint | IIOS-BLUEPRINT-001 | System blueprint |
| Information Engine Architecture | IIOS-IE-ARCH-001 | Layer 0 upstream |
| Observation Engine Architecture | IIOS-OE-ARCH-001 | Layer 1 upstream |
| Evidence Engine Architecture | IIOS-EVE-ENG-ARCH-001 | Layer 2 upstream (direct) |
| Knowledge Engine Architecture | IIOS-KE-ARCH-001 | Downstream consumer |

---

## IIOS Cognitive Layer Stack

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 — DECISION ENGINE     decides, recommends, acts        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4 — REASONING ENGINE    reasons, infers, concludes       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3 — HYPOTHESIS ENGINE   explains, ranks, evolves  ◄ HERE │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2 — EVIDENCE ENGINE     evaluates, weighs, scores        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1 — OBSERVATION ENGINE  perceives, records, timestamps   │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 0 — INFORMATION ENGINE  validates, types, manages data   │
└─────────────────────────────────────────────────────────────────┘
```

**The Hypothesis Engine receives evaluated evidence and returns structured, scored, ranked hypotheses. It does not look below Layer 2 and does not produce outputs for Layer 5.**

---

## Hypothesis Engine Information Flow

```
EVIDENCE ENGINE
    │
    │  Active evidence (ACTIVE status, ECS, EQS, weight, context)
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  HYPOTHESIS ENGINE                                              │
│                                                                 │
│  Evidence Intake → Generation → Validation → Scoring           │
│       ↓                                                         │
│  Ranking → Conflict Detection → Context Assignment             │
│       ↓                                                         │
│  Fusion → Storage → Evolution → Distribution                   │
└─────────────────────────────────────────────────────────────────┘
    │
    │  Ranked, scored, context-enriched hypotheses
    ▼
REASONING ENGINE
```

---

## Table of Contents

1. PART I — HYPOTHESIS PHILOSOPHY
2. PART II — HYPOTHESIS MODEL
3. PART III — CORE COMPONENTS
4. PART IV — HYPOTHESIS LIFECYCLE
5. PART V — HYPOTHESIS SERVICES
6. PART VI — HYPOTHESIS PROCESSING PIPELINES
7. PART VII — HYPOTHESIS QUALITY FRAMEWORK
8. PART VIII — HYPOTHESIS GOVERNANCE
9. PART IX — HYPOTHESIS CONSTITUTION
10. PART X — HYPOTHESIS READINESS CHECKLIST
11. SUPPLEMENT A — HYPOTHESIS TAXONOMY
12. SUPPLEMENT B — SCORING REFERENCE
13. SUPPLEMENT C — CONFLICT MATRIX
14. SUPPLEMENT D — EVOLUTION EXAMPLES
15. SUPPLEMENT E — DEPENDENCY EXAMPLES
16. SUPPLEMENT F — ANTI-PATTERNS
17. SUPPLEMENT G — OPERATIONAL RUNBOOK
18. SUPPLEMENT H — GLOSSARY
19. DOCUMENT FOOTER

---

## PART I — HYPOTHESIS PHILOSOPHY

### 1.1 What is a Hypothesis?

A hypothesis is a structured, testable, evidence-supported explanation of an observed condition in the investment universe. It is the cognitive bridge between what the IIOS has observed and measured (observations and evidence) and what the IIOS might reason about and conclude (the Reasoning Engine's domain).

A hypothesis answers the question: *given this evidence, what is the most coherent explanation of what is occurring?*

The hypothesis is not a conclusion. It is not a signal. It is not a prediction. It is an explanation — a candidate account of reality that is consistent with the available evidence, capable of being tested against additional evidence, and subject to revision as the evidence picture evolves.

In the IIOS architecture, a hypothesis has five mandatory properties:

1. **Evidential grounding** — every hypothesis must be supported by at least one piece of active, qualified evidence. A hypothesis without evidence is a speculation and may not enter the Hypothesis Registry.
2. **Testability** — every hypothesis must specify what additional evidence would confirm, weaken, or refute it. An untestable hypothesis cannot be evolved or falsified, making it analytically inert.
3. **Explicitness** — every hypothesis must articulate the condition it is explaining in structured, unambiguous terms. Vague hypotheses ("something may be happening") are constitutionally prohibited.
4. **Temporality** — every hypothesis is time-bound. It explains conditions as they exist at the time of its construction, relative to a specific market regime and context. Hypotheses do not claim permanence.
5. **Independence from conclusions** — a hypothesis explains; it does not conclude. The Reasoning Engine uses hypotheses as inputs to form conclusions. A hypothesis that contains its own conclusion has violated the cognitive layer separation.

---

### 1.2 Why Hypotheses Exist

The IIOS processes an enormous volume of evidence simultaneously — market microstructure signals, fundamental data, macro indicators, technical patterns, behavioral signals, cross-asset relationships. No single piece of evidence is sufficient to explain what is occurring. The IIOS needs a mechanism for organising evidence into coherent explanatory frames — structured wholes that are more analytically useful than the sum of their evidence parts.

Hypotheses serve four architectural purposes:

**1. Organisation** — Hypotheses group related evidence into coherent explanatory units. Without hypotheses, the Reasoning Engine would receive thousands of disconnected evidence items and be required to discover their relationships on its own. The Hypothesis Engine performs this organisation work.

**2. Ranking** — Not all explanations are equally plausible. The Hypothesis Engine scores and ranks hypotheses by the strength, volume, and consistency of their evidence support. The Reasoning Engine receives a ranked set of explanations, not an undifferentiated cloud of evidence.

**3. Conflict management** — Multiple competing hypotheses may simultaneously explain the same observations. The Hypothesis Engine makes these conflicts explicit, resolves them where possible, and presents them transparently to the Reasoning Engine where they cannot be resolved.

**4. Evolution** — Market conditions change continuously. A hypothesis that was well-supported yesterday may be undermined by new evidence today. The Hypothesis Engine manages the lifecycle of hypotheses — updating scores, retiring unsupported hypotheses, and generating new ones as the evidence picture evolves.

---

### 1.3 Conceptual Distinctions — 20 Terms

The following 20 terms define the conceptual boundaries of the Hypothesis Engine's domain. Architectural clarity requires that each term be used precisely and that no term's meaning be substituted for another.

---

#### 1.3.1 Observation

An **Observation** is a structured, immutable, timestamped record of a perceived state or change in the investment universe, produced by the Observation Engine. Observations are the raw perceptions of the IIOS — they record what happened, without interpretation, inference, or explanation. The Hypothesis Engine does not consume observations directly. It consumes evidence derived from observations.

---

#### 1.3.2 Evidence

**Evidence** is an observation (or collection of observations) that has been evaluated, weighted, and confidence-scored by the Evidence Engine. Evidence is directional — it speaks toward or against specific categories of hypothesis. Evidence is the Hypothesis Engine's sole input. A hypothesis with no supporting evidence cannot exist in the IIOS.

---

#### 1.3.3 Fact

A **Fact** is an observation or evidence item that has been corroborated to a high confidence threshold and designated as ground truth by the Knowledge Engine. Facts are not produced by the Hypothesis Engine — they are produced by the Knowledge Engine from well-established, repeatedly confirmed evidence chains. The Hypothesis Engine uses facts as high-confidence evidence inputs when forming hypotheses, but does not itself designate anything as a fact.

---

#### 1.3.4 Assumption

An **Assumption** is an unverified premise accepted as true for the purposes of constructing a hypothesis. Assumptions differ from evidence in that they have no observational basis — they are taken as given rather than derived from measurement. The Hypothesis Engine uses assumptions only in conditional hypotheses (hypotheses of the form "if X is true, then Y explains the observations"). Assumptions must be explicitly flagged in hypothesis records and may not be treated as evidence.

---

#### 1.3.5 Inference

An **Inference** is a conclusion derived from evidence or observations through a defined logical or statistical reasoning step. Inferences are the output of the Reasoning Engine, not the Hypothesis Engine. The Hypothesis Engine does not infer — it constructs explanations. The distinction: a hypothesis says "the evidence is consistent with this explanation"; an inference says "the evidence implies this conclusion." The Hypothesis Engine stops at explanation; the Reasoning Engine proceeds to inference.

---

#### 1.3.6 Explanation

An **Explanation** is a structured account of why an observed condition exists, expressed in terms that are consistent with available evidence. The Hypothesis Engine produces explanations — specifically, structured, scored, ranked explanations. An explanation becomes a hypothesis when it has been formalised into the hypothesis schema, assigned a unique ID, linked to its supporting evidence, and scored.

---

#### 1.3.7 Hypothesis

A **Hypothesis** is a structured, testable, evidence-supported explanation of an observed condition in the investment universe. It is the primary output of the Hypothesis Engine. Every hypothesis has: a unique canonical ID, a hypothesis type, a subject entity or market domain, a structured assertion of the condition being explained, a list of supporting and contradicting evidence with their weights, a composite hypothesis score (HCS), a confidence score (HCS-C), a context record, a lifecycle status, and a version chain.

---

#### 1.3.8 Theory

A **Theory** is a well-established, repeatedly validated explanatory framework supported by extensive evidence across many market conditions and time periods. Theories in the IIOS (such as mean reversion, momentum, efficient market theory in various forms) inform the hypothesis generation templates used by the Hypothesis Generator. A theory is not produced by the Hypothesis Engine — it is part of the IIOS's foundational knowledge corpus, maintained by the Knowledge Engine.

---

#### 1.3.9 Reasoning

**Reasoning** is the process of deriving conclusions from hypotheses through structured logical, statistical, or causal analysis. Reasoning is performed by the Reasoning Engine (Layer 4), which takes hypotheses as input. The Hypothesis Engine does not reason — it explains. Reasoning answers the question "what does this explanation imply?"; explanation answers the question "what is occurring, given this evidence?"

---

#### 1.3.10 Prediction

A **Prediction** is a probabilistic assertion about a future state of the investment universe. Predictions are the output of the Prediction Engine (a component downstream of the Reasoning Engine). The Hypothesis Engine is architecturally forbidden from producing predictions. A hypothesis that reads "NIFTY50 will rise to 23,000 by Friday" is not a hypothesis — it is a prediction and constitutes a constitutional violation. A hypothesis reads: "NIFTY50 is exhibiting evidence consistent with a momentum continuation regime."

---

#### 1.3.11 Decision

A **Decision** is a chosen course of action in the investment universe — a commitment to buy, sell, hold, or hedge. Decisions are the output of the Decision Engine (Layer 5). The Hypothesis Engine is architecturally forbidden from producing decisions.

---

#### 1.3.12 Belief

A **Belief** is a subjective probability assigned to the truth of a proposition, held by an analytical agent (human or AI). In the IIOS, beliefs are tracked by the Conviction Engine at Layer 4. The Hypothesis Engine does not maintain beliefs — it maintains scored, evidence-grounded hypotheses. The difference: a belief may exist without evidence; a hypothesis may not.

---

#### 1.3.13 Conviction

**Conviction** is the degree of confidence with which the IIOS holds a particular analytical position, computed from the combined weight, consistency, and stability of the hypothesis body. Conviction is a Layer 4/5 concept — it is computed at the Reasoning Engine and Decision Engine layers from the ranked hypothesis set. The Hypothesis Engine produces the ranked hypothesis set that enables conviction computation but does not compute conviction itself.

---

#### 1.3.14 Probability

**Probability** is a numerical measure of the likelihood of a proposition being true, expressed in [0.0, 1.0]. In the Hypothesis Engine, probability appears in the Hypothesis Confidence Score (HCS-C) — the probability that the hypothesis correctly explains the current condition, given the available evidence. The Hypothesis Engine computes HCS-C; it does not compute the probability of future events.

---

#### 1.3.15 Possibility

**Possibility** is a binary assertion: a state is possible if it is not logically or physically prohibited. All hypotheses in the Hypothesis Registry are possible by definition (they passed the validity check). Possibility is a necessary but insufficient condition for a hypothesis to be useful — many mutually exclusive explanations may all be possible simultaneously.

---

#### 1.3.16 Likelihood

**Likelihood** is the relative probability of one hypothesis versus another, given the available evidence. The Hypothesis Ranking Engine produces likelihood-based rankings, expressing the relative plausibility of competing hypotheses. Likelihood is computed from the Hypothesis Score (HCS) using the evidence support, confidence, and consistency dimensions.

---

#### 1.3.17 Confidence

**Confidence** is the degree of certainty that a hypothesis correctly explains the current condition, accounting for evidence quality, evidence consistency, and evidence volume. The Hypothesis Confidence Score (HCS-C) quantifies confidence. Confidence is not certainty — even a high-confidence hypothesis (HCS-C = 0.95) may be incorrect. Confidence reflects the quality of the explanation given the available evidence.

---

#### 1.3.18 Working Hypothesis

A **Working Hypothesis** is a hypothesis currently in active use by the Reasoning Engine — one that has passed all validation and qualification stages, has been scored and ranked, and is being actively considered as an explanation of current market conditions. Working hypotheses are the live analytical substrate of the IIOS.

---

#### 1.3.19 Alternative Hypothesis

An **Alternative Hypothesis** is a competing explanation for the same observed conditions as a primary hypothesis, with different causal attribution or different scope. The Hypothesis Engine always maintains alternative hypotheses — the presence of alternative explanations is architecturally required to prevent the IIOS from locking onto a single explanation and ignoring contradicting evidence.

---

#### 1.3.20 Composite Hypothesis

A **Composite Hypothesis** is a hypothesis constructed from two or more constituent hypotheses that, when combined, produce a more complete or more coherent explanation of observed conditions than any constituent hypothesis alone. Composite hypotheses are produced by the Hypothesis Fusion Manager when constituent hypotheses are mutually reinforcing and non-contradictory.

---

### 1.4 Multiple Simultaneous Valid Hypotheses

A foundational architectural principle of the Hypothesis Engine is that multiple hypotheses may be simultaneously valid. This is not a failure mode — it is an accurate representation of the analytical state of a complex, uncertain market system.

**Why multiple valid hypotheses can coexist:**

1. **Evidence underdetermination** — The available evidence is often insufficient to uniquely determine a single correct explanation. Multiple hypotheses may be equally consistent with the evidence at a given point in time. The Hypothesis Engine preserves all valid explanations rather than forcing a premature selection.

2. **Complementary explanations** — Two hypotheses may explain different aspects of the same observation without contradiction. A momentum hypothesis and a liquidity hypothesis may simultaneously and correctly explain a large intraday move — the momentum explains the direction, the liquidity explains the speed.

3. **Different scope levels** — A macro hypothesis and a company-specific hypothesis may both be valid and both contribute to understanding the same price movement. They operate at different levels of the explanatory hierarchy.

4. **Regime uncertainty** — Market regime transitions are periods of genuine multi-hypothesis validity. During a transition from bull-quiet to bear-volatile, hypotheses premised on the old regime and hypotheses premised on the new regime may both have evidence support until the transition is confirmed.

**The Hypothesis Engine's response to multiple valid hypotheses:**
- All valid hypotheses are maintained in the Registry with their current scores.
- Hypotheses are ranked by score, not filtered to one.
- The Reasoning Engine receives the full ranked set.
- Conflicts between mutually exclusive hypotheses are explicitly flagged.
- Complementary non-conflicting hypotheses are presented together.

---

### 1.5 Hypothesis Engine Design Principles

1. **Explanatory completeness** — The Hypothesis Engine must generate all plausible explanations of observed conditions, not only the most obvious or most probable. Missing explanations are more dangerous than low-ranking ones.
2. **Evidence primacy** — No hypothesis may be constructed, scored, or ranked without evidence. The scores are the evidence speaking, not the Hypothesis Engine's prior beliefs.
3. **Structured testability** — Every hypothesis must specify the evidence that would confirm or refute it. Untestable hypotheses are rejected.
4. **Temporal precision** — Hypotheses explain current conditions as of a specific timestamp and market context. They do not claim to explain future conditions.
5. **Transparent conflict** — Competing explanations are not silently resolved. Conflicts are preserved and presented explicitly.
6. **Evolutionary continuity** — Hypotheses evolve as evidence evolves. The version chain of a hypothesis records this evolution permanently.
7. **Layer separation** — The Hypothesis Engine never imports concepts from Layer 4 (Reasoning) or Layer 5 (Decision). It receives from Layer 2 (Evidence) and delivers to Layer 4 (Reasoning) only.
8. **Auditability** — Every hypothesis must be fully reconstructable from its evidence at any historical point in time, using PIT semantics.

---
## PART II — HYPOTHESIS MODEL

### 2.1 Hypothesis Schema

Every hypothesis in the IIOS conforms to the following canonical schema. This schema is the immutable data contract for all hypothesis records.

**Canonical ID format:** `HYP-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`

Example: `HYP-TEC-MOM-20260703-00000001`

| Field | Type | Required | Description |
|---|---|---|---|
| hypothesis_id | String | Yes | Canonical globally unique ID |
| hypothesis_type | Enum | Yes | From the taxonomy in Part II |
| category_code | String | Yes | Category from taxonomy |
| version_number | Integer | Yes | Starts at 1; increments on revision |
| lifecycle_status | Enum | Yes | CANDIDATE/FORMING/ACTIVE/COMPETING/MERGED/SUPERSEDED/RETIRED/ARCHIVED |
| subject_entity_ids | List[String] | Yes | Canonical entity IDs being explained |
| subject_domain | Enum | Yes | Market domain of the subject |
| assertion | String | Yes | Structured natural language assertion of what is being explained |
| assertion_structured | JSON | Yes | Machine-readable structured form of the assertion |
| hypothesis_timestamp | UTC datetime | Yes | When the hypothesis was formed |
| creation_timestamp | UTC datetime | Yes | When the record was first stored |
| evidence_refs | List[EvidenceRef] | Yes | Min 1; all supporting and contradicting evidence |
| supporting_evidence_count | Integer | Yes | Count of supporting evidence items |
| contradicting_evidence_count | Integer | Yes | Count of contradicting evidence items |
| net_evidence_weight | Float [0,1] | Yes | Weighted sum of supporting minus contradicting |
| hcs | Float [0,1] | Yes | Hypothesis Composite Score |
| hcs_confidence | Float [0,1] | Yes | Hypothesis Confidence Score |
| hcs_tier | Enum | Yes | STRONG/CREDIBLE/PROVISIONAL/WEAK/SPECULATIVE |
| rank_in_type | Integer | No | Rank among hypotheses of the same type |
| rank_global | Integer | No | Global rank across all active hypotheses |
| context_record | ContextRecord | Yes | Market context at hypothesis_timestamp |
| parent_hypothesis_ids | List[String] | No | For composite/hierarchical hypotheses |
| child_hypothesis_ids | List[String] | No | For parent hypotheses |
| competing_hypothesis_ids | List[String] | No | Mutually exclusive alternatives |
| conflict_status | Enum | Yes | NONE/MINOR/MODERATE/MAJOR |
| testability_conditions | List[String] | Yes | Evidence conditions that would confirm/refute |
| falsification_conditions | List[String] | Yes | Evidence conditions that would invalidate |
| governance_tier | Enum | Yes | CRITICAL/HIGH/MEDIUM/LOW |
| domain_owner | String | Yes | Responsible domain team |
| audit_trail_id | UUID | Yes | Pointer to audit records |
| lineage_record_id | UUID | Yes | Pointer to evidence lineage |
| is_ai_generated | Boolean | Yes | True if generated by AI model |
| is_human_assisted | Boolean | Yes | True if human contributed to formation |
| evolution_generation | Integer | Yes | 0 = original; N = Nth evolved generation |

---

### 2.2 Hypothesis Lifecycle Statuses

| Status | Meaning |
|---|---|
| CANDIDATE | Being evaluated for validity; not yet active |
| FORMING | Evidence being assembled; validation in progress |
| ACTIVE | Valid, scored, available to Reasoning Engine |
| COMPETING | Active but in conflict with another hypothesis |
| MERGED | Absorbed into a composite hypothesis |
| SUPERSEDED | Replaced by a newer version |
| RETIRED | Withdrawn because evidence no longer supports it |
| ARCHIVED | Preserved for historical analysis; not active |

---

### 2.3 Hypothesis Category Taxonomy

#### 2.3.1 Market Hypothesis (CAT: MKT)

**Definition:** A hypothesis explaining the state or directional tendency of a broad market or market index — NIFTY50, BANKNIFTY, SENSEX, or major global indices — based on technical, fundamental, macro, or behavioural evidence.

**Scope:** Index-level or market-wide explanations. Not entity-specific (those are Company Hypotheses).

**Examples:**
- NIFTY50 is exhibiting technical distribution evidence consistent with a late bull-market topping process.
- The NSE market breadth is deteriorating while index price remains elevated, consistent with an internal rotation away from large caps.
- India VIX compression below 12 is consistent with market complacency accumulation.

**Canonical type codes:** MKT-TREND, MKT-REGIME, MKT-BREADTH, MKT-MOMENTUM, MKT-MEAN-REV, MKT-TOPPING, MKT-BOTTOMING, MKT-RANGE

**Characteristic evidence sources:** Index price observations, breadth indicators, VIX observations, institutional flow evidence, derivatives open interest.

---

#### 2.3.2 Technical Hypothesis (CAT: TEC)

**Definition:** A hypothesis explaining observed price and volume behaviour of a specific entity using technical analysis evidence — price patterns, indicator states, volume relationships, momentum measures.

**Scope:** Any tradeable entity. Technical hypotheses are characterised by their dependence on historical price-volume observations without reference to fundamental or macro factors.

**Examples:**
- TATASTEEL is exhibiting a confirmed volume-price divergence consistent with distribution accumulation near resistance.
- RELIANCE is in a technical momentum state: 20-day rate of change positive, RSI above 60, price above all major moving averages.
- NIFTYBANK has traced a descending triangle formation over 15 trading sessions.

**Canonical type codes:** TEC-MOM, TEC-REV, TEC-BREAKOUT, TEC-BREAKDOWN, TEC-PATTERN, TEC-VOLUME, TEC-INDICATOR, TEC-SUPPORT, TEC-RESISTANCE, TEC-RANGE

---

#### 2.3.3 Fundamental Hypothesis (CAT: FND)

**Definition:** A hypothesis explaining the valuation state or business condition of a company or sector based on financial metrics — earnings, revenue growth, margins, P/E ratios, debt ratios, cash flow generation.

**Scope:** Company-level or sector-level. Requires fundamental data evidence.

**Examples:**
- HDFC Bank is trading at a valuation discount to historical multiples inconsistent with its earnings growth trajectory.
- Nifty IT sector aggregate P/E is 27x, above the sector historical mean of 22x, consistent with moderate overvaluation evidence.
- INFOSYS revenue guidance reduction evidence is consistent with deteriorating order flow in the US banking segment.

**Canonical type codes:** FND-VALUATION, FND-EARNINGS, FND-REVENUE, FND-MARGINS, FND-CASHFLOW, FND-DEBT, FND-DIVIDEND, FND-MANAGEMENT

---

#### 2.3.4 Macro Hypothesis (CAT: MAC)

**Definition:** A hypothesis explaining the state of macroeconomic conditions and their relationship to market behaviour — interest rates, inflation, GDP, currency dynamics, central bank policy.

**Scope:** Economy-wide or cross-market. Macro hypotheses often form the context layer that modifies the interpretation of company and market hypotheses.

**Examples:**
- RBI rate hold evidence is consistent with a monetary policy pause regime that has historically supported equity valuations.
- India CPI above 6.0% evidence is consistent with a re-tightening risk hypothesis for the next policy cycle.
- USD/INR appreciation trend is consistent with risk-off capital flow evidence from FII outflow observations.

**Canonical type codes:** MAC-RATES, MAC-INFLATION, MAC-GROWTH, MAC-CURRENCY, MAC-POLICY, MAC-FISCAL, MAC-GLOBAL, MAC-LIQUIDITY

---

#### 2.3.5 Sector Hypothesis (CAT: SEC)

**Definition:** A hypothesis explaining the state, condition, or relative performance of a market sector — IT, Banking, Auto, Pharma, Energy, etc.

**Scope:** Sector-level. Bridges macro and company-level explanations.

**Examples:**
- Nifty Auto sector breadth improvement is consistent with a sector recovery hypothesis following Q1 volume weakness.
- Pharma sector is exhibiting a relative strength divergence from the broader market, consistent with a defensive rotation hypothesis.
- Banking sector NPA evidence from Q4 results is consistent with a credit quality stabilisation hypothesis.

**Canonical type codes:** SEC-ROTATION, SEC-MOMENTUM, SEC-RECOVERY, SEC-DETERIORATION, SEC-RELATIVE, SEC-DEFENSIVE, SEC-CYCLICAL

---

#### 2.3.6 Company Hypothesis (CAT: CMP)

**Definition:** A hypothesis explaining the state or condition of a specific listed company — its business trajectory, market position, management actions, or intrinsic valuation.

**Scope:** Single company. The most specific hypothesis level.

**Examples:**
- BAJAJFINSV management guidance reduction evidence is consistent with a credit stress hypothesis in the consumer lending segment.
- WIPRO order intake evidence for two consecutive quarters is consistent with a business recovery hypothesis following restructuring.

**Canonical type codes:** CMP-BUSINESS, CMP-VALUATION, CMP-MANAGEMENT, CMP-PRODUCT, CMP-COMPETITION, CMP-REGULATORY, CMP-TURNAROUND, CMP-DETERIORATION

---

#### 2.3.7 Liquidity Hypothesis (CAT: LIQ)

**Definition:** A hypothesis explaining the market liquidity conditions for an entity, sector, or market — depth, spread, turnover, institutional flow dynamics.

**Scope:** Any entity or market. Liquidity hypotheses explain conditions of market access, not fundamental value.

**Examples:**
- NSE midcap breadth deterioration evidence is consistent with a liquidity withdrawal hypothesis as FII flows exit risk assets.
- NIFTY futures open interest decline concurrent with price rise is consistent with a short-covering liquidity rally hypothesis.
- BANKNIFTY bid-ask spread widening evidence is consistent with reduced market-maker risk appetite.

**Canonical type codes:** LIQ-FLOW, LIQ-DEPTH, LIQ-SPREAD, LIQ-TURNOVER, LIQ-SHORTCOVERING, LIQ-ACCUMULATION, LIQ-DISTRIBUTION

---

#### 2.3.8 Volatility Hypothesis (CAT: VOL)

**Definition:** A hypothesis explaining the volatility state or volatility regime of a market or entity — compression, expansion, mean reversion, term structure.

**Scope:** Index or entity level. Volatility hypotheses are independent of directional hypothesis — volatility can expand in both bull and bear markets.

**Examples:**
- India VIX below 13 for 15 consecutive sessions is consistent with a volatility compression hypothesis preceding a regime expansion event.
- BANKNIFTY realized volatility exceeding implied volatility for three weeks is consistent with an options market mispricing hypothesis.

**Canonical type codes:** VOL-COMPRESSION, VOL-EXPANSION, VOL-MEAN-REV, VOL-TERM-STRUCT, VOL-REGIME, VOL-SKEW, VOL-SURFACE

---

#### 2.3.9 Sentiment Hypothesis (CAT: SNT)

**Definition:** A hypothesis explaining market participant sentiment conditions — optimism, pessimism, fear, greed, uncertainty — derived from sentiment evidence sources.

**Scope:** Market-wide, sector, or entity. Sentiment hypotheses derive primarily from news evidence, social evidence, survey evidence, and derivatives positioning.

**Examples:**
- Social media sentiment index for IT sector has reached extreme optimism territory, consistent with a sentiment exhaustion hypothesis.
- Options put-call ratio has reached a 52-week high, consistent with a maximum pessimism hypothesis.

**Canonical type codes:** SNT-EXTREME-FEAR, SNT-EXTREME-GREED, SNT-OPTIMISM, SNT-PESSIMISM, SNT-UNCERTAINTY, SNT-REVERSAL

---

#### 2.3.10 Behavioral Hypothesis (CAT: BEH)

**Definition:** A hypothesis explaining observed market behaviour in terms of known cognitive biases, herd behaviour, anchoring effects, or other behavioural finance patterns.

**Scope:** Market-wide or entity-level. Behavioral hypotheses are among the most difficult to qualify because behavioural evidence is inherently noisier than price or fundamental evidence.

**Examples:**
- Retail inflow concentration into recent IPOs is consistent with a recency bias and FOMO behavioural hypothesis.
- Institutional anchoring to the 22,000 NIFTY support level is consistent with round-number anchoring evidence.

**Canonical type codes:** BEH-HERD, BEH-ANCHOR, BEH-FOMO, BEH-PANIC, BEH-RECENCY, BEH-OVERCONFIDENCE, BEH-LOSS-AVERSION

---

#### 2.3.11 Relationship Hypothesis (CAT: REL)

**Definition:** A hypothesis explaining the state of a relationship between two or more entities or markets — correlation, cointegration, spread, lead-lag dynamics.

**Scope:** Cross-entity. Consumes relationship evidence from the Relationship Engine and Evidence Engine.

**Examples:**
- HDFC Bank and ICICI Bank correlation has broken down from the historical 0.92 to 0.61, consistent with a sector-internal divergence hypothesis.
- Gold-equity inverse relationship evidence has weakened, consistent with a macro correlation regime shift hypothesis.

**Canonical type codes:** REL-CORRELATION, REL-DIVERGENCE, REL-COINTEGRATION, REL-SPREAD, REL-LEAD-LAG, REL-REGIME-SHIFT

---

#### 2.3.12 Event Hypothesis (CAT: EVT)

**Definition:** A hypothesis explaining how a specific event (earnings, policy announcement, regulatory action, geopolitical event) is affecting or will contextualise market conditions.

**Scope:** Event-linked. Event hypotheses are time-bounded — they are relevant for the duration of an event's analytical impact.

**Examples:**
- RBI policy announcement evidence is consistent with a market re-pricing hypothesis for rate-sensitive sectors.
- SEBI regulatory action on F&O evidence is consistent with a derivative market restructuring hypothesis.

**Canonical type codes:** EVT-CORPORATE, EVT-POLICY, EVT-REGULATORY, EVT-GEOPOLITICAL, EVT-ECONOMIC, EVT-MARKET-STRUCTURE

---

#### 2.3.13 Cross-Market Hypothesis (CAT: XMK)

**Definition:** A hypothesis explaining the relationship between Indian equity markets and other markets — US equities, Asian markets, bond markets, commodity markets.

**Scope:** Multi-market. Requires cross-market evidence.

**Examples:**
- US tech selloff evidence is consistent with a contagion risk hypothesis for Indian IT sector.
- Nikkei outperformance evidence concurrent with INR stability is consistent with Asian equity de-coupling from US risk-off hypothesis.

**Canonical type codes:** XMK-CONTAGION, XMK-DECOUPLING, XMK-CONVERGENCE, XMK-LEAD-LAG, XMK-REGIME-EXPORT

---

#### 2.3.14 Cross-Asset Hypothesis (CAT: XAS)

**Definition:** A hypothesis explaining the relationship between equity evidence and other asset class evidence — bonds, gold, commodities, currencies, crypto.

**Scope:** Multi-asset. High-level explanatory hypotheses that the Reasoning Engine uses to contextualise equity decisions.

**Examples:**
- Concurrent evidence of rising gold, falling equities, and falling 10-year yields is consistent with a risk-off flight-to-safety hypothesis.
- INR weakening concurrent with equity selling is consistent with a capital flight hypothesis rather than a pure equity-specific correction.

**Canonical type codes:** XAS-RISK-OFF, XAS-RISK-ON, XAS-FLIGHT-SAFETY, XAS-INFLATION, XAS-DEFLATION, XAS-CARRY

---

#### 2.3.15 Risk Hypothesis (CAT: RSK)

**Definition:** A hypothesis explaining the current risk state of the portfolio or a specific position — concentration risk, drawdown risk, tail risk, correlation risk.

**Scope:** Portfolio-level or position-level. Risk hypotheses are consumed by both the Reasoning Engine and the Risk Engine.

**Examples:**
- Current portfolio sector concentration evidence is consistent with a bank sector overweight risk hypothesis.
- Simultaneous drawdown across all positions is consistent with a correlated portfolio risk materialisation hypothesis.

**Canonical type codes:** RSK-CONCENTRATION, RSK-DRAWDOWN, RSK-TAIL, RSK-CORRELATION, RSK-LIQUIDITY, RSK-REGIME

---

#### 2.3.16 Portfolio Hypothesis (CAT: PRT)

**Definition:** A hypothesis explaining the current state or trajectory of the portfolio as a whole — performance attribution, factor exposure, style drift, return decomposition.

**Scope:** Portfolio-level. Portfolio hypotheses inform the Reasoning Engine's capital allocation considerations.

**Examples:**
- Portfolio performance attribution evidence is consistent with a factor rotation hypothesis — momentum exposure is outperforming while value exposure is lagging.
- Portfolio Sharpe decline evidence is consistent with a risk-adjusted return deterioration hypothesis driven by increased position correlation.

**Canonical type codes:** PRT-ATTRIBUTION, PRT-FACTOR, PRT-STYLE, PRT-RETURN, PRT-RISK-ADJ

---

#### 2.3.17 Composite Hypothesis (CAT: COM)

**Definition:** A hypothesis constructed from two or more constituent hypotheses of different categories that, together, provide a more complete explanation of observed market conditions than any constituent hypothesis alone.

**Scope:** Multi-category. Requires Hypothesis Fusion Manager.

**Examples:**
- Composite: [NIFTY technical distribution hypothesis] + [FII liquidity withdrawal hypothesis] + [macro rate uncertainty hypothesis] = a comprehensive market-wide weakness explanation.
- Composite: [HDFC Bank fundamental undervaluation hypothesis] + [banking sector recovery hypothesis] = a sector-backed company-specific opportunity explanation.

**Canonical type codes:** COM-MARKET, COM-SECTOR, COM-COMPANY, COM-RISK, COM-PORTFOLIO

---

#### 2.3.18 Historical Hypothesis (CAT: HIS)

**Definition:** A hypothesis generated retrospectively for backtesting and research purposes — explaining market conditions at a past point in time. Historical hypotheses use PIT-compliant evidence only.

**Scope:** Any category. Must be explicitly flagged as historical.

**Canonical type codes:** HIS-{category_code} (inherits category from subject domain)

---

#### 2.3.19 AI-Generated Hypothesis (CAT: AIG)

**Definition:** A hypothesis generated autonomously by an AI model component of the Hypothesis Generator. AI-generated hypotheses must pass the same validation and qualification pipeline as all other hypotheses. The AI generation model and version must be recorded.

**Scope:** Any category.

**Canonical type codes:** AIG-{category_code} (inherits category from subject domain)

---

#### 2.3.20 Human-Assisted Hypothesis (CAT: HUM)

**Definition:** A hypothesis that incorporates direct human analytical input — either fully designed by a human analyst or co-constructed between a human and the AI generation system. Human-assisted hypotheses must be traced to the contributing analyst.

**Scope:** Any category.

**Canonical type codes:** HUM-{category_code} (inherits category from subject domain)

---

### 2.4 HCS Tier Definitions

| Tier | HCS Range | Meaning | Reasoning Engine treatment |
|---|---|---|---|
| STRONG | 0.80–1.00 | Well-supported; high-confidence explanation | Primary consideration |
| CREDIBLE | 0.65–0.79 | Substantially supported; moderate confidence | Active consideration |
| PROVISIONAL | 0.50–0.64 | Partially supported; requires more evidence | Background consideration |
| WEAK | 0.35–0.49 | Minimally supported; high uncertainty | Noted but low weight |
| SPECULATIVE | 0.00–0.34 | Minimal evidence; highly uncertain | Monitoring only |

---
## PART III — CORE COMPONENTS

The Hypothesis Engine is organised into 20 core components across 5 functional clusters.

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLUSTER 1 — REGISTRY & CATALOG                                     │
│  Hypothesis Registry | Hypothesis Catalog                           │
├─────────────────────────────────────────────────────────────────────┤
│  CLUSTER 2 — GENERATION                                             │
│  Hypothesis Builder | Hypothesis Generator | Hypothesis Matcher     │
├─────────────────────────────────────────────────────────────────────┤
│  CLUSTER 3 — EVALUATION                                             │
│  Hypothesis Validator | Hypothesis Scoring Engine                   │
│  Hypothesis Confidence Engine | Hypothesis Comparator               │
│  Hypothesis Ranking Engine                                          │
├─────────────────────────────────────────────────────────────────────┤
│  CLUSTER 4 — MANAGEMENT                                             │
│  Hypothesis Dependency Manager | Hypothesis Context Manager         │
│  Hypothesis Evolution Manager | Hypothesis Conflict Manager         │
│  Hypothesis Fusion Manager | Hypothesis Version Manager             │
├─────────────────────────────────────────────────────────────────────┤
│  CLUSTER 5 — GOVERNANCE & OPERATIONS                                │
│  Hypothesis Search Manager | Hypothesis Governance Manager          │
│  Hypothesis Audit Manager | Hypothesis Archive Manager              │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 3.1 CLUSTER 1 — REGISTRY AND CATALOG

#### 3.1.1 Hypothesis Registry

**Purpose:** The single source of truth for all hypothesis records in the IIOS. All hypothesis creation, version transitions, status transitions, and retirement events are permanently recorded in the Registry.

**Responsibilities:**
- Persist all hypothesis records in structured, queryable form.
- Enforce global uniqueness of hypothesis_ids.
- Maintain complete version chains for every hypothesis.
- Support point-in-time queries (retrieve hypothesis state as of timestamp T).
- Enforce immutability of committed hypothesis versions.
- Provide consistency guarantees across concurrent reads and writes.
- Maintain the global hypothesis count, active count, and tier distribution.

**Inputs:**
- New hypothesis records from Hypothesis Builder.
- Version update records from Hypothesis Version Manager.
- Status transition commands from lifecycle management components.
- Archive commands from Hypothesis Archive Manager.

**Outputs:**
- Hypothesis records to all consumers (Reasoning Engine, Hypothesis Search Manager, Hypothesis Ranking Engine).
- Point-in-time hypothesis snapshots to the Historical Evaluation Pipeline.
- Registry metrics to the Health Service.

**Dependencies:** Database Persistence Layer; Hypothesis Version Manager; Identity Manager.

**Interactions:**
- All 20 Hypothesis Engine components interact with the Registry for read access.
- Write access is restricted to the Hypothesis Builder, Version Manager, and Governance Manager.

**Failure Modes:**
- Write failure: hypothesis creation pipeline stalls; buffer activates.
- Read failure: consumers receive cached snapshots; cache staleness alert triggered.
- Corruption: integrity check failure triggers immediate quarantine of affected records.

**Recovery Strategy:** Warm restart with state recovery from last checkpoint; replay write-ahead log; integrity check all records modified in the last 60 minutes.

**Monitoring:** Registry size (records), write throughput (records/min), read latency (p50/p99), version chain integrity check results, quarantine rate.

**Scalability:** Read-replicas for consumer access; partitioned by hypothesis_type for write sharding.

**Extensibility:** New hypothesis fields added as optional schema extensions; never remove existing fields.

**Engineering Notes:** PIT query performance is critical — capture_timestamp index must be maintained and never dropped.

---

#### 3.1.2 Hypothesis Catalog

**Purpose:** The authoritative registry of all hypothesis type definitions, generation templates, scoring parameters, and governance metadata. The Catalog is the configuration layer for the Hypothesis Engine.

**Responsibilities:**
- Maintain the canonical definition of every hypothesis type code.
- Store generation templates (evidence patterns that trigger hypothesis generation) for each type.
- Store scoring weight configurations per type.
- Maintain freshness SLAs and governance tiers per type.
- Version-control all catalog entries — changes to templates or weights create new catalog versions.
- Reject hypothesis records referencing undefined type codes.

**Inputs:**
- Type definition updates from Hypothesis Governance Manager.
- Template updates from the Research and Evolution subsystems.

**Outputs:**
- Type definitions to Hypothesis Builder, Generator, and Validator.
- Scoring parameters to Hypothesis Scoring Engine.
- Governance metadata to Hypothesis Governance Manager.

**Dependencies:** Hypothesis Governance Manager; Evidence Engine Catalog (for evidence type alignment).

**Interactions:**
- Hypothesis Builder reads templates at hypothesis construction time.
- Hypothesis Validator reads type requirements for validation rules.
- Hypothesis Scoring Engine reads weight configurations.

**Failure Modes:**
- Catalog unavailable: hypothesis creation is blocked; emergency use of last cached catalog version with CATALOG_STALE flag.
- Template corruption: affected hypothesis type is suspended pending repair.

**Recovery Strategy:** Restore catalog from last known-good snapshot; re-validate all active hypotheses against restored catalog.

**Monitoring:** Catalog version, type count, template health, last update timestamp per type.

**Engineering Notes:** The Catalog is read-heavy and write-rare. It should be fully cached in memory with write-through semantics.

---

### 3.2 CLUSTER 2 — GENERATION

#### 3.2.1 Hypothesis Builder

**Purpose:** Constructs hypothesis candidate records from incoming evidence items and Catalog templates, assembling all required fields and linking supporting and contradicting evidence.

**Responsibilities:**
- Receive qualified evidence items from the Evidence Engine.
- Match evidence to hypothesis templates from the Catalog.
- Assemble the hypothesis candidate record: assign fields, link evidence, compute initial net_evidence_weight.
- Request hypothesis_id from the Identity Manager.
- Submit the complete candidate to the Hypothesis Validator.
- Handle multi-evidence assembly for composite hypothesis construction.
- Log all construction events to the audit trail.

**Inputs:**
- Active evidence records from the Evidence Engine (via subscription).
- Hypothesis templates from the Hypothesis Catalog.
- Hypothesis generation signals from the Hypothesis Generator.

**Outputs:**
- Hypothesis candidate records to the Hypothesis Validator.
- Construction event logs to the Audit Manager.

**Dependencies:** Hypothesis Catalog; Evidence Engine distribution service; Hypothesis Validator; Identity Manager.

**Interactions:**
- Works closely with the Hypothesis Generator (Generator identifies the opportunity; Builder assembles the record).
- Passes completed candidates to the Validator.

**Failure Modes:**
- Evidence payload incomplete: partial hypothesis flagged FORMING; builder waits for missing fields (timeout: 60s).
- Template not found: evidence discarded with TEMPLATE_NOT_FOUND log.

**Recovery Strategy:** Failed constructions are retried once; on second failure, logged to dead-letter queue for manual review.

**Monitoring:** Construction throughput, average construction latency, failure rate, dead-letter queue depth.

**Engineering Notes:** The Builder is stateless per hypothesis — it constructs one record per invocation. State across evidence accumulation is managed by the Dependency Manager.

---

#### 3.2.2 Hypothesis Generator

**Purpose:** The intelligence layer of the Generation cluster — identifies when evidence patterns warrant hypothesis generation, selects the appropriate hypothesis type, and signals the Hypothesis Builder.

**Responsibilities:**
- Continuously monitor the active evidence stream for patterns matching generation triggers.
- Maintain a pattern-matching engine against all active Catalog templates.
- Detect when evidence accumulation crosses the minimum threshold for hypothesis generation (configurable per type: default = 2 supporting evidence items with combined net_evidence_weight ≥ 0.40).
- Signal the Hypothesis Builder with the matched template and the triggering evidence set.
- Prevent duplicate hypothesis generation (check Registry before signalling).
- Handle the AI generation path: route AI-generated hypotheses through the standard Builder and Validator.
- Track near-miss patterns (evidence that almost triggered generation) for learning feedback.

**Inputs:**
- Active evidence stream from Evidence Engine.
- Generation trigger configurations from Hypothesis Catalog.
- Existing active hypotheses from Registry (for deduplication check).

**Outputs:**
- Generation signals (template + evidence set) to Hypothesis Builder.
- Near-miss logs to the Evolution Manager.
- Generation metrics to Health Service.

**Dependencies:** Evidence Engine distribution; Hypothesis Catalog; Hypothesis Registry; Hypothesis Builder.

**Failure Modes:**
- Pattern engine overload: evidence intake queue backs up; backpressure applied to Evidence subscription.
- Registry check timeout: generation may produce duplicate; deduplication fallback in Validator.

**Recovery Strategy:** Restart with pattern engine warm-up from last 15-minute evidence window.

**Monitoring:** Evidence intake rate, pattern match rate, generation rate, near-miss rate, deduplication rate.

**Engineering Notes:** The pattern engine must be incremental — it cannot reprocess the full evidence history on each new evidence arrival. Differential evaluation against the active evidence delta is required.

---

#### 3.2.3 Hypothesis Matcher

**Purpose:** Matches incoming evidence to existing hypotheses — determining whether new evidence supports or contradicts active hypotheses, and updating their net_evidence_weight accordingly.

**Responsibilities:**
- Subscribe to the active evidence stream.
- For each new evidence item, search the active hypothesis set for hypotheses that include that evidence type as a relevant evidence category.
- Determine directionality: does this evidence support or contradict the hypothesis?
- Update the hypothesis's evidence_refs, net_evidence_weight, and trigger re-scoring.
- Handle withdrawn evidence (evidence becoming SUPERSEDED) — remove the evidence link and trigger re-scoring.
- Prevent double-counting: the same evidence_id may support at most one direction for a given hypothesis.

**Inputs:**
- Active evidence stream from Evidence Engine (including status change events).
- Active hypothesis set from Registry.

**Outputs:**
- Update signals to Hypothesis Version Manager (triggering a new version with updated evidence refs).
- Re-score signals to Hypothesis Scoring Engine.

**Dependencies:** Evidence Engine; Hypothesis Registry; Hypothesis Version Manager; Hypothesis Scoring Engine.

**Failure Modes:**
- Registry query timeout: evidence match deferred; queued for retry in 5s.
- Version conflict: concurrent update by two evidence items; resolved by Version Manager's serial write.

**Monitoring:** Match rate (evidence items matched to hypotheses per minute), update throughput, version conflict rate.

---

### 3.3 CLUSTER 3 — EVALUATION

#### 3.3.1 Hypothesis Validator

**Purpose:** Performs structural and semantic validation of hypothesis candidates before they enter the Registry as ACTIVE hypotheses.

**Responsibilities:**
- L1 — Schema validation: all required fields present and correctly typed.
- L2 — Identity validation: hypothesis_id is unique; entity_ids exist in Entity Registry.
- L3 — Evidence validation: all evidence_refs exist in Evidence Registry; evidence is ACTIVE status.
- L4 — Temporal validation: hypothesis_timestamp is not in the future; not more than 5 minutes before creation_timestamp.
- L5 — Semantic validation: the assertion field is non-empty and non-trivial; testability_conditions is non-empty.
- L6 — Type validation: hypothesis_type is a valid code in the Catalog.
- L7 — Threshold validation: at least 1 supporting evidence item with net_evidence_weight ≥ 0.20.
- Reject hypotheses failing any level; log rejection reason; forward to dead-letter queue.
- Pass valid candidates to the Hypothesis Scoring Engine.

**Inputs:**
- Hypothesis candidate records from Hypothesis Builder.

**Outputs:**
- VALID candidates to Hypothesis Scoring Engine.
- REJECTED candidates with rejection codes to dead-letter queue and Audit Manager.

**Dependencies:** Entity Registry; Evidence Registry; Hypothesis Catalog.

**Failure Modes:**
- Evidence Registry timeout: validation halted; candidate queued for retry (max 3 attempts, 30s spacing).

**Recovery Strategy:** Restart with empty candidate queue; resubmit buffered candidates.

**Monitoring:** Validation throughput, rejection rate by level, retry rate, dead-letter queue depth.

---

#### 3.3.2 Hypothesis Scoring Engine

**Purpose:** Computes the Hypothesis Composite Score (HCS) and Hypothesis Confidence Score (HCS-C) for every hypothesis, using the 10 quality dimensions defined in Part VII.

**Responsibilities:**
- Compute HCS from the 10 quality dimensions and their weights (defined in Part VII).
- Compute HCS-C from evidence confidence, consistency, and calibration parameters.
- Assign HCS_tier based on tier thresholds.
- Recompute scores whenever evidence refs change (triggered by Hypothesis Matcher) or context changes.
- Apply regime-specific scoring modifiers from the Catalog.
- Store scoring audit records for every scoring event.
- Maintain scoring calibration parameters from the Evolution Manager.

**Inputs:**
- Validated hypothesis candidates from Validator.
- Evidence records (via evidence_refs) for each hypothesis.
- Scoring weights from Hypothesis Catalog.
- Regime context from Context Manager.

**Outputs:**
- Scored hypothesis records (with hcs, hcs_confidence, hcs_tier) to Hypothesis Version Manager.
- Re-score signals to Ranking Engine.
- Scoring audit records to Audit Manager.

**Dependencies:** Evidence Registry; Hypothesis Catalog; Hypothesis Context Manager; Hypothesis Version Manager.

**Failure Modes:**
- Evidence not found (evidence_id no longer in Registry): scoring fails; hypothesis held at FORMING; alert raised.

**Monitoring:** Scoring throughput (hypotheses/min), average scoring latency, score distribution, calibration drift flag.

---

#### 3.3.3 Hypothesis Confidence Engine

**Purpose:** Computes the Hypothesis Confidence Score (HCS-C) specifically — a rigorous probabilistic assessment of how likely the hypothesis is to be the correct explanation of the observed conditions.

**Responsibilities:**
- Aggregate ECS values from all supporting evidence items, accounting for evidence independence.
- Apply the corroboration multiplier (additional independent supporting evidence increases confidence; correlated evidence does not).
- Apply the contradiction penalty (contradicting evidence reduces confidence proportional to its ECS and weight).
- Apply the calibration factor from historical accuracy records (how often has this hypothesis type from these evidence patterns been correct?).
- Produce a calibrated HCS-C in [0.0, 1.0].
- Flag hypotheses where historical calibration data is insufficient (< 30 comparable historical cases): CONFIDENCE_UNCALIBRATED.

**Inputs:**
- Evidence records with ECS, weight, and independence_score from Evidence Engine.
- Historical calibration records from Hypothesis Evolution Manager.
- Hypothesis type from the candidate record.

**Outputs:**
- HCS-C value to Scoring Engine.
- Calibration flags to hypothesis record.

**Dependencies:** Evidence Registry; Hypothesis Evolution Manager; Hypothesis Catalog.

**Failure Modes:**
- Evolution Manager unavailable: HCS-C computed without calibration correction; CONFIDENCE_UNCALIBRATED flag applied.

**Monitoring:** Average HCS-C by type, calibration breach rate, uncalibrated hypothesis percentage.

---

#### 3.3.4 Hypothesis Comparator

**Purpose:** Performs pairwise and multi-way comparison of hypotheses explaining the same subject entity and domain, establishing dominance relationships and relative plausibility ordering.

**Responsibilities:**
- Identify hypothesis pairs/groups that are candidates for comparison (same subject, same domain, overlapping observation window).
- Compute the comparative advantage of each hypothesis across each scoring dimension.
- Determine dominance relationships: hypothesis A dominates hypothesis B if A scores higher on at least one dimension and not lower on any.
- Identify tie cases and flag them as such.
- Feed comparison results to the Hypothesis Ranking Engine.
- Identify cases where two hypotheses are mutually exclusive (competing hypotheses) and flag for Conflict Manager.

**Inputs:**
- Active hypothesis set from Registry (filtered by subject and domain).
- Hypothesis scores from Scoring Engine.

**Outputs:**
- Comparison results (dominance matrix) to Ranking Engine.
- Competing hypothesis flags to Conflict Manager.

**Dependencies:** Hypothesis Registry; Hypothesis Scoring Engine; Hypothesis Conflict Manager.

**Failure Modes:**
- Registry overload: comparison deferred for lower-priority hypothesis types.

**Monitoring:** Comparison throughput, dominance ratio (how many pairs have clear dominance vs ties), competing pair count.

---

#### 3.3.5 Hypothesis Ranking Engine

**Purpose:** Produces and maintains the global and type-specific rankings of active hypotheses, enabling the Reasoning Engine to consume hypotheses in priority order.

**Responsibilities:**
- Maintain a sorted ranking of all active hypotheses globally (rank_global).
- Maintain separate sorted rankings per hypothesis type (rank_in_type).
- Update rankings whenever any hypothesis's HCS changes (triggered by re-scoring).
- Implement the ranking algorithm: primary sort by HCS descending; secondary sort by HCS-C descending; tertiary sort by evidence volume.
- Publish ranking updates to the Distribution Service.
- Handle tie-breaking using the hypothesis_timestamp (older hypothesis with equal score ranks higher).
- Support regime-sensitive ranking: certain hypothesis types receive weighting boosts in specific regimes (configured in Catalog).

**Inputs:**
- Scored hypothesis records from Scoring Engine.
- Comparison results from Comparator.
- Regime context from Context Manager.

**Outputs:**
- Ranked hypothesis lists to Reasoning Engine (via Distribution Service).
- Ranking change events to Health Service.

**Dependencies:** Hypothesis Scoring Engine; Hypothesis Comparator; Hypothesis Context Manager.

**Failure Modes:**
- Re-ranking under high load: rankings may be up to 30 seconds stale during peak evidence intake; staleness flag applied.

**Monitoring:** Ranking latency, rank distribution by tier, rank churn rate (hypotheses changing rank position per minute).

---

### 3.4 CLUSTER 4 — MANAGEMENT

#### 3.4.1 Hypothesis Dependency Manager

**Purpose:** Tracks and enforces dependency relationships between hypotheses — parent-child relationships, supporting relationships, and logical dependency chains.

**Responsibilities:**
- Maintain the dependency graph: for every hypothesis, record which hypotheses it depends on and which depend on it.
- Propagate changes: when a parent hypothesis changes status (e.g., RETIRED), notify all child hypotheses and trigger re-evaluation.
- Detect circular dependencies (prohibited by the Constitution) and reject them.
- Support composite hypothesis assembly: verify that constituent hypotheses are dependency-compatible before fusion.
- Provide dependency path queries (what is the full dependency chain for a given hypothesis?).
- Enforce the constraint that a hypothesis cannot be ACTIVE if any of its required parent hypotheses are RETIRED.

**Inputs:**
- Hypothesis records with parent_hypothesis_ids and child_hypothesis_ids from Registry.
- Status change events from lifecycle management.

**Outputs:**
- Dependency propagation events to affected child hypotheses.
- Dependency violation alerts to Governance Manager.

**Dependencies:** Hypothesis Registry; Hypothesis Version Manager; Hypothesis Governance Manager.

**Failure Modes:**
- Dependency cycle detected: cycle is quarantined; both hypotheses moved to FORMING; alert raised.

**Monitoring:** Dependency graph size, cycle detection rate, propagation latency.

---

#### 3.4.2 Hypothesis Context Manager

**Purpose:** Maintains and enriches the ContextRecord attached to every hypothesis, ensuring that each hypothesis carries a complete description of the market conditions under which it was formed.

**Responsibilities:**
- Capture the market context at hypothesis_timestamp: regime, session, VIX level, market state, active events, macro calendar.
- Enrich hypothesis records with context at formation time.
- Update context records when significant context changes occur (regime transition, VIX spike, major event) — flagging hypotheses whose context has become stale.
- Provide context comparison between a hypothesis's formation context and the current context — enabling the Evolution Manager to assess whether context drift has undermined the hypothesis.
- Maintain a context registry of historical context snapshots for PIT queries.

**Inputs:**
- Context observations from Observation Engine (regime, VIX, session, events).
- Hypothesis records requiring context assignment.

**Outputs:**
- Context-enriched hypothesis records to Version Manager.
- Context staleness alerts to Evolution Manager.

**Dependencies:** Observation Engine; Hypothesis Version Manager; Hypothesis Evolution Manager.

**Failure Modes:**
- Context source unavailable: hypothesis created with CONTEXT_PARTIAL flag; alert raised.

**Monitoring:** Context freshness by domain, partial context rate, context update latency.

---

#### 3.4.3 Hypothesis Evolution Manager

**Purpose:** Manages the long-term evolution of hypotheses as evidence changes, calibrates scoring over time, detects drift, and governs hypothesis version progression.

**Responsibilities:**
- Monitor evidence changes against active hypotheses continuously.
- Determine when an evidence change warrants a new hypothesis version (score change > 0.05 or tier change).
- Signal the Version Manager to create a new version when warranted.
- Track hypothesis evolution trajectories: is the hypothesis strengthening, weakening, or stable?
- Perform long-term calibration: compare historical hypothesis outcomes against their HCS-C scores; detect calibration drift.
- Propose score recalibration when calibration error exceeds 0.10.
- Manage the evolution of generation templates based on historical performance: which evidence patterns reliably generate well-supported hypotheses?
- Maintain the evolution history (all past versions and their performance records).

**Inputs:**
- Evidence change events from Hypothesis Matcher.
- Historical hypothesis outcome records from Archive Manager.
- Context change events from Context Manager.

**Outputs:**
- Version creation signals to Version Manager.
- Calibration reports to Scoring Engine and Confidence Engine.
- Template improvement proposals to Hypothesis Catalog (via Governance Manager).

**Dependencies:** Hypothesis Matcher; Hypothesis Version Manager; Hypothesis Scoring Engine; Hypothesis Archive Manager.

**Failure Modes:**
- Evolution Manager offline: hypotheses are not evolved; evidence changes accumulate in delta buffer; processed on restart.

**Monitoring:** Evolution rate (versions created per hour), calibration error, template performance scores.

---

#### 3.4.4 Hypothesis Conflict Manager

**Purpose:** Detects, classifies, and manages conflicts between competing hypotheses that provide mutually exclusive explanations of the same subject and conditions.

**Responsibilities:**
- Continuously scan the active hypothesis set for conflicts.
- Define a conflict as: two or more hypotheses with the same subject domain, overlapping observation windows, and mutually exclusive assertions.
- Classify conflicts by severity: MINOR (both hypotheses WEAK tier; disagreement is low-stakes), MODERATE (at least one CREDIBLE tier), MAJOR (both CREDIBLE or STRONG tier; the conflict is analytically significant).
- For MINOR conflicts: set conflict_status = MINOR; no other action.
- For MODERATE conflicts: set conflict_status = MODERATE; flag for Evolution Manager review; present both to Reasoning Engine with conflict flag.
- For MAJOR conflicts: set conflict_status = MAJOR; alert immediately; trigger adjudication protocol; present both hypotheses to Reasoning Engine with CONFLICT_UNRESOLVED flag.
- Adjudication protocol: identify which hypothesis has stronger, more independent evidence; reduce effective weight of the weaker side; record adjudication in audit trail.
- Never suppress a conflicting hypothesis silently — conflict must always be visible to consumers.

**Inputs:**
- Active hypothesis set from Registry (updated continuously).
- Hypothesis score updates from Scoring Engine.

**Outputs:**
- Conflict status updates to hypothesis records (via Version Manager).
- Conflict alerts to Governance Manager and Health Service.
- Adjudication records to Audit Manager.

**Dependencies:** Hypothesis Registry; Hypothesis Version Manager; Hypothesis Governance Manager; Hypothesis Audit Manager.

**Failure Modes:**
- Conflict Manager offline: conflicting hypotheses distributed without conflict flag; CONFLICT_CHECK_SKIPPED flag applied to all active hypotheses.

**Monitoring:** Conflict count by severity, adjudication rate, resolution rate, average conflict duration.

---

#### 3.4.5 Hypothesis Fusion Manager

**Purpose:** Combines multiple compatible, mutually reinforcing hypotheses into composite hypotheses that provide richer, more complete explanations than any constituent hypothesis alone.

**Responsibilities:**
- Identify fusion candidates: hypotheses on the same or related subjects that are non-conflicting, mutually reinforcing, and together provide a more complete explanation.
- Apply fusion eligibility criteria: all constituent hypotheses must be ACTIVE; none may have conflict_status MAJOR; all must have HCS ≥ 0.40.
- Construct the composite hypothesis record, linking all constituent hypotheses as parent_hypothesis_ids.
- Compute the composite HCS as a weighted combination of constituent HCS values with coherence bonus.
- Transition constituent hypotheses to MERGED status after fusion (they are preserved but no longer independently distributed to the Reasoning Engine).
- Support composite dissolution: if a constituent hypothesis is retired or its score drops below threshold, dissolve the composite.

**Inputs:**
- Active hypothesis set from Registry.
- Dependency compatibility data from Dependency Manager.
- Fusion eligibility rules from Hypothesis Catalog.

**Outputs:**
- Composite hypothesis candidates to Hypothesis Builder (for construction into a new hypothesis record).
- MERGED status transitions to constituent hypotheses via Version Manager.

**Dependencies:** Hypothesis Registry; Hypothesis Dependency Manager; Hypothesis Builder; Hypothesis Version Manager.

**Failure Modes:**
- Fusion produces incoherent composite: composite rejected by Validator; constituent hypotheses remain ACTIVE independently.

**Monitoring:** Fusion rate, composite hypothesis count, dissolution rate, average composite HCS vs constituent average HCS.

---

#### 3.4.6 Hypothesis Version Manager

**Purpose:** Manages the version chain of every hypothesis, creating new versions on scoring changes, evidence updates, context changes, and governance revisions.

**Responsibilities:**
- Assign version numbers (incremental, starting at 1) to each hypothesis version.
- Create new version records with the delta (what changed from the previous version).
- Transition the previous version to SUPERSEDED when a new version is created.
- Enforce linear version chains (no branching).
- Maintain the version chain for every hypothesis_id.
- Support version queries: retrieve any version by hypothesis_id and version_number.
- Validate version lineage integrity on all reads from the Registry.

**Inputs:**
- Version creation signals from Scoring Engine, Context Manager, Evolution Manager, Matcher, Governance Manager.

**Outputs:**
- New version records to Hypothesis Registry.
- SUPERSEDED transitions for previous versions to Registry.

**Dependencies:** Hypothesis Registry.

**Failure Modes:**
- Write failure: version creation queued; retry with exponential backoff.
- Concurrent version creation conflict: serialised by the Registry write lock per hypothesis_id.

**Monitoring:** Version creation rate, version chain lengths, integrity check results.

---

### 3.5 CLUSTER 5 — GOVERNANCE AND OPERATIONS

#### 3.5.1 Hypothesis Search Manager

**Purpose:** Provides high-performance search and retrieval of hypotheses from the Registry, supporting ad-hoc analysis, research, and system-to-system queries.

**Responsibilities:**
- Maintain search indices: by entity, by type, by status, by HCS tier, by timestamp, by evidence_id.
- Support full-text search on hypothesis assertion fields.
- Support PIT queries: retrieve hypotheses active as of a specified timestamp.
- Support evidence-centric queries: find all hypotheses referencing a given evidence_id.
- Apply access control: enforce read permissions per hypothesis governance_tier.
- Cache frequently accessed hypothesis sets for low-latency retrieval.

**Inputs:**
- Search queries from Reasoning Engine, Research Layer, and Governance Manager.
- Registry updates (to maintain index freshness).

**Outputs:**
- Hypothesis result sets to query originators.

**Dependencies:** Hypothesis Registry; Access Control Layer.

**Failure Modes:**
- Index stale: queries fall back to Registry full-scan with performance degradation; alert raised.

**Monitoring:** Query throughput, query latency (p50/p99), cache hit rate, index freshness.

---

#### 3.5.2 Hypothesis Governance Manager

**Purpose:** Enforces governance policies across the Hypothesis Engine — type approval, access control, retention, compliance, and policy review.

**Responsibilities:**
- Approve new hypothesis type definitions before they enter the Catalog.
- Enforce retention policies: archive hypotheses older than the type-specific retention period.
- Manage access control lists for hypothesis types by governance tier.
- Trigger periodic governance reviews (weekly for HIGH tier types; monthly for MEDIUM; quarterly for LOW).
- Maintain the governance audit log: all governance decisions and policy changes.
- Enforce the Hypothesis Constitution (Part IX): detect constitutional rule violations and escalate.
- Manage the approval workflow for constitutional rule changes.

**Inputs:**
- New type proposals from Research Layer.
- Retention schedule from Hypothesis Catalog.
- Governance review triggers (scheduled).
- Constitutional violation alerts from all components.

**Outputs:**
- Approved/rejected type definitions to Hypothesis Catalog.
- Archive commands to Hypothesis Archive Manager.
- Governance audit records to Hypothesis Audit Manager.

**Dependencies:** Hypothesis Catalog; Hypothesis Audit Manager; Hypothesis Archive Manager.

**Failure Modes:**
- Governance Manager offline: new type approvals blocked; retention not enforced; alert raised.

**Monitoring:** Pending approvals, review cycle adherence, retention compliance rate, constitutional violation count.

---

#### 3.5.3 Hypothesis Audit Manager

**Purpose:** Maintains the complete, tamper-evident, append-only audit trail for all Hypothesis Engine operations.

**Responsibilities:**
- Record every hypothesis creation, status transition, scoring event, version creation, and deletion event.
- Record all governance decisions, access control changes, and constitutional rule violations.
- Record all conflict detections, adjudications, and resolutions.
- Enforce append-only semantics: no audit record may be modified or deleted.
- Retain audit records for the minimum required period (7 years for CRITICAL tier hypotheses).
- Provide audit query access to Governance Manager and Research Layer.
- Produce audit reports on demand.

**Inputs:**
- Audit events from all Hypothesis Engine components.

**Outputs:**
- Audit records (write-only) to audit log store.
- Audit query results to authorised consumers.

**Dependencies:** Audit Log Store; Hypothesis Governance Manager.

**Failure Modes:**
- Audit write failure: hypothesis operation is blocked (audit is mandatory; operation may not proceed without it).

**Monitoring:** Audit write throughput, audit store size, write failure rate.

---

#### 3.5.4 Hypothesis Archive Manager

**Purpose:** Manages the archival of expired, retired, and low-relevance hypotheses, ensuring historical preservation while keeping the active Registry lean.

**Responsibilities:**
- Monitor hypothesis ages against retention policy.
- Execute archival of hypotheses past their active-tier retention period.
- Ensure all archived hypotheses retain their complete version chain, evidence refs, and audit trail.
- Support retrieval of archived hypotheses for research and backtesting.
- Manage tiered storage: hot (active), warm (recently retired, 0–90 days), cold (archived, > 90 days).
- Never permanently delete hypotheses before their regulatory retention period expires.
- Coordinate with the History Manager for PIT query support on archived hypotheses.

**Inputs:**
- Archive commands from Governance Manager.
- Retirement events from lifecycle management.

**Outputs:**
- Archived hypothesis records to cold storage tier.
- Archive confirmation events to Registry (updating status to ARCHIVED).

**Dependencies:** Hypothesis Registry; Hypothesis Governance Manager; Persistence Layer.

**Failure Modes:**
- Archive storage full: new archives queued; capacity alert raised; no active hypotheses affected.

**Monitoring:** Archive queue depth, storage utilisation by tier, archive throughput.

---
## PART IV — HYPOTHESIS LIFECYCLE

### 4.1 Overview

Every hypothesis passes through a defined lifecycle from initial evidence intake to final archival. The lifecycle governs what happens to a hypothesis at each stage, what conditions must be met to progress, and what monitoring is applied.

The lifecycle has four phases and fifteen stages:

```
PHASE 1 — GENESIS          PHASE 2 — QUALIFICATION
  1. Evidence Intake           6.  Scoring
  2. Generation                7.  Ranking
  3. Validation                8.  Comparison
  4. Qualification             9.  Conflict Check
  5. Context Assignment       10.  Fusion (conditional)

PHASE 3 — ACTIVE LIFE      PHASE 4 — SUNSET
 11. Storage                  13. Review
 12. Evolution                14. Archive
                              15. Retirement
```

---

### 4.2 Lifecycle State Machine

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
                    ▼                                             │
 [Evidence Intake] → CANDIDATE ─────► FORMING ──────────────────┤
                                          │                      │
                              validation  │                      │
                                pass      ▼                      │
                                      VALIDATED                  │
                                          │                      │
                                    context assigned             │
                                          │                      │
                                          ▼                      │
                                       SCORED ──────────────────►│ (rescoring loop)
                                          │                      │
                                     conflict check              │
                                          │                      │
                              ┌───────────┴──────────┐          │
                              │                      │          │
                              ▼                      ▼          │
                           ACTIVE            COMPETING          │
                              │                  │              │
               ┌──────────────┼──────────────────┤             │
               │              │                  │             │
               ▼              ▼                  ▼             │
          SUPERSEDED        MERGED            RETIRED          │
               │              │                  │             │
               └──────────────┴──────────────────┴───► ARCHIVED◄─┘
```

---

### 4.3 Stage Definitions

#### Stage 1 — Evidence Intake

**Entry condition:** Evidence Engine publishes an ACTIVE evidence record.  
**Responsible component:** Hypothesis Generator.  
**Actions:** Evidence is evaluated against all generation templates. If a trigger pattern is matched, the evidence set is assembled.  
**Exit condition:** Generation signal sent to Hypothesis Builder OR evidence dropped (no template match).  
**Failure handling:** Unmatched evidence logged with NOT_MATCHED reason; not an error.  
**SLA:** ≤ 100ms from evidence publish to generation signal.

---

#### Stage 2 — Generation

**Entry condition:** Generation signal received by Hypothesis Builder.  
**Responsible component:** Hypothesis Builder.  
**Actions:** Hypothesis candidate record is assembled: all schema fields populated, hypothesis_id assigned, evidence refs linked, net_evidence_weight computed.  
**Exit condition:** Complete candidate record forwarded to Validator.  
**Failure handling:** Incomplete assembly → FORMING status; retry with timeout 60s.  
**SLA:** ≤ 200ms from signal to candidate submission.

---

#### Stage 3 — Validation

**Entry condition:** Hypothesis candidate received by Validator.  
**Responsible component:** Hypothesis Validator.  
**Actions:** Seven validation levels executed in sequence (L1 schema → L7 threshold). Any failure causes immediate rejection with reason code.  
**Exit condition:** VALID → proceed to Qualification. REJECTED → dead-letter queue.  
**Failure handling:** Rejected candidates logged with full reason chain; available for governance review.  
**SLA:** ≤ 50ms per candidate (seven levels in sequence).

---

#### Stage 4 — Qualification

**Entry condition:** Hypothesis has passed all 7 validation levels.  
**Responsible component:** Hypothesis Validator (semantic qualification pass) + Hypothesis Catalog (type-specific rules).  
**Actions:** Semantic qualification checks whether the hypothesis assertion is coherent for its type; applies type-specific qualification rules from the Catalog.  
**Exit condition:** QUALIFIED → proceed to Context Assignment. DISQUALIFIED → dead-letter queue.  
**Failure handling:** Disqualified candidates returned to analyst queue if human-assisted; discarded if fully AI-generated.

---

#### Stage 5 — Context Assignment

**Entry condition:** Qualified hypothesis candidate.  
**Responsible component:** Hypothesis Context Manager.  
**Actions:** ContextRecord is captured: regime, session, VIX, market state, active events. Context is attached to the hypothesis record.  
**Exit condition:** CONTEXT_COMPLETE → proceed to Scoring. CONTEXT_PARTIAL → proceed to Scoring with flag.  
**SLA:** ≤ 30ms.

---

#### Stage 6 — Scoring

**Entry condition:** Context-assigned hypothesis candidate.  
**Responsible component:** Hypothesis Scoring Engine + Hypothesis Confidence Engine.  
**Actions:** HCS computed across all 10 quality dimensions. HCS-C computed from evidence confidence and calibration. HCS_tier assigned.  
**Exit condition:** SCORED → proceed to Ranking.  
**SLA:** ≤ 50ms.

---

#### Stage 7 — Ranking

**Entry condition:** Scored hypothesis.  
**Responsible component:** Hypothesis Ranking Engine.  
**Actions:** Hypothesis inserted into global and type-specific ranking lists. rank_global and rank_in_type assigned.  
**Exit condition:** RANKED → proceed to Comparison.  
**SLA:** ≤ 20ms.

---

#### Stage 8 — Comparison

**Entry condition:** Ranked hypothesis.  
**Responsible component:** Hypothesis Comparator.  
**Actions:** New hypothesis is compared pairwise against active hypotheses with the same subject and domain. Dominance relationships updated.  
**Exit condition:** COMPARED → proceed to Conflict Check.  
**SLA:** ≤ 40ms.

---

#### Stage 9 — Conflict Check

**Entry condition:** Compared hypothesis.  
**Responsible component:** Hypothesis Conflict Manager.  
**Actions:** Conflict scan against active hypotheses. conflict_status set: NONE / MINOR / MODERATE / MAJOR. MAJOR conflicts trigger adjudication.  
**Exit condition:** ACTIVE (conflict_status NONE or MINOR). COMPETING (conflict_status MODERATE or MAJOR).  
**SLA:** ≤ 50ms.

---

#### Stage 10 — Fusion (Conditional)

**Entry condition:** Active hypothesis is identified as a fusion candidate by Fusion Manager.  
**Responsible component:** Hypothesis Fusion Manager.  
**Actions:** Fusion eligibility checked. If eligible, composite hypothesis constructed; constituents transitioned to MERGED.  
**Exit condition:** MERGED (constituent) or ACTIVE (composite). Not all hypotheses undergo fusion.  
**Trigger:** Fusion is asynchronous and periodic (every 5 minutes), not per-hypothesis.

---

#### Stage 11 — Storage

**Entry condition:** ACTIVE or COMPETING hypothesis.  
**Responsible component:** Hypothesis Registry.  
**Actions:** Hypothesis persisted to hot tier. Indices updated. Available to Reasoning Engine consumers.  
**Ongoing:** Hypothesis remains in storage until ARCHIVED or RETIRED.

---

#### Stage 12 — Evolution

**Entry condition:** Ongoing; triggered by evidence changes, context changes, or periodic review.  
**Responsible component:** Hypothesis Evolution Manager.  
**Actions:** Evidence refs updated, scores recomputed, versions incremented, context re-enriched. Hypothesis strengthens or weakens over time.  
**Exit trigger:** Hypothesis drops below minimum HCS → RETIRED. Evidence fully withdrawn → RETIRED. Superseded by new version.

---

#### Stage 13 — Review

**Entry condition:** Governance review cycle or manual trigger.  
**Responsible component:** Hypothesis Governance Manager.  
**Actions:** Domain owner reviews active hypothesis set for quality, relevance, and policy compliance. Low-quality hypotheses may be retired manually.  
**SLA:** Reviews completed within the scheduled review cycle.

---

#### Stage 14 — Archive

**Entry condition:** Hypothesis has passed its active retention period OR has been RETIRED for > 30 days.  
**Responsible component:** Hypothesis Archive Manager.  
**Actions:** Hypothesis moved to warm then cold storage tier. Status set to ARCHIVED. Version chain and evidence refs preserved permanently.

---

#### Stage 15 — Retirement

**Entry condition:** HCS drops below 0.20 AND no active supporting evidence OR Governance Manager manual retirement OR constitutional violation.  
**Responsible component:** Hypothesis Evolution Manager / Governance Manager.  
**Actions:** Status set to RETIRED. Dependency propagation notifies child hypotheses. Not distributed to Reasoning Engine.  
**Recovery:** Retired hypotheses may not be reinstated — a new hypothesis with the same subject is created instead.

---

### 4.4 Lifecycle Duration Reference

| Hypothesis Category | Typical Active Duration | Minimum Active | Maximum Active |
|---|---|---|---|
| Market Hypothesis | 1 day — 2 weeks | 30 min | 90 days |
| Technical Hypothesis | 30 min — 3 days | 5 min | 30 days |
| Fundamental Hypothesis | 1 week — 3 months | 1 day | 12 months |
| Macro Hypothesis | 1 month — 6 months | 1 week | 36 months |
| Sector Hypothesis | 1 week — 2 months | 1 day | 12 months |
| Company Hypothesis | 1 week — 3 months | 1 day | 12 months |
| Liquidity Hypothesis | 1 hour — 1 day | 5 min | 7 days |
| Volatility Hypothesis | 1 day — 2 weeks | 30 min | 90 days |
| Sentiment Hypothesis | 1 day — 1 week | 1 hour | 30 days |
| Event Hypothesis | Event duration + 5 days | Event duration | Event + 30 days |
| Risk Hypothesis | 1 day — 2 weeks | 1 hour | 90 days |
| Composite Hypothesis | Duration of shortest constituent | Per constituent | Per constituent |

---

### 4.5 PIT Semantics for Hypothesis History

All historical queries against the Hypothesis Registry must use PIT semantics:

```
Historical query filter: creation_timestamp <= analysis_timestamp
                         AND ( retirement_timestamp IS NULL
                               OR retirement_timestamp > analysis_timestamp )
```

This ensures that:
1. Hypotheses created after analysis_timestamp are excluded (no look-ahead).
2. Hypotheses that were active at analysis_timestamp are included regardless of their current status.
3. Recalibrations performed after analysis_timestamp do not affect historical analysis.

---
## PART V — HYPOTHESIS SERVICES

The Hypothesis Engine exposes 15 services, each encapsulating a coherent capability. Services are the boundary through which other IIOS engines interact with the Hypothesis Engine.

### 5.1 Service Registry

| Service Code | Service Name | Primary Consumer |
|---|---|---|
| HS-01 | Generation Service | Internal (Generator) |
| HS-02 | Validation Service | Internal (Validator) |
| HS-03 | Scoring Service | Internal + Reasoning Engine |
| HS-04 | Ranking Service | Reasoning Engine |
| HS-05 | Fusion Service | Internal (Fusion Manager) |
| HS-06 | Comparison Service | Internal (Comparator) |
| HS-07 | Dependency Service | Internal (Dependency Manager) |
| HS-08 | Context Service | Internal (Context Manager) |
| HS-09 | Evolution Service | Internal (Evolution Manager) |
| HS-10 | Governance Service | Governance Manager + Research Layer |
| HS-11 | Audit Service | Governance Manager + Compliance |
| HS-12 | Search Service | Reasoning Engine + Research |
| HS-13 | Retrieval Service | Reasoning Engine + Knowledge Engine |
| HS-14 | Archive Service | Internal (Archive Manager) |
| HS-15 | Health Service | System Monitor |

---

### 5.2 Service Definitions

#### HS-01 — Generation Service

**Purpose:** Receives evidence and triggers hypothesis generation when evidence patterns match Catalog templates.

**Inputs:** Active evidence records (ECS ≥ 0.30, status = ACTIVE) from Evidence Engine distribution channel.

**Outputs:** Generation signals to Hypothesis Builder; generation metrics.

**Dependencies:** Evidence Engine distribution channel; Hypothesis Catalog; Hypothesis Registry (deduplication check).

**Consumers:** Internal only.

**Failure Handling:** If Catalog is unavailable, service degrades to last-known template set with CATALOG_STALE flag. If Registry dedup check fails, generation proceeds with potential duplicate; Validator handles deduplication.

**Recovery:** On restart, replay last 15-minute evidence window to catch missed generation opportunities.

**Performance Expectations:** Evidence-to-signal latency ≤ 100ms (p99). Throughput ≥ 1,000 evidence items/second evaluated.

---

#### HS-02 — Validation Service

**Purpose:** Validates hypothesis candidates through 7 sequential levels before admission to the Registry.

**Inputs:** Hypothesis candidate records from Hypothesis Builder.

**Outputs:** VALID candidates to Scoring Service; REJECTED candidates with reason codes to dead-letter queue.

**Dependencies:** Hypothesis Catalog; Entity Registry; Evidence Registry.

**Consumers:** Internal only.

**Failure Handling:** If Evidence Registry is unavailable, validation halts at L3; candidates queued (max 3 attempts, 30s spacing).

**Performance Expectations:** ≤ 50ms per candidate (p99). Throughput ≥ 200 candidates/second.

---

#### HS-03 — Scoring Service

**Purpose:** Computes HCS and HCS-C for hypotheses on creation and on every re-score trigger.

**Inputs:** Validated hypothesis records; evidence records; scoring weights from Catalog; calibration parameters.

**Outputs:** Scored hypothesis records with hcs, hcs_confidence, hcs_tier; scoring audit events.

**Dependencies:** Evidence Registry; Hypothesis Catalog; Hypothesis Confidence Engine.

**Consumers:** Internal (Ranking Service, Version Manager); Reasoning Engine (reads scored hypotheses from Registry).

**Failure Handling:** On evidence lookup failure, scoring deferred (max 60s); if unresolvable, hypothesis marked SCORING_DEFERRED with alert.

**Performance Expectations:** ≤ 50ms per score computation (p99). Throughput ≥ 500 score computations/second.

---

#### HS-04 — Ranking Service

**Purpose:** Maintains the sorted global and type-specific rankings of ACTIVE hypotheses.

**Inputs:** Score update events from Scoring Service; comparison results from Comparison Service.

**Outputs:** Ranked hypothesis lists (global and per-type) published to Distribution Service; rank change events to Health Service.

**Dependencies:** Hypothesis Scoring Engine; Hypothesis Comparator; Hypothesis Context Manager.

**Consumers:** Reasoning Engine (primary); Knowledge Engine (secondary).

**Failure Handling:** If scoring updates are delayed, rankings become stale; Reasoning Engine receives RANKING_STALE flag after 60-second staleness threshold.

**Performance Expectations:** Rank update latency ≤ 20ms per update (p99). Full re-rank cycle ≤ 500ms.

---

#### HS-05 — Fusion Service

**Purpose:** Identifies fusion candidates and constructs composite hypotheses from compatible constituent hypotheses.

**Inputs:** Active hypothesis set from Registry; compatibility data from Dependency Service.

**Outputs:** Composite hypothesis construction requests to Hypothesis Builder; MERGED status transitions to constituent hypotheses.

**Dependencies:** Hypothesis Registry; Hypothesis Dependency Manager; Hypothesis Builder; Fusion eligibility rules from Catalog.

**Consumers:** Internal only.

**Failure Handling:** Fusion failure leaves constituent hypotheses ACTIVE; composite rejected; fusion attempt logged.

**Performance Expectations:** Fusion cycle runs every 5 minutes; each fusion attempt ≤ 500ms.

---

#### HS-06 — Comparison Service

**Purpose:** Performs pairwise hypothesis comparisons and maintains dominance relationships.

**Inputs:** Active hypothesis set (same subject and domain) from Registry; score data from Scoring Service.

**Outputs:** Dominance matrix updates to Ranking Service; competing hypothesis flags to Conflict Service.

**Dependencies:** Hypothesis Registry; Hypothesis Scoring Engine; Hypothesis Conflict Manager.

**Consumers:** Internal (Ranking Service, Conflict Service).

**Failure Handling:** Comparison deferred for low-priority types during load spikes; lower-priority hypotheses may have stale comparisons for up to 60s.

**Performance Expectations:** Pairwise comparison ≤ 10ms; full comparison cycle for one entity ≤ 100ms.

---

#### HS-07 — Dependency Service

**Purpose:** Tracks and enforces hypothesis dependency relationships.

**Inputs:** Dependency data from hypothesis records (parent_hypothesis_ids, child_hypothesis_ids); status change events.

**Outputs:** Dependency propagation events to affected hypotheses; cycle detection alerts; dependency graph queries.

**Dependencies:** Hypothesis Registry; Hypothesis Version Manager.

**Consumers:** Fusion Service; Governance Service; Reasoning Engine (for dependency-aware reasoning).

**Failure Handling:** Dependency propagation failure: child hypotheses receive PARENT_STATUS_UNKNOWN flag; reviewed at next governance cycle.

**Performance Expectations:** Propagation latency ≤ 50ms per event; graph query ≤ 100ms.

---

#### HS-08 — Context Service

**Purpose:** Captures and enriches hypothesis records with market context; detects context drift.

**Inputs:** Market context observations (regime, VIX, session, events) from Observation Engine; hypothesis records requiring context.

**Outputs:** Context-enriched hypothesis records; context staleness alerts.

**Dependencies:** Observation Engine; Hypothesis Version Manager.

**Consumers:** Internal (Scoring Service, Evolution Service).

**Failure Handling:** If context source unavailable, hypothesis proceeds with CONTEXT_PARTIAL flag; context backfilled on source recovery.

**Performance Expectations:** Context capture ≤ 30ms; context drift detection ≤ 5s.

---

#### HS-09 — Evolution Service

**Purpose:** Manages hypothesis evolution: scoring updates, calibration, template improvement, version progression.

**Inputs:** Evidence change events from Hypothesis Matcher; historical outcome records; context change events.

**Outputs:** Version creation signals; calibration reports; template improvement proposals.

**Dependencies:** Hypothesis Matcher; Hypothesis Version Manager; Hypothesis Scoring Engine; Hypothesis Archive Manager.

**Consumers:** Internal; Governance Service (calibration reports); Research Layer (template performance).

**Failure Handling:** Evolution Manager offline: evidence changes buffered; processed on restart (bounded buffer: 100,000 events).

**Performance Expectations:** Version creation ≤ 100ms from trigger event (p99); calibration report generation ≤ 10 minutes.

---

#### HS-10 — Governance Service

**Purpose:** Enforces all governance policies across the Hypothesis Engine.

**Inputs:** New type proposals; retention schedules; governance review triggers; constitutional violation alerts.

**Outputs:** Approval/rejection decisions; archive commands; governance audit records; policy change notifications.

**Dependencies:** Hypothesis Catalog; Hypothesis Audit Manager; Hypothesis Archive Manager.

**Consumers:** Research Layer; Compliance Layer; all internal components (for policy enforcement).

**Failure Handling:** Governance Service offline: new type proposals queued; retention not enforced; all CRITICAL operations blocked; alert raised.

**Performance Expectations:** Type approval turnaround ≤ 5 business days; retention check cycle daily.

---

#### HS-11 — Audit Service

**Purpose:** Maintains the complete audit trail for all Hypothesis Engine operations.

**Inputs:** Audit events from all components.

**Outputs:** Audit records (append-only) to audit log store; audit query results.

**Dependencies:** Audit Log Store.

**Consumers:** Governance Service; Compliance Layer; Research Layer.

**Failure Handling:** Audit write failure blocks the originating operation (audit is mandatory and non-bypassable).

**Performance Expectations:** Audit write ≤ 5ms per event (p99). Audit log query ≤ 500ms for 1,000-record result set.

---

#### HS-12 — Search Service

**Purpose:** High-performance search and retrieval of hypotheses.

**Inputs:** Search queries (entity, type, status, HCS tier, timestamp range, evidence_id, full-text).

**Outputs:** Hypothesis result sets.

**Dependencies:** Hypothesis Registry; Search indices; Access Control Layer.

**Consumers:** Reasoning Engine; Research Layer; Governance Service.

**Failure Handling:** Index stale: fall back to Registry scan with performance degradation; staleness alert raised.

**Performance Expectations:** Single-record retrieval ≤ 5ms; entity query (100 results) ≤ 50ms; time-range query (1,000 results) ≤ 200ms.

---

#### HS-13 — Retrieval Service

**Purpose:** Structured retrieval of hypothesis sets for the Reasoning Engine and Knowledge Engine, with filtering, pagination, and PIT compliance.

**Inputs:** Retrieval requests specifying filters, sort order, page size, and optional PIT timestamp.

**Outputs:** Paginated, filtered hypothesis result sets.

**Dependencies:** Hypothesis Registry; Search Service; Access Control Layer.

**Consumers:** Reasoning Engine (primary); Knowledge Engine.

**Failure Handling:** Query timeout: partial result set returned with TRUNCATED flag; client responsible for retry with adjusted parameters.

**Performance Expectations:** Ranked ACTIVE set for one entity ≤ 100ms. PIT query (1,000 results) ≤ 300ms.

---

#### HS-14 — Archive Service

**Purpose:** Manages tiered storage transitions and long-term hypothesis preservation.

**Inputs:** Archive commands from Governance Service; retirement events.

**Outputs:** Archived hypothesis records; confirmation events to Registry.

**Dependencies:** Hypothesis Registry; Persistence Layer tiered storage.

**Consumers:** Internal (Governance Service, Archive Manager).

**Failure Handling:** Archive storage full: queue new archives; capacity alert; no active hypotheses affected.

**Performance Expectations:** Archive throughput ≥ 10,000 hypotheses/hour during batch archival.

---

#### HS-15 — Health Service

**Purpose:** Monitors the health of all Hypothesis Engine components and publishes telemetry to the System Monitor.

**Inputs:** Health events and metrics from all 20 components.

**Outputs:** Component health status (UP/DEGRADED/DOWN); aggregate metrics; alerts.

**Dependencies:** System Monitor; all Hypothesis Engine components.

**Consumers:** System Monitor; Governance Service; Deployment orchestration.

**Failure Handling:** Health Service itself must be the last component to fail; isolated deployment with dedicated resources.

**Performance Expectations:** Health status update ≤ 10s; metric aggregation cycle 30 seconds.

---
## PART VI — HYPOTHESIS PROCESSING PIPELINES

### 6.1 Overview

The Hypothesis Engine operates twelve processing pipelines, each designed for a specific evidence-to-hypothesis scenario. Pipelines are the orchestration layer — they sequence component interactions into coherent end-to-end flows.

---

### 6.2 Pipeline 1 — Real-Time Generation Pipeline

**Trigger:** New ACTIVE evidence published by Evidence Engine.  
**Latency target:** Evidence publish to ACTIVE hypothesis ≤ 500ms (p99).

```
Evidence Engine
    │
    ▼ (subscribe: evidence-active topic)
[HS-01 Generation Service]
    │
    ├──► template match? NO → log NOT_MATCHED → end
    │
    ├──► template match? YES
    │         │
    │         ▼
    │   [Hypothesis Builder] ──► assemble candidate
    │         │
    │         ▼
    │   [Hypothesis Validator] ──► L1–L7 validation
    │         │
    │         ├──► REJECTED → dead-letter queue → end
    │         │
    │         ▼ VALID
    │   [Context Manager] ──► attach context
    │         │
    │         ▼
    │   [Scoring Engine] ──► compute HCS, HCS-C
    │         │
    │         ▼
    │   [Ranking Engine] ──► assign ranks
    │         │
    │         ▼
    │   [Comparator] ──► pairwise comparison
    │         │
    │         ▼
    │   [Conflict Manager] ──► conflict check
    │         │
    │         ▼
    │   [Version Manager] ──► record v1
    │         │
    │         ▼
    │   [Hypothesis Registry] ──► persist as ACTIVE
    │         │
    │         ▼
    │   [Distribution Service] ──► publish to Reasoning Engine
    │
    └──► [Audit Manager] ──► record creation event
```

---

### 6.3 Pipeline 2 — Evidence-to-Hypothesis Pipeline

**Trigger:** Evidence Matcher identifies that a new evidence item supports or contradicts an existing active hypothesis.  
**Latency target:** Evidence publish to hypothesis re-score ≤ 200ms (p99).

```
Evidence Engine (new or updated evidence)
    │
    ▼
[Hypothesis Matcher]
    │
    ├──► no active hypothesis match → exit
    │
    ├──► match found (supporting) → add to evidence_refs (support)
    │
    ├──► match found (contradicting) → add to evidence_refs (contradict)
    │         │
    │         ▼
    │   [Hypothesis Scoring Engine] ──► recompute HCS, HCS-C
    │         │
    │         ▼
    │   [Ranking Engine] ──► update rank
    │         │
    │         ▼
    │   [Conflict Manager] ──► recheck conflict status
    │         │
    │         ▼
    │   [Version Manager] ──► create new version
    │         │
    │         ▼
    │   [Distribution Service] ──► publish updated hypothesis
```

---

### 6.4 Pipeline 3 — Multi-Evidence Fusion Pipeline

**Trigger:** Evidence Matcher detects 3+ new evidence items meeting the composite threshold.  
**Trigger also:** Periodic fusion scan every 5 minutes.  
**Latency target:** Fusion completion ≤ 2,000ms from trigger.

```
[Hypothesis Fusion Manager] ──► scan for fusion candidates
    │
    ├──► no eligible candidates → exit
    │
    ▼ eligible candidates identified
[Dependency Manager] ──► check compatibility
    │
    ├──► incompatible → exit
    │
    ▼ compatible
[Hypothesis Builder] ──► assemble composite candidate
    │
    ▼
[Hypothesis Validator] ──► validate composite
    │
    ▼
[Scoring Engine] ──► compute composite HCS
    │
    ▼
[Version Manager] ──► transition constituents to MERGED
    │
    ▼
[Registry] ──► persist composite as ACTIVE
    │
    ▼
[Distribution Service] ──► publish composite
```

---

### 6.5 Pipeline 4 — Competing Hypothesis Pipeline

**Trigger:** Conflict Manager detects MAJOR conflict between two active hypotheses.

```
[Conflict Manager]
    │
    ▼ MAJOR conflict detected
Classify both hypotheses as COMPETING
    │
    ▼
Compute adjudication score:
    - Evidence independence scores
    - Net evidence weight comparison
    - Temporal recency of evidence
    │
    ▼
Set conflict_status = MAJOR on both records
    │
    ▼
Reduce effective_weight of weaker side by 40%
    │
    ▼
[Version Manager] ──► record conflict adjudication in both version records
    │
    ▼
[Distribution Service] ──► publish both with CONFLICT_MAJOR flag
    │
    ▼
[Audit Manager] ──► record adjudication event
    │
    ▼
[Governance Manager] ──► alert domain owner for review
```

---

### 6.6 Pipeline 5 — Ranking Pipeline

**Trigger:** Any hypothesis score change.  
**Latency target:** Rank update ≤ 30ms from score change event.

```
[Scoring Engine] ──► emit score_updated event
    │
    ▼
[Ranking Engine]
    │
    ├──► update global rank list (sorted by HCS desc)
    ├──► update type-specific rank list
    │
    ▼
Compute rank changes: identify up-movers and down-movers
    │
    ▼
[Distribution Service] ──► publish ranking update to Reasoning Engine
    │
    ▼
[Health Service] ──► emit rank_churn metric
```

---

### 6.7 Pipeline 6 — Conflict Resolution Pipeline

**Trigger:** MAJOR conflict hypothesis pair; one side's evidence drops significantly (supporting evidence SUPERSEDED or confidence falls below 0.40).  
**Purpose:** Resolve a previously flagged MAJOR conflict.

```
[Conflict Manager] ──► periodic re-scan of COMPETING hypotheses (every 2 minutes)
    │
    ▼ conflict resolution condition met: one side HCS < 0.35
Set weaker hypothesis conflict_status = NONE; HCS_tier = WEAK
    │
    ▼
Set stronger hypothesis conflict_status = NONE
    │
    ▼
[Version Manager] ──► record resolution event in both hypothesis records
    │
    ▼
[Ranking Engine] ──► rerank resolved hypotheses
    │
    ▼
[Distribution Service] ──► publish updated hypotheses (conflict flag removed)
    │
    ▼
[Audit Manager] ──► record resolution
```

---

### 6.8 Pipeline 7 — Context Assignment Pipeline

**Trigger:** (a) New hypothesis requiring context, or (b) regime change detected.  
**Purpose:** Assign and maintain accurate market context on all active hypotheses.

```
Trigger (a): New hypothesis candidate
    │
[Context Manager] ──► capture current context snapshot
    │
    ▼
Attach ContextRecord: regime, session, VIX, events, macro_state
    │
    ▼
Context completeness check: all required fields present?
    ├──► YES → CONTEXT_COMPLETE flag → forward to Scoring
    └──► NO  → CONTEXT_PARTIAL flag → forward to Scoring with partial context

Trigger (b): Regime change event
    │
[Context Manager] ──► query all ACTIVE hypotheses formed in previous regime
    │
    ▼
For each affected hypothesis:
    Emit CONTEXT_STALE flag
    │
    ▼
[Evolution Manager] ──► evaluate whether context drift warrants re-scoring
    │
    ▼
[Scoring Engine] ──► apply regime-sensitive scoring modifier
    │
    ▼
[Version Manager] ──► record context update as new version
```

---

### 6.9 Pipeline 8 — Historical Evaluation Pipeline

**Trigger:** Research Layer or Backtesting System requests historical hypothesis reconstruction.  
**Purpose:** Reconstruct the hypothesis state at a specified historical timestamp, strictly respecting PIT semantics.

```
Research Layer ──► historical query request: {analysis_timestamp, entity, type_filter}
    │
    ▼
[Retrieval Service]
    │
    ├──► apply PIT filter: creation_timestamp <= analysis_timestamp
    ├──► apply activity filter: retirement_timestamp IS NULL OR > analysis_timestamp
    │
    ▼
Retrieve version of each hypothesis valid at analysis_timestamp
    │
    ▼
Reconstruct evidence refs: filter to evidence records with creation_timestamp <= analysis_timestamp
    │
    ▼
Recompute HCS using scoring parameters valid at analysis_timestamp (from parameter history)
    │
    ▼
Return reconstructed hypothesis set to Research Layer with PIT_COMPLIANT flag
    │
    ▼
[Audit Manager] ──► record historical query event
```

---

### 6.10 Pipeline 9 — Evolution Pipeline

**Trigger:** Evidence change event (Hypothesis Matcher) or periodic evolution scan (every 10 minutes).  
**Purpose:** Keep hypothesis scores and versions current as the evidence picture evolves.

```
[Hypothesis Evolution Manager]
    │
    ▼
For each hypothesis with pending evidence change:
    Recompute net_evidence_weight
    │
    ▼
    [Scoring Engine] ──► recompute HCS, HCS-C
    │
    ├──► Score change > 0.05 OR tier change?
    │         YES ──► [Version Manager] create new version
    │         NO  ──► no new version; internal score updated only
    │
    ├──► HCS < 0.20 AND supporting evidence < 1?
    │         YES ──► trigger retirement pipeline
    │
    ▼
Calibration check (weekly):
    Compare historical HCS-C against observed outcomes
    If calibration error > 0.10: emit RECALIBRATION_NEEDED alert
    │
    ▼
Template performance check (monthly):
    Assess which generation templates produce high-scoring hypotheses
    Propose template improvements to Governance Manager
```

---

### 6.11 Pipeline 10 — Validation Pipeline

**Trigger:** Hypothesis candidate received from Hypothesis Builder.

```
[Hypothesis Validator]
    │
    ▼
L1 Schema Validation ──── FAIL → reject (SCHEMA_INVALID)
    │ PASS
    ▼
L2 Identity Validation ── FAIL → reject (IDENTITY_CONFLICT)
    │ PASS
    ▼
L3 Evidence Validation ── FAIL → reject (EVIDENCE_NOT_FOUND)
    │ PASS
    ▼
L4 Temporal Validation ── FAIL → reject (TIMESTAMP_VIOLATION)
    │ PASS
    ▼
L5 Semantic Validation ── FAIL → reject (ASSERTION_TRIVIAL)
    │ PASS
    ▼
L6 Type Validation ────── FAIL → reject (TYPE_UNDEFINED)
    │ PASS
    ▼
L7 Threshold Validation ─ FAIL → reject (INSUFFICIENT_EVIDENCE)
    │ PASS
    ▼
VALID → forward to Scoring Service
```

---

### 6.12 Pipeline 11 — Storage Pipeline

**Trigger:** ACTIVE hypothesis ready for persistence.

```
[Hypothesis Registry] ──► receive validated, scored, ranked, context-assigned hypothesis
    │
    ▼
Assign storage tier: HOT (all new ACTIVE hypotheses)
    │
    ▼
Persist record to hot tier storage
    │
    ▼
Update indices: entity, type, status, HCS, timestamp, evidence_id
    │
    ▼
Compute and store record integrity hash
    │
    ▼
Emit STORED event to Health Service
    │
    ▼
[Audit Manager] ──► record storage event
```

---

### 6.13 Pipeline 12 — Distribution Pipeline

**Trigger:** Hypothesis status transition to ACTIVE or score update.  
**Purpose:** Deliver current hypothesis set to Reasoning Engine.

```
[Distribution Service]
    │
    ▼
Collect all ACTIVE and COMPETING hypotheses updated since last distribution cycle
    │
    ▼
Apply consumer-specific filters (Reasoning Engine may subscribe to specific types)
    │
    ▼
Publish to Reasoning Engine subscription channel (hypothesis-active topic)
    │
    ▼
Confirm acknowledgment from Reasoning Engine (at-least-once delivery)
    │
    ├──► ACK received → done
    └──► NO ACK after 5s → retry (max 3 retries with exponential backoff)
                                  After 3 failures: dead-letter for Reasoning Engine
    │
    ▼
[Audit Manager] ──► record distribution event
```

---
## PART VII — HYPOTHESIS QUALITY FRAMEWORK

### 7.1 Overview

The Hypothesis Composite Score (HCS) quantifies the analytical quality of a hypothesis across 10 dimensions. Every hypothesis is scored on each dimension; the weighted sum produces the HCS.

$$HCS = \sum_{i=1}^{10} w_i \cdot d_i$$

Where $d_i$ is the normalised score for dimension $i$ in $[0.0, 1.0]$ and $w_i$ is the weight for that dimension.

---

### 7.2 Quality Dimension Reference

| Code | Dimension | Weight | Description |
|---|---|---|---|
| D01 | Hypothesis Strength | 0.18 | Decisiveness of the explanation — how clearly the hypothesis explains the observed conditions |
| D02 | Evidence Support | 0.20 | Volume and quality of supporting evidence relative to contradicting evidence |
| D03 | Consistency | 0.12 | Internal logical consistency and absence of self-contradiction |
| D04 | Coverage | 0.08 | Proportion of the observed conditions explained by the hypothesis |
| D05 | Novelty | 0.05 | Degree to which the hypothesis provides a non-obvious or non-trivial explanation |
| D06 | Coherence | 0.10 | Alignment with the broader body of active knowledge and established analytical frameworks |
| D07 | Completeness | 0.07 | Whether all required structural fields and testability conditions are fully populated |
| D08 | Stability | 0.08 | Historical stability of the hypothesis score across multiple evidence updates |
| D09 | Confidence | 0.10 | HCS-C value from the Hypothesis Confidence Engine |
| D10 | Traceability | 0.02 | Completeness and integrity of the evidence lineage and version chain |
| **Total** | | **1.00** | |

---

### 7.3 Dimension Computation Specifications

#### D01 — Hypothesis Strength

Strength measures how decisively the explanation accounts for the observed conditions. A high-strength hypothesis accounts for all key observations; a low-strength hypothesis offers only a partial or ambiguous explanation.

Computation basis:
- Coverage of the primary observation set (what % of the triggering observations are explained by the hypothesis assertion?)
- Specificity of the assertion (does the assertion make a precise, testable claim, or a vague one?)
- Alignment between the assertion type and the evidence category (is price evidence supporting a technical hypothesis, or is there a mismatch?)

Strength is a property of the assertion itself, not of the evidence quantity. A hypothesis can have strong supporting evidence (high D02) but weak strength (low D01) if the assertion is vague.

---

#### D02 — Evidence Support

Evidence support quantifies how well-supported the hypothesis is by the available evidence, net of contradicting evidence.

$$D02 = \frac{\sum_{i \in support} w_i \cdot ECS_i - \sum_{j \in contradict} w_j \cdot ECS_j}{\sum_{i \in support} w_i \cdot ECS_i + \sum_{j \in contradict} w_j \cdot ECS_j}$$

Normalised to [0.0, 1.0]. A hypothesis with only supporting evidence has D02 = 1.0; a hypothesis with equal supporting and contradicting weight has D02 = 0.5.

---

#### D03 — Consistency

Consistency measures internal logical coherence. A hypothesis is inconsistent if it simultaneously asserts conditions that cannot both be true — for example, asserting both momentum continuation and mean reversion without a conditional framing.

Consistency is evaluated by the Validator at L5 (semantic validation). Consistency score = 1.0 if no inconsistency detected; reduced proportionally to the number and severity of inconsistencies found.

---

#### D04 — Coverage

Coverage measures the proportion of the subject domain's observed conditions that the hypothesis explains.

$$D04 = \frac{\text{number of active observations for subject entity explained by hypothesis}}{\text{total number of active observations for subject entity}}$$

A hypothesis that explains only one observation from a rich observation set will have low coverage regardless of how well it explains that one observation.

---

#### D05 — Novelty

Novelty penalises hypotheses that merely restate the obvious and rewards hypotheses that provide non-trivial explanatory value. Novelty is computed by comparing the hypothesis to the existing set of active hypotheses for the same subject: a hypothesis that is highly similar to an already-active hypothesis has low novelty and may be a near-duplicate.

Novelty does not mean that a hypothesis should contradict established knowledge — novelty means the hypothesis adds explanatory content not already represented in the active hypothesis set.

---

#### D06 — Coherence

Coherence measures the hypothesis's alignment with the Knowledge Engine's established knowledge corpus and the IIOS's active macro and regime context. A hypothesis that is inconsistent with confirmed macroeconomic knowledge or current regime characterisation receives a lower coherence score.

Coherence is not a constraint — an incoherent hypothesis is not prohibited. Market regime changes often produce temporarily incoherent hypotheses before the knowledge base catches up. But incoherence is analytically significant information and must be scored accordingly.

---

#### D07 — Completeness

Completeness measures the structural fullness of the hypothesis record. All required fields present = full completeness. Missing testability_conditions, missing falsification_conditions, or incomplete evidence refs reduce completeness.

$$D07 = \frac{\text{required fields populated}}{\text{total required fields}}$$

---

#### D08 — Stability

Stability measures how much the hypothesis score has varied across its recent version history. A hypothesis whose HCS oscillates significantly (> 0.15 range over the last 5 versions) receives a lower stability score. Instability signals that the evidence picture is unsettled and the hypothesis should be weighted with caution by the Reasoning Engine.

$$D08 = 1 - \text{coefficient\_of\_variation}(HCS_{last\_5\_versions})$$

---

#### D09 — Confidence

Confidence is the HCS-C value from the Hypothesis Confidence Engine, representing the probability that the hypothesis is the correct explanation given the available evidence. D09 = HCS-C.

---

#### D10 — Traceability

Traceability measures the integrity and completeness of the evidence lineage attached to the hypothesis. All evidence refs must trace to valid ACTIVE Evidence Engine records; all records must have complete lineage to their source observations.

$$D10 = \frac{\text{evidence refs with complete traceable lineage}}{\text{total evidence refs}}$$

---

### 7.4 HCS Quality Tier Definitions

| Tier | HCS Range | Interpretation |
|---|---|---|
| STRONG | 0.80–1.00 | All key dimensions high; well-evidenced, specific, stable explanation |
| CREDIBLE | 0.65–0.79 | Most dimensions positive; good evidence support; Reasoning Engine should consider seriously |
| PROVISIONAL | 0.50–0.64 | Mixed evidence; some dimensions weak; hold under observation |
| WEAK | 0.35–0.49 | Limited evidence support; significant uncertainty; low weight in reasoning |
| SPECULATIVE | 0.00–0.34 | Minimal evidence; possibly valid but not yet substantiated |

---

### 7.5 Regime-Sensitive Scoring Modifiers

| Regime | Affected Dimension | Modifier | Rationale |
|---|---|---|---|
| BULL_VOLATILE | D08 (Stability) | × 0.85 | High evidence churn reduces stability reliability |
| BEAR_VOLATILE | D05 (Novelty) | × 1.15 | Novel explanations more valuable in volatile bear conditions |
| CRISIS | D02 (Evidence Support) | × 0.80 | Evidence correlation spikes; independence penalty applied |
| RANGE_QUIET | D01 (Strength) | × 0.90 | Price signal strength weakens in ranging markets |
| BULL_QUIET | D06 (Coherence) | × 1.10 | Coherence premium: stable conditions reward consistent explanations |
| REGIME_TRANSITION | D08 (Stability) | × 0.70 | Hypotheses unstable during transitions are appropriately penalised |

---

### 7.6 Quality Monitoring Metrics

| Metric | Alert threshold | Action |
|---|---|---|
| Mean HCS of ACTIVE set | < 0.55 | Review generation template quality |
| % SPECULATIVE tier hypotheses | > 20% | Review evidence intake quality |
| % STRONG + CREDIBLE tier | < 30% | Review scoring calibration |
| Average stability score (D08) | < 0.60 | Evidence churn alert; review evidence engine |
| Completeness failures (D07 < 0.80) | > 5% | Review Builder field assembly |
| Calibration error (D09 vs actual outcomes) | > 0.10 | Trigger Evolution Manager recalibration |

---

## PART VIII — HYPOTHESIS GOVERNANCE

### 8.1 Governance Philosophy

Hypothesis governance exists to ensure that the explanations the IIOS generates about market conditions remain analytically reliable, consistently maintained, and compliant with regulatory requirements. Without governance, the hypothesis set degrades into an unmanaged accumulation of stale, redundant, and potentially misleading explanations.

Governance does not constrain analytical freedom — it ensures that the analytical environment is clean, auditable, and maintainable.

---

### 8.2 Governance Dimension Reference

| Dimension | Governance Level | Description |
|---|---|---|
| Hypothesis type definition | CRITICAL | All types must be approved before use |
| Hypothesis assertion content | HIGH | Assertions must be non-trivial, testable, and type-appropriate |
| Evidence linkage quality | CRITICAL | Evidence refs must point to valid ACTIVE evidence |
| HCS calibration | HIGH | Calibration must be reviewed at least monthly |
| Retention compliance | HIGH | All hypotheses archived on schedule |
| Access control | HIGH | CRITICAL-tier hypotheses restricted to authorised consumers |
| Constitutional rule compliance | CRITICAL | All 80 rules enforced at all times |
| Audit trail completeness | CRITICAL | 100% of operations logged |
| Version chain integrity | CRITICAL | No version chain breaks permitted |
| Historical preservation | HIGH | Retired hypotheses preserved per retention schedule |
| Template governance | MEDIUM | Templates reviewed monthly |
| Naming standards | MEDIUM | All hypothesis IDs, type codes conform to standards |
| Conflict transparency | HIGH | No conflicts silently suppressed |
| Composite governance | MEDIUM | Fusion eligibility reviewed per policy |

---

### 8.3 Governance Tier Matrix

| Tier | Review frequency | Escalation | Examples |
|---|---|---|---|
| CRITICAL | Immediate on violation | Architecture Board | Constitutional rule breach, evidence ref corruption |
| HIGH | Weekly | Domain Owner → Governance Manager | Calibration breach, retention failure |
| MEDIUM | Monthly | Domain Owner | Template quality, naming convention |
| LOW | Quarterly | Domain Owner | Minor process improvements |

---

### 8.4 Hypothesis Type Ownership Responsibility Matrix

| Responsibility | Domain Owner | Governance Manager | Architecture Board |
|---|---|---|---|
| New type proposal | Initiate | Review and approve | Final approval for CRITICAL types |
| Template updates | Propose | Review | Approve if scoring parameters change |
| Retention policy | Follow | Define | Ratify |
| Constitutional rule changes | Propose | Review | Approve |
| Calibration review | Initiate | Monitor | Escalate breaches |
| Access control | Define | Implement | Audit |

---

### 8.5 Naming Standards

**Hypothesis ID:** `HYP-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`

- CAT_CODE: 2–3 uppercase letters (e.g., TEC, MKT, FND)
- TYPE_CODE: 3–5 uppercase letters (e.g., MOM, REV, EARN)
- YYYYMMDD: date of hypothesis formation (UTC)
- SEQ: 8-digit zero-padded sequence number per day per type

**Type codes:** All uppercase, 3–8 characters, no spaces, no special characters. Must be registered in Catalog before use.

**Assertion field:** Natural language, English only. Present tense for current conditions. Maximum 500 characters. Must name the subject entity or domain explicitly.

---

### 8.6 Versioning Standards

- Every change to a hypothesis that affects its analytical content must produce a new version.
- Version numbers are sequential integers starting at 1.
- The delta between consecutive versions must be recorded (which fields changed and why).
- The previous version must be transitioned to SUPERSEDED before the new version is published.
- No version branching permitted.

---

### 8.7 Retention Policy Reference

| Hypothesis category | Active retention | Warm retention | Cold/Archive retention |
|---|---|---|---|
| CRITICAL governance tier | 90 days active | 12 months warm | 7 years cold |
| HIGH governance tier | 30 days active | 6 months warm | 5 years cold |
| MEDIUM governance tier | 14 days active | 3 months warm | 3 years cold |
| LOW governance tier | 7 days active | 1 month warm | 1 year cold |
| Historical (HIS-) | N/A (research only) | 12 months | 7 years |
| Legal hold | Indefinite active | N/A | Until hold released |

---

### 8.8 Security Classification

| Classification | Contents | Access |
|---|---|---|
| CONFIDENTIAL | Hypotheses containing non-public information (pre-announcement earnings, regulatory actions) | Restricted to compliance-cleared personnel only |
| INTERNAL | Standard hypothesis records | All authorised IIOS consumers |
| RESEARCH | Historical and research-purpose hypotheses | Research Layer + Governance |
| PUBLIC | None (no hypothesis records are public) | N/A |

---

### 8.9 Governance Review Cycle

| Review type | Frequency | Trigger | Output |
|---|---|---|---|
| Template quality review | Monthly | Schedule | Template update proposals |
| Scoring calibration review | Monthly | Schedule + CE > 0.10 | Recalibration report |
| Constitutional compliance audit | Quarterly | Schedule | Compliance report |
| Type catalogue review | Quarterly | Schedule | Deprecated types list |
| Retention compliance audit | Monthly | Schedule | Archival status report |
| Security access review | Annually | Schedule | Access control update |

---
## PART IX — HYPOTHESIS CONSTITUTION

### 9.1 Purpose

The Hypothesis Constitution defines the 80 inviolable architectural rules that govern every hypothesis in the IIOS. These rules may not be circumvented by any component, pipeline, or consumer. Constitutional violations trigger immediate escalation to the Architecture Board.

---

### 9.2 Category HC-A — Identity Rules (10 rules)

**HC-A-001** Every hypothesis MUST have a globally unique canonical hypothesis_id assigned by the Hypothesis Engine Identity Manager. No external system or human may assign hypothesis IDs.

**HC-A-002** The hypothesis_id MUST conform to the canonical format: `HYP-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`. No deviation from this format is permitted.

**HC-A-003** A retired hypothesis_id MUST NOT be reused. Retired IDs are permanently recorded in the ID registry.

**HC-A-004** Every hypothesis MUST reference at least one valid, resolvable subject entity via its canonical entity_id. A hypothesis without a subject entity is prohibited.

**HC-A-005** Every hypothesis MUST declare a hypothesis_type. The type MUST exist as an approved entry in the Hypothesis Catalog. Hypotheses referencing undefined types are constitutionally invalid.

**HC-A-006** Every hypothesis MUST declare its category_code. The category MUST be one of the 20 canonical categories defined in Part II. No custom categories may be used without Architecture Board approval.

**HC-A-007** Hypothesis identity conflicts — two hypotheses with different IDs but identical assertions, timestamps, and evidence sets — MUST be detected and resolved by the Validator. The duplicate must be rejected.

**HC-A-008** The version chain for a hypothesis MUST be a strict linear sequence: version 1 → version 2 → version N. No branching, no gaps. Every version must trace its predecessor.

**HC-A-009** Every hypothesis MUST declare its creation_timestamp and hypothesis_timestamp. Both are mandatory. Neither may be null or empty.

**HC-A-010** The entity_ids in a hypothesis MUST all be valid, resolved, non-retired entity records from the Entity Registry at the time of hypothesis creation.

---

### 9.3 Category HC-B — Evidence Support Rules (10 rules)

**HC-B-001** Every hypothesis MUST be supported by at least one ACTIVE, qualified evidence record from the Evidence Engine. A hypothesis with zero supporting evidence is constitutionally prohibited.

**HC-B-002** All evidence_refs in a hypothesis MUST point to valid, non-RETIRED, non-ARCHIVED evidence records. Stale evidence references are a constitutional violation.

**HC-B-003** The net_evidence_weight of a hypothesis at creation MUST be ≥ 0.20. Hypotheses below this threshold must not leave the Generation stage.

**HC-B-004** Evidence used in hypothesis construction MUST NOT be look-ahead evidence (evidence with creation_timestamp after the hypothesis_timestamp). PIT compliance is mandatory.

**HC-B-005** The same evidence record MUST NOT be counted as both supporting and contradicting the same hypothesis. Evidence directionality for a given hypothesis must be assigned at construction and may not be double-counted.

**HC-B-006** When a supporting evidence record transitions to SUPERSEDED or RETIRED, the Hypothesis Matcher MUST remove it from the hypothesis's supporting evidence refs and trigger re-scoring within 60 seconds.

**HC-B-007** The evidence_refs list must maintain the complete directional classification: each evidence ref must be labelled SUPPORTING or CONTRADICTING, never NEUTRAL or UNCLASSIFIED.

**HC-B-008** The Evidence Confidence Score (ECS) of each linked evidence record MUST be preserved at the time of linking. HCS computations use the ECS value at link time, not a dynamically fetched current value (except during explicit re-scoring triggered by Matcher updates).

**HC-B-009** AI-generated hypotheses and human-assisted hypotheses are subject to the same evidence support requirements as autonomously generated hypotheses. Evidence requirements may not be relaxed for any hypothesis source.

**HC-B-010** The maximum evidence age for ACTIVE hypotheses — defined as the elapsed time since the most recent evidence item's observation_timestamp — MUST NOT exceed the freshness SLA for the hypothesis type. A hypothesis whose most recent evidence has expired the freshness SLA must receive a FRESHNESS_WARNING flag and trigger re-evaluation.

---

### 9.4 Category HC-C — Validity Rules (12 rules)

**HC-C-001** A hypothesis MUST pass all 7 validation levels (L1–L7) before being admitted to the Registry. No exception to any validation level is permitted.

**HC-C-002** Every hypothesis MUST have a non-empty, non-trivial assertion. An assertion that is fewer than 20 words, contains no subject entity, or consists solely of placeholders is constitutionally invalid.

**HC-C-003** Every hypothesis MUST declare at least two testability_conditions — evidence conditions that would confirm or strengthen the hypothesis if observed. A hypothesis with zero testability conditions is constitutionally untestable and prohibited.

**HC-C-004** Every hypothesis MUST declare at least one falsification_condition — evidence condition that would invalidate or strongly refute the hypothesis. A hypothesis without a falsification condition cannot be falsified and is constitutionally invalid.

**HC-C-005** The hypothesis_timestamp MUST be in UTC and MUST NOT be in the future. Hypotheses about current conditions may not use a future timestamp.

**HC-C-006** The creation_timestamp MUST be equal to or later than the hypothesis_timestamp. The system cannot record a hypothesis before it forms it.

**HC-C-007** All schema fields marked Required in the hypothesis schema (Part II) MUST be populated. A hypothesis with any required field null or absent is structurally invalid.

**HC-C-008** Hypothesis assertions MUST NOT contain trading recommendations (buy, sell, hold), price targets, or directional predictions. Constitutional violation of this rule triggers immediate rejection.

**HC-C-009** Hypothesis assertions MUST be expressed in the present tense — they describe current conditions. An assertion phrased in the future tense is a prediction and constitutionally prohibited.

**HC-C-010** Conditional hypotheses (those premised on an assumption) MUST explicitly flag the assumption field as containing an unverified premise. Assumptions MUST NOT be presented as evidence.

**HC-C-011** Every composite hypothesis MUST list all constituent hypothesis IDs in parent_hypothesis_ids. A composite hypothesis without traceable constituent links is constitutionally invalid.

**HC-C-012** Historical hypotheses (HIS- prefix) MUST include a PIT_COMPLIANT flag confirming that all evidence and context records used were available at the historical analysis_timestamp. Absent this flag, the hypothesis is not eligible for research use.

---

### 9.5 Category HC-D — Consistency Rules (10 rules)

**HC-D-001** A hypothesis MUST NOT simultaneously assert mutually exclusive conditions without a conditional framing. An unconditional assertion that "prices are rising AND prices are falling" is constitutionally prohibited.

**HC-D-002** Technical hypotheses MUST NOT assert both momentum continuation and mean reversion without conditional framing. The two are mutually exclusive for the same entity at the same time horizon.

**HC-D-003** Macro hypotheses asserting a risk-on regime MUST NOT simultaneously assert risk-off conditions for the same market without conditional framing.

**HC-D-004** The hypothesis assertion MUST be consistent with the hypothesis_type. A hypothesis of type TEC-MOM MUST make a momentum-based assertion, not a fundamental valuation claim.

**HC-D-005** The governance_tier of a hypothesis MUST be consistent with the governance_tier of its hypothesis_type in the Catalog. Individual hypotheses may not override the governance tier assigned to their type.

**HC-D-006** Parent-child hypothesis relationships MUST be logically consistent. A child hypothesis MUST NOT assert conditions that contradict the parent hypothesis without a conflict flag.

**HC-D-007** A composite hypothesis MUST NOT include constituent hypotheses that are in direct conflict (conflict_status = MAJOR) without an explicit conflict disclosure in the composite record.

**HC-D-008** The subject_domain of a hypothesis MUST be consistent with its category_code. A company hypothesis (CMP) MUST NOT declare a macro domain subject.

**HC-D-009** The scoring tier (HCS_tier) MUST be consistent with the numerical HCS value. A hypothesis with HCS = 0.75 MUST be assigned CREDIBLE, not STRONG or PROVISIONAL.

**HC-D-010** Version chain consistency: each new version MUST record an explicit reason for the version change. "Unknown reason" is not a valid version delta reason.

---

### 9.6 Category HC-E — Conflict Rules (10 rules)

**HC-E-001** Conflicting hypotheses MUST NOT be silently suppressed. Both sides of every conflict MUST be preserved and presented to the Reasoning Engine with their conflict_status.

**HC-E-002** The conflict_status field MUST be computed by the Conflict Manager and MUST NOT be manually overridden except by the Governance Manager in a documented governance action.

**HC-E-003** MAJOR conflicts MUST be alerted to the domain owner within 5 minutes of detection. The Conflict Manager is responsible for this notification.

**HC-E-004** Adjudication of a MAJOR conflict MUST be recorded in both conflicting hypothesis records and in the Audit Manager. Silent adjudication is prohibited.

**HC-E-005** A hypothesis adjudicated as the weaker side of a MAJOR conflict MUST receive an effective weight reduction of 30–50%. The exact percentage is determined by the HCS ratio of the two hypotheses. The reduction MUST be documented.

**HC-E-006** A hypothesis in COMPETING status MUST remain in the active hypothesis set distributed to the Reasoning Engine. It MUST NOT be hidden, filtered, or suppressed on the grounds of being the weaker side.

**HC-E-007** Conflict detection MUST be performed on every new hypothesis before it transitions to ACTIVE. No hypothesis may become ACTIVE without a conflict check.

**HC-E-008** Conflict resolution (transition from COMPETING to ACTIVE) MUST be triggered only by an objective change in the evidence picture — not by human preference or administrative action.

**HC-E-009** Circular conflicts — where A conflicts with B, B conflicts with C, and C conflicts with A — MUST be detected and escalated to the Governance Manager as a multi-party conflict requiring governance resolution.

**HC-E-010** The conflict_status field on a hypothesis MUST be updated within 60 seconds of any change that affects the conflict assessment — new evidence, evidence withdrawal, score changes, or retirement of the opposing hypothesis.

---

### 9.7 Category HC-F — Evolution Rules (8 rules)

**HC-F-001** Hypothesis evolution MUST be driven by evidence changes and context changes only. Scores MUST NOT be manually adjusted outside of documented governance recalibration events.

**HC-F-002** A new hypothesis version MUST be created whenever the HCS changes by more than 0.05 or the HCS_tier changes. Score changes below 0.05 do not require a version.

**HC-F-003** The evolution_generation counter MUST be incremented with each new version. The original hypothesis has evolution_generation = 0.

**HC-F-004** Hypothesis retirement through evidence withdrawal MUST be triggered automatically when both: (a) HCS drops below 0.20 AND (b) the number of active supporting evidence items drops to 0. Retirement MUST NOT require human confirmation in this case.

**HC-F-005** A hypothesis that has been retired MUST NOT be reinstated. If conditions change to support a similar explanation, a new hypothesis with a new hypothesis_id MUST be created.

**HC-F-006** Calibration corrections to scoring parameters MUST NOT retroactively alter historical hypothesis scores. Only current and future scoring is affected by recalibration.

**HC-F-007** Template improvements proposed by the Evolution Manager MUST go through governance approval before taking effect. No template change may be applied without Governance Manager sign-off.

**HC-F-008** The Evolution Manager MUST maintain a trajectory record for every active hypothesis: is the hypothesis strengthening, weakening, or stable? This trajectory MUST be available to the Reasoning Engine.

---

### 9.8 Category HC-G — Governance Rules (10 rules)

**HC-G-001** Every hypothesis type MUST have a designated domain owner. Hypothesis types without an owner may not be active.

**HC-G-002** New hypothesis types MUST be approved by the Governance Manager before the first hypothesis of that type is created in the Registry.

**HC-G-003** All hypothesis records MUST carry a governance_tier assignment. Hypotheses without a governance tier may not be distributed to consumers.

**HC-G-004** Access to CONFIDENTIAL-classified hypotheses MUST be enforced at the Retrieval Service layer. No component may bypass access control for any hypothesis, regardless of urgency.

**HC-G-005** Every governance decision affecting the Hypothesis Engine MUST be recorded in the Governance Audit Log. Unrecorded governance decisions are invalid.

**HC-G-006** Retention policy expiry MUST trigger archival. Hypotheses MUST NOT remain in the active Registry beyond their retention period.

**HC-G-007** No hypothesis may be permanently deleted before its regulatory retention period has expired, regardless of quality or relevance.

**HC-G-008** Governance policies MUST be documented, versioned, and accessible to all domain owners. Undocumented policies may not be enforced.

**HC-G-009** A governance review MUST be triggered when: a new hypothesis type is proposed; a constitutional rule is proposed for change; a CRITICAL calibration breach occurs; an access control violation is detected.

**HC-G-010** The Governance Manager MUST maintain a dashboard showing: active hypothesis type count, active hypothesis count by tier, unresolved MAJOR conflicts, open governance actions, and retention compliance rate.

---

### 9.9 Category HC-H — Auditability Rules (8 rules)

**HC-H-001** Every hypothesis creation, status transition, version creation, scoring event, and retirement MUST be recorded in the Audit Manager's append-only log.

**HC-H-002** Audit records MUST be append-only. No audit record may be modified, overwritten, or deleted under any circumstances.

**HC-H-003** Audit records for CRITICAL-tier hypotheses MUST be retained for a minimum of 7 years.

**HC-H-004** All conflict detections, adjudications, and resolutions MUST be recorded in the audit log with full detail of both conflicting hypothesis IDs, the adjudication basis, and the outcome.

**HC-H-005** Hypothesis operations MUST NOT proceed if the Audit Manager cannot accept the corresponding audit record. Audit write failure is blocking.

**HC-H-006** The audit trail MUST be sufficient to fully reconstruct the history of any hypothesis from creation to archival, including every evidence update, score change, conflict event, and version progression.

**HC-H-007** Failed hypothesis operations (validation failures, rejected candidates, dead-letter items) MUST be recorded in the audit log with reason codes.

**HC-H-008** The Audit Manager MUST produce on-demand audit reports for any hypothesis, any time range, and any event type. Audit queries MUST be answerable within 500ms for result sets up to 1,000 records.

---

### 9.10 Category HC-I — Historical Preservation Rules (6 rules)

**HC-I-001** All retired and archived hypotheses MUST be preserved with their complete version chain, evidence refs, and audit trail. No information may be stripped from a retired hypothesis record.

**HC-I-002** Point-in-time queries on historical hypotheses MUST use creation_timestamp semantics, not hypothesis_timestamp semantics. This is the only correct PIT anchor for hypothesis history.

**HC-I-003** Recalibration of scoring parameters MUST NOT alter historical hypothesis scores. Historical scores are immutable records of the system's state at the time they were computed.

**HC-I-004** Historical hypotheses used in backtesting MUST be flagged with PIT_COMPLIANT and must carry the analysis_timestamp for which they were reconstructed. Unflagged historical hypotheses may not be used in quantitative research.

**HC-I-005** The Hypothesis Archive Manager MUST maintain an unbroken chain of custody for all archived hypotheses, with audit trail confirming the archival event, date, and responsible component.

**HC-I-006** Archived hypotheses MUST be retrievable by the Research Layer within 300ms for hot-tier records and within 5 seconds for cold-tier records.

---

### 9.11 Summary of Constitutional Rule Counts

| Category | Code | Count |
|---|---|---|
| Identity | HC-A | 10 |
| Evidence Support | HC-B | 10 |
| Validity | HC-C | 12 |
| Consistency | HC-D | 10 |
| Conflict | HC-E | 10 |
| Evolution | HC-F | 8 |
| Governance | HC-G | 10 |
| Auditability | HC-H | 8 |
| Historical Preservation | HC-I | 6 |
| **Total** | | **84 rules** |

---
## PART X — HYPOTHESIS READINESS CHECKLIST

### 10.1 Purpose

Before a hypothesis is released for consumption by the Reasoning Engine, it must pass all readiness criteria. This checklist defines the minimum standard for a hypothesis to be considered analytically ready.

---

### 10.2 Section R01 — Generated

| Criterion | Required | Check |
|---|---|---|
| Hypothesis candidate record fully assembled | Yes | All schema fields populated |
| hypothesis_id assigned by Identity Manager | Yes | Non-null, conforming to format |
| hypothesis_type registered in Catalog | Yes | Type code exists |
| At least 1 supporting evidence item linked | Yes | evidence_refs not empty |
| Generation signal audit record logged | Yes | Audit Manager confirmation |
| No duplicate hypothesis in Registry for same subject, type, timestamp | Yes | Dedup check passed |

---

### 10.3 Section R02 — Validated

| Criterion | Required | Check |
|---|---|---|
| L1 Schema validation passed | Yes | All required fields present and typed |
| L2 Identity validation passed | Yes | hypothesis_id unique, entity_ids valid |
| L3 Evidence validation passed | Yes | All evidence_refs resolve to ACTIVE records |
| L4 Temporal validation passed | Yes | Timestamps valid; no future timestamps |
| L5 Semantic validation passed | Yes | Assertion non-trivial; testability conditions present |
| L6 Type validation passed | Yes | Type code in Catalog |
| L7 Threshold validation passed | Yes | net_evidence_weight ≥ 0.20 |
| Validation audit record logged | Yes | Audit Manager confirmation |

---

### 10.4 Section R03 — Evidence Linked

| Criterion | Required | Check |
|---|---|---|
| All supporting evidence records ACTIVE status | Yes | Evidence Registry check |
| All contradicting evidence records identified and linked | Yes | Matcher sweep completed |
| Evidence directionality (SUPPORTING/CONTRADICTING) assigned for all refs | Yes | No UNCLASSIFIED refs |
| net_evidence_weight computed and stored | Yes | Field is not null |
| Evidence lineage accessible for all refs | Yes | Lineage pointers valid |
| ECS values captured at link time for all refs | Yes | HCS computation basis established |

---

### 10.5 Section R04 — Scored

| Criterion | Required | Check |
|---|---|---|
| HCS computed across all 10 dimensions | Yes | All dimension scores non-null |
| HCS-C computed and stored | Yes | Confidence Engine output received |
| HCS_tier assigned | Yes | Tier consistent with HCS value |
| Regime-sensitive modifiers applied | Yes | Current regime modifier applied |
| Scoring audit record logged | Yes | Audit Manager confirmation |
| Calibration parameters applied (if available) | Required | CONFIDENCE_UNCALIBRATED flag if not |

---

### 10.6 Section R05 — Ranked

| Criterion | Required | Check |
|---|---|---|
| rank_global assigned | Yes | Ranking Engine output received |
| rank_in_type assigned | Yes | Type-specific rank assigned |
| Ranking based on current HCS | Yes | Rank reflects latest score |
| Ranking audit event emitted | Yes | Health Service metric updated |

---

### 10.7 Section R06 — Compared

| Criterion | Required | Check |
|---|---|---|
| Pairwise comparison against active hypotheses of same subject and domain | Yes | Comparator sweep completed |
| Dominance relationships recorded | Yes | No pending comparisons |
| Competing hypothesis candidates identified | Yes | Forwarded to Conflict Manager |

---

### 10.8 Section R07 — Conflict Checked

| Criterion | Required | Check |
|---|---|---|
| Conflict Manager sweep completed | Yes | All active hypotheses for same subject scanned |
| conflict_status assigned: NONE/MINOR/MODERATE/MAJOR | Yes | Non-null status |
| MAJOR conflicts adjudicated | Required | Adjudication record exists if MAJOR |
| Conflict audit record logged | Yes | Audit Manager confirmation |
| Domain owner notified of MAJOR conflicts | Required | Notification within 5 minutes |

---

### 10.9 Section R08 — Context Assigned

| Criterion | Required | Check |
|---|---|---|
| ContextRecord attached | Yes | All required context fields present |
| regime captured | Yes | Non-null |
| VIX level captured | Yes | Non-null |
| market_session captured | Yes | Non-null |
| active_events list captured | Yes | Can be empty; must be populated |
| CONTEXT_PARTIAL or CONTEXT_COMPLETE flag set | Yes | Status set |

---

### 10.10 Section R09 — Versioned

| Criterion | Required | Check |
|---|---|---|
| version_number = 1 for new hypothesis | Yes | First version recorded |
| Version chain record created in Registry | Yes | Version Manager confirmation |
| Version delta recorded | Yes | "New hypothesis" as delta for v1 |
| Previous version transitioned to SUPERSEDED (for revised hypotheses) | Required if v > 1 | Supersession record present |

---

### 10.11 Section R10 — Governed

| Criterion | Required | Check |
|---|---|---|
| governance_tier assigned from Catalog | Yes | Non-null |
| domain_owner assigned from type ownership record | Yes | Non-null |
| Access control applied per governance_tier | Yes | CRITICAL-tier restrictions enforced |
| Governance audit record logged | Yes | Audit Manager confirmation |

---

### 10.12 Section R11 — Audited

| Criterion | Required | Check |
|---|---|---|
| Audit record created for hypothesis creation event | Yes | audit_trail_id assigned |
| All intermediate events (validation, scoring, conflict check) logged | Yes | Audit trail complete |
| Audit record append-only | Yes | No modification possible |
| Audit store write confirmed | Yes | Blocking write confirmation |

---

### 10.13 Section R12 — Archived (applicable at retirement)

| Criterion | Required | Check |
|---|---|---|
| Complete version chain preserved | Yes | No version chain gaps |
| All evidence refs preserved at retirement time | Yes | Snapshot taken at retirement |
| Audit trail preserved with hypothesis | Yes | audit_trail_id still valid |
| Storage tier transition completed | Yes | Status = ARCHIVED in Registry |
| Retention clock started | Yes | Archival_timestamp recorded |

---

### 10.14 Section R13 — Traceable

| Criterion | Required | Check |
|---|---|---|
| All evidence refs trace to valid Evidence Engine records | Yes | Evidence Registry check |
| Evidence records trace to Observation Engine observations | Yes | Lineage chain valid |
| Version chain is unbroken from v1 to current | Yes | No version gaps |
| Audit trail covers all lifecycle events | Yes | No audit gaps |
| lineage_record_id populated | Yes | Non-null |

---

### 10.15 Section R14 — Ready for Reasoning Engine

| Criterion | Required | Check |
|---|---|---|
| lifecycle_status = ACTIVE or COMPETING | Yes | Status confirmed |
| HCS_tier ≥ SPECULATIVE (any tier is distributable) | Yes | HCS ≥ 0.0 (SPECULATIVE or above) |
| conflict_status set | Yes | Non-null |
| Testability conditions populated | Yes | At least 2 conditions |
| Falsification conditions populated | Yes | At least 1 condition |
| Distribution Service ready to publish | Yes | Consumer channel active |
| Reasoning Engine subscription confirmed | Yes | Channel health check passed |

---

### 10.16 Use-Case Readiness Matrix

| Use Case | Min Sections Required | Min HCS Tier | Additional Requirements |
|---|---|---|---|
| Real-time Reasoning Engine input | R01–R14 all | SPECULATIVE | ACTIVE status |
| High-conviction decision support | R01–R14 all | CREDIBLE | conflict_status NONE or MINOR |
| Portfolio risk analysis | R01–R14 all | WEAK | RSK or PRT category |
| Backtesting research | R01–R14 all | Any | PIT_COMPLIANT flag; HIS prefix |
| Regulatory audit | R01–R14 all | Any | Full audit trail; 7-year retention |
| Knowledge Engine update | R01–R13 | PROVISIONAL | Evidence refs complete |
| Real-time conflict monitoring | R01–R11 | Any | conflict_status monitored |

---
## SUPPLEMENT A — HYPOTHESIS TAXONOMY

### A.1 Purpose

The Hypothesis Taxonomy is the authoritative reference of all hypothesis type codes, their category affiliation, typical evidence sources, minimum HCS for CREDIBLE tier, typical active duration, governance tier, and Reasoning Engine priority.

---

### A.2 Market Domain Hypothesis Types

| Type Code | Name | Primary Evidence | Min HCS (CREDIBLE) | Typical Duration | Gov Tier | RE Priority |
|---|---|---|---|---|---|---|
| MKT-TREND | Market trend hypothesis | Price, volume, breadth | 0.65 | 1–14 days | HIGH | HIGH |
| MKT-REGIME | Market regime hypothesis | Regime evidence, VIX, macro | 0.65 | 1–30 days | CRITICAL | CRITICAL |
| MKT-BREADTH | Market breadth hypothesis | Breadth indicators, advance/decline | 0.65 | 1–7 days | HIGH | HIGH |
| MKT-MOMENTUM | Market momentum hypothesis | RSI, MACD, rate-of-change | 0.65 | 30 min–5 days | HIGH | HIGH |
| MKT-MEAN-REV | Market mean reversion hypothesis | Z-score, bollinger band deviation | 0.65 | 1–7 days | HIGH | MEDIUM |
| MKT-TOPPING | Market topping hypothesis | Distribution evidence, volume-price div | 0.70 | 3–21 days | CRITICAL | CRITICAL |
| MKT-BOTTOMING | Market bottoming hypothesis | Accumulation evidence, VIX spike | 0.70 | 3–21 days | CRITICAL | CRITICAL |
| MKT-RANGE | Market ranging hypothesis | Range evidence, low directional signal | 0.60 | 3–14 days | HIGH | MEDIUM |

---

### A.3 Technical Hypothesis Types

| Type Code | Name | Primary Evidence | Min HCS (CREDIBLE) | Typical Duration | Gov Tier | RE Priority |
|---|---|---|---|---|---|---|
| TEC-MOM | Technical momentum | Price, RSI, MACD, RoC | 0.65 | 1–5 days | HIGH | HIGH |
| TEC-REV | Technical mean reversion | Price, Bollinger, Z-score | 0.65 | 1–5 days | HIGH | HIGH |
| TEC-BREAKOUT | Technical breakout | Price, volume at resistance | 0.70 | 30 min–3 days | HIGH | CRITICAL |
| TEC-BREAKDOWN | Technical breakdown | Price, volume at support | 0.70 | 30 min–3 days | HIGH | CRITICAL |
| TEC-PATTERN | Price pattern | Pattern observation, volume | 0.65 | 1–10 days | MEDIUM | HIGH |
| TEC-VOLUME | Volume anomaly | Volume, price-volume divergence | 0.60 | 1–3 days | MEDIUM | MEDIUM |
| TEC-INDICATOR | Indicator state | Oscillator, trend indicator | 0.60 | 30 min–2 days | LOW | MEDIUM |
| TEC-SUPPORT | Support zone hypothesis | Price at support, order flow | 0.65 | 1–5 days | HIGH | HIGH |
| TEC-RESISTANCE | Resistance zone hypothesis | Price at resistance, order flow | 0.65 | 1–5 days | HIGH | HIGH |
| TEC-RANGE | Technical range hypothesis | Price range evidence | 0.60 | 1–7 days | MEDIUM | MEDIUM |

---

### A.4 Fundamental Hypothesis Types

| Type Code | Name | Primary Evidence | Min HCS (CREDIBLE) | Typical Duration | Gov Tier |
|---|---|---|---|---|---|
| FND-VALUATION | Valuation hypothesis | P/E, P/B, EV/EBITDA evidence | 0.65 | 1–12 months | HIGH |
| FND-EARNINGS | Earnings trajectory hypothesis | EPS, revenue growth evidence | 0.65 | 1–6 months | HIGH |
| FND-REVENUE | Revenue hypothesis | Revenue evidence, guidance evidence | 0.65 | 1–6 months | HIGH |
| FND-MARGINS | Margin hypothesis | Gross/EBITDA margin evidence | 0.65 | 1–6 months | HIGH |
| FND-CASHFLOW | Cashflow hypothesis | FCF evidence, capex evidence | 0.65 | 1–6 months | HIGH |
| FND-DEBT | Debt hypothesis | D/E, interest coverage evidence | 0.65 | 1–6 months | HIGH |
| FND-DIVIDEND | Dividend hypothesis | Dividend announcement evidence | 0.70 | 1–3 months | HIGH |
| FND-MANAGEMENT | Management action hypothesis | Guidance, buyback, restructuring evidence | 0.65 | 1–3 months | HIGH |

---

### A.5 Macro, Sector, Risk, and Portfolio Types

| Type Code | Name | Category | Primary Evidence | Gov Tier |
|---|---|---|---|---|
| MAC-RATES | Rate policy hypothesis | MAC | RBI rate evidence, bond yield evidence | HIGH |
| MAC-INFLATION | Inflation hypothesis | MAC | CPI, WPI evidence | HIGH |
| MAC-GROWTH | GDP growth hypothesis | MAC | GDP evidence, PMI evidence | HIGH |
| MAC-CURRENCY | Currency hypothesis | MAC | FX rate evidence, capital flow evidence | HIGH |
| MAC-POLICY | Monetary policy hypothesis | MAC | RBI guidance, policy statement evidence | CRITICAL |
| SEC-ROTATION | Sector rotation hypothesis | SEC | Relative strength, flow evidence | HIGH |
| SEC-MOMENTUM | Sector momentum hypothesis | SEC | Sector price, breadth evidence | HIGH |
| SEC-RECOVERY | Sector recovery hypothesis | SEC | Fundamental improvement evidence | HIGH |
| RSK-CONCENTRATION | Concentration risk hypothesis | RSK | Portfolio exposure evidence | CRITICAL |
| RSK-DRAWDOWN | Drawdown risk hypothesis | RSK | Portfolio P&L evidence | CRITICAL |
| RSK-TAIL | Tail risk hypothesis | RSK | VIX evidence, skew evidence | CRITICAL |
| PRT-ATTRIBUTION | Performance attribution hypothesis | PRT | Return decomposition evidence | HIGH |
| PRT-FACTOR | Factor exposure hypothesis | PRT | Factor loading evidence | HIGH |
| LIQ-FLOW | Institutional flow hypothesis | LIQ | FII/DII flow evidence | HIGH |
| VOL-COMPRESSION | Volatility compression hypothesis | VOL | VIX, HV evidence | HIGH |
| SNT-EXTREME | Extreme sentiment hypothesis | SNT | Sentiment survey, PCR evidence | HIGH |
| BEH-HERD | Herd behaviour hypothesis | BEH | Flow concentration evidence | MEDIUM |
| EVT-EARNINGS | Earnings event hypothesis | EVT | Earnings announcement evidence | HIGH |
| XMK-CONTAGION | Contagion risk hypothesis | XMK | Cross-market correlation evidence | CRITICAL |
| XAS-RISK-OFF | Risk-off hypothesis | XAS | Multi-asset evidence | CRITICAL |

---

## SUPPLEMENT B — HYPOTHESIS SCORING REFERENCE

### B.1 Dimension Weight Table

| Dim | Code | Weight | Normalised |
|---|---|---|---|
| D01 | Strength | 0.18 | 18.0% |
| D02 | Evidence Support | 0.20 | 20.0% |
| D03 | Consistency | 0.12 | 12.0% |
| D04 | Coverage | 0.08 | 8.0% |
| D05 | Novelty | 0.05 | 5.0% |
| D06 | Coherence | 0.10 | 10.0% |
| D07 | Completeness | 0.07 | 7.0% |
| D08 | Stability | 0.08 | 8.0% |
| D09 | Confidence | 0.10 | 10.0% |
| D10 | Traceability | 0.02 | 2.0% |
| **Total** | | **1.00** | **100%** |

---

### B.2 Representative HCS by Scenario

| Scenario | D01 | D02 | D09 | HCS (approx) | Tier |
|---|---|---|---|---|---|
| Strong technical breakout with volume confirmation, high ECS evidence | 0.90 | 0.92 | 0.88 | ~0.87 | STRONG |
| Fundamental undervaluation with multi-source corroboration | 0.85 | 0.88 | 0.82 | ~0.83 | STRONG |
| Macro rate pause evidence with consistent indicators | 0.80 | 0.80 | 0.78 | ~0.78 | CREDIBLE |
| Sector rotation with partial evidence | 0.70 | 0.72 | 0.70 | ~0.70 | CREDIBLE |
| Technical pattern with single evidence source | 0.65 | 0.62 | 0.65 | ~0.63 | PROVISIONAL |
| Sentiment hypothesis with noisy evidence | 0.55 | 0.58 | 0.52 | ~0.55 | PROVISIONAL |
| Behavioural hypothesis with minimal corroboration | 0.45 | 0.42 | 0.48 | ~0.44 | WEAK |
| AI-generated hypothesis with low ECS evidence | 0.35 | 0.38 | 0.32 | ~0.35 | WEAK |
| Single evidence item, unverified source | 0.25 | 0.28 | 0.25 | ~0.26 | SPECULATIVE |
| Hypothesis forming (evidence still accumulating) | 0.15 | 0.20 | 0.18 | ~0.17 | SPECULATIVE |

---

### B.3 HCS-C Calibration Reference

| HCS-C Range | Interpretation | Historical Accuracy Target |
|---|---|---|
| 0.85–1.00 | Very high confidence | 85–100% of comparable past hypotheses were correct |
| 0.70–0.84 | High confidence | 70–84% historical accuracy |
| 0.55–0.69 | Moderate confidence | 55–69% historical accuracy |
| 0.40–0.54 | Low confidence | 40–54% historical accuracy |
| 0.00–0.39 | Very low confidence | < 40% historical accuracy |

**Calibration requirement:** For any hypothesis type and source tier, if | assigned HCS-C mean − observed accuracy | > 0.10 over 90 days, RECALIBRATION_NEEDED alert is triggered.

---

### B.4 Evidence Independence Effect on HCS-C

When N evidence items all support the same hypothesis but are correlated (independence_score < 0.50), the effective contribution to HCS-C is reduced:

$$HCS\text{-}C_{effective} = 1 - \prod_{i=1}^{N}(1 - ECS_i \cdot IS_i)$$

Where $IS_i$ is the independence score of evidence item $i$. When $IS_i = 1.0$ for all items (fully independent), the formula gives maximum confidence. When $IS_i \approx 0$ (all correlated), the formula converges to the confidence of the single strongest evidence item.

---

## SUPPLEMENT C — CONFLICT MATRIX

### C.1 Conflict Classification

Two hypotheses conflict if they are:
- Same subject entity or domain
- Same or overlapping observation window (within 30% of each other's time span)
- Mutually exclusive assertions — the conditions asserted by Hypothesis A are logically incompatible with the conditions asserted by Hypothesis B

---

### C.2 Conflict Severity Classification Matrix

| Hypothesis A Tier | Hypothesis B Tier | Conflict Severity | Adjudication Required |
|---|---|---|---|
| STRONG (≥0.80) | STRONG (≥0.80) | MAJOR | Yes — immediate |
| STRONG (≥0.80) | CREDIBLE (0.65–0.79) | MAJOR | Yes — immediate |
| CREDIBLE (0.65–0.79) | CREDIBLE (0.65–0.79) | MAJOR | Yes — immediate |
| STRONG/CREDIBLE | PROVISIONAL (0.50–0.64) | MODERATE | Yes — within 60 minutes |
| PROVISIONAL | PROVISIONAL | MODERATE | Review within 4 hours |
| Any | WEAK (0.35–0.49) | MINOR | Monitor |
| Any | SPECULATIVE (0–0.34) | MINOR | Monitor |

---

### C.3 Adjudication Decision Rules

| Condition | Adjudication Decision |
|---|---|
| Hypothesis A has 3+ more independent evidence items than B | A dominates; B effective weight reduced by 40% |
| A's ECS-weighted average is 0.15+ above B | A dominates; B effective weight reduced by 35% |
| B's evidence is 3x more recent than A | B may be dominant despite lower HCS; review triggered |
| A and B have identical HCS within 0.05 | DEADLOCK; both flagged COMPETING; Reasoning Engine handles both |
| One hypothesis contains a CONTEXT_STALE flag | Non-stale hypothesis dominates |

---

### C.4 Conflict Timeline Requirements

| Event | Maximum Time Allowed |
|---|---|
| MAJOR conflict detection to status update | 60 seconds |
| MAJOR conflict detection to domain owner alert | 5 minutes |
| MAJOR conflict adjudication | 15 minutes (automated) |
| MAJOR conflict review completion | 2 business days |
| MODERATE conflict status update | 5 minutes |
| MINOR conflict status update | 30 minutes |
| Conflict resolution (evidence-driven) | 60 seconds from trigger |

---

### C.5 EQS Impact of Conflict on Hypothesis Quality

| Conflict Status | D02 (Evidence Support) modifier | D03 (Consistency) modifier | Net HCS impact (approx) |
|---|---|---|---|
| NONE | × 1.00 | × 1.00 | 0 |
| MINOR | × 0.95 | × 0.95 | −0.03 |
| MODERATE | × 0.85 | × 0.85 | −0.06 |
| MAJOR | × 0.65 | × 0.70 | −0.12 |

Note: These modifiers are applied to the weaker side of the conflict. The stronger side is unmodified.

---
## SUPPLEMENT D — EVOLUTION EXAMPLES

### D.1 Purpose

This supplement provides three detailed examples of hypothesis evolution — documenting how a hypothesis is created, how it evolves as evidence changes, and how it is eventually retired or superseded.

---

### D.2 Evolution Example 1 — Technical Momentum Hypothesis

**Scenario:** NIFTY50 enters a momentum phase.

**Day 0 — Creation (v1):**
- Triggering evidence: MKT-PRC-OHLCV-1D shows 3 consecutive higher highs and higher lows; RSI (14-day) = 62; 20-day rate-of-change = +4.2%.
- Hypothesis: `HYP-TEC-MOM-20260703-00000001`
- Assertion: "NIFTY50 is exhibiting a positive momentum state: three consecutive higher-high, higher-low sessions; 14-day RSI at 62; 20-day RoC at +4.2%. Conditions are consistent with a momentum continuation regime."
- Supporting evidence: 3 items. HCS = 0.72. HCS_tier = CREDIBLE.

**Day 2 — Evidence update (v2):**
- New evidence: 4th consecutive higher-high session; RSI rises to 67; institutional inflow evidence (FII net buyer for 2nd consecutive day).
- Matcher adds 2 new supporting evidence items.
- HCS rises to 0.78. Tier: CREDIBLE (near STRONG threshold).
- Version 2 created. Delta: "3 new evidence items added; HCS +0.06."

**Day 5 — Regime context update (v3):**
- New evidence: India VIX falls to 11.8 (low volatility regime).
- Context Manager flags BULL_QUIET regime now active.
- Regime modifier for D06 (Coherence) applied: × 1.10 (coherence premium in BULL_QUIET).
- HCS rises to 0.81. Tier: STRONG.
- Version 3 created.

**Day 8 — Contradicting evidence (v4):**
- New evidence: Volume-price divergence detected — NIFTY50 makes higher high but daily volume is 15% below 20-day average. Bearish volume divergence observation.
- Matcher adds contradicting evidence item (ECS = 0.72, weight = 0.35).
- net_evidence_weight reduced. HCS falls to 0.75. Tier: CREDIBLE.
- Version 4 created. Conflict_status checked: no other competing hypothesis; NONE.

**Day 11 — Breakdown of momentum (v5 → retirement):**
- New evidence: Price gaps down 1.8% on high volume; RSI falls below 50; 20-day RoC turns negative (−0.3%).
- 3 supporting evidence items SUPERSEDED by Matcher.
- 2 strong contradicting evidence items added.
- HCS falls to 0.19. Tier: below SPECULATIVE threshold.
- Constitutional rule HC-F-004 triggers: HCS < 0.20 AND supporting evidence = 0.
- Hypothesis retired. Version 5 records retirement. Dependency children notified.

**Evolution trajectory:** CREDIBLE → CREDIBLE (growing) → STRONG → CREDIBLE (conflict) → RETIRED (evidence collapse).

---

### D.3 Evolution Example 2 — Fundamental Valuation Hypothesis

**Scenario:** HDFC Bank earnings quality improvement.

**Creation (v1) — Post-Q4 results:**
- Triggering evidence: Quarterly earnings evidence (ECS 0.92): revenue +18% YoY, NIM expansion to 4.3%, NPAs declined to 1.2%.
- Hypothesis: `HYP-FND-VALUATION-20260703-00000002`
- Assertion: "HDFC Bank is exhibiting fundamental indicators consistent with earnings quality improvement — NIM expansion, NPA reduction, and revenue growth above sector median — while trading at a 12-month forward P/E of 17.5x, a 15% discount to its 5-year mean of 20.6x. This is consistent with a valuation undervaluation hypothesis."
- HCS = 0.78. Tier: CREDIBLE.

**1 month later (v2) — Analyst estimate upgrades:**
- New evidence: Bloomberg consensus earnings estimates upgraded for the next 2 quarters; target price upgrades from 3 institutional analysts.
- HCS = 0.82. Tier: STRONG.

**2 months later (v3) — Sector context improvement:**
- New evidence: Sector rotation hypothesis for Banking becomes active; FII inflow evidence into banking sector.
- Context change: sector_context field updated.
- HCS = 0.84. Tier: STRONG.

**4 months later (v4) — Valuation re-rating:**
- New evidence: P/E has re-rated to 19.8x — now close to the 5-year mean. The valuation discount thesis is weakening.
- Contradicting evidence: P/E above 19.0x signals re-rating nearly complete; residual upside evidence reduced.
- D01 (Strength) reduces: the assertion "trading at 15% discount to mean" is no longer accurate.
- HCS falls to 0.61. Tier: PROVISIONAL.

**5 months later — Supersession:**
- New evidence is sufficient to create a new hypothesis: HYP-FND-VALUATION-20261203-00000005 with updated assertion reflecting the re-rated valuation.
- Original hypothesis v4 transitions to SUPERSEDED.
- Dependency children (composite hypothesis using this as constituent) notified.

---

### D.4 Evolution Example 3 — Composite Hypothesis Evolution

**Scenario:** Full market weakness composite.

**Step 1 — Three constituent hypotheses become ACTIVE:**
- H1: `HYP-MKT-TOPPING-...` (HCS 0.75) — market distribution evidence
- H2: `HYP-LIQ-FLOW-...` (HCS 0.72) — FII outflow evidence
- H3: `HYP-MAC-RATES-...` (HCS 0.68) — rate tightening risk evidence

**Step 2 — Fusion Manager identifies fusion opportunity:**
- All three are non-conflicting.
- All are related to the same broad explanation: market weakness conditions.
- Compatibility check passed.

**Step 3 — Composite constructed:**
- `HYP-COM-MARKET-20260703-00000003`
- Assertion: "NIFTY50 market conditions are consistent with a composite weakness hypothesis: concurrent distribution pattern evidence, institutional outflow evidence, and monetary tightening risk evidence create a coherent multi-dimensional explanation for potential market weakness."
- Composite HCS = weighted(H1, H2, H3) + coherence_bonus(+0.05) = 0.78. Tier: CREDIBLE.

**Step 4 — One constituent weakens:**
- H3 (macro rates hypothesis) evidence weakens — RBI holds rates; MAC-RATES evidence shifts to neutral.
- H3 HCS falls to 0.41.
- Composite HCS recomputed: 0.71 (lower, but still CREDIBLE).
- Composite v2 created.

**Step 5 — H3 retired:**
- H3 retires. Dissolution check: does the composite hold with 2 constituents?
- Dissolution threshold: if a constituent falls below 0.35 and was contributing > 25% of composite weight → dissolve.
- H3 contributed 22%: below 25% threshold → composite survives with 2 constituents.
- Composite HCS recomputed to 0.74. Tier: CREDIBLE.
- Composite v3 created. parent_hypothesis_ids updated (H3 removed).

---

## SUPPLEMENT E — DEPENDENCY EXAMPLES

### E.1 Purpose

This supplement illustrates hypothesis dependency relationships — how composite hypotheses depend on constituent hypotheses, how hierarchical hypotheses depend on their parent, and how dependency changes propagate.

---

### E.2 Example 1 — Parent-Child Hierarchy

```
MACRO REGIME HYPOTHESIS (Parent)
HYP-MAC-POLICY-20260703-00000010
"India macro conditions are consistent with a monetary tightening risk regime"
HCS = 0.72

    ├──► SECTOR IMPACT HYPOTHESIS (Child 1)
    │    HYP-SEC-ROTATION-20260703-00000011
    │    "Banking sector rate sensitivity is consistent with underperformance
    │     in a rate tightening environment"
    │    Depends on: Parent hypothesis (rate tightening must hold)
    │    HCS = 0.68
    │
    └──► COMPANY IMPACT HYPOTHESIS (Child 2)
         HYP-CMP-VALUATION-20260703-00000012
         "HDFC Bank forward P/E of 17.5x is at risk in a rate tightening environment
          due to NIM compression expectations"
         Depends on: Parent hypothesis AND Child 1
         HCS = 0.63

Propagation: If Parent hypothesis is retired → Child 1 dependency flag set → Child 2
dependency flag set (cascade through both levels).
```

---

### E.3 Example 2 — Composite Dependency

```
COMPOSITE WEAKNESS HYPOTHESIS
HYP-COM-MARKET-20260703-00000020
    │
    ├── HYP-MKT-TOPPING-... (parent_hypothesis_id)
    │   status: ACTIVE, HCS: 0.75
    │
    ├── HYP-LIQ-FLOW-... (parent_hypothesis_id)
    │   status: ACTIVE, HCS: 0.72
    │
    └── HYP-VOL-COMPRESSION-... (parent_hypothesis_id)
        status: ACTIVE, HCS: 0.68

Dependency rules:
- If ANY constituent drops to RETIRED AND its HCS contribution was > 25%
  → composite dissolution triggered
- If ALL constituents are RETIRED → composite must retire
- If 1 constituent is COMPETING (conflict) → composite flagged CONFLICT_IN_CONSTITUENT
```

---

### E.4 Dependency Cycle Detection

The Dependency Manager MUST detect and reject circular dependencies:

```
PROHIBITED PATTERN:
HYP-A depends on HYP-B
HYP-B depends on HYP-C
HYP-C depends on HYP-A   ← CYCLE DETECTED

Action: All three hypotheses quarantined;
        Governance Manager notified;
        Cycle resolution required before any are activated.
```

---

## SUPPLEMENT F — ANTI-PATTERNS

### F.1 Purpose

Anti-patterns are architectural mistakes that recur in hypothesis engine implementations. This supplement documents the 10 most dangerous anti-patterns and their detection and remediation.

---

### AP-01 — The Predictive Hypothesis

**Description:** A hypothesis that contains a price target, a directional forecast, or a future-state assertion. Example: "NIFTY50 will reach 24,000 by August."

**Harm:** Violates the cognitive layer separation. Predictions belong in the Prediction Engine (Layer 4+). If predictions enter the Hypothesis Engine, the Reasoning Engine receives pre-concluded inputs and performs circular reasoning.

**Detection:** assertion field scanned for future tense verbs, price targets, date-bound outcomes. Constitutional rule HC-C-008 violation.

**Remediation:** Reject at L5 semantic validation. Rephrase: "NIFTY50 is exhibiting evidence consistent with upward momentum conditions."

---

### AP-02 — The Evidence-Free Hypothesis

**Description:** A hypothesis constructed from assumptions or analyst opinion without any linked Evidence Engine records.

**Harm:** The IIOS operates on evidence. Evidence-free hypotheses corrupt the scoring system because they receive arbitrary scores that are not grounded in observed data quality.

**Detection:** HC-B-001 violation; evidence_refs empty.

**Remediation:** Reject at L7 threshold validation. If the analyst has a view without evidence, they must wait for evidence to accumulate before the hypothesis can be formed.

---

### AP-03 — The Stale Hypothesis

**Description:** A hypothesis whose evidence has all expired the freshness SLA but which remains ACTIVE.

**Harm:** The Reasoning Engine receives explanations based on outdated information, potentially the opposite of current conditions.

**Detection:** HC-B-010; Matcher detects all evidence refs STALE; FRESHNESS_WARNING flag.

**Remediation:** Trigger re-evaluation; if no fresh evidence exists to re-support the hypothesis, retire it.

---

### AP-04 — The Mute Conflict

**Description:** A conflicting hypothesis that has been silently suppressed rather than flagged and presented to the Reasoning Engine.

**Harm:** The Reasoning Engine receives an artificially clean picture — a single explanation when multiple competing ones exist. This leads to overconfident decisions.

**Detection:** HC-E-001 audit; conflict suppression events monitored by Audit Manager.

**Remediation:** All suppression logic is prohibited. Conflicting hypotheses must be distributed. The Conflict Manager must never suppress — only flag.

---

### AP-05 — The Grandfathered Hypothesis

**Description:** A hypothesis that was created during a different regime and allowed to remain ACTIVE without re-evaluation as the regime changes.

**Harm:** Hypotheses that made sense in BULL_QUIET may be actively misleading in BEAR_VOLATILE. Regime-stale hypotheses corrupt the Reasoning Engine's context.

**Detection:** Context Manager detects CONTEXT_STALE flag when regime changes; hypothesis not re-evaluated.

**Remediation:** All ACTIVE hypotheses must receive CONTEXT_STALE flag on regime change. Evolution Manager re-evaluates all flagged hypotheses within 30 minutes.

---

### AP-06 — The Correlated Confidence Inflation

**Description:** Ten correlated evidence items supporting the same hypothesis, each with ECS = 0.80, are treated as ten independent confirmations, producing HCS-C ≈ 1.0 when the correct value is 0.80.

**Harm:** Systematic overconfidence. The IIOS acts with near-certainty on explanations that are only moderately well-supported.

**Detection:** HC-C (independence check) from Evidence Engine; independence_score low for all evidence refs.

**Remediation:** Confidence Engine applies the independence-adjusted HCS-C formula (Supplement B.4). Correlated evidence is identified and adjusted.

---

### AP-07 — The Zombie Hypothesis

**Description:** A hypothesis that should have been retired (HCS < 0.20, no supporting evidence) but persists because the retirement trigger was not fired.

**Harm:** Accumulation of low-quality hypotheses degrades the active hypothesis set quality. Reasoning Engine is distracted by noise.

**Detection:** Evolution Manager periodic sweep; HC-F-004 constitutional monitoring.

**Remediation:** Enforce HC-F-004 strictly: automatic retirement when HCS < 0.20 AND supporting evidence = 0. No human confirmation required.

---

### AP-08 — The Embedded Conclusion

**Description:** A hypothesis whose assertion contains an embedded interpretation or conclusion, rather than a description of observed conditions. Example: "The market is about to correct" (prediction) vs "The market is exhibiting distribution evidence consistent with a late-cycle topping pattern" (legitimate hypothesis).

**Harm:** Introduces Layer 4 (Reasoning) content into Layer 3 (Explanation). The Reasoning Engine cannot reason independently from hypotheses that have pre-concluded.

**Detection:** NLP scanning of assertion field for conclusion language; HC-C-009 (future tense prohibition).

**Remediation:** Rewrite assertion as a present-tense description of observed conditions. Training for AI hypothesis generator on assertion framing.

---

### AP-09 — The Versioning Bypass

**Description:** A component directly modifies a hypothesis record in the Registry without going through the Version Manager, breaking the version chain.

**Harm:** Destroys the audit trail. Historical reconstruction is impossible. The hypothesis's evolution cannot be traced.

**Detection:** HC-A-008 integrity check; Registry write-access monitoring; unauthorised write alerts.

**Remediation:** Registry enforces write access restrictions. Only Version Manager may write to hypothesis fields that affect analytical content. Direct writes trigger immediate audit alert.

---

### AP-10 — The Unregistered Type

**Description:** A hypothesis is constructed using a type code that has not been approved in the Hypothesis Catalog, allowing uncontrolled type proliferation.

**Harm:** Unregistered types cannot be scored with validated parameters, cannot be governed with defined retention policies, and produce hypotheses of unknown quality.

**Detection:** HC-A-005 violation; Validator L6 check.

**Remediation:** Validator rejects at L6. The proposer must submit the type for Catalog registration through the governance workflow.

---
## SUPPLEMENT G — OPERATIONAL RUNBOOK

### G.1 Purpose

This runbook provides the operational procedures for starting, stopping, monitoring, and recovering the Hypothesis Engine in a production deployment.

---

### OR-01 — Startup Sequence

The Hypothesis Engine MUST be started in the following order. Components must not be started out of sequence.

| Step | Component | Check | SLA |
|---|---|---|---|
| 1 | Hypothesis Catalog | Load all type definitions; verify catalog version | ≤ 10s |
| 2 | Hypothesis Registry (read-only mode) | Connect to persistence layer; verify integrity | ≤ 15s |
| 3 | Hypothesis Audit Manager | Connect to audit log store; verify append capability | ≤ 5s |
| 4 | Hypothesis Registry (read-write mode) | Enable write access; replay WAL from last checkpoint | ≤ 30s |
| 5 | Hypothesis Version Manager | Verify version chain integrity of last 24h records | ≤ 20s |
| 6 | Hypothesis Identity Manager | Load last-used sequence numbers; verify no ID conflicts | ≤ 5s |
| 7 | Hypothesis Context Manager | Connect to Observation Engine context feed | ≤ 10s |
| 8 | Hypothesis Confidence Engine | Load calibration parameters from Evolution Manager | ≤ 10s |
| 9 | Hypothesis Scoring Engine | Load scoring weights from Catalog | ≤ 5s |
| 10 | Hypothesis Validator | Warm up validation rule set from Catalog | ≤ 5s |
| 11 | Hypothesis Ranking Engine | Load current active hypothesis scores for initial ranking | ≤ 15s |
| 12 | Hypothesis Comparator | Warm up entity-domain index | ≤ 10s |
| 13 | Hypothesis Conflict Manager | Scan active hypotheses for existing conflicts | ≤ 20s |
| 14 | Hypothesis Dependency Manager | Load dependency graph from Registry | ≤ 15s |
| 15 | Hypothesis Matcher | Subscribe to Evidence Engine active evidence stream | ≤ 5s |
| 16 | Hypothesis Generator | Load generation templates from Catalog; subscribe to evidence stream | ≤ 10s |
| 17 | Hypothesis Builder | Ready to accept generation signals | ≤ 5s |
| 18 | Hypothesis Fusion Manager | Load fusion eligibility rules; schedule fusion cycle | ≤ 5s |
| 19 | Hypothesis Evolution Manager | Resume pending evolution queue | ≤ 15s |
| 20 | Hypothesis Search Manager | Rebuild search indices | ≤ 60s |
| 21 | Hypothesis Governance Manager | Load governance policies; check review schedule | ≤ 5s |
| 22 | Hypothesis Archive Manager | Verify archive storage tiers accessible | ≤ 5s |
| 23 | Distribution Service | Open Reasoning Engine distribution channel | ≤ 5s |
| 24 | Health Service | Begin monitoring all components | ≤ 5s |

**Total expected startup time:** ≤ 5 minutes  
**Startup complete signal:** Health Service reports all 20 components UP.  
**Post-startup check:** Verify at least 10 ACTIVE hypotheses in Registry; verify Reasoning Engine subscription acknowledged.

---

### OR-02 — Graceful Shutdown Sequence

| Step | Action |
|---|---|
| 1 | Stop accepting new evidence from Evidence Engine (pause subscription) |
| 2 | Complete all in-flight hypothesis construction and validation (wait max 30s) |
| 3 | Complete all pending scoring and ranking operations (wait max 20s) |
| 4 | Flush distribution queue to Reasoning Engine |
| 5 | Stop Distribution Service |
| 6 | Flush Evolution Manager delta buffer |
| 7 | Stop Hypothesis Generator and Builder |
| 8 | Write checkpoint to Registry (WAL flush) |
| 9 | Stop Scoring Engine and Ranking Engine |
| 10 | Stop Conflict Manager and Fusion Manager |
| 11 | Stop Version Manager and Matcher |
| 12 | Stop Context Manager |
| 13 | Stop Audit Manager (flush final audit records) |
| 14 | Stop Registry |
| 15 | Stop Health Service last |

---

### OR-03 — Recovery Procedures

#### Procedure R-01 — Registry Failure Recovery

**Condition:** Hypothesis Registry unavailable (write or read failure).

1. Activate emergency buffer: all new hypotheses stored in memory buffer (max 10,000 records).
2. Switch consumers (Reasoning Engine) to last-known-good snapshot (up to 60s stale).
3. Diagnose Registry cause: disk space, connectivity, or corruption.
4. If disk/connectivity: restore connection; replay buffer from memory.
5. If corruption: restore from last clean checkpoint; run integrity verification; replay WAL.
6. Post-recovery: run conflict scan against full active set; rebuild search indices.

#### Procedure R-02 — Evidence Engine Disconnection

**Condition:** Evidence Engine feed becomes unavailable.

1. Hypothesis Matcher flags all active hypotheses: EVIDENCE_FEED_PAUSED.
2. Hypothesis Generator pauses generation (no new evidence to trigger).
3. Active hypotheses distributed with EVIDENCE_FEED_PAUSED flag.
4. Reasoning Engine receives the flag and applies evidence_staleness_penalty.
5. On reconnection: Evidence Engine replays last 15 minutes of evidence delta; Matcher processes replay.
6. Post-reconnection: re-score all hypotheses that received new evidence in replay.

#### Procedure R-03 — Confidence Engine Failure

**Condition:** Hypothesis Confidence Engine unavailable.

1. All new hypotheses receive CONFIDENCE_UNCALIBRATED flag.
2. HCS-C computed using simplified formula (mean ECS of supporting evidence, adjusted for volume).
3. Reasoning Engine receives CONFIDENCE_ENGINE_DEGRADED alert.
4. On recovery: Confidence Engine recomputes HCS-C for all hypotheses created during outage.
5. Version Manager creates new versions for all affected hypotheses.

#### Procedure R-04 — Conflict Manager Failure

**Condition:** Hypothesis Conflict Manager unavailable.

1. All new hypotheses receive CONFLICT_CHECK_SKIPPED flag.
2. Hypotheses distributed with the skip flag.
3. Reasoning Engine applies universal conflict_uncertainty_penalty (−0.05 to all hypothesis effective weights).
4. On recovery: Conflict Manager runs retroactive scan on all hypotheses created during outage.

#### Procedure R-05 — Audit Manager Failure

**Condition:** Hypothesis Audit Manager unavailable (write failure).

1. All hypothesis operations are BLOCKED (audit is non-bypassable per HC-H-005).
2. Emergency audit buffer activated (in-memory, max 1,000 records).
3. Hypothesis Engine enters DEGRADED mode: only read operations permitted.
4. Audit Manager failure alert escalated to CRITICAL immediately.
5. On recovery: Buffer flushed to audit log; read-write operations resumed.

---

### OR-04 — Performance Targets

| Metric | Target | Measurement Condition |
|---|---|---|
| Evidence-to-ACTIVE hypothesis latency (p50) | ≤ 200ms | Single evidence trigger, standard type |
| Evidence-to-ACTIVE hypothesis latency (p99) | ≤ 500ms | Single evidence trigger, standard type |
| Re-scoring latency on evidence update (p99) | ≤ 200ms | Matcher to scored hypothesis |
| Rank update latency (p99) | ≤ 30ms | Score change to rank update |
| Conflict detection latency (p99) | ≤ 50ms | New hypothesis to conflict status |
| Fusion cycle latency | ≤ 2,000ms | 3-constituent composite |
| Single hypothesis retrieval (p99) | ≤ 10ms | By hypothesis_id from Registry |
| Entity hypothesis set retrieval (p99) | ≤ 100ms | All ACTIVE for one entity |
| Historical PIT query (p99) | ≤ 300ms | 1,000 record result set |
| Full startup | ≤ 5 minutes | Cold start |
| Graceful shutdown | ≤ 3 minutes | |
| Evidence throughput | ≥ 1,000 evidence items/second | Evaluation rate |
| Hypothesis throughput (creation) | ≥ 100 hypotheses/minute | Peak generation rate |

---

### OR-05 — Capacity Reference

| Resource | Target | Alert threshold |
|---|---|---|
| Active hypothesis count | ≤ 50,000 | > 40,000 |
| ACTIVE hypothesis count (hot tier) | ≤ 10,000 | > 8,000 |
| Evidence items per active hypothesis (average) | ≤ 20 | > 30 |
| Dependency graph nodes | ≤ 500,000 | > 400,000 |
| Hypothesis creation rate (peak) | ≤ 500/minute | > 400/minute |
| Version chain length (average) | ≤ 10 versions | > 20 versions |
| Generation service queue depth | ≤ 5,000 | > 3,000 |
| Distribution channel queue depth | ≤ 10,000 | > 7,000 |
| Archive storage capacity (warm tier) | Sized for 12 months | > 80% full |

---

## SUPPLEMENT H — HYPOTHESIS ENGINE GLOSSARY

### H.1 Purpose

This glossary defines all terms specific to the Hypothesis Engine architecture. Terms are listed alphabetically.

---

**Adjudication**
The process by which the Conflict Manager determines which of two MAJOR-conflict hypotheses has stronger evidence support, resulting in a reduced effective weight for the weaker side. Adjudication is transparent — it is recorded in both hypothesis records and in the Audit Manager.

**Assertion**
The structured natural-language statement at the core of a hypothesis, expressing the condition being explained. Assertions must be present-tense, entity-specific, non-predictive, and testable. An assertion is the intellectual content of a hypothesis — all other fields exist to characterise and qualify the assertion.

**Candidate**
A hypothesis record that has been assembled by the Hypothesis Builder but has not yet passed validation. Candidates are in CANDIDATE lifecycle status and are not available to the Reasoning Engine.

**Coherence**
The degree to which a hypothesis aligns with the established knowledge corpus and the current market context. Coherence is quality dimension D06 of the HCS.

**Competing Hypothesis**
A hypothesis in COMPETING lifecycle status — one that is in MODERATE or MAJOR conflict with another active hypothesis. Competing hypotheses are distributed to the Reasoning Engine with their conflict_status visible.

**Composite Hypothesis**
A hypothesis constructed from two or more constituent hypotheses by the Hypothesis Fusion Manager. A composite provides a more complete explanation than any constituent alone.

**Confidence Score (HCS-C)**
The Hypothesis Confidence Score — the probabilistic assessment of whether a hypothesis correctly explains the observed conditions. Computed by the Hypothesis Confidence Engine from supporting evidence ECS values, independence scores, and historical calibration.

**Constitutional Rule**
One of the 84 inviolable architectural rules in Part IX that govern every hypothesis in the IIOS. Constitutional rules may not be circumvented by any component or operator.

**Context Record**
A structured record capturing the market conditions at the hypothesis_timestamp — regime, session, VIX, market state, events, macro calendar. Every hypothesis carries a ContextRecord.

**Coverage**
The proportion of the subject entity's active observations that the hypothesis explains. Coverage is quality dimension D04 of the HCS.

**Dependency Graph**
The complete directed graph of dependency relationships between hypotheses — which hypotheses depend on which others as parents or as composite constituents.

**Dissolution**
The process by which a composite hypothesis is disbanded because one or more constituent hypotheses have been retired and their contribution exceeded the dissolution threshold.

**Effective Weight**
The weight of a hypothesis in the Reasoning Engine's consideration, after applying any conflict-adjudication reduction. A hypothesis adjudicated as the weaker side of a MAJOR conflict has its effective weight reduced by 30–50%.

**Evidence Directionality**
The classification of each evidence item in a hypothesis's evidence_refs as either SUPPORTING (evidence consistent with the hypothesis assertion) or CONTRADICTING (evidence inconsistent with the assertion).

**Falsification Condition**
A specified evidence condition that, if observed, would strongly refute or invalidate the hypothesis. Constitutional rule HC-C-004 requires at least one falsification condition per hypothesis.

**Forming**
A lifecycle status for hypotheses being assembled by the Hypothesis Builder — evidence has been partially collected but construction is not complete.

**Fusion**
The process of combining multiple compatible, non-conflicting hypotheses into a single composite hypothesis that provides a richer explanation than any constituent alone.

**Generation Template**
A pattern specification in the Hypothesis Catalog that defines what combination and quantity of evidence items should trigger the generation of a hypothesis of a given type.

**Governance Tier**
The classification of a hypothesis type by its analytical sensitivity and regulatory importance: CRITICAL / HIGH / MEDIUM / LOW. Governance tier determines review frequency, retention period, access control, and escalation procedures.

**HCS**
The Hypothesis Composite Score — the overall quality score of a hypothesis, computed as the weighted sum of 10 quality dimensions. HCS ∈ [0.0, 1.0].

**HCS-C**
See Confidence Score.

**HCS Tier**
The qualitative classification of a hypothesis based on its HCS value: STRONG (≥0.80) / CREDIBLE (0.65–0.79) / PROVISIONAL (0.50–0.64) / WEAK (0.35–0.49) / SPECULATIVE (<0.35).

**Historical Hypothesis**
A hypothesis generated for a past point in time using PIT-compliant evidence. Historical hypotheses are marked HIS- and are used for backtesting and research.

**Identity Manager**
The component responsible for assigning globally unique hypothesis_ids to all new hypotheses.

**Lineage Record**
The complete traceable chain from hypothesis to its supporting evidence to the underlying observations to the raw information sources. Lineage must be maintained permanently.

**Novelty**
The degree to which a hypothesis provides explanatory content not already represented in the active hypothesis set. Novelty is quality dimension D05 of the HCS.

**Purity**
The architectural property of a hypothesis containing only explanation — no predictions, signals, decisions, or recommendations. Analogous to purity in the Observation and Evidence Engines.

**Regime**
The prevailing market regime at the hypothesis_timestamp — e.g., BULL_QUIET, BEAR_VOLATILE, CRISIS. Captured in the ContextRecord and used for regime-sensitive scoring.

**Stability**
The degree to which a hypothesis's HCS has remained consistent across recent versions. Stability is quality dimension D08 of the HCS.

**Strength**
The decisiveness with which the hypothesis assertion explains the observed conditions. Strength is quality dimension D01 of the HCS — the highest-weighted dimension.

**Testability Condition**
A specified evidence condition that, if observed, would confirm or strengthen the hypothesis. Constitutional rule HC-C-003 requires at least two testability conditions per hypothesis.

**Trajectory**
The trend of a hypothesis's HCS over its recent version history: STRENGTHENING, WEAKENING, or STABLE. Maintained by the Evolution Manager and available to the Reasoning Engine.

**Version Chain**
The linear sequence of all versions of a hypothesis, from the original (version 1) through all subsequent evolutions. No branching permitted.

**Zombie Hypothesis**
An anti-pattern (AP-07): a hypothesis whose HCS has dropped below 0.20 and whose supporting evidence has been exhausted, yet which has not been retired. Constitutional rule HC-F-004 prevents zombie hypotheses.

---
## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | HYPOTHESIS ENGINE ARCHITECTURE |
| Document code | IIOS-HYP-ENG-ARCH-001 |
| Version | 1.0 |
| Status | RATIFIED |
| Cognitive layer | Layer 3 of 5 |
| Preceding layer | Evidence Engine (IIOS-EVE-ENG-ARCH-001) |
| Succeeding layer | Reasoning Engine (IIOS-RSN-ENG-ARCH-001) |
| Part I — Hypothesis Philosophy | 20 conceptual distinctions; 8 hypothesis types explained; 5 design principles |
| Part II — Hypothesis Model | Full schema (37 fields); 8 lifecycle statuses; 20 hypothesis categories; 5 HCS tiers |
| Part III — Core Components | 20 components across 5 clusters; full specifications for each |
| Part IV — Hypothesis Lifecycle | 4 phases; 15 stages; state machine diagram; duration reference; PIT semantics |
| Part V — Hypothesis Services | 15 services (HS-01 through HS-15); failure handling; performance targets |
| Part VI — Processing Pipelines | 12 pipelines with ASCII flow diagrams |
| Part VII — Quality Framework | 10 HCS dimensions; formulas; tier definitions; regime modifiers; monitoring |
| Part VIII — Hypothesis Governance | 14 governance dimensions; tier matrix; ownership matrix; retention; security |
| Part IX — Hypothesis Constitution | 84 constitutional rules across 9 categories (HC-A through HC-I) |
| Part X — Readiness Checklist | 14 readiness sections; 7-use-case readiness matrix |
| Supplement A — Hypothesis Taxonomy | 50+ hypothesis type codes across all 20 categories |
| Supplement B — Scoring Reference | Dimension weight table; HCS scenarios; HCS-C calibration; independence formula |
| Supplement C — Conflict Matrix | Severity classification matrix; adjudication rules; timeline; HCS impact |
| Supplement D — Evolution Examples | 3 detailed evolution examples (momentum, fundamental, composite) |
| Supplement E — Dependency Examples | Parent-child hierarchy; composite dependency; cycle detection |
| Supplement F — Anti-Patterns | 10 anti-patterns (AP-01 through AP-10) |
| Supplement G — Operational Runbook | 24-step startup; 15-step shutdown; 5 recovery procedures; performance targets; capacity |
| Supplement H — Glossary | 35+ alphabetically ordered terms |
| Constitutional rules — HC-A (Identity) | 10 rules |
| Constitutional rules — HC-B (Evidence Support) | 10 rules |
| Constitutional rules — HC-C (Validity) | 12 rules |
| Constitutional rules — HC-D (Consistency) | 10 rules |
| Constitutional rules — HC-E (Conflict) | 10 rules |
| Constitutional rules — HC-F (Evolution) | 8 rules |
| Constitutional rules — HC-G (Governance) | 10 rules |
| Constitutional rules — HC-H (Auditability) | 8 rules |
| Constitutional rules — HC-I (Historical Preservation) | 6 rules |
| **Total constitutional rules** | **84 rules** |
| HCS quality dimensions | 10 |
| Readiness criteria sections | 14 |
| Processing pipelines | 12 |
| Core components | 20 |
| Services | 15 |
| Hypothesis categories | 20 |
| Hypothesis lifecycle statuses | 8 |
| Hypothesis schema fields | 37 |

---

### Master Compliance Checklist

| Section | Included | Verified |
|---|---|---|
| Part I — Hypothesis Philosophy | ✅ | ✅ |
| Part II — Hypothesis Model | ✅ | ✅ |
| Part III — Core Components | ✅ | ✅ |
| Part IV — Lifecycle | ✅ | ✅ |
| Part V — Services | ✅ | ✅ |
| Part VI — Processing Pipelines | ✅ | ✅ |
| Part VII — Quality Framework | ✅ | ✅ |
| Part VIII — Governance | ✅ | ✅ |
| Part IX — Hypothesis Constitution | ✅ | ✅ |
| Part X — Readiness Checklist | ✅ | ✅ |
| Supplement A — Hypothesis Taxonomy | ✅ | ✅ |
| Supplement B — Scoring Reference | ✅ | ✅ |
| Supplement C — Conflict Matrix | ✅ | ✅ |
| Supplement D — Evolution Examples | ✅ | ✅ |
| Supplement E — Dependency Examples | ✅ | ✅ |
| Supplement F — Anti-Patterns | ✅ | ✅ |
| Supplement G — Operational Runbook | ✅ | ✅ |
| Supplement H — Glossary | ✅ | ✅ |

---

### Governing Documents

| Document | Code | Relationship |
|---|---|---|
| IIOS Architecture Overview | IIOS-SYS-000 | System root |
| Evidence Engine Architecture | IIOS-EVE-ENG-ARCH-001 | Direct upstream: provides evidence |
| Observation Engine Architecture | IIOS-OE-ARCH-001 | Layer 1 upstream |
| Information Engine Architecture | IIOS-IE-ARCH-001 | Layer 0 upstream |
| Knowledge Engine Architecture | IIOS-KE-ARCH-001 | Downstream: consumes hypotheses |
| Entity Engine Architecture | IIOS-EE-ARCH-001 | Referenced: entity identity |
| Relationship Engine Architecture | IIOS-RE-ARCH-001 | Referenced: relationship hypothesis context |
| Event Engine Architecture | IIOS-EVT-ARCH-001 | Referenced: event hypothesis context |
| Database Persistence Architecture | IIOS-DB-ARCH-001 | Underlying: persistence for Hypothesis Registry |

---

### Architectural Impact Statement

The Hypothesis Engine occupies the explanatory centre of the IIOS cognitive stack. It is the first layer that moves beyond pure measurement and evaluation — the first layer that asks not "what happened?" but "why is this happening?"

Every reasoning chain that leads to a trading decision passes through the hypothesis layer. A Reasoning Engine that receives well-structured, well-scored, conflict-transparent, ranked hypotheses makes better decisions than one receiving a flat, unstructured cloud of evidence. The hypothesis layer is where the IIOS transforms analytical inputs into coherent explanatory frames that the Reasoning Engine can reason about.

The architectural invariants established in this document — evidence primacy, prediction prohibition, conflict transparency, structural testability, PIT semantics, constitutional identity rules, permanent auditability — are the minimum conditions for the Hypothesis Engine to function as a reliable analytical intermediary between the evidence layer and the reasoning layer.

A hypothesis engine that generates predictions is a prediction engine wearing a hypothesis mask. A hypothesis engine that silences conflicts is a confirmation engine. A hypothesis engine that allows evidence-free hypotheses is an opinion engine. This architecture is designed to prevent all three of these failure modes.

The Hypothesis Engine explains. Nothing more. Nothing less.

---

### Version History

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1 | Architecture inception | IIOS Architecture Board | Initial draft: model, components, lifecycle |
| 0.5 | First review | IIOS Architecture Board | Added quality framework, constitution |
| 0.9 | Pre-ratification | All domain owners | Added supplements, anti-patterns, glossary |
| 1.0 | Ratification | IIOS Architecture Board | Ratified; all 10 parts and supplements A–H complete |

---

*This document is RATIFIED. No component of the IIOS Hypothesis Engine may be designed, implemented, or operated in a manner inconsistent with the architecture defined herein. Proposed changes must be submitted as Architecture Change Requests to the IIOS Architecture Board.*

*End of HYPOTHESIS_ENGINE_ARCHITECTURE.md — IIOS-HYP-ENG-ARCH-001 v1.0 RATIFIED*

---## SUPPLEMENT I — GOVERNANCE DECISION RECORDS

### GDR-HYP-001 — Prediction Prohibition is Absolute

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Should the Hypothesis Engine be permitted to generate weak predictions (probabilistic forecasts with wide confidence intervals) provided they are clearly labelled?

**Decision:** No. The prediction prohibition is absolute. The Hypothesis Engine generates zero predictions under any circumstances.

**Rationale:**
1. The cognitive layer architecture is premised on strict functional separation. Once predictions are permitted at the hypothesis layer — even weakly, even labelled — the Reasoning Engine receives pre-concluded inputs. This destroys the analytical independence of the Reasoning Engine and makes the IIOS's overall reasoning circular.
2. The distinction between a "probabilistic explanation" and a "prediction" is architecturally unstable under operational pressure. Once the boundary becomes permissive, operational staff will inevitably push it further. Absolute prohibition prevents boundary erosion.
3. The Reasoning Engine and Prediction Engine (downstream layers) are purpose-built to generate probabilistic forward assessments. They are better at it than the Hypothesis Engine because they operate on the full ranked hypothesis set, not on individual evidence patterns. Attempting to add predictive capability to the Hypothesis Engine produces inferior predictions at the cost of architectural integrity.
4. Regulatory and audit requirements demand clear separation between "what the system observed" (observations), "what the evidence suggests" (evidence), "what the current explanation is" (hypothesis), and "what the system predicts will happen" (prediction). A Hypothesis Engine that predicts makes this regulatory separation impossible.

**Consequence accepted:** Users who want forward-looking assessments must use the Reasoning Engine or Prediction Engine outputs. Hypothesis Engine outputs answer "what is occurring," not "what will occur."

---

### GDR-HYP-002 — Multiple Simultaneous Hypotheses Are Mandatory

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** Should the Hypothesis Engine be designed to converge on a single "best" hypothesis for each entity at each point in time, to simplify the Reasoning Engine's inputs?

**Decision:** No. The Hypothesis Engine must maintain all valid hypotheses simultaneously. Single-hypothesis convergence is architecturally prohibited.

**Rationale:**
1. Single-hypothesis convergence is appropriate only when the evidence is sufficient to uniquely determine the correct explanation. This condition rarely holds in financial markets. Forcing convergence prematurely produces false certainty.
2. The Reasoning Engine is designed to reason over multiple competing hypotheses. It has the capacity to weigh a ranked set. Reducing its inputs to a single hypothesis removes the most analytically valuable information it could receive: the relative plausibility of alternative explanations.
3. Historical analysis of market failures consistently shows that correct predictions were available in the hypothesis set but suppressed in favour of the dominant view. Maintaining all valid hypotheses ensures the correct explanation is always present even when it is not ranked first.
4. Regulatory accountability requires that the decision-maker (Reasoning Engine and above) had access to all available explanations — not just the most convenient one.

**Consequence accepted:** The Reasoning Engine must be designed to handle a ranked set of potentially conflicting hypotheses. This is the correct and more sophisticated design.

---

### GDR-HYP-003 — Evidence is the Only Valid Hypothesis Input

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** May analyst opinion, narrative analysis, or macroeconomic commentary be used as direct hypothesis input without being processed through the Evidence Engine?

**Decision:** No. The only valid input to hypothesis construction is evidence from the Evidence Engine. No hypothesis may be constructed from unquantified inputs.

**Rationale:**
1. Unquantified inputs cannot be scored, weighted, or calibrated. A hypothesis based on analyst commentary has no principled HCS — its score would be arbitrary.
2. The IIOS's analytical reliability depends on the traceability of every output back to measured observations. If hypotheses can be built from untraceable narrative inputs, this traceability guarantee breaks.
3. Analyst commentary and macroeconomic narratives are not prohibited from influencing the IIOS — but they must enter through the correct channel. The Research Layer can submit human-assisted evidence to the Evidence Engine, which then validates and scores it. This evidence then becomes a valid hypothesis input.
4. The boundary prevents the introduction of cognitive biases directly into the hypothesis layer. Analyst anchoring, recency bias, and narrative fallacies are well-documented. The Evidence Engine's quality scoring acts as a filter.

**Consequence accepted:** Analyst insights must be converted to evidence through the Evidence Engine's Human Annotation workflow before they can influence hypotheses. This adds latency but preserves analytical integrity.

---

### GDR-HYP-004 — Constitutional Rules Are Non-Negotiable Under Operational Pressure

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** May constitutional rules be temporarily suspended during high-load periods, market crises, or emergency conditions to allow the system to continue operating?

**Decision:** Constitutional rules governing identity (HC-A), evidence support (HC-B), validity (HC-C), conflict transparency (HC-E), and auditability (HC-H) may never be suspended. Operational continuity rules in HC-F, HC-G, and HC-I may have emergency degradation modes, but the core integrity rules are inviolable.

**Rationale:**
1. Crisis conditions are precisely when the constitutional rules are most important. During a market crisis, the volume and urgency of hypothesis generation increases. The pressure to bypass validation, skip conflict checks, or allow evidence-free hypotheses is greatest precisely when doing so would be most dangerous.
2. A constitutional rule that can be suspended is not a constitutional rule — it is a preference. The value of the constitution comes from its unconditional nature.
3. Degradation modes are defined in OR-03 (Operational Runbook). These degradation modes preserve core integrity while allowing reduced functionality. They are not constitutional violations — they are pre-defined operating envelopes.

**Consequence accepted:** Under severe crisis conditions, the Hypothesis Engine may slow or partially halt rather than violate its constitution. This is the correct failure mode: a slower, correct system is preferable to a faster, corrupted one.

---

### GDR-HYP-005 — Hypothesis IDs Are Permanent and Non-Reusable

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** After a hypothesis is retired and archived, may its hypothesis_id be reused for efficiency?

**Decision:** Never. Retired hypothesis IDs are permanently reserved and may not be reused.

**Rationale:**
1. Audit trail integrity requires that any reference to a hypothesis_id in the historical record unambiguously identifies a single hypothesis. If IDs are reused, a historical audit query for hypothesis_id X might find two different hypotheses — the retired one and the new one — making historical analysis ambiguous.
2. Downstream references (Reasoning Engine decision records, Knowledge Engine facts derived from hypotheses) embed hypothesis_ids. These references must remain permanently valid and unambiguous.
3. The ID space is effectively infinite (YYYYMMDD + 8-digit sequence = 99,999,999 hypotheses per type per day). There is no practical pressure to reuse IDs.

**Consequence accepted:** Retired hypothesis IDs accumulate permanently in the ID registry. This is a trivial storage cost relative to the analytical safety it provides.

---

### GDR-HYP-006 — Hypothesis Evolution Must Not Retroactively Alter Historical Scores

**Decision date:** Founding architecture decision  
**Status:** Ratified

**Question:** When scoring calibration parameters are updated, should historical hypothesis scores be retroactively corrected to reflect the improved calibration?

**Decision:** No. Calibration updates affect only current and future hypothesis scoring. Historical scores are immutable.

**Rationale:**
1. Historical hypothesis scores are the analytical basis for past decisions. Retroactively correcting them is equivalent to rewriting history — it destroys the auditability of those decisions.
2. Backtesting research depends on historical hypothesis scores being what they actually were at the time of analysis, not what they would have been with hindsight-improved calibration. Retroactive correction introduces look-ahead bias into research.
3. The correct use of improved calibration is prospective: better scoring of future hypotheses. Historical research should be conducted using the scores that were actually in effect, with explicit documentation of any known calibration issues.

**Consequence accepted:** Historical hypothesis scores may be known to be miscalibrated relative to current parameters. This is analytically acceptable — the miscalibration is a documented property of the historical record, not an error to be corrected.

---

## SUPPLEMENT J — HYPOTHESIS ENGINE INTEGRATION CONTRACTS

### J.1 Contract with the Evidence Engine (Upstream)

**Direction:** Evidence Engine → Hypothesis Engine  
**Channel:** Event bus subscription (evidence-active topic)  
**Protocol:** Publish-subscribe; at-least-once delivery

**Required evidence fields for hypothesis generation:**

| Field | Type | Required |
|---|---|---|
| evidence_id | String | Yes |
| evidence_type | String | Yes |
| symbol | String | Yes |
| evidence_timestamp | UTC datetime | Yes |
| status | Enum (must be ACTIVE) | Yes |
| weight | Float [0,1] | Yes |
| effective_weight | Float [0,1] | Yes |
| ecs | Float [0,1] | Yes |
| eqs | Float [0,1] | Yes |
| context | JSON | Yes |
| independence_score | Float [0,1] | Yes |
| conflict_status | Enum | Yes |

**SLA:**  
- Evidence Engine delivers within 500ms of ACTIVE transition.  
- Hypothesis Engine acknowledges within 2,000ms.  
- Unacknowledged evidence retried 3 times; after that: dead-lettered.

---

### J.2 Contract with the Reasoning Engine (Downstream)

**Direction:** Hypothesis Engine → Reasoning Engine  
**Channel:** Event bus (hypothesis-active topic) + on-demand Retrieval Service  
**Protocol:** Publish-subscribe + REST

**Distribution payload fields:**

| Field | Type | Required |
|---|---|---|
| hypothesis_id | String | Yes |
| hypothesis_type | Enum | Yes |
| subject_entity_ids | List | Yes |
| assertion | String | Yes |
| hcs | Float [0,1] | Yes |
| hcs_confidence | Float [0,1] | Yes |
| hcs_tier | Enum | Yes |
| rank_global | Integer | Yes |
| rank_in_type | Integer | Yes |
| conflict_status | Enum | Yes |
| competing_hypothesis_ids | List | No |
| evolution_trajectory | Enum (STRENGTHENING/WEAKENING/STABLE) | Yes |
| context_record | JSON | Yes |
| evidence_summary | JSON (count, min_ecs, max_ecs, net_weight) | Yes |
| lifecycle_status | Enum | Yes |
| hypothesis_timestamp | UTC datetime | Yes |

**SLA:**
- Hypothesis Engine distributes ACTIVE transition within 200ms.
- Reasoning Engine acknowledges within 1,000ms.
- Retrieval Service: single hypothesis ≤ 10ms; entity set ≤ 100ms; PIT query ≤ 300ms.

---

### J.3 Breaking Change Policy

Breaking changes to integration contracts require Architecture Board approval with minimum 30-day migration notice to all consumers.

---

## SUPPLEMENT K — HYPOTHESIS ENGINE PERFORMANCE BENCHMARKS

### K.1 Design Performance Targets

| Metric | Target | Condition |
|---|---|---|
| Evidence-to-ACTIVE latency (p50) | ≤ 150ms | Single trigger, standard type |
| Evidence-to-ACTIVE latency (p99) | ≤ 500ms | Single trigger, standard type |
| Composite hypothesis assembly (p99) | ≤ 2,000ms | 3 constituents |
| Re-scoring on evidence update (p99) | ≤ 200ms | Matcher to scored |
| Rank update latency (p99) | ≤ 30ms | Score change to rank |
| Conflict detection (p99) | ≤ 50ms | New hypothesis |
| Single hypothesis retrieval | ≤ 10ms | By ID, hot tier |
| Entity active set retrieval | ≤ 100ms | All ACTIVE, 1 entity |
| PIT historical query (1,000 results) | ≤ 300ms | PIT-compliant |
| Full startup | ≤ 5 minutes | Cold start, 24 steps |
| Graceful shutdown | ≤ 3 minutes | |

### K.2 Availability and Resilience

| Target | Requirement |
|---|---|
| Uptime SLA | 99.9% |
| RTO | ≤ 15 minutes |
| RPO | ≤ 60 seconds |
| Warm restart | ≤ 5 minutes |
| Max generation queue depth | 5,000 candidates |
| Backpressure activation | ≤ 500ms |

### K.3 Quality SLA

| Quality Metric | Target |
|---|---|
| Evidence-free hypotheses in production | 0 |
| Predictions in hypothesis assertions | 0 |
| Zombie hypotheses (HCS<0.20, no evidence, still ACTIVE) | 0 |
| Unresolved MAJOR conflicts > 2 business days | 0 |
| Missing audit records | 0 |
| Version chain breaks | 0 |

---

*End of HYPOTHESIS_ENGINE_ARCHITECTURE.md — IIOS-HYP-ENG-ARCH-001 v1.0 RATIFIED*

---## SUPPLEMENT L — HYPOTHESIS ENGINE FAILURE MODE ANALYSIS

### L.1 Critical Failure Modes

| ID | Failure Mode | Detection | Immediate Response | Recovery |
|---|---|---|---|---|
| FM-01 | Hypothesis Registry unavailable | Health check; write errors | Activate emergency buffer (10,000 records); switch consumers to snapshot | Restore Registry; replay buffer; verify integrity |
| FM-02 | Confidence Engine crash | Component health timeout | Compute HCS-C with simplified formula; flag CONFIDENCE_UNCALIBRATED | Restart; recompute HCS-C for all hypotheses created during outage |
| FM-03 | Conflict Manager crash | Component health timeout | Apply CONFLICT_CHECK_SKIPPED flag; distribute with universal conflict penalty | Restart; run retroactive conflict scan on last 60 minutes |
| FM-04 | Validator crash | Component health timeout | Halt hypothesis creation; queue candidates | Restart; reprocess queued candidates from head |
| FM-05 | Evidence Engine disconnect | Feed heartbeat timeout | Flag all active hypotheses EVIDENCE_FEED_PAUSED; halt generation | Reconnect; replay last 15-minute evidence delta |
| FM-06 | Ranking Engine crash | Component health timeout | Distribute hypotheses with RANKING_STALE flag | Restart; rebuild rankings from current scores |
| FM-07 | Audit Manager failure | Write error | BLOCK all hypothesis operations; enter read-only mode | Restore Audit Manager; flush emergency buffer; resume operations |
| FM-08 | Dependency cycle detected | Dependency Manager check | Quarantine all hypotheses in cycle; alert Governance Manager | Manual cycle resolution; re-activate validated hypotheses |
| FM-09 | Version chain corruption | Integrity check failure | Quarantine affected hypothesis chain | Restore from last clean checkpoint; rebuild chain from audit log |
| FM-10 | Generation queue overflow | Queue depth > 5,000 | Apply backpressure to Evidence Engine subscription | Drain queue; scale Generation Service; investigate root cause |

---

### L.2 Cascade Risk Assessment

| Outage Duration | Downstream Impact on Reasoning Engine |
|---|---|
| 0–2 minutes | Reasoning Engine uses cached active hypotheses; no decision impact |
| 2–10 minutes | Hypotheses become stale; Reasoning Engine applies staleness penalty to all hypotheses |
| 10–30 minutes | Active hypothesis set no longer reflects current evidence; Reasoning Engine confidence reduces significantly |
| 30–60 minutes | RTO exceeded; trading decisions should be paused; emergency escalation |
| > 60 minutes | Full system audit required before resuming hypothesis production |

---

### L.3 Non-Recoverable Failure Conditions

The following require human intervention before the Hypothesis Engine may resume:

1. **Hypothesis Registry corruption** — any hypothesis with missing version chain or missing evidence refs. Full audit required.
2. **Prediction detected in production assertion** — any hypothesis assertion containing a prediction that reached the Reasoning Engine. Security and architecture review required.
3. **Audit trail gap** — any period where hypothesis operations occurred without audit records. Cannot self-certify integrity; external review required.
4. **Constitutional rule persistent violation** — any HC-A, HC-B, or HC-C rule violated more than once in 24 hours. Architecture Board review required before restart.

---

### L.4 Degraded Mode Capabilities

When the Hypothesis Engine enters DEGRADED mode:

| Capability | Full Mode | Degraded Mode |
|---|---|---|
| New hypothesis creation | Available | Available with reduced validation speed |
| Scoring | Full 10-dimension HCS | Simplified 6-dimension HCS (D05 Novelty and D08 Stability deferred) |
| Conflict detection | Real-time | Deferred (batch scan every 5 minutes) |
| Fusion | Available | Suspended |
| Distribution to Reasoning Engine | Real-time | Batched every 30 seconds |
| Historical PIT queries | Available | Suspended (archive queries blocked) |
| Governance actions | Available | Deferred (non-urgent) |

---

*This document is RATIFIED. No component of the IIOS Hypothesis Engine may be designed, implemented, or operated in a manner inconsistent with the architecture defined herein.*

*End of HYPOTHESIS_ENGINE_ARCHITECTURE.md — IIOS-HYP-ENG-ARCH-001 v1.0 RATIFIED*

---## SUPPLEMENT M — HYPOTHESIS ENGINE CALIBRATION METHODOLOGY

### M.1 Overview

Hypothesis calibration verifies that the HCS-C values assigned to hypotheses accurately reflect historical accuracy — that hypotheses with HCS-C = 0.80 are correct approximately 80% of the time.

---

### M.2 Calibration Data Requirements

| Requirement | Description |
|---|---|
| Outcome record | Whether the hypothesis correctly explained the condition it was asserting |
| Outcome evaluation horizon | Defined per hypothesis type (1 day for technical; 30 days for fundamental; 90 days for macro) |
| Minimum sample | At least 30 completed outcome records per calibration bin per type |
| Look-ahead compliance | All outcome records must postdate their hypothesis_timestamp by the evaluation horizon |
| Maximum staleness | No calibration uses outcome records older than 18 months |

---

### M.3 Calibration Procedure

For each hypothesis type T:

1. Retrieve all retired/archived hypotheses of type T with outcomes recorded.
2. Group by HCS-C bin: [0.0–0.2), [0.2–0.4), [0.4–0.6), [0.6–0.8), [0.8–1.0].
3. For each bin: observed_accuracy = count(correct outcomes) / total outcomes.
4. Calibration error CE = |midpoint − observed_accuracy|.
5. CE > 0.10 for any bin: flag type for RECALIBRATION.
6. CE > 0.20 for any bin: suspend type pending governance approval.

---

### M.4 Outcome Definition by Hypothesis Category

| Category | Outcome definition | Evaluation horizon |
|---|---|---|
| TEC (technical) | Price behaviour consistent with assertion within horizon | 1–5 trading days |
| FND (fundamental) | Earnings/valuation evidence confirms assertion | 1–3 months |
| MAC (macro) | Macro data confirms assertion | 1–3 months |
| MKT (market) | Index behaviour confirms assertion | 3–10 trading days |
| SEC (sector) | Sector relative performance confirms assertion | 2–4 weeks |
| RSK (risk) | Risk event materialisation or non-materialisation | 1–14 days |
| VOL (volatility) | Volatility regime confirms assertion | 5–15 trading days |
| XAS / XMK (cross) | Cross-asset behaviour confirms assertion | 5–20 trading days |
| SNT (sentiment) | Sentiment reversal or continuation confirms assertion | 3–7 trading days |
| EVT (event) | Post-event price/fundamental outcome confirms assertion | Event + 5–30 days |

---

### M.5 Calibration Governance

| Trigger | Response | Governance Level |
|---|---|---|
| CE > 0.10 for any bin | Recalibration proposed; requires approval | MEDIUM |
| CE > 0.20 for any bin | Type suspended; mandatory recalibration | HIGH |
| Insufficient sample (< 30) | CONFIDENCE_UNCALIBRATED flag; no calibration applied | LOW (flag only) |
| Calibration fraud detected (CE < −0.05 or > 1.05) | Security review; architecture audit | CRITICAL |

---

### M.6 Weight Recalibration

Beyond confidence calibration, dimension weights (D01–D10) are reviewed semi-annually:
- Rank correlation between each dimension score and hypothesis outcome accuracy computed.
- If any dimension rank correlation < 0.30 over 12 months, the weight of that dimension is reduced.
- Proposed weight changes submitted to Architecture Board for approval.
- No weight change may reduce any single dimension below 0.01 or raise it above 0.30 without explicit Architecture Board ratification.

---

### M.7 Calibration Audit Trail

Every calibration event must record:
- calibration_id (UUID)
- calibration_timestamp (UTC)
- hypothesis_type
- n_hypotheses_sampled
- ce_by_bin (JSON)
- current_accuracy_by_bin (JSON)
- recalibration_applied (boolean)
- governance_approval_id (if applicable)
- evolution_manager_version (software version)

Calibration audit records are permanent and may not be modified or deleted.

---

*End of HYPOTHESIS_ENGINE_ARCHITECTURE.md — all supplements complete.*

---