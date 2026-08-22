# REASONING ENGINE ARCHITECTURE

**Document Code:** IIOS-RSN-ENG-ARCH-001  
**Version:** 1.0  
**Status:** RATIFIED  
**Classification:** INTERNAL — ARCHITECTURE  
**Layer:** Cognitive Layer 4 of 5  
**Predecessor Layer:** Hypothesis Engine (IIOS-HYP-ENG-ARCH-001)  
**Successor Layer:** Decision Engine (IIOS-DEC-ENG-ARCH-001)

---

## Document Purpose and Scope

This document defines the complete engineering architecture of the Reasoning Engine — the fourth cognitive layer of the Investment Intelligence Operating System (IIOS). The Reasoning Engine receives ranked, scored, conflict-flagged hypotheses from the Hypothesis Engine and transforms them into structured, explainable reasoning chains that the Decision Engine can act upon with confidence.

**Scope:**
- All components of the Reasoning Engine
- The complete reasoning lifecycle from hypothesis intake to archived reasoning
- All processing pipelines, services, quality frameworks, and governance structures
- Constitutional rules governing reasoning integrity
- Operational procedures

**Out of scope:**
- Implementation code of any form
- Database schema definitions
- API contracts
- Trade signals, trade recommendations, trade execution, or portfolio decisions

**Fundamental Constraint:** The Reasoning Engine constructs logical reasoning chains from hypotheses and produces explainable conclusions. It does not predict future states. It does not make or recommend trading decisions. It does not execute. The Decision Engine is the only cognitive layer permitted to make portfolio decisions, and it does so from the Reasoning Engine output as input — not as instructions.

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
| Evidence Engine Architecture | IIOS-EVE-ENG-ARCH-001 | Layer 2 upstream |
| Hypothesis Engine Architecture | IIOS-HYP-ENG-ARCH-001 | Layer 3 upstream (direct) |
| Knowledge Engine Architecture | IIOS-KE-ARCH-001 | Parallel consumer |

---

## IIOS Cognitive Layer Stack

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 — DECISION ENGINE     decides, acts, portfolio         │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4 — REASONING ENGINE    infers, reasons, explains ◄ HERE │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3 — HYPOTHESIS ENGINE   explains, ranks, evolves         │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2 — EVIDENCE ENGINE     evaluates, weighs, scores        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1 — OBSERVATION ENGINE  perceives, records, timestamps   │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 0 — INFORMATION ENGINE  validates, types, manages data   │
└─────────────────────────────────────────────────────────────────┘
```

**The Reasoning Engine receives explanations and returns structured conclusions. It is the cognitive centre — the first layer that performs inference, integrates multiple perspectives, and produces explainable analytical positions.**

---

## Reasoning Engine Information Flow

```
HYPOTHESIS ENGINE
    │
    │  Ranked, scored, conflict-flagged hypotheses
    │  (ACTIVE + COMPETING; full HCS, HCS-C, trajectory)
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  REASONING ENGINE                                               │
│                                                                 │
│  Hypothesis Intake → Context Building → Evidence Mapping        │
│       ↓                                                         │
│  Reasoning Construction → Inference → Validation               │
│       ↓                                                         │
│  Conflict Detection → Debate → Consensus                       │
│       ↓                                                         │
│  Confidence Assignment → Explanation Generation                │
│       ↓                                                         │
│  Audit → Storage → Distribution                                │
└─────────────────────────────────────────────────────────────────┘
    │
    │  Structured reasoning chains with conclusions,
    │  confidence scores, debate records, explanations
    ▼
DECISION ENGINE

    │  (parallel)
    ▼
KNOWLEDGE ENGINE
```

---

## Table of Contents

1. PART I — REASONING PHILOSOPHY
2. PART II — REASONING TAXONOMY
3. PART III — CORE COMPONENTS
4. PART IV — REASONING LIFECYCLE
5. PART V — REASONING SERVICES
6. PART VI — REASONING PROCESSING PIPELINES
7. PART VII — REASONING QUALITY FRAMEWORK
8. PART VIII — REASONING GOVERNANCE
9. PART IX — REASONING CONSTITUTION
10. PART X — REASONING READINESS CHECKLIST
11. SUPPLEMENT A — REASONING TAXONOMY REFERENCE
12. SUPPLEMENT B — LOGIC REFERENCE
13. SUPPLEMENT C — INFERENCE PATTERNS
14. SUPPLEMENT D — DEBATE EXAMPLES
15. SUPPLEMENT E — REASONING GRAPHS
16. SUPPLEMENT F — ANTI-PATTERNS
17. SUPPLEMENT G — OPERATIONAL RUNBOOK
18. SUPPLEMENT H — GLOSSARY
19. DOCUMENT FOOTER

---

## PART I — REASONING PHILOSOPHY

### 1.1 What is Reasoning?

Reasoning is the cognitive process of drawing conclusions from premises through structured, principled, and auditable chains of inference. It is what the IIOS does when it moves from "what is occurring" (the domain of hypotheses) to "what does this mean" (the domain of conclusions) and ultimately toward "what should be done" (the domain of decisions).

The Reasoning Engine occupies the most complex analytical position in the IIOS cognitive stack. It is the first layer that produces conclusions — statements that go beyond description and explanation to make genuine analytical assertions about the state of the investment universe and their implications. It is the last layer before action, and it must be the most rigorous.

In human cognition, reasoning is often fast, intuitive, and opaque — prone to biases, anchoring, narrative fallacies, and motivated cognition. The IIOS Reasoning Engine is architecturally designed to make these failures impossible: every inference must be traceable to the hypotheses that support it, every conclusion must be explainable in structured terms, and every conflict must be explicitly resolved rather than silently suppressed.

The Reasoning Engine answers four questions that no upstream layer can answer:

1. **What is the most coherent interpretation of the current hypothesis set?** — Not just what is explained, but what those explanations imply when considered together.
2. **Where do multiple valid hypotheses conflict, and how should those conflicts be resolved into actionable conclusions?** — The Hypothesis Engine flags conflicts; the Reasoning Engine resolves them.
3. **What is the degree of conviction with which the IIOS holds a given analytical position?** — Not just confidence in individual hypotheses, but integrated conviction across a reasoning chain.
4. **Why does the IIOS hold the positions it holds?** — Explainability is not a feature — it is a constitutional requirement.

---

### 1.2 Why Reasoning Exists

Without a Reasoning Engine, the Decision Engine would receive thousands of hypotheses and be required to perform all inference, conflict resolution, and integration itself. This would produce several failure modes:

**1. Incoherent decisions from conflicting inputs:** Multiple competing hypotheses on the same subject, unresolved, would produce contradictory decision signals.

**2. Inability to integrate multi-dimensional evidence:** A decision about TATASTEEL involves technical hypotheses, fundamental hypotheses, sector hypotheses, macro hypotheses, and risk hypotheses simultaneously. The Decision Engine cannot integrate 20 separate hypotheses into a coherent position — the Reasoning Engine must perform that integration.

**3. Loss of explainability:** Without a reasoning layer, the IIOS cannot explain why it holds a given analytical position. It can only say "this hypothesis scored 0.83" — not "this hypothesis, combined with this macro context and this risk consideration, implies this analytical position."

**4. No debate:** Markets are inherently multi-perspective. The Reasoning Engine is designed to conduct internal analytical debate — to consider the bull and bear cases explicitly, weigh them, and produce a position that reflects the full complexity of the evidence.

**5. No meta-cognition:** The Reasoning Engine can reason about its own reasoning — it can detect when its conclusions are poorly grounded, when its confidence is inflated relative to the evidence, and when it is reasoning from analogy rather than from direct evidence.

---

### 1.3 Conceptual Distinctions — 23 Terms

The following 23 terms define the conceptual boundaries of the Reasoning Engine. Architectural clarity requires that each be used with precision.

---

#### 1.3.1 Observation

An **Observation** is a structured, immutable, timestamped record of a perceived state in the investment universe (Layer 1). The Reasoning Engine does not consume observations directly — it operates on hypotheses, which are grounded in evidence, which is grounded in observations. Observations are the ultimate epistemic foundation.

---

#### 1.3.2 Evidence

**Evidence** is an evaluated, weighted, confidence-scored analytical input derived from observations by the Evidence Engine (Layer 2). Evidence is the empirical substrate of the IIOS — what the system has measured and validated. The Reasoning Engine receives evidence indirectly, through the hypotheses it supports or contradicts.

---

#### 1.3.3 Hypothesis

A **Hypothesis** is a structured, testable, evidence-supported explanation of an observed condition, produced by the Hypothesis Engine (Layer 3). The Reasoning Engine takes hypotheses as its primary input. A hypothesis is the explanatory unit; reasoning transforms explanations into conclusions.

---

#### 1.3.4 Inference

An **Inference** is a conclusion derived from hypotheses through a structured logical, statistical, or causal reasoning step. Inference is the primary act of the Reasoning Engine. An inference answers: "given these explanations of current conditions, what analytical conclusion follows?" An inference is not a prediction — it is a structured derivation from available explanations.

---

#### 1.3.5 Logic

**Logic** is the systematic study and application of valid inference rules. In the IIOS, logic provides the formal backbone of reasoning chains: the structure of deductive arguments, the conditions for valid inductive generalisation, and the criteria for abductive inference to the best explanation. The Logic Engine component enforces that all inferences conform to defined logical rules.

---

#### 1.3.6 Reasoning

**Reasoning** is the full process of constructing, validating, debating, and integrating inferences into a coherent analytical position. A single inference is a step; reasoning is the sequence of steps, their integration, the debate about their implications, the resolution of conflicts, and the production of an explainable conclusion. Reasoning is what the Reasoning Engine does.

---

#### 1.3.7 Explanation

An **Explanation** is an account of why a condition exists. Explanations are produced by the Hypothesis Engine (Layer 3). The Reasoning Engine takes explanations as input and produces conclusions as output. The difference: an explanation says "this is consistent with these evidence patterns"; a conclusion says "therefore, the analytical position is X with conviction C."

---

#### 1.3.8 Understanding

**Understanding** is the integration of multiple explanations and inferences into a coherent, stable model of a domain. Understanding is the output of the Knowledge Engine, which operates in parallel with the Reasoning Engine. The Reasoning Engine produces conclusions; the Knowledge Engine builds understanding from those conclusions over time.

---

#### 1.3.9 Knowledge

**Knowledge** is a justified, reliably established conclusion held by the IIOS as part of its persistent analytical framework. Knowledge is maintained by the Knowledge Engine. The Reasoning Engine produces the reasoning chains from which the Knowledge Engine derives knowledge — but the Reasoning Engine does not itself hold knowledge.

---

#### 1.3.10 Prediction

A **Prediction** is a probabilistic assertion about a future state of the investment universe. The Reasoning Engine is architecturally prohibited from making predictions. Predictions are the output of downstream prediction sub-engines that operate after the Reasoning Engine has produced its conclusions.

---

#### 1.3.11 Decision

A **Decision** is a chosen course of action in the investment universe. The Reasoning Engine does not make decisions. Decisions are the output of the Decision Engine (Layer 5), which acts on the Reasoning Engine's conclusions.

---

#### 1.3.12 Belief

A **Belief** is a subjective probability held by an agent about the truth of a proposition. In the IIOS, beliefs are formalised as conviction scores — structured, evidence-grounded probability assignments to analytical positions. The Reasoning Engine produces conviction scores; it does not maintain subjective beliefs.

---

#### 1.3.13 Confidence

**Confidence** is the epistemological certainty with which an analytical position is held, given the quality, volume, and consistency of the reasoning chain supporting it. The Reasoning Engine computes Reasoning Confidence Score (RCS) for every conclusion. Confidence is not certainty — high confidence means well-grounded; it does not mean correct.

---

#### 1.3.14 Conviction

**Conviction** is the integrated degree to which the IIOS commits to a given analytical position, computed from the confidence, consistency, and stability of the full reasoning chain. Conviction is a Layer 4/5 concept — the Reasoning Engine computes conviction; the Decision Engine uses it to weight portfolio actions.

---

#### 1.3.15 Probability

**Probability** is a numerical measure in [0.0, 1.0] of the likelihood of a proposition being true. The Reasoning Engine computes probabilities in two forms: (1) the RCS — the probability that the reasoning chain correctly characterises the current analytical state; (2) Bayesian posterior probabilities updated as new hypotheses arrive.

---

#### 1.3.16 Uncertainty

**Uncertainty** is the degree to which the available evidence and hypotheses fail to uniquely determine a conclusion. High uncertainty is not a failure — it is analytically accurate and must be represented explicitly in the reasoning output. The Decision Engine receives uncertainty alongside conviction and weights its decisions accordingly.

---

#### 1.3.17 Deduction

**Deduction** is inference that guarantees its conclusion if the premises are true. A deductive argument is valid if its conclusion follows necessarily from its premises. In the IIOS, pure deduction applies in limited domains — e.g., "if earnings are negative AND the company has negative cash flow, then at minimum one financial health indicator is negative." Most IIOS reasoning is probabilistic rather than deductive.

---

#### 1.3.18 Induction

**Induction** is inference that draws general conclusions from specific observations. Inductive reasoning generalises from patterns in historical evidence to analytical conclusions about current conditions. "This pattern has preceded declining breadth in 85% of historical cases" is an inductive basis for a reasoning chain. Induction is ampliative — it goes beyond the evidence — and must be flagged as such.

---

#### 1.3.19 Abduction

**Abduction** is inference to the best explanation — selecting the hypothesis that best explains a set of observations. When the Hypothesis Engine has generated multiple explanations and the Reasoning Engine must select which is most coherent, abductive logic is employed: which explanation, if true, would make the evidence most expected?

---

#### 1.3.20 Causal Reasoning

**Causal Reasoning** identifies cause-and-effect relationships between analytical factors — not just correlation, but directional causal attribution. "FII outflows cause INR depreciation, which causes higher import costs for energy-intensive sectors." Causal reasoning enables the Reasoning Engine to trace second and third-order implications of market events.

---

#### 1.3.21 Counterfactual Reasoning

**Counterfactual Reasoning** asks "what would be true if X were different?" It is the reasoning mode that produces conditional conclusions: "if the rate hold hypothesis were incorrect, what would the evidence imply instead?" Counterfactual reasoning is essential for stress-testing conclusions and for contrarian analytical positions.

---

#### 1.3.22 Bayesian Reasoning

**Bayesian Reasoning** is the formal probabilistic framework for updating beliefs in light of new evidence. The Reasoning Engine uses Bayesian updating: prior conviction + new hypothesis evidence = posterior conviction. This ensures that conviction scores reflect cumulative evidence rather than only the most recent.

$$P(H|E) = \frac{P(E|H) \cdot P(H)}{P(E)}$$

Where H is the analytical position, E is the new evidence-weighted hypothesis, P(H) is the prior conviction, and P(H|E) is the updated conviction.

---

#### 1.3.23 Meta-Reasoning

**Meta-Reasoning** is reasoning about the quality, limitations, and reliability of the reasoning process itself. The Meta Reasoning Manager asks: "Is this reasoning chain well-grounded? Are we over-confident given the evidence? Are we reasoning from pattern recognition rather than from causal analysis? What are the failure modes of our current conclusions?" Meta-reasoning is the Reasoning Engine's self-audit mechanism.

---

### 1.4 Reasoning Engine Design Principles

1. **Explainability by constitution:** Every conclusion must be fully traceable to the reasoning chain, hypotheses, evidence, and observations that support it. An unexplained conclusion may not be distributed.
2. **Conviction from evidence:** Conviction scores must be computed from evidence quality and reasoning chain quality, not from assumption or preference.
3. **Explicit uncertainty:** High-uncertainty conclusions are not suppressed — they are flagged and quantified. The Decision Engine needs to know when the IIOS is uncertain.
4. **Mandatory debate:** For every conclusion of CRITICAL or HIGH analytical significance, the Counter Argument Engine must present the strongest case against it.
5. **Temporal precision:** Conclusions explain current conditions. They do not predict future states.
6. **Layer discipline:** The Reasoning Engine never imports inputs from Layer 5 (Decision) and never produces outputs formatted for execution.
7. **Multi-perspective completeness:** The Reasoning Engine must evaluate hypotheses from multiple analytical perspectives — technical, fundamental, macro, risk — before producing an integrated conclusion.
8. **Meta-cognition:** The Reasoning Engine must assess the quality of its own conclusions and flag those with known limitations.

---
## PART II — REASONING TAXONOMY

### 2.1 Reasoning Schema

Every reasoning chain produced by the Reasoning Engine conforms to this canonical schema.

**Canonical ID format:** `RSN-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`

Example: `RSN-DED-TECH-20260703-00000001`

| Field | Type | Required | Description |
|---|---|---|---|
| reasoning_id | String | Yes | Canonical globally unique reasoning chain ID |
| reasoning_type | Enum | Yes | From taxonomy in Part II |
| category_code | String | Yes | Category from taxonomy |
| version_number | Integer | Yes | Starts at 1 |
| lifecycle_status | Enum | Yes | FORMING/ACTIVE/CONTESTED/SUPERSEDED/RETIRED/ARCHIVED |
| subject_entity_ids | List[String] | Yes | Canonical entity IDs being reasoned about |
| subject_domain | Enum | Yes | Market domain |
| premise_hypothesis_ids | List[String] | Yes | Input hypotheses (minimum 1) |
| inference_steps | List[InferenceStep] | Yes | Ordered chain of logical steps |
| conclusion | String | Yes | Structured natural language conclusion |
| conclusion_structured | JSON | Yes | Machine-readable conclusion |
| rcs | Float [0,1] | Yes | Reasoning Confidence Score |
| rcs_tier | Enum | Yes | DEFINITIVE/STRONG/MODERATE/TENTATIVE/EXPLORATORY |
| conviction_score | Float [0,1] | Yes | Bayesian-integrated conviction |
| uncertainty_score | Float [0,1] | Yes | 1 − conviction_score (explicit uncertainty) |
| reasoning_timestamp | UTC datetime | Yes | When reasoning chain was constructed |
| creation_timestamp | UTC datetime | Yes | When record was first stored |
| context_record | ContextRecord | Yes | Market context at reasoning_timestamp |
| debate_record_id | UUID | No | If debate was conducted |
| consensus_record_id | UUID | No | If consensus was sought |
| counter_argument_ids | List[UUID] | No | IDs of counter-arguments considered |
| conflict_status | Enum | Yes | NONE/MINOR/MODERATE/MAJOR |
| explanation_record_id | UUID | Yes | Pointer to generated explanation |
| lineage_record_id | UUID | Yes | Pointer to hypothesis and evidence lineage |
| governance_tier | Enum | Yes | CRITICAL/HIGH/MEDIUM/LOW |
| domain_owner | String | Yes | Responsible domain team |
| audit_trail_id | UUID | Yes | Pointer to audit records |
| is_ai_generated | Boolean | Yes | True if chain constructed by AI model |
| is_contested | Boolean | Yes | True if counter-argument engine produced significant opposition |
| meta_assessment | JSON | No | Meta-reasoning quality assessment |

---

### 2.2 Reasoning Lifecycle Statuses

| Status | Meaning |
|---|---|
| FORMING | Reasoning chain being constructed; hypotheses being integrated |
| ACTIVE | Valid, concluded, confidence-scored; available to Decision Engine |
| CONTESTED | Active but opposed by significant counter-argument |
| SUPERSEDED | Replaced by an updated version |
| RETIRED | Withdrawn because underlying hypotheses or evidence no longer support it |
| ARCHIVED | Preserved for historical analysis; not active |

---

### 2.3 Reasoning Type Taxonomy

#### 2.3.1 Deductive Reasoning (CAT: DED)

**Definition:** Reasoning in which the conclusion necessarily follows from the premises, given valid logical structure. If the premises are true and the inference rule is valid, the conclusion cannot be false.

**Role in IIOS:** Applied when the relationship between hypotheses is deterministic or near-deterministic. Used primarily for rule-based reasoning in the risk and governance domains.

**Examples in IIOS:**
- Premise 1: Portfolio drawdown exceeds 2% intraday (RSK hypothesis active).
- Premise 2: All risk protocols require halt when drawdown exceeds 2%.
- Conclusion (deductive): Risk halt protocol must be considered.

**Canonical type codes:** DED-RISK, DED-RULE, DED-CONSTRAINT

**Limitations:** Pure deduction in financial markets is rare — most domains involve probabilistic rather than deterministic relationships. Deductive reasoning is most powerful when applied to governance constraints, risk thresholds, and structural market rules.

---

#### 2.3.2 Inductive Reasoning (CAT: IND)

**Definition:** Reasoning that draws general conclusions from specific cases. The premises support the conclusion without guaranteeing it. Inductive reasoning generalises from observed patterns to broader analytical positions.

**Role in IIOS:** Applied when historical evidence patterns are used to justify current analytical conclusions. "This breadth deterioration pattern has preceded corrections in 79% of historical cases" is an inductive premise.

**Examples:**
- Historical evidence: Out of 14 occurrences of VIX rising above 20 while NIFTY was within 3% of its 52-week high, the market declined > 5% within 30 trading days in 11 of them (79%).
- Inductive conclusion: Current conditions — VIX at 21.5, NIFTY within 2% of 52-week high — are inductively consistent with elevated correction risk.

**Canonical type codes:** IND-HISTORICAL, IND-PATTERN, IND-STATISTICAL, IND-FREQUENCY

**Limitations:** Inductive conclusions are probabilistic, not certain. Small sample sizes, non-stationarity of market regimes, and survivorship bias are key inductive failure modes.

---

#### 2.3.3 Abductive Reasoning (CAT: ABD)

**Definition:** Inference to the best explanation — selecting the most coherent hypothesis from among competing alternatives. When multiple explanations are possible, abductive reasoning asks: which, if true, would make the available evidence most expected?

**Role in IIOS:** This is the primary integration logic of the Reasoning Engine — when multiple hypotheses are active for the same subject, abductive reasoning selects or weights them by explanatory coherence.

**Examples:**
- Three active hypotheses for NIFTY decline: (H1) profit-taking, (H2) FII outflow, (H3) systemic risk.
- Evidence: Volume is low (inconsistent with panic); FII data shows modest net selling; no credit spread widening.
- Abductive conclusion: H1 (profit-taking) provides the best explanation for the observed evidence pattern.

**Canonical type codes:** ABD-BEST-EXPLAIN, ABD-COMPARATIVE, ABD-WEIGHTED

---

#### 2.3.4 Probabilistic Reasoning (CAT: PRB)

**Definition:** Reasoning that operates over probability distributions rather than discrete true/false values. Probabilistic reasoning maintains uncertainty explicitly and produces probability-weighted conclusions.

**Role in IIOS:** Central to the Reasoning Engine's conviction computation. All conclusions have associated probability distributions, not point estimates.

**Examples:**
- Input: H1 (momentum continuation) HCS = 0.78, HCS-C = 0.82. H2 (mean reversion) HCS = 0.54, HCS-C = 0.61.
- Probabilistic reasoning: P(momentum prevails) = 0.65; P(mean reversion) = 0.27; P(range/ambiguity) = 0.08.
- Conclusion: Momentum thesis holds with 65% conviction; mean reversion cannot be dismissed.

**Canonical type codes:** PRB-DISTRIBUTION, PRB-WEIGHTING, PRB-SCENARIO

---

#### 2.3.5 Bayesian Reasoning (CAT: BAY)

**Definition:** Formal probabilistic inference using Bayes theorem: updating prior beliefs (conviction) with new evidence (new hypotheses) to produce posterior beliefs.

**Role in IIOS:** The primary framework for conviction updating. As new hypotheses arrive and existing hypotheses evolve, the Reasoning Engine updates its conviction scores using Bayesian updating.

**Canonical type codes:** BAY-PRIOR-UPDATE, BAY-POSTERIOR, BAY-SEQUENTIAL

**Formula:**

$$P(Conclusion|H_{new}) = \frac{P(H_{new}|Conclusion) \cdot P(Conclusion)}{P(H_{new})}$$

---

#### 2.3.6 Causal Reasoning (CAT: CAU)

**Definition:** Reasoning that traces directional cause-and-effect relationships between factors — not just correlation, but the direction and mechanism of influence.

**Role in IIOS:** Used when the Reasoning Engine needs to trace second and third-order implications of analytical positions. Causal chains enable the Reasoning Engine to assess which entities and sectors will be affected by a macro or structural change.

**Examples:**
- RBI rate hike → bond yields rise → equity risk premium increases → P/E compression likely → growth stocks disproportionately affected.
- INR depreciation → import costs rise → EBITDA margin pressure for import-dependent companies → earnings risk hypothesis strengthened.

**Canonical type codes:** CAU-DIRECT, CAU-SECOND-ORDER, CAU-THIRD-ORDER, CAU-FEEDBACK

---

#### 2.3.7 Temporal Reasoning (CAT: TMP)

**Definition:** Reasoning that explicitly incorporates the time dimension — considering how conditions have evolved over time, what rates of change imply, and how current conditions relate to historical precedents.

**Role in IIOS:** Market analysis is inherently temporal. Temporal reasoning considers velocity (rate of change), momentum (persistence of trends), and duration (how long a condition has persisted) as analytical factors.

**Canonical type codes:** TMP-MOMENTUM, TMP-DURATION, TMP-SEASONALITY, TMP-REGIME-TRANSITION

---

#### 2.3.8 Cross-Market Reasoning (CAT: XMK)

**Definition:** Reasoning that integrates evidence and hypotheses from multiple equity markets — NSE, BSE, global indices — to produce conclusions about inter-market dynamics.

**Canonical type codes:** XMK-CONTAGION, XMK-DECOUPLING, XMK-LEAD-LAG

---

#### 2.3.9 Cross-Asset Reasoning (CAT: XAS)

**Definition:** Reasoning that integrates evidence across asset classes — equities, bonds, currencies, commodities, gold — to produce macro-financial conclusions.

**Examples:** Rising gold + falling equities + falling bond yields = risk-off reasoning chain. USD/INR appreciation + FII equity outflows = capital flight reasoning.

**Canonical type codes:** XAS-RISK-OFF, XAS-RISK-ON, XAS-INFLATION, XAS-DEFLATION

---

#### 2.3.10 Portfolio Reasoning (CAT: PRT)

**Definition:** Reasoning about the portfolio as an analytical unit — performance attribution, factor exposure, correlation risk, capacity constraints, and return profile.

**Canonical type codes:** PRT-ATTRIBUTION, PRT-FACTOR, PRT-CAPACITY, PRT-CORRELATION

---

#### 2.3.11 Macro Reasoning (CAT: MAC)

**Definition:** Reasoning about macroeconomic conditions — interest rates, inflation, GDP growth, monetary policy, fiscal policy — and their implications for market regimes and asset class performance.

**Canonical type codes:** MAC-RATES, MAC-INFLATION, MAC-GROWTH, MAC-POLICY, MAC-REGIME

---

#### 2.3.12 Fundamental Reasoning (CAT: FND)

**Definition:** Reasoning about company or sector intrinsic value, business quality, and earnings trajectory — applying fundamental analytical frameworks to form valuation and business quality conclusions.

**Canonical type codes:** FND-VALUATION, FND-EARNINGS, FND-QUALITY, FND-MOMENTUM, FND-TURNAROUND

---

#### 2.3.13 Technical Reasoning (CAT: TEC)

**Definition:** Reasoning from price and volume patterns, technical indicators, and market microstructure to form conclusions about price dynamics and market structure.

**Canonical type codes:** TEC-TREND, TEC-MOMENTUM, TEC-STRUCTURE, TEC-SUPPORT, TEC-BREAKOUT

---

#### 2.3.14 Behavioral Reasoning (CAT: BEH)

**Definition:** Reasoning that incorporates market participant behaviour — herd dynamics, cognitive biases, sentiment extremes — as analytical inputs.

**Canonical type codes:** BEH-SENTIMENT, BEH-POSITIONING, BEH-CONTRARIAN, BEH-CROWDING

---

#### 2.3.15 Event Reasoning (CAT: EVT)

**Definition:** Reasoning about how a specific event (corporate, macro, regulatory, geopolitical) contextualises or alters the analytical landscape.

**Canonical type codes:** EVT-CORPORATE, EVT-MACRO, EVT-REGULATORY, EVT-MARKET

---

#### 2.3.16 Relationship Reasoning (CAT: REL)

**Definition:** Reasoning about inter-entity relationships — correlations, lead-lag dynamics, spread relationships — and how changes in these relationships affect analytical conclusions.

**Canonical type codes:** REL-CORRELATION, REL-SPREAD, REL-COINTEGRATION, REL-REGIME-SHIFT

---

#### 2.3.17 Risk Reasoning (CAT: RSK)

**Definition:** Reasoning about risk conditions — portfolio risk, market risk, tail risk, liquidity risk — and their implications for analytical positions and conviction levels.

**Canonical type codes:** RSK-TAIL, RSK-DRAWDOWN, RSK-CONCENTRATION, RSK-REGIME, RSK-SYSTEMIC

---

#### 2.3.18 Contrarian Reasoning (CAT: CTR)

**Definition:** Reasoning that deliberately constructs the analytical case against the dominant hypothesis or conclusion. Contrarian reasoning is not contrarianism for its own sake — it is the systematic search for the best counter-argument to the prevailing analytical position.

**Canonical type codes:** CTR-BEAR, CTR-BULL, CTR-MEAN-REV, CTR-SENTIMENT

---

#### 2.3.19 Consensus Reasoning (CAT: CNS)

**Definition:** Reasoning that synthesises multiple competing analytical perspectives into a consensus position — identifying the areas of agreement among competing hypotheses and weighting the final conclusion accordingly.

**Canonical type codes:** CNS-TECHNICAL-FUNDAMENTAL, CNS-MACRO-SECTOR, CNS-MULTI-AGENT

---

#### 2.3.20 AI Collaborative Reasoning (CAT: AIC)

**Definition:** Reasoning constructed through the structured collaboration of multiple AI analytical perspectives — different AI models or analytical sub-agents contributing to a multi-agent debate, with the Reasoning Engine synthesising the result.

**Canonical type codes:** AIC-DEBATE, AIC-SYNTHESIS, AIC-ENSEMBLE

---

#### 2.3.21 Hybrid Reasoning (CAT: HYB)

**Definition:** Reasoning that combines multiple reasoning types in a structured sequence — for example, abductive selection of the best hypothesis, followed by causal chain analysis, followed by Bayesian conviction updating.

**Canonical type codes:** HYB-ABD-CAU, HYB-IND-BAY, HYB-MULTI-TYPE

---

#### 2.3.22 Recursive Reasoning (CAT: REC)

**Definition:** Reasoning that uses the output of prior reasoning cycles as premises for new reasoning cycles. Recursive reasoning is the mechanism by which the Reasoning Engine updates its conclusions as new evidence arrives.

**Constitutional constraint:** Recursive reasoning must have a defined termination condition. Unbounded recursion is prohibited.

**Canonical type codes:** REC-UPDATE, REC-REFINE, REC-ESCALATE

---

#### 2.3.23 Meta Reasoning (CAT: MET)

**Definition:** Reasoning about the quality, limitations, and reliability of the Reasoning Engine outputs themselves. Meta reasoning asks: "How well-grounded is this conclusion? What are the known failure modes of this reasoning chain? Where is our confidence inflated relative to the evidence?"

**Canonical type codes:** MET-QUALITY, MET-CONFIDENCE-CALIBRATION, MET-LIMITATION

---

### 2.4 RCS Tier Definitions

| Tier | RCS Range | Meaning | Decision Engine treatment |
|---|---|---|---|
| DEFINITIVE | 0.85–1.00 | Very high logical validity; strong evidence coverage | High-conviction input to Decision Engine |
| STRONG | 0.70–0.84 | Well-grounded; solid reasoning chain | Substantial input to Decision Engine |
| MODERATE | 0.55–0.69 | Reasonably grounded; some logical gaps | Moderate-weight input with uncertainty flag |
| TENTATIVE | 0.40–0.54 | Partially grounded; significant gaps | Low-weight input; high uncertainty |
| EXPLORATORY | 0.00–0.39 | Minimal grounding; speculative | Context only; not actionable |

---
## PART III — CORE COMPONENT ARCHITECTURE

The Reasoning Engine is decomposed into 20 components across 5 functional clusters. Each component is a cohesive unit of responsibility with defined inputs, outputs, dependencies, and failure modes.

---

### 3.1 Cluster Layout

| Cluster | Number | Components | Role |
|---|---|---|---|
| Cluster 1: Registry and Catalog | 2 | Reasoning Registry, Reasoning Catalog | Storage, indexing, retrieval |
| Cluster 2: Construction | 4 | Reasoning Builder, Reasoning Chain Manager, Reasoning Graph, Inference Engine | Building and maintaining reasoning chains |
| Cluster 3: Evaluation | 4 | Logic Engine, Confidence Engine, Conflict Resolver, Counter Argument Engine | Evaluating validity, confidence, and opposition |
| Cluster 4: Synthesis | 4 | Consensus Engine, Weighting Engine, Dependency Manager, Context Manager | Synthesising multiple reasoning chains into conclusions |
| Cluster 5: Governance | 6 | Multi-Agent Debate Manager, Meta Reasoning Manager, Explainability Manager, Reasoning Audit Manager, Reasoning Archive Manager, Recursive Reasoning Manager | Governance, explainability, oversight, evolution |

---

### 3.2 Cluster 1 — Registry and Catalog

#### 3.2.1 Reasoning Registry

**Purpose:** The central operational store for all ACTIVE and CONTESTED reasoning chains. Functions as the single source of truth for the current analytical state of the IIOS.

**Responsibilities:**
- Accept and validate new reasoning chains from the Reasoning Builder
- Maintain lifecycle status transitions across all active chains
- Enforce uniqueness of canonical IDs
- Provide low-latency read access to active reasoning chains for all downstream consumers
- Emit lifecycle change events to the EventBus
- Maintain the CONTESTED status tracking for challenged chains

**Inputs:**
- New reasoning chains (from Reasoning Builder)
- Status change notifications (from Conflict Resolver, Counter Argument Engine)
- Archive requests (from Reasoning Archive Manager)

**Outputs:**
- Active and contested reasoning chains (to Reasoning Catalog, Decision Engine, Explainability Manager)
- Lifecycle events (to EventBus)
- Query responses (to all components with read access)

**Dependencies:**
- Storage layer (primary operational database)
- EventBus (lifecycle notifications)
- Reasoning Catalog (indexing)

**Failure modes:**
- Write failure: reasoning chain not persisted; triggers retry with circuit-breaker pattern
- Read latency spike: downstream components receive stale data; mitigated by read replica
- Status inconsistency: contested and active states mismatch; resolved by Reasoning Audit Manager reconciliation

**Monitoring metrics:**
- Active chain count by domain and type
- Write latency (P50, P95, P99)
- Lifecycle transition rate
- Query latency per consumer

**Scalability:** Registry partitioned by subject domain. Cross-domain queries routed through Reasoning Catalog.

---

#### 3.2.2 Reasoning Catalog

**Purpose:** The search and discovery layer — providing structured querying, classification, and multi-dimensional indexing of all reasoning chains (active, contested, superseded, archived).

**Responsibilities:**
- Maintain multi-dimensional index: by entity, domain, type, status, RCS tier, conviction tier, timestamp range
- Serve complex queries (e.g., "all ACTIVE DEFINITIVE reasoning chains for NIFTY with a causal step referencing RBI policy")
- Provide sorted, paginated result sets
- Maintain reasoning lineage maps (which chains reference which hypotheses)
- Support reasoning chain version tracking
- Provide analytical summaries: distribution of active chains by type, confidence distribution

**Inputs:**
- All reasoning chains (from Reasoning Registry, via change feed)
- Index rebuild requests

**Outputs:**
- Query results (to any component, including Decision Engine, Explainability Manager, Meta Reasoning Manager)
- Lineage maps
- Distribution summaries

**Dependencies:**
- Reasoning Registry (source of truth)
- Storage layer (catalog tables)

**Failure modes:**
- Index drift: catalog out of sync with registry; reconciliation triggered by Reasoning Audit Manager
- Query timeout: large multi-dimensional query degrades; mitigated by query complexity limits
- Missing lineage entry: hypothesis linkage incomplete; audit alert raised

---

### 3.3 Cluster 2 — Construction

#### 3.3.1 Reasoning Builder

**Purpose:** The primary factory for reasoning chains. Takes incoming validated hypotheses from the Hypothesis Engine and constructs well-formed, typed reasoning chains.

**Responsibilities:**
- Accept validated hypothesis bundles from the Hypothesis Engine
- Select the appropriate reasoning type(s) based on hypothesis nature, evidence profile, and subject domain
- Instantiate the Reasoning Schema (Part II) with all required fields
- Delegate to the Inference Engine for step-by-step inference construction
- Invoke the Context Manager to capture the market context at reasoning time
- Validate the completed chain structure before submitting to the Reasoning Registry
- Handle multi-type reasoning chains (HYB)

**Inputs:**
- Hypothesis bundles (from Hypothesis Engine; hypotheses must be VALIDATED status)
- Context record (from Context Manager)
- Inference steps (from Inference Engine)

**Outputs:**
- Completed reasoning chains (to Reasoning Registry)
- Construction errors (to Reasoning Audit Manager)

**Dependencies:**
- Inference Engine
- Context Manager
- Reasoning Registry
- Logic Engine (validation of completed chain structure)

**Failure modes:**
- Schema validation failure: incomplete or inconsistent chain; chain not submitted; error logged
- Inference construction failure: Inference Engine returns error; fallback to EXPLORATORY type with low RCS
- Type selection failure: no appropriate reasoning type found; raises AMBIGUITY alert

**Engineering notes:** Reasoning Builder does not select execution strategies or portfolio decisions. Its output is a structured analytical reasoning chain. All action implications are for the Decision Engine.

---

#### 3.3.2 Reasoning Chain Manager

**Purpose:** Manages the full lifecycle of in-flight reasoning chains, including versioning, supersession, and chain linkage.

**Responsibilities:**
- Track all in-progress reasoning chain construction events
- Detect when a new hypothesis invalidates an existing reasoning chain premise
- Trigger chain supersession: create new version, archive old, update lineage
- Maintain chain dependency graph: chains that build on other chains
- Coordinate recursive reasoning chain updates
- Detect circular dependencies in chain-on-chain references

**Inputs:**
- New hypothesis events (from EventBus)
- Chain construction events (from Reasoning Builder)
- Invalidation signals (from Conflict Resolver, Evidence Engine, Hypothesis Engine)

**Outputs:**
- Chain supersession events (to Reasoning Registry, EventBus)
- Circular dependency alerts (to Reasoning Audit Manager)
- Chain version history (to Reasoning Catalog)

**Dependencies:**
- Reasoning Registry (read)
- Reasoning Catalog (lineage query)
- Recursive Reasoning Manager (for recursive update orchestration)

**Failure modes:**
- Circular dependency: two chains each require the other as a premise; detected via graph traversal; resolved by flagging both as CONTESTED with human review alert
- Supersession cascade: large hypothesis update triggers wide-scale supersession; rate-limited to prevent avalanche

---

#### 3.3.3 Reasoning Graph

**Purpose:** Maintains a persistent directed acyclic graph (DAG) of all reasoning chains and their inter-dependencies, providing the network view of the Reasoning Engine analytical state.

**Responsibilities:**
- Build and maintain the reasoning chain DAG
- Detect and alert on DAG cycles (constitutional violation RC-A-007)
- Compute graph metrics: chain depth, branching factor, convergence points
- Provide graph traversal queries (e.g., "what reasoning chains depend on hypothesis H-123?")
- Support visual export of the reasoning graph for Streamlit dashboard

**Graph node types:**
- HYPOTHESIS_NODE: Input hypothesis (from Hypothesis Engine)
- REASONING_NODE: Reasoning chain
- CONCLUSION_NODE: Terminal output conclusion
- DEBATE_NODE: Multi-agent debate event
- COUNTER_NODE: Counter-argument node

**Edge types:**
- PREMISE_OF: Hypothesis is a premise of a reasoning chain
- CONCLUSION_OF: Conclusion derived from reasoning chain
- CONTESTED_BY: Counter-argument challenges conclusion
- SUPPORTS: Evidence or hypothesis supports another
- DEPENDENT_ON: Chain depends on conclusion of another chain

**Failure modes:**
- DAG size exceeds memory limit: oldest archived nodes pruned from in-memory representation; persisted in storage
- Cycle detected: system raises RC-A-007 constitutional violation; affected chains flagged CONTESTED

---

#### 3.3.4 Inference Engine

**Purpose:** The computational core of the Reasoning Engine. Constructs the step-by-step inference chain from premises to conclusion, applying the appropriate inference rules for the declared reasoning type.

**Responsibilities:**
- Apply deductive inference rules (modus ponens, modus tollens, hypothetical syllogism)
- Apply inductive inference templates (statistical pattern generalisation)
- Apply abductive inference templates (explanatory coherence scoring)
- Apply probabilistic inference (probability-weighted conjunction of premises)
- Apply Bayesian updating (prior × likelihood / evidence)
- Apply causal inference (directed acyclic causal graph reasoning)
- Detect logical fallacies in proposed inference chains
- Score inference step validity (each step has an individual validity score)
- Aggregate step scores into chain-level RCS

**Inference step schema:**

| Field | Description |
|---|---|
| step_id | Sequential integer within chain |
| step_type | DEDUCTION / INDUCTION / ABDUCTION / PROBABILISTIC / BAYESIAN / CAUSAL |
| premise_inputs | IDs of premises (hypotheses, facts, prior conclusions) |
| inference_rule | Named inference rule applied |
| conclusion | Output of this step |
| step_validity_score | Float [0,1] |
| fallacy_flags | List of detected logical fallacy types |
| notes | Engineering annotation |

**Logical fallacies detected:**
- Affirming the consequent
- Denying the antecedent
- Correlation-causation conflation
- Base rate neglect
- Small sample overgeneralisation
- Circular argument
- Survivor bias
- Post hoc ergo propter hoc

**Failure modes:**
- Invalid inference step: fallacy detected; step validity score = 0; chain RCS reduced
- Inference rule mismatch: declared reasoning type inconsistent with applied rule; chain flagged for review
- Premise unavailable: required hypothesis not found; chain construction halted; error raised

---

### 3.4 Cluster 3 — Evaluation

#### 3.4.1 Logic Engine

**Purpose:** Independent validation of all completed reasoning chains before they reach ACTIVE status. The Logic Engine is the gatekeeper between FORMING and ACTIVE.

**Responsibilities:**
- Validate logical consistency: are all premises present and valid?
- Validate inference rule correctness for declared reasoning type
- Validate that the conclusion logically follows from the inference steps
- Detect inter-chain logical contradictions
- Validate premise-conclusion temporal consistency (no future-dated premises)
- Enforce constitutional rules RC-A-001 through RC-A-010

**Validation outputs:**
- VALID: Chain meets all logical requirements; proceed to ACTIVE
- MINOR_DEFECT: Chain has recoverable issues; proceed with MODERATE or lower RCS cap
- MAJOR_DEFECT: Chain has fundamental logical errors; reject; return to Reasoning Builder

**Inputs:**
- Completed reasoning chains (from Reasoning Builder)
- Active reasoning chains (from Reasoning Registry — for inter-chain contradiction check)

**Outputs:**
- Validation results (to Reasoning Builder, Reasoning Registry)
- Constitutional violation alerts (to Reasoning Audit Manager)

**Failure modes:**
- False negative: invalid chain passes validation; caught by Meta Reasoning Manager or debate process
- False positive: valid chain rejected; re-submission path with manual review escalation

---

#### 3.4.2 Confidence Engine

**Purpose:** Computes the Reasoning Confidence Score (RCS) and conviction score for every reasoning chain.

**Responsibilities:**
- Aggregate inference step validity scores into chain-level RCS
- Apply evidence coverage weighting: chains with broader evidence support score higher
- Apply logical validity weighting: chains with stronger deductive structure score higher
- Apply consistency penalty: chains with contested premises penalised
- Compute conviction score using Bayesian updating over historical RCS of similar chains
- Assign RCS tier (DEFINITIVE/STRONG/MODERATE/TENTATIVE/EXPLORATORY)
- Update RCS when new evidence or hypotheses arrive

**RCS Formula:**

$$RCS = w_1 \cdot V_{chain} + w_2 \cdot C_{evidence} + w_3 \cdot S_{consistency} - w_4 \cdot P_{fallacy} - w_5 \cdot P_{conflict}$$

Where:
- V_chain = average inference step validity score
- C_evidence = evidence coverage breadth (0 = no direct evidence, 1 = full coverage)
- S_consistency = internal consistency score (no contradictions = 1.0)
- P_fallacy = fallacy penalty (each detected fallacy subtracts proportionally)
- P_conflict = conflict penalty (contested hypotheses in premise reduce score)
- Weights w1–w5 = domain-calibrated (default: 0.35, 0.25, 0.20, 0.10, 0.10)

**Conviction Score:**

$$Conviction = P_{posterior}(Chain_{correct}|Evidence_{current})$$

Updated each time new relevant evidence arrives.

**Failure modes:**
- Unanchored conviction: no historical data to anchor prior; default prior = 0.50; annotated in meta_assessment
- RCS inflation: evidence coverage score inflated due to weak evidence; mitigated by evidence quality weighting (from Evidence Engine ECS)

---

#### 3.4.3 Conflict Resolver

**Purpose:** Detects, categorises, and resolves conflicts between active reasoning chains that cover the same subject but reach divergent conclusions.

**Responsibilities:**
- Monitor newly ACTIVE reasoning chains for conflicts with existing chains
- Classify conflict severity: MINOR (directional disagreement within uncertainty bands), MODERATE (substantive divergence), MAJOR (directly contradictory conclusions)
- For MINOR conflicts: annotate both chains with conflict reference; no status change
- For MODERATE conflicts: trigger debate (Multi-Agent Debate Manager)
- For MAJOR conflicts: mark both chains CONTESTED; trigger immediate debate
- After resolution: update chain status and conviction scores accordingly
- Maintain conflict resolution log

**Conflict detection algorithm:**
1. Query Reasoning Catalog for active chains with overlapping subject entity IDs
2. Compare conclusion_structured fields: direction, magnitude, timeframe
3. Score directional agreement: +1 (same direction), 0 (orthogonal), -1 (opposite)
4. Score magnitude agreement: continuous scale based on normalised distance
5. Compute conflict score: 1 − (directional agreement score × magnitude agreement score)
6. Map conflict score to severity tier

**Failure modes:**
- Conflict missed: two contradictory chains both reach ACTIVE with no conflict flag; caught by periodic reconciliation audit
- False conflict: chains covering different timeframes or conditions flagged as conflicting; resolved by timeframe-aware comparison

---

#### 3.4.4 Counter Argument Engine

**Purpose:** The systematic devil advocate — for every ACTIVE reasoning chain of STRONG or DEFINITIVE tier, the Counter Argument Engine constructs the best available counter-argument.

**Design principle:** A conviction that cannot withstand a rigorous counter-argument is a weak conviction. The Counter Argument Engine is the intellectual immune system of the Reasoning Engine.

**Responsibilities:**
- For all STRONG/DEFINITIVE chains: construct at least one counter-argument
- Counter-argument construction steps:
  1. Invert the primary conclusion (bearish if bullish; causal disconnect if causal chain asserted)
  2. Search for evidence consistent with the inverted conclusion
  3. Identify the weakest inference step in the primary chain (lowest step validity score)
  4. Construct an alternative interpretation of that step
  5. Assess whether the alternative interpretation, if true, would overturn the conclusion
- Score the counter-argument strength: CA_STRENGTH (0 = trivial counter; 1 = overturning counter)
- If CA_STRENGTH >= 0.65: mark primary chain CONTESTED; trigger debate

**Canonical counter-argument schema:**
- counter_argument_id: UUID
- primary_chain_id: the chain being challenged
- challenge_type: INVERSION / ALTERNATIVE_PREMISE / WEAK_STEP / EVIDENCE_REINTERPRETATION
- challenge_conclusion: structured natural language statement
- ca_strength: float [0,1]
- supporting_evidence_ids: evidence supporting the counter-argument
- weakest_step_challenged: step_id of the primary chain step challenged
- resolution_status: OPEN / DEBATE_INITIATED / RESOLVED_CONFIRMED / RESOLVED_OVERTURNED

**Failure modes:**
- Trivial counter-arguments: every chain gets a weak counter that never triggers debate; mitigated by CA_STRENGTH threshold
- Overthrow cascade: strong counter-argument overturns a chain that many others depend on; cascade managed by Reasoning Chain Manager

---
### 3.5 Cluster 4 — Synthesis

#### 3.5.1 Consensus Engine

**Purpose:** When multiple active reasoning chains cover the same subject with different conclusions, the Consensus Engine synthesises a consensus position — the analytically weighted reconciliation of competing conclusions.

**Responsibilities:**
- Collect all active and contested reasoning chains for a given subject entity and domain
- Compute weighted average conviction using RCS and historical performance weight per chain
- Identify consensus conclusion: the conclusion supported by the plurality of well-grounded chains
- Identify dissenting positions: chains that fall outside the consensus band
- Produce a Consensus Record: structured consensus position with explicit uncertainty quantification
- Update when chains are superseded, retired, or archived

**Consensus computation:**

For a set of n active chains {C_1, C_2, ..., C_n} covering subject S:

$$P_{consensus}(conclusion) = \frac{\sum_{i=1}^{n} RCS_i \cdot w_{hist,i} \cdot \mathbb{1}[C_i.conclusion = conclusion]}{\sum_{i=1}^{n} RCS_i \cdot w_{hist,i}}$$

Where w_hist,i is the historical performance weight of chain type i (from Learning System feedback).

**Consensus confidence band:** Consensus positions with entropy H(consensus distribution) < 0.3 are HIGH-CONFIDENCE. H >= 0.6 = CONTESTED.

**Canonical consensus record:**
- consensus_id: UUID
- subject_entity_ids: List of entities
- consensus_conclusion: structured
- consensus_rcs: float [0,1]
- dissenting_chains: list of chain IDs outside consensus band
- consensus_entropy: float [0,1]
- contributing_chains: list of chain IDs
- snapshot_timestamp: UTC

**Failure modes:**
- No consensus: all chains equally weighted in opposite directions; system outputs CONTESTED consensus with high entropy; Decision Engine treats as ambiguous
- Stale consensus: contributing chain superseded but consensus not refreshed; mitigated by change-feed trigger

---

#### 3.5.2 Weighting Engine

**Purpose:** Provides the analytical weights used by the Consensus Engine, Confidence Engine, and other synthesis components to combine multiple reasoning chains into integrated positions.

**Responsibilities:**
- Maintain domain-calibrated weights for each reasoning type (e.g., macro reasoning weighted higher in high-VIX regime)
- Maintain regime-conditional weights (weights shift based on current market regime)
- Maintain recency weights (more recent chains weighted higher within recency decay window)
- Provide historical performance weights (chains from reasoning types with higher historical accuracy weighted higher)
- Update weights dynamically as Learning System provides performance feedback

**Weight categories:**
| Weight Type | Basis | Update frequency |
|---|---|---|
| Type weights | Reasoning type base reliability | Weekly (Learning System) |
| Regime weights | Current market regime classification | Per cycle |
| Recency weights | Exponential decay over time since construction | Continuous |
| Performance weights | Historical accuracy of similar chains | Daily |
| Domain weights | Subject domain reliability calibration | Weekly |

**Failure modes:**
- Weight divergence: aggressive weight updates produce extreme imbalance; safeguarded by weight clipping (no weight > 5x min weight)
- Regime misclassification: wrong regime → wrong weight profile; mitigated by regime uncertainty band

---

#### 3.5.3 Dependency Manager

**Purpose:** Manages inter-reasoning-chain dependencies — tracking which chains depend on the conclusions of other chains, and propagating updates when dependencies change.

**Responsibilities:**
- Maintain the dependency graph (complementary to Reasoning Graph, focused on update propagation)
- Detect when a chain is superseded or retired and propagate invalidation to all dependent chains
- Compute dependency depth: chains that are 2+ hops dependent on a changed chain
- Enforce maximum dependency depth (constitutional rule RC-A-008: max depth = 5)
- Alert when deep dependency chains are affected by upstream changes

**Dependency propagation algorithm:**
1. Chain C_base is superseded
2. Query dependency graph for all chains D_1..D_k with DEPENDENT_ON edge to C_base
3. For each D_i: compute impact score (0 = minor impact, 1 = conclusion overturned)
4. For impact score >= 0.5: mark D_i as CONTESTED; trigger re-evaluation
5. For impact score < 0.5: annotate D_i with PREMISE_EVOLVED flag; RCS reduced by 0.10

**Failure modes:**
- Dependency cascade: high-impact upstream change triggers wide cascade of CONTESTED chains; rate-limited by cascade budget per cycle
- Circular dependency: D depends on C, C depends on D; detected by cycle check during dependency graph build; both chains flagged CONTESTED

---

#### 3.5.4 Context Manager

**Purpose:** Captures, stores, and supplies the market context at the time a reasoning chain is constructed. Ensures every reasoning chain is permanently associated with the market conditions under which it was formed.

**Responsibilities:**
- Capture current market context snapshot at reasoning construction time
- Structure context record: regime, macro, sector conditions, liquidity, volatility, calendar context
- Supply context records to Reasoning Builder, Inference Engine, and Explainability Manager
- Enable context-conditional reasoning: different reasoning chains valid under different contexts
- Support context comparison: comparing current context to context of historical chains

**Context record schema:**

| Field | Description |
|---|---|
| context_id | UUID |
| capture_timestamp | UTC datetime |
| market_regime | BULL_TREND / BEAR_TREND / RANGE / CRISIS / RECOVERY / DISTRIBUTION |
| vix_level | Float (volatility index) |
| vix_percentile | Float [0,1] — percentile within 2-year history |
| breadth_reading | Float — advance-decline breadth |
| liquidity_condition | HIGH / NORMAL / STRESSED |
| macro_backdrop | JSON — rates, inflation, growth flags |
| sector_leadership | List of leading/lagging sectors |
| event_flags | List of active event hypotheses affecting context |
| nifty_level | Float |
| nifty_vs_52wk_high_pct | Float |
| calendar_position | PRE_EXPIRY / EXPIRY / POST_EXPIRY / BUDGET / EARNINGS_SEASON / NORMAL |
| session | PRE_MARKET / MARKET_HOURS / POST_MARKET |

**Failure modes:**
- Stale context: reasoning chain built with outdated context snapshot; mitigated by context timestamp validation (max age = 5 minutes)
- Incomplete context: one or more context fields unavailable; chain annotated with CONTEXT_INCOMPLETE flag; RCS reduced by 0.05

---

### 3.6 Cluster 5 — Governance

#### 3.6.1 Multi-Agent Debate Manager

**Purpose:** Orchestrates the structured multi-agent debate process — bringing together multiple analytical perspectives to challenge and refine contested or ambiguous reasoning chains.

**Design principle:** Debate is mandatory for MAJOR conflicts and for all DEFINITIVE-tier chains before they are delivered to the Decision Engine. No reasoning chain achieves DEFINITIVE status without surviving structured opposition.

**Debate roles:**
| Role | Description |
|---|---|
| Proposer | Presents and defends the primary reasoning chain conclusion |
| Challenger | Presents counter-arguments (from Counter Argument Engine) |
| Devil Advocate | Argues the strongest case against the proposer regardless of personal prior |
| Synthesiser | Integrates proposer and challenger positions into consensus |
| Meta Judge | Evaluates the quality of the debate process itself |

**Debate protocol:**
1. Opening statements: Proposer and Challenger state positions
2. Evidence round: both sides present supporting evidence and hypotheses
3. Challenge round: Challenger attacks weakest inference steps
4. Defence round: Proposer defends challenged steps
5. Synthesis: Synthesiser produces integrated position
6. Meta assessment: Meta Judge evaluates debate quality and reasoning soundness
7. Verdict: RCS updated based on debate outcome

**Debate verdict outcomes:**
- CONFIRMED: Proposer position survives; chain remains ACTIVE at same or higher RCS
- REFINED: Proposer position partially modified; chain updated; RCS adjusted
- CONTESTED: No clear winner; chain status = CONTESTED; both positions preserved
- OVERTURNED: Challenger position prevails; original chain RETIRED; new chain built from challenger position

**Failure modes:**
- No challenger: Counter Argument Engine finds no significant counter; debate skipped; chain confirmed by default with note
- Debate deadlock: Synthesiser cannot integrate opposing positions; chain remains CONTESTED; escalated to Meta Reasoning Manager

---

#### 3.6.2 Meta Reasoning Manager

**Purpose:** The self-assessment layer — evaluates the quality, limitations, and calibration of the Reasoning Engine outputs. The Meta Reasoning Manager is the Reasoning Engine reasoning about itself.

**Responsibilities:**
- Assess whether the most active reasoning chains are appropriately distributed across reasoning types (no reasoning type monoculture)
- Detect overconfidence: large clusters of DEFINITIVE chains in one direction suggest calibration issue
- Detect underconfidence: extremely few DEFINITIVE chains despite good market conditions suggest conservatism bias
- Assess reasoning chain diversity: are diverse perspectives represented?
- Detect recency bias: overweight of very recent chains
- Detect regime mismatch: current regime classification inconsistent with chain distribution
- Produce periodic Meta Reasoning Report: summary of quality assessment findings
- Alert on systematic quality issues (MET-QUALITY constitutional alerts)

**Meta reasoning quality dimensions:**
| Dimension | Description |
|---|---|
| Type diversity | Fraction of active chain types represented |
| Confidence calibration | Agreement between RCS and historical accuracy |
| Directional balance | Ratio of bullish to bearish chains |
| Temporal balance | Ratio of short-term to long-term chains |
| Debate coverage | Fraction of DEFINITIVE chains that have passed debate |
| Counter coverage | Fraction of STRONG chains with counter-arguments |

**Failure modes:**
- Meta assessment blindspot: systematic bias in the Reasoning Engine not detectable from within; mitigated by Learning System external feedback
- Oscillation: meta corrections flip the Reasoning Engine between overconfidence and underconfidence; dampened by exponential smoothing of meta interventions

---

#### 3.6.3 Explainability Manager

**Purpose:** Generates the human-readable explanatory record for every reasoning chain, making the Reasoning Engine analytically transparent.

**Responsibilities:**
- For every ACTIVE/CONTESTED chain: generate a structured natural language explanation
- Explanation components: premise summary, inference chain narrative, conclusion statement, uncertainty quantification, key assumptions, conditions under which conclusion would change
- Generate chain visualisation record: text representation of reasoning DAG for this chain
- Generate counter-argument summary if applicable
- Maintain explanation versioning (explanations updated when chains are updated)
- Supply explanations to Streamlit dashboard, Telegram bot, Decision Engine annotation

**Explanation schema:**
| Field | Description |
|---|---|
| explanation_id | UUID |
| chain_id | Reasoning chain this explains |
| chain_version | Version number |
| premise_summary | Concise statement of key premises |
| inference_narrative | Step-by-step narrative of the reasoning process |
| conclusion_statement | Formal conclusion in plain language |
| uncertainty_statement | Explicit quantification of what is uncertain |
| key_assumptions | What must be true for this conclusion to hold |
| invalidation_conditions | What would overturn this conclusion |
| confidence_prose | Prose translation of RCS tier |
| counter_summary | Summary of best counter-argument if applicable |
| generated_timestamp | UTC |

**Failure modes:**
- Explanation staleness: chain updated but explanation not refreshed; mitigated by change-feed trigger
- Unintelligible explanation: NLG module produces garbled output; fallback to template-based structured explanation

---

#### 3.6.4 Reasoning Audit Manager

**Purpose:** The compliance and integrity layer. Records all reasoning chain construction events, validates constitutional rule compliance, and supports regulatory-grade audit trail requirements.

**Responsibilities:**
- Record every reasoning chain creation, update, status change, and deletion event
- Validate constitutional rule compliance for all ACTIVE chains on a rolling basis
- Detect and flag constitutional violations
- Maintain immutable audit trail in append-only audit log
- Support point-in-time reconstruction: given a timestamp, reconstruct the exact state of the Reasoning Engine
- Produce daily audit summary report

**Audit record schema:**
| Field | Description |
|---|---|
| audit_id | UUID |
| chain_id | Chain affected |
| event_type | CREATE / UPDATE / STATUS_CHANGE / ARCHIVE / VIOLATION |
| event_timestamp | UTC |
| actor | Component that triggered the event |
| previous_state | Snapshot before event |
| new_state | Snapshot after event |
| constitutional_rules_checked | List of rules validated |
| violations_detected | List of violations if any |

**Failure modes:**
- Audit write failure: event not captured; circuit-breaker triggers; chain held in FORMING until audit write succeeds
- Audit log corruption: cryptographic hash chain detects tampering; alerts raised immediately

---

#### 3.6.5 Reasoning Archive Manager

**Purpose:** Manages the lifecycle transition from ACTIVE/RETIRED to ARCHIVED, ensuring all historical reasoning chains are preserved for Learning System use, regulatory compliance, and future analysis.

**Responsibilities:**
- Move RETIRED and SUPERSEDED chains to ARCHIVED status on schedule
- Maintain archive completeness: every chain ever constructed must be preserved (no deletions)
- Apply retention policy per governance tier (CRITICAL = permanent; HIGH = 10 years; MEDIUM = 5 years; LOW = 3 years)
- Provide archive search capability for historical analysis
- Support Learning System read access to archived chains for performance attribution

**Failure modes:**
- Archive write failure: chain stuck in RETIRED status; retry queue with dead-letter alert
- Archive retrieval latency: large historical queries slow; mitigated by columnar archive storage

---

#### 3.6.6 Recursive Reasoning Manager

**Purpose:** Manages the recursive reasoning pattern — where the output of a prior reasoning cycle is used as a premise in a new reasoning cycle. Ensures termination and prevents infinite loops.

**Responsibilities:**
- Track all active recursive reasoning chains
- Enforce maximum recursion depth (constitutional rule RC-A-009: max depth = 3)
- Enforce termination condition: recursion terminates when conclusion delta < threshold or when max depth reached
- Detect non-convergent recursion (conclusion oscillating between cycles)
- Produce recursive reasoning summary: how many cycles, final convergence, delta trajectory

**Termination conditions:**
- Conclusion delta (|RCS_cycle_n - RCS_cycle_{n-1}|) < 0.02: converged
- Recursion depth = 3: hard stop regardless of convergence
- Conclusion oscillation detected: mark chain CONTESTED; halt recursion; alert

**Failure modes:**
- Non-termination: recursion depth limit prevents hanging; hard stop always applied
- Oscillation: conclusion swings between opposite directions across cycles; CONTESTED status assigned; Meta Reasoning Manager alerted

---
## PART IV — REASONING LIFECYCLE

### 4.1 Overview

The Reasoning Engine processes hypotheses through a well-defined 15-stage lifecycle. Each stage produces a defined artifact, transitions through a defined state, and has defined timing constraints.

---

### 4.2 Lifecycle Stages

#### Stage 1: Hypothesis Intake

**Description:** The Reasoning Engine receives validated hypothesis bundles from the Hypothesis Engine. Only hypotheses with lifecycle status VALIDATED are accepted.

**Input:** Hypothesis bundle (1..N hypotheses with linked evidence IDs)
**Output:** Accepted intake record with hypothesis IDs, intake timestamp, and subject entity mapping
**Timing constraint:** < 50ms
**Guard conditions:** Hypothesis status must be VALIDATED. HCS must be >= 0.30 (below this threshold, hypothesis is held in low-priority queue).
**Failure handling:** Invalid status → reject with error; HCS below minimum → queue for reconsideration when market regime changes

---

#### Stage 2: Context Capture

**Description:** The Context Manager captures the current market context record at the moment hypotheses are received.

**Input:** Hypothesis intake record
**Output:** Context record (see Context Manager schema in Part III)
**Timing constraint:** < 30ms
**Guard conditions:** Context data must be < 5 minutes old (otherwise: CONTEXT_STALE flag raised)

---

#### Stage 3: Reasoning Type Selection

**Description:** The Reasoning Builder analyses the hypothesis bundle and selects the appropriate reasoning type(s) for chain construction.

**Selection algorithm:**
1. Examine hypothesis category (from Hypothesis Engine taxonomy)
2. Examine evidence types in the hypothesis evidence set
3. Examine subject domain (NIFTY, sector, individual equity, macro, cross-asset)
4. Apply type selection matrix (see Supplement A)
5. If ambiguous: default to HYB (Hybrid) type with highest-applicable component types
**Output:** Reasoning type selection record
**Timing constraint:** < 20ms

---

#### Stage 4: Inference Construction

**Description:** The Inference Engine constructs the step-by-step inference chain from premises to conclusion.

**Input:** Hypothesis bundle, context record, reasoning type selection
**Output:** Draft inference chain with step validity scores
**Timing constraint:** < 200ms
**Key logic:**
- Each inference step is validated for logical correctness
- Fallacy detection applied to each step
- Step validity scores computed; any step with validity < 0.30 triggers chain-level alert

---

#### Stage 5: Evidence Mapping

**Description:** The Reasoning Builder maps the evidence underlying each hypothesis to the inference steps, ensuring every inference step has traceable evidence.

**Input:** Hypothesis evidence IDs, inference steps
**Output:** Evidence-annotated inference chain
**Timing constraint:** < 100ms
**Guard condition:** Every inference step that references a factual claim must have at least one evidence pointer. Steps with no evidence pointer are annotated EVIDENCE_GAP; RCS penalty applied.

---

#### Stage 6: Logic Validation

**Description:** The Logic Engine independently validates the completed chain structure.

**Input:** Evidence-annotated inference chain
**Output:** Validation verdict (VALID / MINOR_DEFECT / MAJOR_DEFECT)
**Timing constraint:** < 100ms
**Failure path:** MAJOR_DEFECT → chain returned to Reasoning Builder; MINOR_DEFECT → proceed with RCS cap; VALID → proceed to Stage 7

---

#### Stage 7: Conflict Detection

**Description:** The Conflict Resolver checks the new chain against all active chains for the same subject entity.

**Input:** Validated inference chain + active chain query results from Reasoning Catalog
**Output:** Conflict status (NONE / MINOR / MODERATE / MAJOR)
**Timing constraint:** < 150ms
**Action by severity:** NONE/MINOR → proceed; MODERATE → debate scheduled (async); MAJOR → chain enters CONTESTED immediately; debate initiated

---

#### Stage 8: Counter Argument Construction

**Description:** The Counter Argument Engine constructs the best available counter-argument for the chain.

**Input:** Validated chain
**Output:** Counter-argument record with CA_STRENGTH
**Timing constraint:** < 200ms
**Guard:** Chains with RCS < 0.55 (TENTATIVE/EXPLORATORY) receive abbreviated counter-argument check only.
**Action:** CA_STRENGTH >= 0.65 → chain enters CONTESTED; debate initiated

---

#### Stage 9: Confidence Scoring

**Description:** The Confidence Engine computes the RCS and conviction score for the chain.

**Input:** Evidence-mapped inference chain, conflict status, counter-argument record
**Output:** RCS, RCS tier, conviction score, uncertainty score
**Timing constraint:** < 50ms

---

#### Stage 10: Debate (conditional)

**Description:** If chain has entered CONTESTED status (Stage 7 or 8), the Multi-Agent Debate Manager orchestrates the debate.

**Input:** Primary chain, counter-argument record, available evidence
**Output:** Debate verdict (CONFIRMED / REFINED / CONTESTED / OVERTURNED)
**Timing constraint:** < 500ms (fast debate); escalation to async debate if > 500ms
**Effect on chain:** CONFIRMED → RCS preserved/increased; REFINED → chain updated; CONTESTED → chain holds CONTESTED status; OVERTURNED → chain RETIRED; new chain constructed from winner position

---

#### Stage 11: Consensus Integration

**Description:** The Consensus Engine integrates the newly ACTIVE chain into the subject entity consensus position.

**Input:** New/updated ACTIVE chain, existing consensus record for subject
**Output:** Updated consensus record
**Timing constraint:** < 100ms

---

#### Stage 12: Explanation Generation

**Description:** The Explainability Manager generates the human-readable explanation record.

**Input:** ACTIVE chain, inference steps, evidence records, counter-argument record if applicable
**Output:** Explanation record
**Timing constraint:** < 300ms

---

#### Stage 13: Governance Annotation

**Description:** Governance tier, domain owner, audit trail creation.

**Input:** ACTIVE chain
**Output:** Fully annotated chain with governance fields; initial audit record created
**Timing constraint:** < 50ms

---

#### Stage 14: Storage and Registry

**Description:** Chain written to Reasoning Registry, indexed in Reasoning Catalog, Reasoning Graph updated.

**Input:** Fully annotated chain with all records
**Output:** Confirmed storage acknowledgment; graph updated
**Timing constraint:** < 100ms

---

#### Stage 15: Distribution

**Description:** ACTIVE chain made available to Decision Engine, Streamlit dashboard, Telegram bot, Learning System, and any other registered consumers.

**Input:** Stored chain reference
**Output:** Distribution events on EventBus; chain available via query API
**Timing constraint:** < 50ms

---

### 4.3 Lifecycle Stage Summary

| Stage | Name | Input | Output | Max Latency |
|---|---|---|---|---|
| 1 | Hypothesis Intake | Hypothesis bundle | Intake record | 50ms |
| 2 | Context Capture | Intake record | Context record | 30ms |
| 3 | Type Selection | Hypotheses + context | Type selection | 20ms |
| 4 | Inference Construction | Bundle + type | Draft chain | 200ms |
| 5 | Evidence Mapping | Chain + evidence | Annotated chain | 100ms |
| 6 | Logic Validation | Annotated chain | Validation verdict | 100ms |
| 7 | Conflict Detection | Chain + active chains | Conflict status | 150ms |
| 8 | Counter Argument | Validated chain | Counter-argument | 200ms |
| 9 | Confidence Scoring | Chain + all records | RCS + conviction | 50ms |
| 10 | Debate (conditional) | Contested chain | Debate verdict | 500ms |
| 11 | Consensus Integration | New active chain | Updated consensus | 100ms |
| 12 | Explanation Generation | Chain + all records | Explanation record | 300ms |
| 13 | Governance Annotation | Chain | Annotated chain | 50ms |
| 14 | Storage | Fully annotated | Stored ACK | 100ms |
| 15 | Distribution | Chain reference | Events emitted | 50ms |

**Total lifecycle latency target:**
- Happy path (no debate): < 1,300ms
- With debate: < 1,800ms
- With recursive reasoning: < 3,000ms

---

### 4.4 State Machine

```
[INTAKE]
    |
    v
[FORMING] ─── validation failure ──> [ERROR]
    |
    v
[LOGIC_CHECK] ─── MAJOR_DEFECT ──> [FORMING] (rebuild)
    |
    v
[CONFLICT_CHECK]
    |────── NONE/MINOR ──────────────┐
    |────── MODERATE/MAJOR ──────────v
    |                          [CONTESTED]
    |                               |
    |                          [DEBATE]
    |                               |
    |              ┌────────────────┼────────────────┐
    |         CONFIRMED          REFINED          OVERTURNED
    |              |                |                 |
    |          [ACTIVE]       [REBUILT]           [RETIRED]
    |              |
    v              v
[ACTIVE] ◄─────────
    |
    |── new evidence ──> [ACTIVE] (RCS updated)
    |── superseded ──────────────────────────> [SUPERSEDED]
    |── retired ─────────────────────────────> [RETIRED]
    |
[ARCHIVED]
```

---

### 4.5 Point-in-Time Semantics

Every reasoning chain is queryable at any historical point in time. The Reasoning Engine maintains complete point-in-time (PIT) semantics:

- Every state transition is recorded with a timestamp
- Queries can specify `as_of_timestamp` to retrieve the state of a chain at any historical moment
- The Reasoning Audit Manager ensures PIT consistency
- PIT queries are used by the Learning System for performance attribution

---
## PART V — REASONING SERVICES

The Reasoning Engine exposes 14 canonical services. Each service is the public contract by which external systems and internal components access Reasoning Engine capabilities.

---

### RS-01 — Inference Service

**Service identifier:** RS-01
**Service name:** Inference Service
**Service type:** Synchronous computation

**Purpose:** Core reasoning chain construction — takes validated hypotheses and returns completed, scored reasoning chains.

**Interface:**
- Input: InferenceRequest {hypothesis_ids: List[String], subject_entity_ids: List[String], requested_reasoning_types: List[Enum], priority: HIGH/NORMAL/LOW}
- Output: InferenceResponse {reasoning_chain_id: String, rcs: Float, rcs_tier: Enum, conviction_score: Float, status: ACTIVE/CONTESTED, inference_step_count: Integer}

**SLA:** P50 < 800ms, P95 < 1,500ms, P99 < 2,500ms
**Callers:** Hypothesis Engine (primary), MasterOrchestrator
**Authentication:** IIOS internal service mesh — no external access
**Idempotency:** Same hypothesis set + same context → same chain ID (deterministic ID generation)
**Error codes:** HYPOTHESIS_NOT_FOUND, INFERENCE_CONSTRUCTION_FAILED, CONTEXT_UNAVAILABLE, TYPE_SELECTION_AMBIGUOUS

---

### RS-02 — Logic Validation Service

**Service identifier:** RS-02
**Service name:** Logic Validation Service
**Service type:** Synchronous validation

**Purpose:** Validates a proposed reasoning chain for logical correctness independently of chain construction.

**Interface:**
- Input: LogicValidationRequest {chain_id: String or chain_draft: ReasoningChainDraft}
- Output: LogicValidationResponse {verdict: VALID/MINOR_DEFECT/MAJOR_DEFECT, defect_list: List[Defect], step_validity_scores: List[Float]}

**SLA:** P50 < 80ms, P95 < 150ms, P99 < 300ms
**Callers:** Reasoning Builder, external validation workflows
**Use case:** Allows external systems to validate proposed reasoning chain drafts before formal submission.

---

### RS-03 — Debate Orchestration Service

**Service identifier:** RS-03
**Service name:** Debate Orchestration Service
**Service type:** Asynchronous orchestration

**Purpose:** Orchestrates multi-agent debate for contested reasoning chains.

**Interface:**
- Input: DebateRequest {chain_id: String, trigger_reason: CONFLICT/COUNTER_ARGUMENT/MANUAL, priority: URGENT/NORMAL}
- Output: DebateResult {debate_id: UUID, verdict: CONFIRMED/REFINED/CONTESTED/OVERTURNED, updated_chain_id: String, debate_duration_ms: Integer}

**SLA:** P50 < 400ms, P95 < 800ms, P99 < 1,500ms (fast debate)
**Note:** Long debates (> 1,500ms) scheduled as async jobs; immediate result = DEBATE_SCHEDULED with async callback

---

### RS-04 — Consensus Query Service

**Service identifier:** RS-04
**Service name:** Consensus Query Service
**Service type:** Synchronous query

**Purpose:** Returns the current consensus position for a subject entity across all active reasoning chains.

**Interface:**
- Input: ConsensusQueryRequest {subject_entity_ids: List[String], domain: Enum, as_of_timestamp: Optional[UTC]}
- Output: ConsensusResponse {consensus_id: UUID, consensus_conclusion: Struct, consensus_rcs: Float, consensus_entropy: Float, contributing_chain_count: Integer, dissenting_chain_count: Integer}

**SLA:** P50 < 30ms, P95 < 80ms, P99 < 150ms
**Callers:** Decision Engine (primary), Streamlit dashboard, MasterOrchestrator

---

### RS-05 — Confidence Service

**Service identifier:** RS-05
**Service name:** Confidence Service
**Service type:** Synchronous computation

**Purpose:** Computes or recomputes the RCS and conviction score for a given reasoning chain.

**Interface:**
- Input: ConfidenceRequest {chain_id: String, recompute: Boolean}
- Output: ConfidenceResponse {rcs: Float, rcs_tier: Enum, conviction_score: Float, uncertainty_score: Float, rcs_components: JSON}

**SLA:** P50 < 40ms, P95 < 100ms, P99 < 200ms

---

### RS-06 — Conflict Resolution Service

**Service identifier:** RS-06
**Service name:** Conflict Resolution Service
**Service type:** Synchronous detection + async resolution

**Purpose:** Detects conflicts between reasoning chains and initiates resolution.

**Interface:**
- Input: ConflictCheckRequest {chain_id: String, check_against: ALL_ACTIVE or List[chain_ids]}
- Output: ConflictCheckResponse {conflict_status: NONE/MINOR/MODERATE/MAJOR, conflicting_chain_ids: List[String], conflict_score: Float, resolution_action: NONE/ANNOTATE/DEBATE/CONTEST}

**SLA:** P50 < 100ms, P95 < 200ms, P99 < 400ms

---

### RS-07 — Explanation Service

**Service identifier:** RS-07
**Service name:** Explanation Service
**Service type:** Synchronous retrieval + async generation

**Purpose:** Returns the explanation record for a reasoning chain.

**Interface:**
- Input: ExplanationRequest {chain_id: String, generate_if_missing: Boolean, format: FULL/SUMMARY/PROSE}
- Output: ExplanationResponse {explanation_id: UUID, premise_summary: String, inference_narrative: String, conclusion_statement: String, uncertainty_statement: String, confidence_prose: String, counter_summary: Optional[String]}

**SLA:** Retrieval: P50 < 20ms; Generation: P50 < 250ms, P95 < 500ms
**Callers:** Decision Engine (for decision justification), Streamlit dashboard, Telegram bot

---

### RS-08 — Dependency Service

**Service identifier:** RS-08
**Service name:** Dependency Service
**Service type:** Synchronous graph query

**Purpose:** Returns the dependency graph for a given reasoning chain — what chains it depends on, what chains depend on it.

**Interface:**
- Input: DependencyRequest {chain_id: String, direction: UPSTREAM/DOWNSTREAM/BOTH, max_depth: Integer [1–5]}
- Output: DependencyResponse {upstream_chains: List[ChainRef], downstream_chains: List[ChainRef], depth_reached: Integer, circular_dependency_detected: Boolean}

**SLA:** P50 < 50ms, P95 < 150ms, P99 < 300ms

---

### RS-09 — Context Service

**Service identifier:** RS-09
**Service name:** Context Service
**Service type:** Synchronous read/write

**Purpose:** Provides access to context records for reasoning chains and for current market state.

**Interface:**
- Input (read): ContextReadRequest {chain_id: String or timestamp: UTC}
- Input (capture): ContextCaptureRequest {} (empty — captures current state)
- Output (read): ContextRecord (full schema from Part III)
- Output (capture): ContextRecord (newly captured)

**SLA:** Read: P50 < 10ms; Capture: P50 < 25ms

---

### RS-10 — Validation Service

**Service identifier:** RS-10
**Service name:** Validation Service
**Service type:** Synchronous validation

**Purpose:** Full constitutional validation of a reasoning chain — checks all applicable constitutional rules.

**Interface:**
- Input: ValidationRequest {chain_id: String, rule_categories: Optional[List[Enum]]}
- Output: ValidationResponse {overall_result: PASS/WARN/FAIL, rule_results: List[RuleResult], violation_count: Integer, warning_count: Integer}

**SLA:** P50 < 80ms, P95 < 200ms, P99 < 400ms
**Note:** Full validation (all rules) used for DEFINITIVE-tier chains; abbreviated validation (key rules) for lower tiers.

---

### RS-11 — Audit Service

**Service identifier:** RS-11
**Service name:** Audit Service
**Service type:** Write (append-only) + read

**Purpose:** Records reasoning chain audit events and supports audit trail queries.

**Interface:**
- Input (write): AuditEvent {chain_id, event_type, actor, previous_state, new_state}
- Input (read): AuditQuery {chain_id, event_type_filter, time_range, page_size}
- Output (read): AuditTrail {events: List[AuditRecord], total_count, page_info}

**SLA:** Write: P50 < 15ms; Read: P50 < 50ms

---

### RS-12 — Reasoning Search Service

**Service identifier:** RS-12
**Service name:** Reasoning Search Service
**Service type:** Synchronous query

**Purpose:** Multi-dimensional search across all reasoning chains (active, archived, historical).

**Interface:**
- Input: ReasoningSearchRequest {entity_ids: Optional[List], domain: Optional[Enum], type: Optional[Enum], rcs_min: Optional[Float], rcs_tier: Optional[Enum], status: Optional[Enum], time_range: Optional, contains_keyword: Optional[String], as_of_timestamp: Optional[UTC]}
- Output: ReasoningSearchResponse {chains: List[ChainSummary], total_count, page_info, query_latency_ms}

**SLA:** P50 < 100ms, P95 < 300ms, P99 < 800ms (complex historical queries may be async)

---

### RS-13 — Archive Service

**Service identifier:** RS-13
**Service name:** Archive Service
**Service type:** Asynchronous write + synchronous read

**Purpose:** Archives retired/superseded chains and provides read access to historical archive.

**Interface:**
- Input (archive): ArchiveRequest {chain_id, reason: RETIRED/SUPERSEDED/SCHEDULED}
- Input (read): ArchiveReadRequest {chain_id, as_of_timestamp}
- Output (archive): ArchiveAcknowledgment {chain_id, archived_at, archive_location}
- Output (read): ArchivedChain (full chain record at requested timestamp)

**SLA:** Archive: P95 < 500ms (async); Read: P50 < 200ms

---

### RS-14 — Health Service

**Service identifier:** RS-14
**Service name:** Health Service
**Service type:** Synchronous health check

**Purpose:** Returns the operational health status of the Reasoning Engine and all its sub-components.

**Interface:**
- Input: HealthCheckRequest {include_components: Boolean, include_metrics: Boolean}
- Output: HealthResponse {overall_status: HEALTHY/DEGRADED/CRITICAL, component_statuses: List[ComponentHealth], key_metrics: JSON, last_check_timestamp: UTC}

**Component health statuses:**
| Status | Meaning |
|---|---|
| HEALTHY | Component operating within SLA |
| DEGRADED | Component operational but SLA breached |
| CRITICAL | Component non-functional or producing invalid output |
| UNKNOWN | Component status cannot be determined |

**SLA:** P50 < 20ms (cached), P95 < 100ms (full check)
**Callers:** ControlTower, Streamlit dashboard, MasterOrchestrator

---
## PART VI — PROCESSING PIPELINES

The Reasoning Engine operates through 10 primary processing pipelines. Each pipeline coordinates a specific end-to-end analytical workflow.

---

### Pipeline 1: Hypothesis-to-Reasoning Pipeline

**Purpose:** The primary end-to-end pipeline — from hypothesis intake to ACTIVE reasoning chain in Reasoning Registry.

**Trigger:** New validated hypothesis bundle received from Hypothesis Engine

**Flow:**

```
[Hypothesis Engine]
        |
        v (validated hypothesis bundle)
[Reasoning Builder] <── [Context Manager] (context record)
        |
        v (type selection)
[Inference Engine]
        |
        v (draft inference chain)
[Logic Engine] ── MAJOR_DEFECT ──> [Reasoning Builder] (rebuild)
        |
        v (VALID / MINOR_DEFECT)
[Conflict Resolver] ── MAJOR conflict ──> [Contested Queue]
        |                                        |
        v NONE/MINOR                             v
[Counter Argument Engine] ── CA_STRENGTH>=0.65 ──> [Contested Queue]
        |                                        |
        v                                [Debate Pipeline]
[Confidence Engine]
        |
        v (RCS computed)
[Reasoning Registry] <── [Reasoning Audit Manager] (audit record)
        |
        v
[Reasoning Catalog] (indexed)
[Reasoning Graph] (DAG updated)
        |
        v
[Consensus Engine] (consensus updated)
[Explainability Manager] (explanation generated)
        |
        v
[Distribution] (EventBus notification, Decision Engine consumer notified)
```

**Key SLAs:**
- Happy path total: < 1,300ms
- Conflict detected path: < 1,600ms (adds conflict analysis)
- Contested/debate path: < 1,800ms

---

### Pipeline 2: Evidence Mapping Pipeline

**Purpose:** Maps hypothesis evidence records to inference steps, providing full traceability from evidence to conclusion.

**Trigger:** Called by Reasoning Builder during Hypothesis-to-Reasoning Pipeline, Stage 5

**Flow:**

```
[Reasoning Builder] (inference chain draft)
        |
        v (hypothesis evidence IDs)
[Evidence Engine read-access] (fetch evidence records)
        |
        v (evidence records)
[Evidence Mapper] (match evidence to inference steps)
        |── evidence available ──> [Annotated chain with evidence pointers]
        |── evidence gap ──────> [EVIDENCE_GAP annotation; RCS penalty applied]
        |
        v
[Reasoning Builder] (evidence-annotated chain returned)
```

**Design note:** Evidence records are read-only references — the Reasoning Engine never modifies Evidence Engine records. The Evidence Engine remains the single source of truth for evidence.

---

### Pipeline 3: Inference Update Pipeline

**Purpose:** Updates an existing reasoning chain when new evidence or updated hypotheses arrive — without rebuilding from scratch.

**Trigger:** EventBus notification of hypothesis HCS update or new evidence for an active chain

**Flow:**

```
[EventBus] (hypothesis_updated or evidence_updated event)
        |
        v
[Reasoning Chain Manager] (identify affected chains)
        |── chain affected? YES ──────────────────────┐
        |── chain affected? NO (below threshold) ──── v (discard)
        |                                      [Context Manager] (new context)
        v                                             |
[Inference Engine] (partial re-inference — only affected steps)
        |
        v
[Confidence Engine] (RCS recomputed)
        |
        v
[Logic Engine] (re-validate)
        |
        v
[Reasoning Registry] (chain version incremented)
[Reasoning Catalog] (index refreshed)
[Explainability Manager] (explanation refreshed)
[Reasoning Audit Manager] (update event recorded)
```

---

### Pipeline 4: Debate Pipeline

**Purpose:** Orchestrates the full multi-agent debate workflow for a contested reasoning chain.

**Trigger:** Conflict Resolver or Counter Argument Engine flags a chain as CONTESTED

**Flow:**

```
[CONTESTED Chain]
        |
        v
[Multi-Agent Debate Manager] (initialise debate)
        |
        v (assemble debate context)
[Counter Argument Engine] (retrieve or construct best counter)
[Reasoning Catalog] (retrieve related active chains)
[Context Manager] (current context)
        |
        v
[Debate Round 1: Opening Statements]
        |
        v
[Debate Round 2: Evidence Challenge]
        |
        v
[Debate Round 3: Inference Step Challenge]
        |
        v
[Consensus Engine] (Synthesiser role — integrate positions)
        |
        v
[Meta Reasoning Manager] (Meta Judge — evaluate debate quality)
        |
        v (verdict)
[CONFIRMED] ──> [Reasoning Registry] (chain ACTIVE, RCS updated)
[REFINED] ──────> [Reasoning Builder] (reconstruct with refined premises)
[CONTESTED] ────> [Reasoning Registry] (chain remains CONTESTED)
[OVERTURNED] ───> [Reasoning Registry] (chain RETIRED; new chain from winner)
        |
        v
[Reasoning Audit Manager] (debate event recorded)
[Explainability Manager] (debate summary appended to explanation)
```

---

### Pipeline 5: Consensus Update Pipeline

**Purpose:** Updates the consensus position for a subject entity whenever an active chain changes.

**Trigger:** Reasoning Registry change event (chain created, updated, RETIRED, SUPERSEDED)

**Flow:**

```
[Reasoning Registry] (chain lifecycle event)
        |
        v
[Consensus Engine] (query all active chains for subject entity)
        |
        v
[Weighting Engine] (compute current weights per chain)
        |
        v
[Consensus Engine] (recompute weighted consensus position)
        |
        v (new consensus record)
[Reasoning Registry] (consensus record updated)
[EventBus] (consensus_updated event emitted)
[Decision Engine] (notified of consensus update)
```

---

### Pipeline 6: Confidence Update Pipeline

**Purpose:** Updates RCS and conviction score for active chains when the underlying evidence or hypothesis HCS changes.

**Trigger:** Evidence record updated; Hypothesis HCS updated; Debate verdict received

**Flow:**

```
[EventBus] (evidence_updated / hypothesis_hcs_updated / debate_verdict events)
        |
        v
[Confidence Engine] (recompute RCS using updated inputs)
        |
        v
[RCS tier change?]
        |── YES ──> [Reasoning Registry] (tier updated; lifecycle event emitted)
        |── NO ───> [Reasoning Registry] (RCS value updated silently)
        |
        v
[Consensus Engine] (consensus recomputed for affected entities)
[Weighting Engine] (historical performance weights checked)
```

---

### Pipeline 7: Explanation Pipeline

**Purpose:** Generates or refreshes the human-readable explanation for a reasoning chain.

**Trigger:** Chain reaches ACTIVE status; chain updated; explanation explicitly requested

**Flow:**

```
[Chain ACTIVE or updated]
        |
        v
[Explainability Manager] (retrieve chain, inference steps, evidence)
        |
        v
[Counter Argument Engine] (retrieve counter-argument summary if applicable)
[Reasoning Catalog] (retrieve related chains for context)
        |
        v
[Explainability Manager] (construct explanation record)
        |── premise_summary ─────────────> assembled from hypothesis narratives
        |── inference_narrative ─────────> step-by-step reasoning prose
        |── conclusion_statement ────────> formal conclusion
        |── uncertainty_statement ───────> explicit uncertainty quantification
        |── invalidation_conditions ─────> conditions that would overturn
        |── counter_summary ─────────────> best counter-argument summary
        |
        v
[Storage] (explanation record written)
[Reasoning Registry] (chain.explanation_record_id updated)
[EventBus] (explanation_generated event)
```

---

### Pipeline 8: Validation Pipeline

**Purpose:** Full constitutional validation of reasoning chains, run on all chains approaching DEFINITIVE tier.

**Trigger:** Scheduled validation run; RCS crosses STRONG threshold; manual validation request

**Flow:**

```
[Chain approaching STRONG/DEFINITIVE tier]
        |
        v
[Validation Service RS-10]
        |
        v (rule set by governance tier)
[Constitutional Rules RC-A through RC-K applied]
        |
        v (per-rule results)
[PASS] ──────> [Chain confirmed; validation record attached]
[WARN] ──────> [Chain annotated with warnings; RCS capped at STRONG max]
[FAIL] ──────> [Chain downgraded; Reasoning Audit Manager alerted; rebuild required]
        |
        v
[Reasoning Registry] (validation result recorded)
[Reasoning Audit Manager] (validation event recorded)
```

---

### Pipeline 9: Storage and Distribution Pipeline

**Purpose:** Ensures consistent, durable storage of all reasoning chain records and immediate distribution to consumers.

**Flow:**

```
[Completed chain with all records]
        |
        v
[Storage Layer] (primary write: chain + metadata)
        |
        v
[Write confirmation received]
        |
        v (parallel writes)
[Reasoning Registry] (cache updated)
[Reasoning Catalog] (index updated)
[Reasoning Graph] (DAG node added)
        |
        v
[EventBus] (chain_created/chain_updated event)
        |
        v (fan-out to subscribers)
[Decision Engine] ──── (new chain available)
[Streamlit Dashboard] ─ (dashboard refresh)
[Telegram Bot] ──────── (notification if significant chain)
[Learning System] ───── (performance tracking)
[Knowledge Engine] ─── (chain stored for future reference)
```

---

### Pipeline 10: Recursive Reasoning Pipeline

**Purpose:** Manages the controlled execution of recursive reasoning — where chain output becomes input for the next cycle.

**Trigger:** Recursive Reasoning Manager identifies a chain marked for recursive update

**Flow:**

```
[Reasoning Chain C1 (ACTIVE, marked for recursive update)]
        |
        v
[Recursive Reasoning Manager] (check depth, termination conditions)
        |── depth limit reached ──> [HALT; chain annotated with RECURSION_LIMIT]
        |── convergence met ──────> [HALT; chain confirmed as converged]
        |── continue ─────────────────────────────────────────────────────┐
        |                                                                  v
        |                                                    [Hypothesis Intake]
        |                                                    (C1 conclusion treated
        |                                                     as premise for C2)
        |                                                          |
        |                                                    [Hypothesis-to-Reasoning
        |                                                         Pipeline (C2)]
        |                                                          |
        |                                                    [C2 conclusion vs C1]
        |                                                          |
        |                                                    [Delta computation]
        |                                                          |
        |                                              delta < threshold ──> CONVERGED
        |                                              delta >= threshold ──> recurse
        |
        v
[Reasoning Chain Manager] (C1 superseded by C2; lineage updated)
[Recursive Reasoning Manager] (recursion summary recorded)
```

---
## PART VII — QUALITY FRAMEWORK

### 7.1 Overview

The Reasoning Confidence Score (RCS) is the primary quality metric of the Reasoning Engine. Every active reasoning chain carries an RCS in the range [0.0, 1.0]. The RCS integrates 12 quality dimensions into a single composite score.

---

### 7.2 The 12 Quality Dimensions

#### QD-01: Logical Validity

**Definition:** The degree to which each inference step follows validly from its premises, given the declared reasoning type and inference rules.

**Measurement:** Average inference step validity score across all steps in the chain.

**Weight in RCS:** 0.20 (highest weight — logical validity is the foundation of reasoning quality)

**Degradation triggers:**
- Logical fallacy detected in any step → -0.05 per fallacy
- Invalid inference rule for declared type → -0.10
- Circular argument detected → -0.20 (hard floor applied)

---

#### QD-02: Evidence Coverage

**Definition:** The breadth and quality of evidence underlying the reasoning chain premises.

**Measurement:** Weighted average of Evidence Confidence Scores (ECS) from the Evidence Engine for all evidence referenced by the hypothesis premises.

**Weight in RCS:** 0.18

**Degradation triggers:**
- EVIDENCE_GAP on any inference step → -0.05 per gap
- All premises rely on a single evidence source → -0.08 (concentration penalty)
- Evidence staleness (evidence > 24h old for intraday chains) → -0.05

---

#### QD-03: Internal Consistency

**Definition:** The absence of logical contradictions within a single reasoning chain — no premise contradicts another premise within the same chain.

**Measurement:** Binary metric (consistent = 1.0; inconsistency detected = 0.0) modified by severity.

**Weight in RCS:** 0.15

**Degradation triggers:**
- Minor inconsistency (directional disagreement between premises) → 0.50
- Major inconsistency (directly contradictory premises) → 0.00 (chain invalid; rebuild required)

---

#### QD-04: Completeness

**Definition:** The degree to which the reasoning chain addresses all material analytical considerations relevant to its subject and domain.

**Measurement:** Completeness checklist score — fraction of required analytical dimensions covered given the subject domain.

**Weight in RCS:** 0.10

**Required dimensions by domain:**
- EQUITY_TREND: [Technical analysis, Volume analysis, Sector context, Macro backdrop, Fundamental support]
- MACRO_REGIME: [Rate environment, Inflation trajectory, Growth outlook, Liquidity conditions, Policy direction]
- SECTOR_THESIS: [Fundamental drivers, Valuation context, Earnings momentum, Competitive dynamics, Regulatory context]

---

#### QD-05: Coherence

**Definition:** The degree to which the conclusion is proportionate to and logically consistent with the premises — no inferential leaps, no conclusions stronger than the premises support.

**Measurement:** Coherence score computed by Logic Engine — compares conclusion strength to inference step validity aggregate.

**Weight in RCS:** 0.08

**Degradation triggers:**
- Conclusion stronger than premises support → -0.10 per magnitude unit of excess
- Missing step between premises and conclusion (inferential gap) → -0.08

---

#### QD-06: Explainability

**Definition:** The degree to which the reasoning chain can be fully explained in human-comprehensible language — every step traceable, every premise named, every conclusion justified.

**Measurement:** Explainability checklist — all required explanation record fields populated and non-empty.

**Weight in RCS:** 0.08

**Constitutional constraint:** Chains lacking a complete explanation record cannot achieve DEFINITIVE tier (RC-C-001).

---

#### QD-07: Traceability

**Definition:** The degree to which the full ancestry of a reasoning chain can be traced — from conclusion back through inference steps to hypotheses to evidence to raw observations.

**Measurement:** Lineage completeness score — fraction of ancestry links present and valid.

**Weight in RCS:** 0.07

**Degradation triggers:**
- Missing hypothesis pointer → -0.05
- Missing evidence pointer from hypothesis → -0.04
- Missing observation pointer from evidence → -0.03

---

#### QD-08: Confidence Calibration

**Definition:** The historical accuracy of the confidence tier assigned to similar chains — DEFINITIVE-tier chains should historically be correct at a higher rate than STRONG-tier chains.

**Measurement:** Learning System provides calibration score per tier per domain per reasoning type. Chains in well-calibrated domains score higher; poorly calibrated domains penalised.

**Weight in RCS:** 0.06

**Note:** For new reasoning types with no historical record, calibration score defaults to 0.50 (neutral); explicit uncertainty annotation required.

---

#### QD-09: Robustness

**Definition:** The stability of the conclusion under reasonable variations in the premises — if one premise is weakened, does the conclusion still hold?

**Measurement:** Robustness test: for each premise, reduce its HCS by 0.20 and recompute chain validity. Robustness score = fraction of single-premise reductions that do not overturn the conclusion.

**Weight in RCS:** 0.04

---

#### QD-10: Temporal Stability

**Definition:** The persistence of the conclusion over the intended analytical timeframe — the conclusion should not oscillate materially within its declared timeframe window.

**Measurement:** Temporal stability score — variance of RCS over the most recent 10 update cycles for the same chain.

**Weight in RCS:** 0.02

**Degradation triggers:**
- High variance (std_dev > 0.15 over 10 cycles) → -0.05

---

#### QD-11: Conflict Resolution Quality

**Definition:** The quality and completeness of conflict resolution — contested chains that have been properly debated and resolved score higher than chains with unresolved conflicts.

**Measurement:** NONE conflict → full score (1.0); MINOR resolved → 0.90; MODERATE resolved → 0.80; MAJOR resolved → 0.70; CONTESTED unresolved → 0.50.

**Weight in RCS:** 0.01

---

#### QD-12: Transparency

**Definition:** The degree to which all assumptions, limitations, and failure conditions are explicitly stated in the chain record.

**Measurement:** Transparency checklist — key assumptions populated, invalidation conditions stated, meta_assessment completed.

**Weight in RCS:** 0.01

---

### 7.3 RCS Formula Reference

$$RCS = \sum_{d=1}^{12} w_d \cdot Q_d - \sum_{p} penalty_p$$

Subject to:
- $RCS \in [0.00, 1.00]$
- $\sum_{d=1}^{12} w_d = 1.00$
- Fallacy penalty: each detected fallacy subtracts 0.05 from RCS
- Major inconsistency hard floor: RCS ≤ 0.20 if QD-03 = 0.00

---

### 7.4 Quality Monitoring

| Metric | Alert threshold | Action |
|---|---|---|
| Average active chain RCS < 0.55 | Daily avg drops below | Meta Reasoning Manager review |
| Fraction of DEFINITIVE chains < 5% of active | Sustained 5+ cycles | Confidence calibration review |
| Fraction of CONTESTED > 30% | Single cycle | Conflict Resolver health check |
| Average debate resolution rate < 70% | Weekly avg | Debate quality review |
| Evidence gap rate > 20% | Daily avg | Evidence Engine data quality check |
| Explanation missing rate > 5% | Daily count | Explainability Manager health check |

---

## PART VIII — GOVERNANCE

### 8.1 Governance Tiers

| Tier | Definition | Examples |
|---|---|---|
| CRITICAL | Reasoning chains that could inform risk halt or governance protocol triggers | RSK domain chains, RBI policy chains, crisis-regime chains |
| HIGH | Chains informing core analytical positions on major indices | NIFTY/BANKNIFTY reasoning chains, sector thesis chains |
| MEDIUM | Chains informing individual equity or derivative analytical positions | Mid/small-cap equity chains, standard derivative chains |
| LOW | Exploratory or research-grade chains not actively used by Decision Engine | Research chains, exploratory analytical chains |

---

### 8.2 Governance Matrix

| Dimension | CRITICAL | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| Debate required | Always | STRONG+ tier | DEFINITIVE tier only | Never mandatory |
| Constitutional check | Full (all rules) | Full | Abbreviated | Key rules only |
| RCS minimum to publish | 0.50 | 0.40 | 0.30 | No minimum |
| Retention period | Permanent | 10 years | 5 years | 3 years |
| Explainability required | Always | Always | Yes | Best effort |
| Audit record | Immutable | Immutable | Standard | Standard |
| Review cycle | Intraday | Daily | Weekly | Monthly |

---

### 8.3 Domain Ownership

| Domain | Owner | Review authority |
|---|---|---|
| Index reasoning (NIFTY, BANKNIFTY) | Market Intelligence Domain | MasterOrchestrator |
| Risk domain reasoning | Risk Control Engine | RiskGuardian |
| Macro domain reasoning | Global Intelligence Domain | MasterOrchestrator |
| Sector domain reasoning | Market Intelligence Domain | MasterOrchestrator |
| Individual equity reasoning | Opportunity Engine | MasterOrchestrator |
| Derivative reasoning | Options Engine | Opportunity Engine |

---

### 8.4 Security and Confidentiality

Reasoning chains contain sensitive market analytical positions. The following controls apply:

| Control | Implementation |
|---|---|
| Access control | Service mesh authentication; no external access |
| Encryption at rest | AES-256 for all persisted reasoning records |
| Encryption in transit | TLS 1.3 for all inter-service communication |
| Audit log integrity | Cryptographic hash chain for audit records |
| Input validation | All hypothesis bundle inputs schema-validated before processing |
| Rate limiting | Maximum 1,000 InferenceService calls per minute |
| Dependency isolation | Reasoning Engine cannot call Execution Engine directly |

---

### 8.5 Review Cycle

| Tier | Review type | Frequency |
|---|---|---|
| CRITICAL | RCS and conflict status review | Per cycle (intraday) |
| HIGH | Reasoning chain validity review | Daily |
| MEDIUM | Sample review | Weekly |
| LOW | Archival review | Monthly |
| All | Meta Reasoning quality report | Daily |
| All | Confidence calibration review | Weekly |

---
## PART IX — CONSTITUTION

The Reasoning Engine Constitution defines the non-negotiable rules governing every reasoning chain produced by the IIOS. Constitutional rules are permanent, system-level constraints that cannot be overridden by any individual component or configuration change.

Constitutional rules are coded as: **RC-{Category}-{Number}**

---

### Category RC-A: Logical Integrity

**RC-A-001** Every reasoning chain must have at least one inference step. Chains with zero inference steps are invalid and must not reach ACTIVE status.

**RC-A-002** Every inference step must reference at least one premise. Inference steps without premises (unsupported conclusions) are prohibited.

**RC-A-003** The declared reasoning type must be compatible with the inference rules applied. A chain declared as DEDUCTIVE must apply only deductive inference rules to core steps.

**RC-A-004** Logical fallacies detected by the Inference Engine are blocking defects for DEFINITIVE-tier chains. A DEFINITIVE chain with a detected logical fallacy must be downgraded to STRONG at maximum.

**RC-A-005** The conclusion of a reasoning chain must follow from the inference steps. No chain may claim a conclusion stronger than the sum of its premises and inference steps supports.

**RC-A-006** All deductive chains must be checked for modus ponens or modus tollens validity before ACTIVE status is granted.

**RC-A-007** The Reasoning Graph must be a directed acyclic graph at all times. The detection of a cycle in the Reasoning Graph is a P0 alert and must result in immediate flagging of all involved chains as CONTESTED.

**RC-A-008** Dependency chains must not exceed depth 5. A reasoning chain that is 6 or more hops dependent on a base conclusion is invalid and must not be constructed.

**RC-A-009** Recursive reasoning must not exceed depth 3. The Recursive Reasoning Manager must enforce this as a hard ceiling.

**RC-A-010** No reasoning chain may reference its own conclusion as a premise (immediate circularity). This is detected by the Logic Engine and is a permanent blocking defect.

---

### Category RC-B: Evidence Integrity

**RC-B-001** Every reasoning chain must trace to at least one piece of supporting evidence. Reasoning chains built entirely on assertion without evidence are prohibited.

**RC-B-002** Evidence used in reasoning chains must have a valid Evidence Confidence Score (ECS) greater than 0.30. Evidence below this threshold may not be used as a primary premise.

**RC-B-003** Evidence timestamps must be consistent with the reasoning chain timestamp. Evidence dated after the reasoning chain construction timestamp may not be used (temporal anachronism is prohibited).

**RC-B-004** DEFINITIVE-tier reasoning chains must reference at least two independent evidence records. Single-evidence DEFINITIVE chains are not permitted.

**RC-B-005** Evidence records referenced by reasoning chains are immutable from the Reasoning Engine perspective. The Reasoning Engine must not modify, update, or delete Evidence Engine records.

**RC-B-006** If an evidence record is subsequently invalidated by the Evidence Engine, any reasoning chain that used it as a primary premise must be re-evaluated within one processing cycle.

**RC-B-007** Evidence concentration: no DEFINITIVE chain may have more than 60% of its evidence weight from a single data source. Concentration above this limit requires a MODERATE or lower tier.

---

### Category RC-C: Explainability

**RC-C-001** Every ACTIVE reasoning chain must have a complete explanation record. Chains with missing explanation records must not be delivered to the Decision Engine.

**RC-C-002** The explanation record must include: premise summary, inference narrative, conclusion statement, uncertainty statement, key assumptions, and invalidation conditions. All fields are required.

**RC-C-003** Explanation records must be refreshed within one processing cycle of any chain update. Stale explanations (not refreshed after update) are a governance violation.

**RC-C-004** The uncertainty statement must explicitly quantify what is uncertain. A statement that says only "there is uncertainty" without specifying the nature or magnitude of the uncertainty is insufficient.

**RC-C-005** The invalidation conditions must specify at least two concrete conditions that would overturn the conclusion. Generic or vacuous invalidation conditions are prohibited.

**RC-C-006** DEFINITIVE-tier chains must have explanations reviewed by the Meta Reasoning Manager before delivery to the Decision Engine. The Meta Reasoning Manager review is not optional.

---

### Category RC-D: Traceability

**RC-D-001** Every reasoning chain must have a complete lineage record: hypothesis_ids → evidence_ids → observation_ids. Missing lineage records are a constitutional violation.

**RC-D-002** The Reasoning Engine must support point-in-time reconstruction of its state at any historical timestamp. This requires that all state transitions are recorded with UTC timestamps in the audit log.

**RC-D-003** Every reasoning chain version must be preserved. No version of a reasoning chain may be deleted. Superseded versions are archived, not removed.

**RC-D-004** The lineage record must survive chain supersession. When a chain is superseded, the new chain must reference both its own lineage and the lineage of the superseded chain.

**RC-D-005** The Reasoning Audit Manager must record every state transition with: actor, timestamp, previous state, new state, and reason for change. Audit records may not be amended after creation.

---

### Category RC-E: Consistency

**RC-E-001** The Reasoning Engine must not hold two ACTIVE DEFINITIVE chains for the same subject entity with directly contradictory conclusions at the same time. If two such chains exist, at least one must be moved to CONTESTED status immediately.

**RC-E-002** Chains that are logically inconsistent must not both be ACTIVE at STRONG tier or above for the same subject. The Conflict Resolver must detect and resolve this.

**RC-E-003** When a chain is superseded, all chains that used the superseded chain as a dependency must be re-evaluated within one processing cycle.

**RC-E-004** Consensus records must be consistent with the underlying active chains. A consensus record that does not reflect the current distribution of active chain conclusions is a constitutional violation.

**RC-E-005** RCS tier consistency: the RCS value and the RCS tier must be consistent. A chain with RCS = 0.90 must not be tagged as MODERATE. The Confidence Engine must enforce this.

---

### Category RC-F: Transparency

**RC-F-001** No reasoning chain may contain hidden premises. All premises must be explicitly listed in the reasoning chain schema.

**RC-F-002** The reasoning type must be explicitly declared in every chain. Chains with type = UNKNOWN are not permitted to reach ACTIVE status.

**RC-F-003** All weights used in the RCS computation must be documented in the chain record. The RCS must be reproducible from the documented weights and quality dimension scores.

**RC-F-004** If a reasoning chain uses AI-generated inference steps (is_ai_generated = True), this must be explicitly disclosed in the chain record and in the explanation record.

**RC-F-005** The context record used during chain construction must be permanently attached to the chain. The context at time of construction must never be retroactively modified.

**RC-F-006** Conviction score methodology must be documented in the chain meta_assessment. Anonymous conviction scores (scores with no documented calculation basis) are not permitted for STRONG or DEFINITIVE tiers.

---

### Category RC-G: Conflict Handling

**RC-G-001** All MODERATE or MAJOR conflicts must trigger the Debate Pipeline. Conflict severity >= MODERATE cannot be resolved without debate.

**RC-G-002** Debate verdicts must be applied to chain status within one processing cycle of the debate completing. Delayed application of debate verdicts is a governance violation.

**RC-G-003** OVERTURNED chains must be immediately RETIRED. An OVERTURNED chain must not remain ACTIVE.

**RC-G-004** The counter-argument record must be preserved for all chains where a counter-argument was constructed, regardless of whether it triggered a debate.

**RC-G-005** A CONTESTED chain must not be delivered to the Decision Engine as a primary high-conviction analytical input. A CONTESTED chain may be delivered as context only, with explicit CONTESTED annotation.

**RC-G-006** No chain may be forcibly confirmed by overriding a CONTESTED status without completing the Debate Pipeline. Manual status overrides that bypass the debate process are prohibited.

---

### Category RC-H: Governance

**RC-H-001** Every reasoning chain must be assigned a governance tier (CRITICAL/HIGH/MEDIUM/LOW) before reaching ACTIVE status.

**RC-H-002** CRITICAL-tier chains must receive a full constitutional check before reaching ACTIVE status. Abbreviated validation is not permitted for CRITICAL chains.

**RC-H-003** Domain ownership must be assigned to every ACTIVE reasoning chain. Unowned chains must not be delivered to the Decision Engine.

**RC-H-004** Retention periods must be enforced. No chain below the governance-tier retention period may be permanently deleted. Deletion of chains within retention period is a constitutional violation.

**RC-H-005** The Reasoning Engine must produce a daily governance summary report. This report must include: active chain count by tier, contested chain count, debate activity, constitutional violations detected.

**RC-H-006** Any constitutional violation must be recorded in the Reasoning Audit Manager within one processing cycle of detection. Violations must not be silently suppressed.

---

### Category RC-I: Auditability

**RC-I-001** The audit log is append-only. No audit record may be modified or deleted after creation.

**RC-I-002** Every inference step construction event must be recorded in the audit log. There must be no gap in the audit trail for any chain that reaches ACTIVE status.

**RC-I-003** Audit records must be cryptographically signed. Any tampering with an audit record must be detectable via the cryptographic hash chain.

**RC-I-004** The audit trail must support full point-in-time reconstruction. Given any historical timestamp, the Reasoning Audit Manager must be able to reconstruct the exact state of the Reasoning Registry.

**RC-I-005** Audit records must be stored in a physically separate storage location from the primary Reasoning Registry. A single storage failure must not destroy both operational data and audit trail simultaneously.

---

### Category RC-J: Historical Preservation

**RC-J-001** Every reasoning chain ever constructed must be preserved in the archive indefinitely (CRITICAL/HIGH tiers) or for the governance-tier retention period (MEDIUM/LOW tiers).

**RC-J-002** Archived chains must be readable in full by the Learning System for performance attribution without any data loss or degradation.

**RC-J-003** Chain versioning must be complete. Every version of every chain that ever existed must be retrievable by version number.

**RC-J-004** The archive must survive system reboots, deployments, and schema migrations. The archive is not ephemeral and must not be in-memory only.

---

### Category RC-K: Quality

**RC-K-001** The minimum acceptable RCS for a chain delivered to the Decision Engine as a primary input is 0.40 (TENTATIVE tier minimum). Chains below this threshold may only be provided as background context.

**RC-K-002** The average RCS of the active chain pool must not fall below 0.45 for more than three consecutive processing cycles. A sustained drop below this level must trigger a Meta Reasoning Manager quality review.

**RC-K-003** DEFINITIVE-tier chains must not be assigned unless the chain has passed all of: logic validation (VALID), full constitutional check (PASS), debate if contested, complete explanation record, and Meta Reasoning Manager review.

**RC-K-004** The Reasoning Engine must maintain at least 3 distinct reasoning types active for any subject entity where a DEFINITIVE-tier chain is present. Single-type reasoning monoculture is prohibited for DEFINITIVE-tier conclusions.

**RC-K-005** All DEFINITIVE-tier chains must include a documented robustness test result. Chains that have not been robustness-tested may not exceed STRONG tier.

---
## PART X — READINESS CHECKLIST

Before a reasoning chain is delivered to the Decision Engine as a primary analytical input, it must pass the following 14-section readiness checklist. This checklist is enforced by the Validation Service (RS-10) and the Reasoning Audit Manager.

---

### 10.1 Reasoning Chain Complete

| Check | Required condition | Status field |
|---|---|---|
| RC-COMPLETE-001 | reasoning_id populated and globally unique | PASS / FAIL |
| RC-COMPLETE-002 | reasoning_type declared and valid | PASS / FAIL |
| RC-COMPLETE-003 | At least 1 inference step present | PASS / FAIL |
| RC-COMPLETE-004 | All inference steps have step_validity_score assigned | PASS / FAIL |
| RC-COMPLETE-005 | conclusion field populated (non-empty) | PASS / FAIL |
| RC-COMPLETE-006 | conclusion_structured field populated and schema-valid | PASS / FAIL |
| RC-COMPLETE-007 | context_record attached | PASS / FAIL |
| RC-COMPLETE-008 | All required schema fields populated (per Part II schema) | PASS / FAIL |

**Minimum to proceed:** All 8 items PASS

---

### 10.2 Evidence Linked

| Check | Required condition |
|---|---|
| RC-EVD-001 | At least 1 evidence record linked via hypothesis premises |
| RC-EVD-002 | No evidence record with ECS < 0.30 used as primary premise |
| RC-EVD-003 | Evidence timestamps consistent with reasoning timestamp |
| RC-EVD-004 | DEFINITIVE chains have >= 2 independent evidence records |
| RC-EVD-005 | No EVIDENCE_GAP flags on primary inference steps |

**Minimum to proceed:** RC-EVD-001, RC-EVD-002, RC-EVD-003 must all PASS. RC-EVD-004 required for DEFINITIVE tier only.

---

### 10.3 Hypotheses Evaluated

| Check | Required condition |
|---|---|
| RC-HYP-001 | All premise hypotheses have status VALIDATED |
| RC-HYP-002 | All premise hypotheses have HCS >= 0.30 |
| RC-HYP-003 | premise_hypothesis_ids list is non-empty |
| RC-HYP-004 | Hypothesis Engine lineage record present |

**Minimum to proceed:** All 4 PASS

---

### 10.4 Logic Validated

| Check | Required condition |
|---|---|
| RC-LGC-001 | Logic Engine verdict = VALID or MINOR_DEFECT |
| RC-LGC-002 | No logical fallacies in primary inference steps (for DEFINITIVE tier) |
| RC-LGC-003 | Inference rules consistent with declared reasoning type |
| RC-LGC-004 | No circular argument detected |
| RC-LGC-005 | Conclusion strength proportionate to premises |

**Minimum to proceed:** RC-LGC-001 required (MAJOR_DEFECT blocks). RC-LGC-002 required for DEFINITIVE only.

---

### 10.5 Conflicts Resolved

| Check | Required condition |
|---|---|
| RC-CNF-001 | Conflict Resolver has run for this chain |
| RC-CNF-002 | conflict_status field populated |
| RC-CNF-003 | If conflict_status = MODERATE/MAJOR, debate has been completed |
| RC-CNF-004 | No unresolved MAJOR conflict |
| RC-CNF-005 | CONTESTED chains annotated with CONTESTED status in chain record |

**Minimum to proceed:** All 5 PASS

---

### 10.6 Consensus Achieved

| Check | Required condition |
|---|---|
| RC-CNS-001 | Consensus Engine has processed this chain |
| RC-CNS-002 | consensus_record_id populated if consensus record exists |
| RC-CNS-003 | Chain contribution to consensus weighted correctly |

**Minimum to proceed:** RC-CNS-001 PASS

---

### 10.7 Confidence Assigned

| Check | Required condition |
|---|---|
| RC-CONF-001 | rcs field populated (non-null, non-zero) |
| RC-CONF-002 | rcs_tier field assigned and consistent with rcs value |
| RC-CONF-003 | conviction_score populated |
| RC-CONF-004 | uncertainty_score = 1 - conviction_score |
| RC-CONF-005 | RCS meets minimum for governance tier |

**Minimum to proceed:** All 5 PASS

---

### 10.8 Explanation Generated

| Check | Required condition |
|---|---|
| RC-EXPL-001 | explanation_record_id populated and valid |
| RC-EXPL-002 | premise_summary non-empty |
| RC-EXPL-003 | inference_narrative non-empty |
| RC-EXPL-004 | conclusion_statement non-empty |
| RC-EXPL-005 | uncertainty_statement non-empty and specific |
| RC-EXPL-006 | invalidation_conditions contains >= 2 conditions |
| RC-EXPL-007 | Explanation version matches current chain version |

**Minimum to proceed:** All 7 PASS

---

### 10.9 Traceable

| Check | Required condition |
|---|---|
| RC-TRC-001 | lineage_record_id populated and valid |
| RC-TRC-002 | Lineage traces: chain → hypotheses → evidence → observations |
| RC-TRC-003 | Full chain version history accessible |
| RC-TRC-004 | Reasoning Graph contains node for this chain |

**Minimum to proceed:** RC-TRC-001, RC-TRC-002 required

---

### 10.10 Governed

| Check | Required condition |
|---|---|
| RC-GOV-001 | governance_tier assigned |
| RC-GOV-002 | domain_owner populated |
| RC-GOV-003 | Governance tier consistent with subject domain |
| RC-GOV-004 | CRITICAL chains: full constitutional check completed |

**Minimum to proceed:** RC-GOV-001, RC-GOV-002 required

---

### 10.11 Audited

| Check | Required condition |
|---|---|
| RC-AUD-001 | audit_trail_id populated and valid |
| RC-AUD-002 | At least one CREATE event in audit trail |
| RC-AUD-003 | All state transitions recorded in audit trail |

**Minimum to proceed:** All 3 PASS

---

### 10.12 Archived (conditional)

| Check | Required condition |
|---|---|
| RC-ARC-001 | For RETIRED/SUPERSEDED chains: archive record confirmed |
| RC-ARC-002 | For ARCHIVED chains: archive is complete and readable |

**Minimum to proceed:** Required only for RETIRED/SUPERSEDED/ARCHIVED status

---

### 10.13 Counter-Arguments Considered

| Check | Required condition |
|---|---|
| RC-CA-001 | Counter Argument Engine has processed chain (for STRONG/DEFINITIVE) |
| RC-CA-002 | counter_argument_ids field populated (if CA constructed) |
| RC-CA-003 | If CA_STRENGTH >= 0.65: chain is CONTESTED (not ACTIVE) |
| RC-CA-004 | Counter-argument preserved in archive regardless of outcome |

**Minimum to proceed:** RC-CA-001, RC-CA-003 required for STRONG/DEFINITIVE tiers

---

### 10.14 Ready for Decision Engine

| Check | Required condition |
|---|---|
| RC-DE-001 | lifecycle_status = ACTIVE |
| RC-DE-002 | RCS >= 0.40 |
| RC-DE-003 | Explanation complete (all fields) |
| RC-DE-004 | Conflict status resolved |
| RC-DE-005 | No unresolved constitutional violations |
| RC-DE-006 | domain_owner and governance_tier assigned |
| RC-DE-007 | For CONTESTED chains: explicit CONTESTED annotation in delivery payload |
| RC-DE-008 | Chain not expired: reasoning_timestamp within declared timeframe window |

**Minimum to proceed:** All 8 PASS (RC-DE-007 applies only to CONTESTED chains, relaxed for non-contested)

---

### 10.15 Use-Case Readiness Matrix

| Use Case | Minimum RCS | Debate required | Counter-argument required | Full explanation required |
|---|---|---|---|---|
| Decision Engine primary input | 0.40 (TENTATIVE) | If CONTESTED | If STRONG+ | Yes |
| Decision Engine DEFINITIVE input | 0.85 (DEFINITIVE) | Always | Always | Yes |
| Dashboard display | 0.30 | No | No | Summary |
| Telegram notification | 0.55 (MODERATE) | No | No | Summary |
| Learning System training | No minimum | No | No | No |
| Research and exploration | No minimum | No | No | No |

---
## SUPPLEMENT A — REASONING TAXONOMY REFERENCE

This supplement provides the complete reference table for all 23 reasoning types, including category codes, type codes, evidence requirements, minimum confidence thresholds, and applicable domains.

---

### A.1 Taxonomy Reference Table

| # | Category | CAT Code | Example Type Codes | Min Evidence | Min HCS for Premises | Applicable Domains | Key Inference Rules |
|---|---|---|---|---|---|---|---|
| 1 | Deductive | DED | DED-RISK, DED-RULE, DED-CONSTRAINT | 1 direct | 0.50 | Risk, Governance, Rule-based | Modus Ponens, Modus Tollens |
| 2 | Inductive | IND | IND-HISTORICAL, IND-PATTERN, IND-STATISTICAL | 3+ historical | 0.40 | Technical, Historical analysis | Statistical generalisation |
| 3 | Abductive | ABD | ABD-BEST-EXPLAIN, ABD-COMPARATIVE | 2+ competing | 0.40 | Multi-hypothesis subjects | Explanatory coherence scoring |
| 4 | Probabilistic | PRB | PRB-DISTRIBUTION, PRB-WEIGHTING | 2+ sources | 0.35 | All domains | Probability weighting |
| 5 | Bayesian | BAY | BAY-PRIOR-UPDATE, BAY-POSTERIOR | 1 prior + 1 new | 0.35 | All domains | Bayesian update |
| 6 | Causal | CAU | CAU-DIRECT, CAU-SECOND-ORDER | 1 causal direction | 0.50 | Macro, Event, Sector | DAG causal inference |
| 7 | Temporal | TMP | TMP-MOMENTUM, TMP-DURATION | 5+ time-series points | 0.35 | Technical, Macro | Temporal pattern matching |
| 8 | Cross-Market | XMK | XMK-CONTAGION, XMK-LEAD-LAG | 2+ market evidence | 0.40 | Global, Index | Correlation/lead-lag analysis |
| 9 | Cross-Asset | XAS | XAS-RISK-OFF, XAS-INFLATION | 3+ asset class evidence | 0.40 | Macro, Portfolio | Asset class regime inference |
| 10 | Portfolio | PRT | PRT-ATTRIBUTION, PRT-FACTOR | Portfolio state data | 0.40 | Portfolio | Attribution analysis |
| 11 | Macro | MAC | MAC-RATES, MAC-GROWTH, MAC-POLICY | 2+ macro indicators | 0.40 | Macro, Regime | Macro regime inference |
| 12 | Fundamental | FND | FND-VALUATION, FND-EARNINGS | Fundamental data | 0.45 | Equity, Sector | Valuation model |
| 13 | Technical | TEC | TEC-TREND, TEC-MOMENTUM | 10+ price bars | 0.35 | Equity, Index | Pattern recognition |
| 14 | Behavioral | BEH | BEH-SENTIMENT, BEH-CONTRARIAN | Sentiment data | 0.35 | Equity, Index | Sentiment extreme rules |
| 15 | Event | EVT | EVT-CORPORATE, EVT-MACRO | Event record | 0.45 | Corporate, Macro | Event impact inference |
| 16 | Relationship | REL | REL-CORRELATION, REL-SPREAD | 2+ entity data | 0.40 | Cross-entity | Relationship analysis |
| 17 | Risk | RSK | RSK-TAIL, RSK-DRAWDOWN | Risk metrics | 0.40 | Risk, Portfolio | Risk rule inference |
| 18 | Contrarian | CTR | CTR-BEAR, CTR-MEAN-REV | Counter evidence | 0.35 | Any | Inversion + evidence search |
| 19 | Consensus | CNS | CNS-TECHNICAL-FUNDAMENTAL | Multiple chain types | 0.40 | Any | Weighted consensus |
| 20 | AI Collaborative | AIC | AIC-DEBATE, AIC-SYNTHESIS | Multi-agent output | 0.40 | Any | Debate synthesis |
| 21 | Hybrid | HYB | HYB-ABD-CAU, HYB-MULTI-TYPE | Combined requirements | Max of component types | Any | Combined rule set |
| 22 | Recursive | REC | REC-UPDATE, REC-REFINE | Prior cycle output | Same as base type | Any | Prior cycle as premise |
| 23 | Meta | MET | MET-QUALITY, MET-CALIBRATION | Chain quality metrics | 0.40 | Meta / Quality | Quality assessment rules |

---

### A.2 Type Selection Matrix

When the Reasoning Builder receives a hypothesis bundle, it uses the following type selection criteria:

| Hypothesis category (from HE) | Hypothesis type | Recommended reasoning type | Alternative type |
|---|---|---|---|
| TECHNICAL | PRICE_MOMENTUM | TEC | IND |
| TECHNICAL | STRUCTURE_BREAKOUT | TEC | ABD |
| FUNDAMENTAL | VALUATION | FND | PRB |
| FUNDAMENTAL | EARNINGS_SURPRISE | FND + EVT | ABD |
| MACRO | RATE_ENVIRONMENT | MAC | CAU |
| MACRO | REGIME_TRANSITION | MAC | BAY |
| SECTOR | ROTATION | XAS | ABD |
| EVENT | CORPORATE_ANNOUNCEMENT | EVT | DED |
| RISK | PORTFOLIO_DRAWDOWN | RSK | DED |
| SENTIMENT | EXTREME_FEAR | BEH | CTR |
| SENTIMENT | EXTREME_GREED | BEH | CTR |
| CROSS_MARKET | GLOBAL_CORRELATION | XMK | XAS |
| CROSS_ASSET | RISK_OFF_SIGNAL | XAS | MAC |
| MULTI_HYPOTHESIS | COMPETING | ABD | CNS |
| MULTI_HYPOTHESIS | CUMULATIVE | CNS | HYB |

---

### A.3 RCS Thresholds by Reasoning Type

Some reasoning types have inherently higher or lower achievable RCS due to the nature of their inference rules:

| Reasoning Type | Maximum achievable RCS | Reason |
|---|---|---|
| Deductive | 1.00 | Perfect deduction possible in constrained domains |
| Bayesian | 0.95 | Limited by prior reliability |
| Causal | 0.90 | Causal identification is difficult; uncertainty floor |
| Inductive | 0.85 | Sample limitations; non-stationarity |
| Abductive | 0.82 | Best-explanation selection; alternative explanations |
| Probabilistic | 0.90 | Well-calibrated probabilities achievable |
| Fundamental | 0.88 | Data quality and model uncertainty |
| Technical | 0.85 | Pattern-based; inherent false-positive rate |
| Macro | 0.88 | Economic relationships are imprecise |
| Behavioral | 0.80 | Sentiment is inherently noisy |
| Meta | 0.90 | Quality assessment; calibrated by design |
| Contrarian | 0.75 | Contrarian by construction; minority position |

---

## SUPPLEMENT B — LOGIC REFERENCE

This supplement provides the formal logic reference used by the Inference Engine (Part III Cluster 2).

---

### B.1 Core Inference Rules

#### B.1.1 Modus Ponens (MP)

**Structure:**
- Premise 1: If P then Q (P → Q)
- Premise 2: P
- Conclusion: Q

**IIOS application:** Used when a known causal relationship (P → Q) and a confirmed antecedent (P) allow deduction of the consequent (Q).

**Example:**
- Rule: If RBI hikes rates, then bond yields rise (R → B)
- Fact: RBI has hiked rates (R confirmed)
- Conclusion: Bond yields are rising (B)

---

#### B.1.2 Modus Tollens (MT)

**Structure:**
- Premise 1: If P then Q (P → Q)
- Premise 2: Not Q
- Conclusion: Not P

**IIOS application:** Used when the expected consequent of a hypothesis is not observed, providing evidence against the hypothesis.

**Example:**
- Rule: If bull market, then breadth > 60% (B → D)
- Observation: Breadth = 35% (not D)
- Conclusion: Not in bull market (not B)

---

#### B.1.3 Hypothetical Syllogism (HS)

**Structure:**
- Premise 1: P → Q
- Premise 2: Q → R
- Conclusion: P → R

**IIOS application:** Constructs multi-step causal chains.

**Example:**
- If RBI hikes → bond yields rise
- If bond yields rise → equity risk premium increases
- Conclusion: If RBI hikes → equity risk premium increases

---

#### B.1.4 Disjunctive Syllogism (DS)

**Structure:**
- Premise 1: P or Q
- Premise 2: Not P
- Conclusion: Q

**IIOS application:** When two exhaustive hypotheses are active and one is ruled out, the other is confirmed.

---

#### B.1.5 Conjunction (CONJ)

**Structure:**
- Premise 1: P
- Premise 2: Q
- Conclusion: P and Q

**IIOS application:** Multiple independent pieces of evidence all confirming the same direction — conjunctive reinforcement.

---

#### B.1.6 Abductive Best Explanation (ABE)

**Structure:**
- Observation: O
- H1 explains O better than H2, H3, ..., Hn
- Conclusion: H1 is the best current explanation of O (subject to revision)

**IIOS application:** Core selection rule for abductive reasoning.

---

#### B.1.7 Bayesian Update (BU)

**Structure:**
- Prior: P(H) — prior probability of hypothesis H
- Likelihood: P(E|H) — probability of evidence E given H is true
- Evidence: P(E) — marginal probability of evidence
- Posterior: P(H|E) = P(E|H) * P(H) / P(E)

**IIOS application:** Conviction score update rule. Each new piece of evidence updates the conviction score.

---

### B.2 Logical Fallacies Detected by Inference Engine

| Fallacy | Code | Description | Detection method |
|---|---|---|---|
| Affirming the Consequent | FAL-01 | Concluding P from P→Q and Q | Structural check on modus ponens misuse |
| Denying the Antecedent | FAL-02 | Concluding Not Q from P→Q and Not P | Structural check on MT misuse |
| Circular Argument | FAL-03 | Conclusion appears in premises | Graph cycle detection |
| Post Hoc | FAL-04 | Temporal sequence confused with causation | Causal rule validator |
| Base Rate Neglect | FAL-05 | Ignoring prior probability in Bayesian context | Bayesian chain prior check |
| Small Sample | FAL-06 | Inductive generalisation from n < 5 | Sample size validator |
| Correlation-Causation | FAL-07 | Treating correlation as causal without mechanism | Causal chain structure check |
| Survivor Bias | FAL-08 | Historical analysis using only surviving instances | Dataset provenance check |
| Straw Man | FAL-09 | Counter-argument attacks weakened version of hypothesis | CA quality validator |
| False Dichotomy | FAL-10 | Only two options when more exist | Hypothesis completeness check |

**Penalty per detected fallacy:** -0.05 from RCS (capped at -0.30 total fallacy penalty)
**Blocking threshold:** 3 or more fallacies in primary inference steps → chain cannot exceed MODERATE tier

---

### B.3 Logical Validity Conditions by Reasoning Type

| Reasoning Type | Validity condition |
|---|---|
| DEDUCTIVE | All premises true AND inference rule correctly applied → conclusion necessarily true |
| INDUCTIVE | Premises representative AND sample adequate AND pattern significant → conclusion probable |
| ABDUCTIVE | No better explanation available than the selected one → conclusion is best current explanation |
| PROBABILISTIC | All probability estimates within [0,1] AND conditional independence assumptions met → conclusions valid |
| BAYESIAN | Prior is justified AND likelihood function is specified AND base rate included → posterior valid |
| CAUSAL | Causal direction established (not just correlation) AND mechanism specified → chain valid |

---
## SUPPLEMENT C — INFERENCE PATTERNS

This supplement provides four detailed worked inference pattern examples showing how the Inference Engine constructs reasoning chains for representative IIOS use cases.

---

### C.1 Pattern 1: NIFTY Bull Trend Confirmation (Abductive + Technical)

**Subject entity:** NIFTY 50 Index
**Reasoning type:** HYB-ABD-TEC (Hybrid: Abductive + Technical)
**Governance tier:** HIGH

**Active hypotheses received:**
- H-TEC-TREND-001 (HCS 0.82): NIFTY is in a confirmed uptrend — price above 20/50/200 DMA, all moving averages aligned upward
- H-TEC-MOMENTUM-002 (HCS 0.76): RSI 14d = 64, positive momentum without overbought condition
- H-BEH-SENTIMENT-003 (HCS 0.58): Retail sentiment modestly bullish; institutional positioning neutral-to-long

**Three competing explanations:**
- E1: Genuine bull trend — trend will continue
- E2: Momentum trap — trend is exhausted; will reverse
- E3: Choppy range — false breakout; will revert to range

**Inference chain:**

Step 1 (ABE): Evaluate explanatory coherence.
- E1 (Genuine bull): consistent with H-TEC-TREND-001 (confirmed moving average alignment) + H-TEC-MOMENTUM-002 (strong but not overbought). Coherence = HIGH.
- E2 (Momentum trap): inconsistent with H-TEC-TREND-001; RSI 64 is not overbought territory (overbought = 70+). Coherence = LOW.
- E3 (Range): inconsistent with H-TEC-TREND-001 (confirmed breakout). Coherence = LOW.
- Best explanation: E1 (Genuine bull trend)
- Step validity: 0.82

Step 2 (TEC-STRUCT): Structural confirmation. NIFTY making higher highs and higher lows over the past 20 trading sessions (confirmed from price bars).
- Step validity: 0.85

Step 3 (IND-HISTORICAL): Historical base rate. In the last 5 occurrences where NIFTY was in confirmed triple-MA alignment with RSI 60–70, trend continued for >= 15 trading sessions in 4 of 5 cases (80% base rate).
- Step validity: 0.78

Step 4 (BEH-CONTEXT): Sentiment is not at extreme bullish reading (no contrarian trigger). Neutral-to-long institutional positioning is consistent with continuing uptrend rather than reversal signal.
- Step validity: 0.72

**Conclusion:** NIFTY is in a high-probability bull trend continuation phase, supported by technical structure, momentum condition, and historical precedent. Conclusion confidence is 78%.

**RCS computation:**
- QD-01 (Logic): average step validity = (0.82 + 0.85 + 0.78 + 0.72) / 4 = 0.7925
- QD-02 (Evidence): 3 independent hypotheses with HCS >= 0.58 → coverage = 0.82
- QD-03 (Consistency): all hypotheses directionally consistent → 1.00
- No fallacies; no conflicts
- **RCS = 0.80 (STRONG tier)**

---

### C.2 Pattern 2: RBI Rate Hike Impact Chain (Causal + Macro)

**Subject entity:** Indian Equity Market / Fixed Income
**Reasoning type:** CAU-SECOND-ORDER (Causal, second-order)
**Governance tier:** CRITICAL

**Premise hypotheses:**
- H-MAC-RATES-001 (HCS 0.90): RBI has hiked the repo rate by 25 bps — confirmed from official announcement
- H-MAC-INFLATION-002 (HCS 0.85): CPI inflation at 6.2%, above target — this was the catalyst for the hike
- H-FND-EARNINGS-003 (HCS 0.68): Corporate debt financing costs will rise for highly leveraged companies

**Inference chain:**

Step 1 (Modus Ponens — DED): If repo rate rises, then 10-year G-Sec yield rises (historical transmission rule, confirmed relationship).
- Premise 1: Repo rate has risen (H-MAC-RATES-001, HCS 0.90) — confirmed.
- Conclusion: 10-year G-Sec yield expected to rise within 1–3 sessions.
- Step validity: 0.88

Step 2 (CAU-SECOND-ORDER — causal chain): Rising 10-year yield → increases equity risk premium → compresses P/E multiples → disproportionately affects growth/tech sector (high duration equities).
- Causal mechanism: Higher risk-free rate → higher required return on equity → lower justified P/E.
- Historical confirmation: Every RBI rate hike cycle since 2010 has been associated with Nifty IT sector underperformance relative to NIFTY within 5 sessions (7 of 8 occurrences).
- Step validity: 0.82

Step 3 (FND — fundamental impact): Highly leveraged companies (D/E > 1.5x) face direct earnings per share compression from higher interest expense.
- Supporting evidence: H-FND-EARNINGS-003 (HCS 0.68).
- Impact: 100 bps increase in cost of debt → ~8% compression in EPS for median highly-leveraged mid-cap.
- Step validity: 0.72

Step 4 (ABD — net assessment): Best current explanation for expected equity market direction: mild negative for broad market (via risk premium channel), strongly negative for IT/growth (via duration channel), moderately negative for leveraged mid-caps (via earnings channel). Banking sector ambiguous — NIMs may improve.
- Step validity: 0.76

**Conclusion:** RBI rate hike creates a structured headwind for equity markets via three channels: P/E compression (broad), earnings erosion (leveraged), and sector rotation away from high-duration IT/growth. Conviction: moderate-to-high given confirmed rate action.

**RCS: 0.82 (STRONG approaching DEFINITIVE threshold)**

---

### C.3 Pattern 3: Bayesian Conviction Update (Bayesian)

**Scenario:** An existing ACTIVE reasoning chain has prior conviction score 0.62 for "BANKNIFTY bearish bias next 5 sessions". New evidence arrives: FII data shows net buying of 1,200 crore in bank stocks today (unexpected).

**Existing chain:**
- Chain ID: RSN-BAY-IND-20260703-00000042
- Prior conviction: 0.62 (bearish)
- Basis: credit spread widening, RSI divergence, weak breadth in banking

**New evidence:**
- E-NEW: FII net buy 1,200 crore in banking sector
- This evidence is bullish (contradicts current bearish conviction)
- Evidence strength: E-strength = 0.70 (significant FII buy size vs historical distribution)

**Bayesian update inference:**

Step 1: Compute likelihood ratio.
- P(FII_NET_BUY | BEARISH) = 0.20 (FII buying in bearish periods — historically 20% of sessions)
- P(FII_NET_BUY | BULLISH) = 0.65 (FII buying in bullish periods — historically 65% of sessions)
- Likelihood ratio = P(E|BULLISH) / P(E|BEARISH) = 0.65 / 0.20 = 3.25

Step 2: Compute updated odds.
- Prior odds (BEARISH vs BULLISH) = 0.62 / 0.38 = 1.63
- Posterior odds = prior odds × (1 / likelihood ratio) = 1.63 / 3.25 = 0.50
- Posterior P(BEARISH) = 0.50 / (1 + 0.50) = 0.33

Step 3: New conviction score.
- Updated bearish conviction: 0.33 (was 0.62)
- Equivalent: chain is no longer bearish conviction; direction becomes AMBIGUOUS

**Inference step validity:** 0.85 (formal Bayesian update from documented priors)

**Chain update:** The chain is updated to MODERATE RCS with CONTESTED status. Consensus Engine is notified. Decision Engine receives updated conviction score.

---

### C.4 Pattern 4: Meta-Reasoning Quality Assessment

**Scenario:** The Meta Reasoning Manager performs its daily quality assessment of the active reasoning chain pool.

**Active chain pool state:**
- 47 active chains total
- 31 chains covering NIFTY or BANKNIFTY (66% concentration on two entities)
- 38 chains are BULLISH conclusion (81% directional skew)
- Only 3 chains are DEFINITIVE tier
- Average RCS: 0.61
- Debate completion rate: 45% (target: 80% for STRONG+ chains)

**Meta reasoning inference:**

Step 1 (MET-QUALITY): Entity concentration assessment.
- 66% of chains on 2 entities; constitutional rule RC-K-004 requires type diversity but not entity diversity limits.
- Assessment: No violation, but flag for awareness. Concentration indicates narrow analytical scope.
- Meta finding: CONCENTRATION_MODERATE

Step 2 (MET-CONFIDENCE-CALIBRATION): Directional skew assessment.
- 81% bullish; Market is in BULL_TREND regime.
- Historical calibration: In BULL_TREND regimes, 75–85% bullish skew is normal.
- Assessment: Skew is within expected range for current regime.
- Meta finding: DIRECTIONAL_SKEW_ACCEPTABLE

Step 3 (MET-QUALITY): Debate completion gap.
- 45% debate completion vs 80% target for STRONG+ chains.
- This is a quality gap — many STRONG chains have not been debated.
- Constitutional implication: RC-C-006 requires DEFINITIVE chains to pass Meta review; none of the 3 DEFINITIVE chains have passed debate.
- Meta finding: DEBATE_BACKLOG_CRITICAL

Step 4 (MET-QUALITY): RCS distribution.
- Average RCS 0.61 is acceptable (above RC-K-002 minimum 0.45).
- But zero DEFINITIVE-tier chains with debate completion — DEFINITIVE chains were assigned without debate.
- **Constitutional violation: RC-K-003** — DEFINITIVE chains must have passed debate.

**Meta reasoning conclusion:** Active chain pool is healthy in directional calibration and average RCS. CRITICAL quality gap: debate completion rate below threshold; three DEFINITIVE chains assigned without required debate. Immediate remediation required.

**Action triggered:** Reasoning Audit Manager records RC-K-003 violation; Multi-Agent Debate Manager immediately queued for all three DEFINITIVE chains; RCS of those chains temporarily capped at STRONG (0.84) pending debate completion.

---
## SUPPLEMENT D — MULTI-AGENT DEBATE EXAMPLES

This supplement provides three detailed multi-agent debate examples, illustrating how the Multi-Agent Debate Manager orchestrates structured disagreement.

---

### D.1 Debate Example 1: NIFTY Directional Disagreement

**Debate trigger:** Conflict Resolver detected MAJOR conflict between:
- Chain A (RSN-TEC-TREND-20260703-00000088, RCS 0.82): "NIFTY is in bull trend continuation; target 24,500 within 5 sessions"
- Chain B (RSN-TEC-STRUCTURE-20260703-00000091, RCS 0.75): "NIFTY showing distribution; reversal risk high in next 5 sessions"

**Debate context:** Current NIFTY = 24,100. VIX = 14.5 (low). FII recent data: mild net buying.

---

**Round 1 — Opening Statements**

Proposer (Chain A advocate): The trend is confirmed by triple moving average alignment, positive RSI without overbought condition, and 12 consecutive sessions of higher highs. The analytical weight of confirmed trend evidence is higher than pattern-based distribution concern. Bull trend continuation is the primary thesis.

Challenger (Chain B advocate): Distribution pattern signals institutional selling into strength. Volume has been declining on up days for the past 6 sessions (supply drying up). The last 3 sessions show wicks at the top (intraday rejection). These are classic distribution characteristics that precede reversals.

---

**Round 2 — Evidence Challenge**

Proposer evidence:
- E1: 20/50/200 DMA alignment (ECS 0.88) — strongest technical confirmation signal
- E2: RSI 14d = 63 (ECS 0.80) — momentum intact
- E3: FII net buying 3 of last 5 sessions (ECS 0.72) — institutional support
- Counter to declining volume: volume decline on up moves is expected in mature bull trends (not exclusively distribution)

Challenger evidence:
- E4: Volume declining on up days for 6 consecutive sessions (ECS 0.78) — textbook distribution
- E5: Intraday upper wicks on 3 of last 3 sessions (ECS 0.74) — intraday rejection
- E6: Advance-decline breadth declining for 4 sessions despite NIFTY making new highs (ECS 0.82) — divergence
- Counter to FII buying: FII data is aggregated; underlying stock-level FII activity shows selling in heavyweights with buying in small-caps (low quality bid)

---

**Round 3 — Inference Step Challenge**

Challenger attacks Chain A Step 2: "Moving average alignment confirms trend" — the challenge is that moving average alignment is a lagging indicator. It confirms the past, not the future. The distribution evidence is leading.

Proposer response: Moving average alignment is not just a trend-confirming indicator; it also measures the alignment of different market participants (short-term, medium-term, long-term). When all three are aligned, it indicates broad-based participation — not just short-term momentum.

Challenger attacks Chain A Step 3 (inductive base rate): "80% historical base rate for trend continuation" — the 5-occurrence sample is very small. A single outlier reversal would reduce the base rate to 67%. This is a SMALL_SAMPLE fallacy concern.

Proposer response: Accepts the small sample limitation. Annotates Step 3 with FAL-06 concern. Adjusts step validity from 0.78 to 0.68.

---

**Round 4 — Synthesis (Synthesiser role)**

**Areas of agreement:**
- NIFTY is currently in an uptrend (DMA alignment is real)
- Volume and breadth dynamics are showing signs of fatigue
- Short-term direction is genuinely ambiguous

**Integration:**
- The bull trend thesis is analytically valid for the medium term (5–15 sessions)
- The distribution thesis raises legitimate near-term caution (1–3 sessions)
- These are not fully contradictory — they speak to different timeframes

**Synthesised position:** Bull trend remains structurally intact; near-term risk of consolidation or mild pullback elevated due to distribution signals; conviction for aggressive upside is lowered.

---

**Round 5 — Meta Judge Assessment**

- Debate quality: HIGH. Both sides presented evidence of quality ECS >= 0.72.
- Chain A has a noted small-sample fallacy (FAL-06 acknowledged). Step 3 validity reduced.
- Chain B evidence on breadth divergence (E6, ECS 0.82) is compelling and not refuted.

**Verdict: REFINED**

Chain A updated: conclusion refined from "strong bull continuation" to "bull trend intact; near-term elevated consolidation risk". RCS updated: 0.78 (was 0.82, reduced for acknowledged fallacy).

Chain B: remains active as CONTESTED complement to Chain A. Status updated to ACTIVE (not RETIRED) — it represents a legitimate near-term concern.

---

### D.2 Debate Example 2: Macro Regime Disagreement

**Debate trigger:** Counter Argument Engine produced CA_STRENGTH = 0.72 against:
- Chain C (RSN-MAC-REGIME-20260703-00000105, RCS 0.86 DEFINITIVE): "India macro environment entering an inflationary regime"

**Counter-argument constructed by CAE:**
- CA-001: RBI forward guidance explicitly states "transient" inflation; policy response calibrated for temporary shock
- CA-002: Commodity prices (crude oil) have moderated in the past 3 weeks — reducing imported inflation pressure
- CA-003: Core inflation (ex-food-fuel) has been stable for 6 months — the headline spike is food-driven

---

**Round 1 — Opening**

Proposer (Chain C): CPI printed 6.2% — above RBI 6% tolerance ceiling. M2 money supply growth is running at 12% YoY. Real interest rates are negative (-0.8%). These are the structural conditions of an inflationary regime, irrespective of RBI rhetoric.

Challenger (CA-001/002/003): The inflation is supply-side, not demand-pull. Commodity moderation is beginning. Core inflation stable. RBI has demonstrated credibility in anchoring expectations. This is a temporary inflation shock, not a regime.

---

**Round 2 — Evidence Challenge**

Proposer evidence:
- E1: CPI 6.2% (ECS 0.95) — government data
- E2: M2 growth 12% (ECS 0.88)
- E3: Real rate = -0.8% (ECS 0.90)
- E4: WPI (wholesale price index) 9.5% — upstream inflation feeding into CPI pipeline

Challenger evidence:
- CA-E1: 3-week commodity moderation (Brent crude -8% from peak, ECS 0.80)
- CA-E2: Core CPI (ex food-fuel) 4.8% — within RBI comfort zone (ECS 0.88)
- CA-E3: 1-year breakeven inflation rate = 5.4% — market expects inflation to moderate (ECS 0.76)

---

**Round 3 — Inference Challenge**

Challenger attacks: The "inflationary regime" definition requires sustained broad-based inflation. Current data shows one category (food) driving the headline. The regime threshold is not met.

Proposer response: WPI at 9.5% indicates broad pipeline pressure — it will feed into CPI with a 3–6 month lag. This is not a one-category shock. The regime is early-stage.

---

**Synthesis:**

Both sides have well-grounded positions. The disagreement is fundamentally about regime classification threshold and persistence expectations. Core inflation data supports challenger. WPI pipeline data supports proposer.

**Meta Judge:** This is a genuinely contested analytical question. Both chains are well-evidenced. No fallacies detected.

**Verdict: CONTESTED**

Both Chain C and the counter-argument remain ACTIVE. Chain C status updated to CONTESTED. Decision Engine receives both positions with explicit uncertainty annotation. Conviction score for Chain C: reduced from 0.86 to 0.70. Uncertainty explicitly flagged.

---

### D.3 Debate Example 3: Cross-Asset Signal

**Trigger:** Conflict Resolver detected MODERATE conflict.
- Chain D: "Risk-off signal: gold rising, equities falling, bonds rallying — flight to safety confirmed" (RCS 0.79)
- Chain E: "Equity decline is sector rotation, not systemic risk-off — banking and IT selling while consumption holds" (RCS 0.72)

**Synthesiser-only debate (abbreviated — no full opening rounds needed for MODERATE):**

Chain D evidence: Gold +2.3% (ECS 0.88); NIFTY -1.2% (ECS 0.90); 10yr G-Sec yield -8bps (ECS 0.87).

Chain E evidence: Consumption sector +0.8% while NIFTY -1.2% (ECS 0.82); Midcap index -0.3% vs largecap -1.4% (ECS 0.80); No significant FII selling in consumption names.

**Synthesiser assessment:** Both are consistent with the data but speak to different analytical framings. Risk-off (Chain D) vs rotation (Chain E) can both be partially true simultaneously — the system is experiencing sector rotation but with gold rising, the complete picture includes a systemic caution element.

**Verdict: REFINED (for both)**

Chain D refined: "Mild systemic caution signal — gold and bond move consistent with risk-off; equity decline is partially systemic and partially rotation."

Chain E refined: "Sector rotation is the dominant equity dynamic; systemic risk element cannot be dismissed."

Both chains ACTIVE with revised RCS (Chain D: 0.76; Chain E: 0.74). Consensus record updated to reflect blended position.

---
## SUPPLEMENT E — REASONING GRAPHS

This supplement shows three representative reasoning graphs as ASCII diagrams, illustrating how the Reasoning Graph component structures multi-chain analytical reasoning.

---

### E.1 Reasoning Graph 1: NIFTY Bull Trend DAG

This graph shows the full reasoning chain for a NIFTY bull trend conclusion, including all nodes and edge types.

```
[OBS-PRICE-001]          [OBS-VOL-002]           [OBS-ADV-003]
(Price bars: 20 days)    (Volume data: 20 days)  (Advance-Decline: 20d)
      |                        |                        |
      v SUPPORTS               v SUPPORTS               v SUPPORTS
[EVD-TREND-001]          [EVD-VOL-TREND-002]     [EVD-BREADTH-003]
(Triple DMA alignment)   (Volume on up days)     (Breadth 67%)
ECS=0.88                 ECS=0.72                ECS=0.79
      |                        |                        |
      v PREMISE_OF              v PREMISE_OF             v PREMISE_OF
      +------------------------+-----------------------+
                               |
                               v
                   [HYP-TEC-TREND-001]
                   (NIFTY confirmed uptrend)
                   HCS = 0.82
                               |
      +------------------------+-----------------------+
      |                        |                        |
      v PREMISE_OF              v PREMISE_OF             v PREMISE_OF
[HYP-TEC-MOM-002]      [HYP-BEH-SENT-003]      [HYP-IND-HIST-004]
(Momentum intact)      (Sentiment neutral-bull) (Historical base rate)
HCS=0.76               HCS=0.58                 HCS=0.72
      |                        |                        |
      +------------------------+-----------------------+
                               |
                               v
                  [RSN-HYB-ABD-TEC-001]
                  (NIFTY Bull Trend Chain)
                  RCS=0.80 STRONG ACTIVE
                               |
                    +----------+---------+
                    |                    |
                    v CONCLUSION_OF      v CONTESTED_BY
              [CONCL-BULL-001]     [CNT-DIST-001]
              (Bull continuation)  (Distribution counter)
              Conv=0.75            CA_STRENGTH=0.52
                    |
                    v
              [Decision Engine input]
```

---

### E.2 Reasoning Graph 2: Multi-Chain Consensus DAG for BANKNIFTY

This graph shows multiple chains for the same subject entity (BANKNIFTY) being synthesised into a consensus.

```
[Macro Evidence]    [Technical Evidence]    [Fundamental Evidence]
     |                     |                       |
     v                     v                       v
[HYP-MAC-RATES]    [HYP-TEC-BANK]          [HYP-FND-NIM]
(Rate hike)        (Double top pattern)    (NIM expansion)
HCS=0.90           HCS=0.74                HCS=0.70
     |                     |                       |
     v                     v                       v
[RSN-CAU-MAC-001]  [RSN-TEC-BANK-002]      [RSN-FND-BANK-003]
(Rate headwind)    (Distribution signal)   (NIM positive)
RCS=0.82 STRONG    RCS=0.75 STRONG         RCS=0.71 MODERATE
     |                     |                       |
     +---------------------+-----------------------+
                           |
                           v
                  [Consensus Engine]
                  Weighted synthesis:
                  RSN-CAU weight: 0.45
                  RSN-TEC weight: 0.35
                  RSN-FND weight: 0.20
                           |
                           v
                  [CONS-BANK-001]
                  Consensus: BANKNIFTY bearish-to-neutral
                  Consensus RCS = 0.77
                  Entropy = 0.34 (moderately contested)
                  Contributing chains: 3
                  Dissenting: RSN-FND (bullish, 20% weight)
                           |
                           v
                  [Decision Engine]
                  (Delivered with dissent annotation)
```

---

### E.3 Reasoning Graph 3: Recursive Reasoning Update Cycle

This graph shows the evolution of a reasoning chain across two recursive cycles.

```
CYCLE 1:
[HYP-MAC-INFLATION-001]      [HYP-XAS-COMMODITY-002]
(CPI 6.2%)                   (Crude oil +12%)
HCS=0.90                     HCS=0.82
     |                              |
     +------------------------------+
                    |
                    v
         [RSN-MAC-REGIME-001-v1]
         (Inflationary regime: early)
         RCS=0.78 STRONG
         Conviction=0.72
                    |
                    | (new evidence: crude moderation)
                    v
         [RECURSIVE REASONING TRIGGER]
         (Recursive Reasoning Manager)
         Depth: 1; Max: 3

CYCLE 2:
[HYP-MAC-INFLATION-001]      [HYP-XAS-COMMODITY-003]
(CPI 6.2% — unchanged)       (Crude oil now -8% from peak)
HCS=0.90                     HCS=0.80
     |                              |
     +------------------------------+
                    |
                    v (Bayesian update: crude moderation
                       reduces inflationary conviction)
         [RSN-MAC-REGIME-001-v2]
         (Inflationary regime: weakening)
         RCS=0.72 STRONG (was 0.78)
         Conviction=0.56 (was 0.72)
         Delta = |0.56 - 0.72| = 0.16 > threshold (0.02)
                    |
                    | (delta > threshold: another cycle needed?)
                    | no: depth=2, economic significance checked
                    | convergence direction: declining conviction
                    | trend is clear: CONVERGING toward resolution
                    | HALT at depth=2; mark as CONVERGED
                    v

         [RSN-MAC-REGIME-001-v1] ──> SUPERSEDED
         [RSN-MAC-REGIME-001-v2] ──> ACTIVE
         Lineage: v2 DEPENDENT_ON v1 (preserved)
```

---

## SUPPLEMENT F — ANTI-PATTERNS

This supplement documents 10 reasoning anti-patterns — systematic mistakes in reasoning chain construction that reduce quality and should be detected and prevented.

---

### AP-01: Single-Evidence Overconfidence

**Anti-pattern:** A reasoning chain achieves DEFINITIVE tier based on a single, very strong piece of evidence, ignoring contradictory signals.

**Example:** Chain assigned RCS 0.88 (DEFINITIVE) based solely on a high-HCS macro hypothesis, with no technical, fundamental, or sentiment confirmation.

**Why it fails:** Single evidence concentration violates RC-B-004 and RC-K-004 (type diversity). A single source of evidence, however strong, cannot provide the diverse confirmation required for DEFINITIVE status.

**Detection:** Evidence concentration check in Evidence Mapping Pipeline. RC-B-007 enforcement (max 60% single-source).

**Remediation:** Downgrade to STRONG; require additional independent evidence types before DEFINITIVE can be assigned.

---

### AP-02: Lagging Indicator Overweight

**Anti-pattern:** The reasoning chain assigns excessive weight to lagging indicators (moving averages, EMA crossovers, historical baselines) while ignoring leading indicators (breadth, sentiment extremes, flow data).

**Why it fails:** Lagging indicators confirm the past but have limited predictive value. A chain built primarily on lagging indicators provides low analytical value for the Decision Engine.

**Detection:** Evidence source type check — if > 70% of evidence is from lagging indicators, flag for review.

**Remediation:** Require at least one leading indicator evidence source for chains in the STRONG/DEFINITIVE tier.

---

### AP-03: Regime Blindness

**Anti-pattern:** A reasoning chain constructed in a BULL_TREND regime is applied unchanged in a CRISIS or BEAR_TREND regime.

**Why it fails:** Most analytical relationships change across regimes. A technical trend signal valid in BULL_TREND has significantly different reliability in BEAR_TREND.

**Detection:** Context Manager tracks regime at construction time. If current regime differs from construction-time regime, chain receives CONTEXT_STALE_REGIME flag.

**Remediation:** Regime-mismatch chains automatically demoted by one RCS tier. Rebuild required for DEFINITIVE chains.

---

### AP-04: Confirmation Bias Chain

**Anti-pattern:** All evidence, hypotheses, and inference steps selected to confirm a pre-formed conclusion. Counter-evidence systematically excluded from consideration.

**Why it fails:** RC-F-001 prohibits hidden premises. A chain that only considers confirming evidence is analytically invalid regardless of its stated RCS.

**Detection:** Counter Argument Engine detects when significant counter-evidence exists but is absent from the chain. Reasoning Audit Manager flags asymmetric evidence selection.

**Remediation:** Counter-argument construction mandatory for STRONG+ chains. Explicit counter-evidence reference required in evidence mapping.

---

### AP-05: Precision Illusion

**Anti-pattern:** RCS stated as 0.8234 implying precision that the underlying quality dimensions cannot support.

**Why it fails:** Quality dimension scores are estimates. Reporting RCS to 4 decimal places implies measurement precision that does not exist and misleads consumers.

**Remediation:** RCS reported to 2 decimal places. Tier (STRONG/MODERATE etc.) is the primary communication vehicle.

---

### AP-06: Dependency Cascade Blindness

**Anti-pattern:** A chain is constructed that depends 4 levels deep on another chain, without the chain author being aware of this upstream dependency.

**Why it fails:** A change in the depth-1 chain can cascade through 4 levels, suddenly changing the dependent chain status without any direct trigger on the dependent chain.

**Detection:** Dependency Manager enforces max depth 5 (RC-A-008). Chains approaching depth 4+ receive a DEEP_DEPENDENCY warning annotation.

**Remediation:** Deep dependency chains should be rebuilt to reference primary evidence directly where possible, rather than through 4 intermediate chains.

---

### AP-07: Temporal Mismatch

**Anti-pattern:** A chain built on intraday evidence is used to justify a multi-week analytical conclusion, or vice versa.

**Why it fails:** Different timeframes have different analytical properties. Intraday breadth data is too noisy to anchor multi-week conclusions.

**Detection:** Context Manager checks temporal consistency between evidence timestamps and declared chain timeframe.

**Remediation:** Evidence timestamps must be consistent with chain declared timeframe. Mismatched timeframe evidence flagged as EVIDENCE_TIMEFRAME_MISMATCH.

---

### AP-08: Zombie Chain

**Anti-pattern:** A reasoning chain remains ACTIVE long after the evidence and hypotheses that supported it have been superseded or invalidated.

**Why it fails:** Zombie chains deliver stale analytical conclusions to the Decision Engine. This is directly prohibited by RC-E-003 and RC-B-006.

**Detection:** Reasoning Chain Manager monitors hypothesis status changes. When a premise hypothesis is retired, the dependent chain is automatically flagged for re-evaluation.

**Remediation:** Automated re-evaluation triggered within one cycle. If re-evaluation produces RCS < 0.30, chain is immediately RETIRED.

---

### AP-09: Debate Avoidance

**Anti-pattern:** A chain is systematically kept below the RCS threshold that would trigger mandatory debate, even though its analytical implications are significant.

**Why it fails:** The debate requirement exists to challenge reasoning chains. Avoiding debate by calibrating RCS to just below the threshold defeats this purpose.

**Detection:** Meta Reasoning Manager monitors chains that have been near the STRONG threshold for 5+ cycles without crossing it.

**Remediation:** Meta Reasoning Manager can escalate a chain to mandatory debate review regardless of RCS if it determines the chain is analytically significant enough to require challenge.

---

### AP-10: False Precision in Conviction Scores

**Anti-pattern:** Conviction scores are updated too frequently (every cycle) based on very small evidence changes, creating the impression of precision while actually introducing noise.

**Why it fails:** Bayesian updating on very small evidence shifts produces micro-updates that are below the measurement threshold of the underlying evidence quality.

**Detection:** Confidence Engine tracks conviction update history. If conviction has changed by < 0.02 in the last 10 updates, the chain is classified as STABLE_CONVICTION.

**Remediation:** For STABLE_CONVICTION chains, conviction updates are batched and applied only when cumulative update >= 0.05.

---
## SUPPLEMENT G — OPERATIONAL RUNBOOK

This runbook defines startup, shutdown, and recovery procedures for the Reasoning Engine in production.

---

### G.1 Pre-Start Checklist

Before the Reasoning Engine is started, all of the following conditions must be verified:

| Step | Check | Action if failed |
|---|---|---|
| G-PRE-01 | Storage layer accessible and responsive | Block start; alert |
| G-PRE-02 | Reasoning Registry writable | Block start; alert |
| G-PRE-03 | Reasoning Catalog index intact | Rebuild index then start |
| G-PRE-04 | Reasoning Graph DAG loads without cycles | Alert; quarantine cyclic nodes; start with warning |
| G-PRE-05 | Audit log writable | Block start; audit is mandatory |
| G-PRE-06 | Hypothesis Engine reachable | Start in degraded mode; buffer hypothesis intake |
| G-PRE-07 | EventBus reachable | Block start; downstream distribution requires EventBus |
| G-PRE-08 | Context Service has current market context (< 10 min old) | Start with CONTEXT_STALE flag; alert |
| G-PRE-09 | Weighting Engine has current regime weights | Load last known weights; alert if > 24h old |
| G-PRE-10 | Last known state snapshot accessible | Load from checkpoint; alert if checkpoint > 1h old |

---

### G.2 Startup Sequence (24 steps)

**Step 1:** Load constitutional rules (all RC-A through RC-K categories) from configuration store.

**Step 2:** Load governance tier definitions and domain ownership mapping.

**Step 3:** Connect to storage layer. Verify read/write capability.

**Step 4:** Load Reasoning Registry from storage. Deserialise all ACTIVE and CONTESTED chains into in-memory registry.

**Step 5:** Verify chain count matches last known checkpoint. Alert on discrepancy > 5%.

**Step 6:** Build Reasoning Graph DAG from loaded chains. Run cycle detection. Quarantine any cyclic nodes.

**Step 7:** Load Reasoning Catalog indexes. Verify index freshness against chain timestamps.

**Step 8:** Load Weighting Engine regime weights and historical performance weights.

**Step 9:** Connect to Context Service. Capture current market context.

**Step 10:** Connect to Hypothesis Engine intake channel. Begin buffering any incoming hypothesis bundles.

**Step 11:** Start Reasoning Audit Manager. Verify audit log connectivity and hash chain integrity.

**Step 12:** Start Inference Engine. Run self-test: execute one synthetic inference chain. Verify output.

**Step 13:** Start Logic Engine. Run self-test: validate one known-valid chain, one known-invalid chain. Verify correct verdicts.

**Step 14:** Start Confidence Engine. Run self-test: compute RCS for one synthetic chain. Verify result within expected range.

**Step 15:** Start Counter Argument Engine. Run self-test.

**Step 16:** Start Conflict Resolver. Run self-test.

**Step 17:** Start Multi-Agent Debate Manager. Verify debate role agents are available.

**Step 18:** Start Consensus Engine and Weighting Engine.

**Step 19:** Start Explainability Manager. Verify NLG capability.

**Step 20:** Start Meta Reasoning Manager.

**Step 21:** Start Recursive Reasoning Manager.

**Step 22:** Connect to EventBus. Subscribe to required event types: hypothesis_validated, hypothesis_updated, evidence_updated, hypothesis_retired.

**Step 23:** Process any buffered hypothesis intake (accumulated during startup).

**Step 24:** Emit health check event. Mark Reasoning Engine status = HEALTHY. Log startup banner:

```
=== REASONING ENGINE STARTED ===
Time:            {UTC timestamp}
Active chains:   {count}
Contested:       {count}
Registry status: HEALTHY
Services ready:  14 of 14
Constitution:    {total rules} rules loaded
```

---

### G.3 Graceful Shutdown Sequence

**Step 1:** Stop accepting new hypothesis intake. Return HTTP 503 on new inference requests.

**Step 2:** Allow all in-flight inference chains (Stage 1–9 of lifecycle) to complete. Maximum wait: 30 seconds.

**Step 3:** Complete any in-progress debates. Maximum wait: 60 seconds.

**Step 4:** Flush Reasoning Registry to storage. Verify write completion.

**Step 5:** Flush Reasoning Catalog index to storage.

**Step 6:** Save Reasoning Graph checkpoint.

**Step 7:** Write final audit log entries: shutdown event for each component.

**Step 8:** Close EventBus connections.

**Step 9:** Close storage connections.

**Step 10:** Log shutdown banner:

```
=== REASONING ENGINE SHUTDOWN ===
Time:               {UTC timestamp}
Final active chains:{count}
Final contested:    {count}
Chains in-flight:   {count} (completed/abandoned)
Pending debates:    {count} (completed/abandoned)
Shutdown reason:    GRACEFUL / SIGTERM / SIGINT
```

---

### G.4 Recovery Procedures

#### G.4.1 Recovery After Unexpected Termination

**Detection:** Missing shutdown banner in log; stale checkpoint timestamp.

**Steps:**
1. Load last successful checkpoint. Identify gap between checkpoint and expected current state.
2. Replay EventBus event log from checkpoint timestamp to now. Reconstruct any missed hypothesis intakes.
3. Re-evaluate all chains that were FORMING at time of shutdown (incomplete chains may have partial state).
4. Run Reasoning Audit Manager reconciliation: verify audit trail is complete up to checkpoint.
5. Run Conflict Resolver full scan on all active chains (new evidence may have arrived during downtime).
6. Resume normal operations.

**Expected recovery time:** < 5 minutes for < 1 hour downtime.

---

#### G.4.2 Recovery from Reasoning Registry Corruption

**Detection:** Checksum mismatch on registry load; unexpected chain count.

**Steps:**
1. Stop all reads from corrupted registry.
2. Load last verified archive snapshot.
3. Replay change events from EventBus log since snapshot.
4. Validate restored registry against audit trail.
5. Flag any chains that cannot be fully reconstructed as CONTESTED (manual review required).
6. Resume with restored registry.

---

#### G.4.3 Recovery from Reasoning Graph Cycle Detection

**Detection:** Cycle check during startup or during chain construction.

**Steps:**
1. Identify all chains involved in the cycle (cycle membership).
2. Move all involved chains to CONTESTED.
3. Suspend Dependency Manager updates for involved chains.
4. Alert Reasoning Audit Manager (RC-A-007 constitutional violation).
5. Manually review: identify which chain introduced the cycle (newest chain).
6. RETIRE the offending chain. Break the cycle.
7. Resume Dependency Manager. Re-run cycle check.

---

#### G.4.4 Recovery from Debate Manager Failure

**Detection:** Debate queue growing; debates not completing.

**Steps:**
1. Capture current debate queue state.
2. Restart Multi-Agent Debate Manager component only (other components unaffected).
3. Re-queue pending debates.
4. CONTESTED chains remain CONTESTED until debates complete.
5. Alert Decision Engine: some CONTESTED chains are pending resolution.

---

#### G.4.5 Recovery from Performance Degradation

**Detection:** RS-01 Inference Service P95 > 2,500ms (above SLA); RS-04 Consensus Query P95 > 200ms.

**Steps:**
1. Check storage layer latency. If storage is the bottleneck, route reads to read replica.
2. Check Reasoning Catalog index fragmentation. Trigger index rebuild if fragmented.
3. Check Reasoning Graph size. If > 5,000 nodes in memory, archive oldest inactive nodes.
4. Check Counter Argument Engine throughput. If backlogged, pause CA construction for LOW-tier chains.
5. Alert ControlTower if degradation persists > 10 minutes.

---

### G.5 Performance Targets

| Metric | Target | Alert threshold | Critical threshold |
|---|---|---|---|
| Hypothesis intake latency | < 50ms | > 100ms | > 500ms |
| Full inference pipeline (happy path) | < 1,300ms | > 2,000ms | > 5,000ms |
| Full inference with debate | < 1,800ms | > 3,000ms | > 8,000ms |
| Consensus query latency | < 30ms | > 80ms | > 300ms |
| Explanation retrieval latency | < 20ms | > 50ms | > 200ms |
| Active chain registry size | < 500 | > 800 | > 1,500 |
| Constitutional violation rate | 0 per day | Any | Any |
| Debate backlog | < 5 pending | > 10 | > 25 |
| Daily reasoning chain turnover | 20–100 | < 5 | > 500 |

---

### G.6 Capacity Reference

| Dimension | Design capacity | Degraded operation threshold |
|---|---|---|
| Concurrent inference chains | 50 | > 100 (queue or shed) |
| Active chains in registry | 500 | > 800 (archive oldest) |
| Concurrent debates | 5 | > 10 (queue) |
| Reasoning Graph nodes in memory | 5,000 | > 8,000 (prune archived) |
| Audit log write rate | 500 events/min | > 1,000 (async batch) |
| Evidence records per chain | 20 | > 50 (store by reference only) |

---
## SUPPLEMENT H — GLOSSARY

Alphabetically ordered definitions for all significant terms used in this architecture document.

---

**Abductive Reasoning:** Inference to the best explanation — selecting the most coherent hypothesis from competing alternatives. The primary multi-hypothesis integration logic of the Reasoning Engine.

**Active Chain:** A reasoning chain in ACTIVE lifecycle status — fully constructed, validated, confidence-scored, and available for consumption by the Decision Engine.

**Audit Trail:** The immutable, append-only record of all events affecting a reasoning chain, maintained by the Reasoning Audit Manager.

**Bayesian Reasoning:** Formal probabilistic inference using Bayes theorem to update prior beliefs with new evidence to produce posterior beliefs (conviction scores).

**CA_STRENGTH:** Counter-Argument Strength — a float [0,1] score measuring how strongly a counter-argument challenges the primary reasoning chain. CA_STRENGTH >= 0.65 triggers CONTESTED status.

**Causal Reasoning:** Reasoning that traces directional cause-and-effect relationships between factors, distinguishing correlation from causation and tracing second and third-order implications.

**Chain Depth:** The number of hops in the dependency graph from the current chain back to primary evidence. Maximum allowed: 5 (RC-A-008).

**Conclusion Delta:** The change in conviction score between successive recursive reasoning cycles. Used as a convergence criterion (threshold: 0.02).

**Confidence Engine:** The component responsible for computing the Reasoning Confidence Score (RCS) and conviction score for every reasoning chain.

**Constitutional Rule:** A non-negotiable system-level rule (RC-A through RC-K) that all reasoning chains must comply with at all times.

**Context Manager:** The component responsible for capturing and supplying the market context record at the time a reasoning chain is constructed.

**Context Record:** A structured snapshot of market conditions at a specific timestamp, used to contextualise reasoning chains.

**Contested Chain:** A reasoning chain in CONTESTED lifecycle status — active but opposed by a significant counter-argument or in unresolved conflict with another chain.

**Conviction Score:** The Bayesian-updated posterior probability that the reasoning chain conclusion is correct, given all current evidence.

**Counter Argument Engine:** The systematic devil-advocate component — constructs the best available counter-argument for every STRONG or DEFINITIVE reasoning chain.

**DAG (Directed Acyclic Graph):** The data structure used by the Reasoning Graph to represent inter-chain dependencies. Must remain acyclic at all times (RC-A-007).

**Debate Pipeline:** The orchestrated multi-agent debate workflow for contested or conflicting reasoning chains.

**Debate Verdict:** The outcome of a multi-agent debate: CONFIRMED / REFINED / CONTESTED / OVERTURNED.

**Decision Engine:** The downstream Layer 5 cognitive layer that receives reasoning chains from the Reasoning Engine and makes portfolio-level decisions.

**Deductive Reasoning:** Reasoning in which the conclusion necessarily follows from the premises. Valid deduction plus true premises guarantees a true conclusion.

**Dependency Manager:** The component that manages inter-chain dependencies and propagates invalidation events when upstream chains change.

**DEFINITIVE Tier:** The highest RCS tier (0.85–1.00). Chains at this tier must pass debate, counter-argument check, full constitutional validation, and Meta Reasoning Manager review.

**Discernment:** The Reasoning Engine capability to select the most analytically sound hypothesis from competing alternatives — distinct from mere selection.

**ECS (Evidence Confidence Score):** Quality score of an evidence record, produced by the Evidence Engine. Used as input to evidence coverage quality dimension (QD-02).

**Evidence Coverage (QD-02):** The breadth and quality of evidence underlying the reasoning chain premises. One of the 12 quality dimensions.

**Evidence Mapping Pipeline:** The pipeline that maps hypothesis evidence records to specific inference steps, providing full traceability.

**Explainability Manager:** The component responsible for generating the human-readable explanation record for every reasoning chain.

**Explanation Record:** A structured record containing all components of the human-readable reasoning explanation (premise summary, inference narrative, conclusion statement, uncertainty statement, etc.).

**Fallacy Penalty:** The RCS penalty applied per detected logical fallacy (-0.05 per fallacy, maximum -0.30 total).

**Governance Tier:** The classification of a reasoning chain by analytical significance: CRITICAL / HIGH / MEDIUM / LOW.

**HCS (Hypothesis Confidence Score):** The quality score of a hypothesis, produced by the Hypothesis Engine. Must be >= 0.30 for hypothesis to be accepted as a premise.

**Hybrid Reasoning (HYB):** A reasoning type that combines multiple reasoning types in a structured sequence.

**Hypothesis Engine:** The upstream Layer 3 cognitive layer that supplies validated hypotheses to the Reasoning Engine.

**Hypothesis Intake:** Stage 1 of the reasoning lifecycle — receiving and accepting validated hypothesis bundles.

**Inductive Reasoning:** Reasoning that draws general conclusions from specific cases. Produces probable but not certain conclusions.

**Inference Engine:** The computational core that constructs step-by-step inference chains, applies inference rules, and detects logical fallacies.

**Inference Step:** A single logical operation within a reasoning chain, with defined premises, inference rule, conclusion, and validity score.

**Invalidation Conditions:** The explicit conditions under which a reasoning chain conclusion would be overturned. Required in all ACTIVE chain explanation records (RC-C-005).

**Logical Validity (QD-01):** The degree to which each inference step follows validly from its premises. The highest-weighted quality dimension in the RCS formula.

**Meta Reasoning Manager:** The self-assessment layer — evaluates quality, limitations, and calibration of the Reasoning Engine outputs.

**Multi-Agent Debate Manager:** The component that orchestrates structured multi-agent debate processes for contested reasoning chains.

**PIT (Point-in-Time):** The capability to reconstruct the exact state of the Reasoning Engine at any historical timestamp.

**Probabilistic Reasoning:** Reasoning that operates over probability distributions rather than discrete true/false values.

**RCS (Reasoning Confidence Score):** The composite quality score [0,1] of a reasoning chain, computed from 12 quality dimensions.

**RCS Tier:** The qualitative classification of an RCS value: DEFINITIVE (0.85+), STRONG (0.70–0.84), MODERATE (0.55–0.69), TENTATIVE (0.40–0.54), EXPLORATORY (0.00–0.39).

**Reasoning Audit Manager:** The compliance and integrity layer that records all chain events and enforces constitutional rule compliance.

**Reasoning Builder:** The primary factory for reasoning chains — selects reasoning type, delegates to Inference Engine, and submits completed chains to the Registry.

**Reasoning Catalog:** The search and discovery layer providing multi-dimensional indexing of all reasoning chains.

**Reasoning Chain:** The core analytical artifact of the Reasoning Engine — a structured record linking premises through inference steps to a conclusion.

**Reasoning Chain Manager:** The component managing in-flight reasoning chain lifecycle, versioning, supersession, and chain linkage.

**Reasoning Graph:** The directed acyclic graph (DAG) representing all reasoning chains and their inter-dependencies.

**Reasoning Registry:** The central operational store for all ACTIVE and CONTESTED reasoning chains.

**Recursive Reasoning Manager:** The component managing recursive reasoning patterns, enforcing depth limits and termination conditions.

**Recursive Reasoning (REC):** Reasoning where the output of a prior cycle is used as a premise for a new cycle.

**Risk Reasoning (RSK):** Reasoning specifically about risk conditions and their implications.

**Supersession:** The process of replacing one version of a reasoning chain with an updated version.

**Temporal Reasoning (TMP):** Reasoning that explicitly incorporates the time dimension — velocity, momentum, duration, and seasonality.

**Uncertainty Score:** 1 − conviction_score. The explicit representation of what the Reasoning Engine does not know with confidence.

**Weighting Engine:** The component providing domain-calibrated, regime-conditional, and recency-adjusted weights for evidence and chain synthesis.

**Zombie Chain:** An anti-pattern — a reasoning chain that remains ACTIVE after the evidence and hypotheses supporting it have been superseded or invalidated (Anti-Pattern AP-08).

---

## SUPPLEMENT I — GOVERNANCE DECISION RECORDS

Governance Decision Records (GDRs) document the key architectural decisions made during the design of the Reasoning Engine.

---

### GDR-RSN-001: Debate as Mandatory for DEFINITIVE Tier

**Date:** Architecture design phase
**Decision:** All DEFINITIVE-tier reasoning chains must complete the Multi-Agent Debate Pipeline before reaching DEFINITIVE status.
**Rationale:** A conviction that cannot survive structured opposition is not a sound conviction. The debate requirement is the institutional guarantee of intellectual honesty. Without it, DEFINITIVE-tier assignments are unvalidated assertions.
**Alternatives considered:**
- Optional debate only for contested chains: Rejected — DEFINITIVE status requires debate even in absence of opposition, because the absence of an obvious counter-argument does not mean no valid counter exists.
- Abbreviated review instead of full debate: Rejected — the debate process produces a substantively different outcome than a solo review.
**Impact:** Increases DEFINITIVE-tier assignment latency by ~500ms. Accepted as the cost of analytical integrity.

---

### GDR-RSN-002: Conviction Score Separate from RCS

**Date:** Architecture design phase
**Decision:** The conviction score and the RCS are distinct metrics maintained separately.
**Rationale:** RCS measures the quality of the reasoning chain (how well-grounded is the logic). Conviction measures the posterior probability that the conclusion is correct given all evidence. These are related but conceptually distinct: a well-grounded chain (high RCS) about an inherently uncertain question may still have low conviction. A poorly-grounded chain (low RCS) is analytically invalid regardless of its apparent conviction.
**Impact:** Decision Engine receives two signals: analytical quality (RCS) and directional confidence (conviction). Both are required for nuanced decision-making.

---

### GDR-RSN-003: Maximum Dependency Depth = 5

**Date:** Architecture design phase
**Decision:** Dependency chains are limited to 5 hops maximum (RC-A-008).
**Rationale:** Chains that are 6+ hops removed from primary evidence are analytically fragile — a change anywhere in the 5-hop ancestor chain can invalidate them. Beyond depth 5, the chain is so derived that its analytical value is questionable and its maintenance burden is excessive.
**Alternatives considered:** Depth 3: Too restrictive — legitimate multi-step macro analytical chains require depth 4–5. Unlimited depth: Creates DAG maintenance risk; cascade propagation becomes computationally expensive.

---

### GDR-RSN-004: Maximum Recursive Depth = 3

**Date:** Architecture design phase
**Decision:** Recursive reasoning is limited to depth 3 (RC-A-009).
**Rationale:** Financial market analytical conclusions typically converge within 2–3 cycles of recursive updating. Beyond depth 3, additional cycles rarely produce materially different conclusions — the marginal gain does not justify the computational and complexity cost.
**Impact:** Chains not converged after 3 cycles are classified as CONTESTED and held for manual review.

---

### GDR-RSN-005: Explicit Uncertainty Quantification Mandatory

**Date:** Architecture design phase
**Decision:** Every explanation record must contain an explicit uncertainty_statement (RC-C-004).
**Rationale:** The primary failure mode of analytical systems is overconfidence. Requiring an explicit uncertainty statement in every explanation forces the Reasoning Engine to articulate what it does not know, not just what it does. This protects the Decision Engine from treating imprecise conclusions as precise ones.
**Impact:** Explanations without uncertainty statements are constitutionally invalid. Explanation generation complexity increases by ~15%.

---

### GDR-RSN-006: Evidence Concentration Cap at 60%

**Date:** Architecture design phase
**Decision:** No DEFINITIVE chain may have > 60% of evidence weight from a single source (RC-B-007).
**Rationale:** Evidence concentration creates hidden single-point-of-failure risk. If the single source is incorrect or stale, the entire DEFINITIVE chain collapses. The 60% cap enforces minimum evidence diversity.
**Alternatives considered:** 80% cap: Too permissive — 80% single-source concentration is excessive. 40% cap: Too restrictive — some domains have limited evidence sources.
**Calibration note:** 60% chosen to allow one dominant source while requiring at least one independent corroboration.

---
## SUPPLEMENT J — INTEGRATION CONTRACTS

This supplement defines the formal integration contracts between the Reasoning Engine and all upstream and downstream systems.

---

### J.1 Contract with Hypothesis Engine (Upstream, Layer 3)

**Relationship:** Hypothesis Engine is the primary producer of analytical premises for the Reasoning Engine.

**What the Hypothesis Engine MUST provide:**
- Hypothesis records with status = VALIDATED before submission to Reasoning Engine
- HCS value and HCS tier for every hypothesis
- Evidence record IDs for all evidence underlying the hypothesis
- Subject entity canonical IDs
- Hypothesis lifecycle status must be VALIDATED (not FORMING, CONTESTED, or RETIRED)
- Hypothesis canonical ID in format HYP-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}

**What the Reasoning Engine WILL NOT accept:**
- Hypotheses with status != VALIDATED
- Hypotheses with HCS < 0.30 (held in low-priority queue)
- Hypotheses without at least one evidence ID pointer
- Hypotheses with future-dated timestamps

**What the Reasoning Engine GUARANTEES to the Hypothesis Engine:**
- Hypothesis records are never modified by the Reasoning Engine
- Hypothesis status changes are not triggered by the Reasoning Engine
- Evidence records referenced by hypotheses are never modified
- The Reasoning Engine will notify via EventBus when a hypothesis is used as a premise

**Failure mode:** If Hypothesis Engine is unavailable, the Reasoning Engine buffers incoming events and processes when connectivity restores. Maximum buffer: 500 hypothesis events.

---

### J.2 Contract with Evidence Engine (Upstream, Layer 2)

**Relationship:** Evidence Engine is the source of all evidence records referenced by hypotheses and reasoning chains.

**What the Reasoning Engine accesses from Evidence Engine:**
- Evidence records (read-only) — by evidence ID
- ECS values for evidence records
- Evidence timestamps

**What the Reasoning Engine NEVER does to Evidence Engine:**
- Never writes to Evidence Engine records
- Never modifies ECS values
- Never deletes evidence records

**What happens when evidence is invalidated:**
- Evidence Engine emits evidence_invalidated event on EventBus
- Reasoning Engine Reasoning Chain Manager detects all active chains referencing that evidence
- Affected chains re-evaluated within one cycle

---

### J.3 Contract with Decision Engine (Downstream, Layer 5)

**Relationship:** Decision Engine is the primary consumer of Reasoning Engine outputs.

**What the Reasoning Engine GUARANTEES to Decision Engine:**
- All ACTIVE chains delivered to Decision Engine have passed full readiness checklist (Part X)
- CONTESTED chains are explicitly annotated with CONTESTED status
- Every chain delivered includes: chain_id, rcs, rcs_tier, conviction_score, uncertainty_score, reasoning_type, conclusion, conclusion_structured, explanation_record_id, governance_tier, conflict_status
- Consensus records are updated within one cycle of any underlying chain change

**What the Decision Engine MUST NOT do:**
- Modify reasoning chain records
- Override reasoning chain RCS or tier assignments
- Treat CONTESTED chains as high-conviction primary inputs
- Use reasoning chains beyond their declared timeframe window

**What the Reasoning Engine will NOT provide:**
- Trading signals (the Reasoning Engine produces analytical conclusions, not trade directives)
- Position sizing recommendations
- Order instructions

---

### J.4 Contract with Learning System (Downstream, Layer 13)

**Relationship:** Learning System receives reasoning chain performance data to feed back into quality calibration.

**What the Reasoning Engine provides to Learning System:**
- Full reasoning chain records on archive (all chains, all versions)
- Conviction score at time of chain construction
- Debate verdicts
- Counter-argument records

**What the Learning System provides back to Reasoning Engine:**
- Historical accuracy rates per reasoning type per domain (used by Confidence Engine for calibration)
- Weighting Engine historical performance weights
- Calibrated tier accuracy rates (used by QD-08)

**Feedback loop latency:** Learning System updates weights daily (overnight); Weighting Engine loads new weights at next daily startup.

---

### J.5 Contract with Knowledge Engine

**Relationship:** Knowledge Engine receives reasoning chains as part of the IIOS permanent knowledge store.

**What the Reasoning Engine provides:**
- All ACTIVE reasoning chains for archival in Knowledge Engine
- Explanation records

**What Knowledge Engine provides to Reasoning Engine:**
- Stored reasoning chains for historical reference during reasoning construction
- Entity and relationship records referenced in reasoning chains

---

### J.6 Contract with ControlTower (Layer 17)

**Relationship:** ControlTower monitors the Reasoning Engine health and telemetry.

**What the Reasoning Engine reports to ControlTower:**
- Health status via RS-14 Health Service
- Constitutional violation counts
- Daily summary: active chains, debated chains, contested chains
- Performance metrics: latency percentiles per service

---

## SUPPLEMENT K — PERFORMANCE BENCHMARKS

---

### K.1 Reasoning Chain Construction Benchmarks

| Benchmark | Condition | Target | Acceptable | Fail |
|---|---|---|---|---|
| Simple inductive chain (3 steps) | Single hypothesis | < 300ms | < 600ms | > 1,200ms |
| Multi-hypothesis abductive chain (5 steps) | 3 hypotheses | < 800ms | < 1,500ms | > 3,000ms |
| Causal chain (4 steps) | 2 hypotheses | < 600ms | < 1,200ms | > 2,500ms |
| Bayesian update | Existing chain + new evidence | < 100ms | < 250ms | > 600ms |
| Full debate pipeline | CONTESTED chain | < 500ms | < 1,500ms | > 5,000ms |
| Recursive update (2 cycles) | Recursive chain | < 2,000ms | < 4,000ms | > 8,000ms |
| Full readiness check | DEFINITIVE chain | < 200ms | < 400ms | > 800ms |

---

### K.2 Service Latency Benchmarks

| Service | P50 | P95 | P99 |
|---|---|---|---|
| RS-01 Inference Service | 800ms | 1,500ms | 2,500ms |
| RS-02 Logic Validation | 80ms | 150ms | 300ms |
| RS-03 Debate Orchestration | 400ms | 800ms | 1,500ms |
| RS-04 Consensus Query | 30ms | 80ms | 150ms |
| RS-05 Confidence Service | 40ms | 100ms | 200ms |
| RS-06 Conflict Resolution | 100ms | 200ms | 400ms |
| RS-07 Explanation (retrieve) | 20ms | 50ms | 200ms |
| RS-07 Explanation (generate) | 250ms | 500ms | 1,000ms |
| RS-08 Dependency | 50ms | 150ms | 300ms |
| RS-09 Context (capture) | 25ms | 60ms | 150ms |
| RS-10 Validation | 80ms | 200ms | 400ms |
| RS-11 Audit (write) | 15ms | 40ms | 100ms |
| RS-12 Reasoning Search | 100ms | 300ms | 800ms |
| RS-13 Archive (write) | 200ms | 500ms | 1,200ms |
| RS-14 Health Check | 20ms | 100ms | 300ms |

---

### K.3 Scale Targets

| Dimension | Per-cycle | Per-day | Per-month |
|---|---|---|---|
| Reasoning chains constructed | 5–30 | 50–300 | 1,000–9,000 |
| Debates conducted | 0–5 | 3–30 | 60–600 |
| Conviction score updates | 20–100 | 200–1,500 | 5,000–45,000 |
| Counter-arguments constructed | 5–20 | 50–200 | 1,000–6,000 |
| Explanation records generated | 5–30 | 50–300 | 1,000–9,000 |
| Audit events recorded | 50–300 | 500–3,000 | 15,000–90,000 |
| Constitutional checks | 5–30 | 50–300 | 1,000–9,000 |

---

## SUPPLEMENT L — FAILURE MODE ANALYSIS

---

### L.1 Component Failure Modes

| Component | Failure Mode | Detection | Recovery | Impact |
|---|---|---|---|---|
| Inference Engine | Crash/hang | Health check timeout | Auto-restart | Reasoning construction halted; buffer fills |
| Logic Engine | False negative (passes invalid chain) | Meta Reasoning audit | Re-validate affected chains | Invalid chains may reach ACTIVE |
| Confidence Engine | RCS computation error | NaN/out-of-range check | Fallback RCS = 0.40 TENTATIVE | Chains receive conservative score |
| Conflict Resolver | Missed conflict | Periodic reconciliation | Re-run conflict scan | Two contradictory chains both ACTIVE |
| Counter Argument Engine | No counter found | Explicit no-counter result | Chain confirmed by default | Missing opposition for DEFINITIVE chains |
| Debate Manager | Deadlock | Timeout after 5s | Verdict = CONTESTED; manual review | Chain held in CONTESTED indefinitely |
| Consensus Engine | Stale consensus | Timestamp check | Recompute consensus | Decision Engine receives stale consensus |
| Context Manager | Stale context | Context age > 10 min | Flag CONTEXT_STALE; continue | Chains built on outdated context |
| Explainability Manager | NLG failure | Template fallback | Template-based explanation | Less natural explanation but complete |
| Reasoning Audit Manager | Write failure | Circuit breaker | Retry queue + dead-letter | Constitutional violation (RC-I-002) |
| Storage Layer | Write failure | Write ACK timeout | Retry 3x; circuit breaker | Chains not persisted; data loss risk |
| EventBus | Unavailable | Connection monitor | Buffer events locally | Downstream distribution delayed |

---

### L.2 System-Level Failure Modes

| Scenario | Severity | Impact | Mitigation |
|---|---|---|---|
| Full reasoning engine failure | P0 | Decision Engine receives no new analytical input | Fallback: Decision Engine uses last known consensus records |
| Constitutional violation RC-A-007 (DAG cycle) | P0 | Reasoning Graph integrity compromised | Quarantine affected chains; cycle breaking procedure |
| Mass invalidation cascade | P1 | Majority of active chains simultaneously CONTESTED | Rate-limit cascade; spread over 5 cycles |
| Stale conviction scores (no updates for >2 cycles) | P1 | Decision Engine uses outdated conviction | Auto-refresh trigger; constitutional check |
| Debate backlog > 25 | P2 | Many DEFINITIVE chains held as CONTESTED | Prioritise debates; accept STRONG tier delivery temporarily |
| Evidence feed disruption | P2 | Evidence mapping gaps in new chains | Use cached evidence; flag EVIDENCE_STALE |
| Context service failure | P2 | Reasoning chains built with stale context | Use last known context; flag CONTEXT_STALE; proceed |

---
## SUPPLEMENT M — CALIBRATION METHODOLOGY

The Reasoning Engine relies on calibrated weights and thresholds to compute accurate RCS values. This supplement documents the calibration methodology.

---

### M.1 RCS Weight Calibration

The 12 quality dimension weights (w_1 through w_12) are calibrated against historical reasoning chain performance data using the following process:

**Step 1 — Historical data collection:**
Collect all archived reasoning chains with known outcomes (did the chain conclusion prove correct or incorrect in the subsequent N trading sessions, where N = the chain declared timeframe).

**Step 2 — Regression analysis:**
For each reasoning chain i with known outcome y_i (1 = correct, 0 = incorrect):

$$y_i \approx f(QD_{1,i}, QD_{2,i}, ..., QD_{12,i})$$

Use logistic regression to estimate the relationship between quality dimension scores and outcome.

**Step 3 — Weight derivation:**
The regression coefficients, normalised to sum to 1.0, provide the calibrated quality dimension weights.

**Step 4 — Domain stratification:**
Calibration is performed separately for each domain (Technical, Macro, Fundamental, Behavioral, etc.) and each reasoning type. Domain-specific weights capture the fact that QD-01 (Logical Validity) is more important for Deductive chains while QD-02 (Evidence Coverage) is more important for Inductive chains.

**Step 5 — Update frequency:**
Weights are recalibrated weekly using the past 90 trading days of outcome data. A minimum of 30 confirmed outcome chains per domain-type combination is required to update that category; otherwise prior weights are retained.

---

### M.2 RCS Tier Threshold Calibration

The tier thresholds (DEFINITIVE >= 0.85, STRONG >= 0.70, etc.) are calibrated to be predictive of analytical accuracy:

| Tier | Target accuracy rate | Actual (current calibration) |
|---|---|---|
| DEFINITIVE | >= 80% correct conclusions | Calibration target |
| STRONG | >= 70% correct conclusions | Calibration target |
| MODERATE | >= 55% correct conclusions | Calibration target |
| TENTATIVE | 40–55% correct conclusions | Baseline above random |
| EXPLORATORY | < 40% correct conclusions | Research only |

Calibration is considered successful when the actual accuracy rate for each tier falls within ±5% of the target rate over a rolling 90-day window.

---

### M.3 Conviction Score Prior Calibration

The Bayesian conviction updating uses domain-calibrated priors:

| Domain | Default prior (uninformative) | Calibrated prior range |
|---|---|---|
| Index Technical | 0.50 | 0.55–0.65 (slightly bullish bias in Indian market) |
| Macro Regime | 0.50 | 0.50 (regime changes are rare; equal prior) |
| Risk | 0.50 | 0.45 (conservative: default skepticism about tail risk) |
| Fundamental Valuation | 0.50 | 0.52 (mild positive bias: markets are usually efficiently priced) |
| Sentiment Contrarian | 0.50 | 0.55 (mild contrarian: sentiment extremes are moderately reliable) |

Priors are reviewed quarterly.

---

### M.4 CA_STRENGTH Calibration

The CA_STRENGTH threshold for triggering CONTESTED status (currently 0.65) is calibrated as follows:

**Objective:** Minimise the rate of false CONTESTED assignments (chains correctly ACTIVE but flagged CONTESTED) while capturing genuine challenges.

**Calibration process:**
- Track CA_STRENGTH for all counter-arguments constructed over 90 days
- Track whether chains with given CA_STRENGTH were subsequently overturned
- Set threshold at the CA_STRENGTH value where P(chain overturned | CA_STRENGTH = threshold) = 0.35

**Current calibration:** CA_STRENGTH >= 0.65 corresponds to approximately 38% overturn probability historically — meaning a chain facing a CA_STRENGTH 0.65 counter-argument has a meaningful (~38%) chance of being overturned on debate. This justifies CONTESTED status.

---

### M.5 Debate Outcome Calibration

The debate process is calibrated to avoid systematic verdicts in one direction (e.g., always confirming).

**Calibration target:**
- CONFIRMED rate: 40–60% of debates
- REFINED rate: 20–35% of debates
- CONTESTED (no verdict) rate: 5–15% of debates
- OVERTURNED rate: 5–20% of debates

**If calibration drifts (e.g., CONFIRMED rate > 70%):** This suggests the Counter Argument Engine is systematically constructing weak challenges, or the Proposer role is systematically better resourced than the Challenger role. Meta Reasoning Manager raises a calibration alert.

---

## PART I ADDENDUM — REASONING ENGINE DESIGN PRINCIPLES (EXTENDED)

This addendum extends the 8 design principles stated in Part I with additional explanatory context for each.

---

### DP-01: Explainability is Non-Negotiable

**Original statement:** Every reasoning chain must be fully explainable in human-comprehensible language.

**Extended context:** This principle exists because the primary risk of an AI analytical system is not that it is wrong, but that it is wrong in a way nobody can detect or question. An unexplainable conclusion is an unauditable conclusion. The Reasoning Engine must never produce a conclusion that cannot be traced, step by step, from raw market observation through evidence and hypothesis to its final form. The explanation mandate is therefore not a usability feature — it is a core safety mechanism.

---

### DP-02: Mandatory Opposition

**Original statement:** Every DEFINITIVE conclusion must survive structured debate.

**Extended context:** Debate is not a performance — it is the mechanism by which weak reasoning chains are identified and either improved or discarded. The Reasoning Engine should not debate because it wants to look thorough; it should debate because it knows that every analytical conviction has a best counter-argument, and that the analytical value of a conclusion is proportional to the quality of the opposition it has survived.

---

### DP-03: Explicit Uncertainty Quantification

**Original statement:** Every conclusion carries an explicit uncertainty score.

**Extended context:** The most dangerous conclusions in financial analysis are those that appear precise but are not. Explicit uncertainty quantification forces the Reasoning Engine to confront what it does not know with the same discipline it applies to what it does know. A conviction score of 0.72 is not a statement of 72% certainty — it is a statement that 28% of the analytical probability mass is explicitly unaccounted for.

---

### DP-04: Traceability from Conclusion to Raw Data

**Original statement:** Every conclusion must trace to raw data.

**Extended context:** Traceability is the mechanism by which the analytical quality can be audited at any level of detail. If a conclusion is subsequently shown to be wrong, the post-hoc analysis should be able to identify exactly which inference step, which hypothesis, which evidence record, or which observation was the source of the error. Without full traceability, post-hoc learning is impossible.

---

### DP-05: Hypothesis-Agnostic Reasoning

**Original statement:** The Reasoning Engine evaluates hypotheses; it does not advocate for them.

**Extended context:** The Reasoning Engine receives hypotheses from the Hypothesis Engine as analytical proposals, not as conclusions to be defended. It must evaluate them as objectively as possible, using the Counter Argument Engine and Multi-Agent Debate Manager to represent alternative interpretations. A Reasoning Engine that systematically confirms the hypotheses it receives is not reasoning — it is rubber-stamping.

---

### DP-06: Governance Enforced, Not Optional

**Original statement:** Governance rules are non-negotiable constraints, not guidelines.

**Extended context:** The constitutional rules (RC-A through RC-K) are not suggestions. They cannot be overridden by configuration, by high-conviction signals, or by time pressure. The governance framework exists precisely because pressure is when governance matters most — in a crisis, when the temptation to bypass controls is highest, the controls must be most reliable.

---

### DP-07: Separation from Execution

**Original statement:** The Reasoning Engine never produces trade directives or portfolio decisions.

**Extended context:** This separation is architecturally absolute. The Reasoning Engine is an analytical layer. The Decision Engine is the decision layer. The Execution Engine is the execution layer. The Reasoning Engine must not attempt to span into decision-making — it produces reasoning chains, not portfolio instructions. This separation exists to ensure that every analytical-to-action transition is explicitly mediated by the Decision Engine, with its own governance framework and quality controls.

---

### DP-08: Continuous Quality Improvement

**Original statement:** The Reasoning Engine learns from every outcome.

**Extended context:** The quality calibration system (Supplement M), the Weighting Engine, and the Learning System feedback loop exist to ensure that the Reasoning Engine improves over time. Every confirmed outcome is a data point for calibration. Every overturned conclusion is a learning signal. The Meta Reasoning Manager monitors calibration drift. This principle requires not just that the system processes feedback, but that it acts on it — adjusting weights, thresholds, and priors based on empirical performance rather than static assumptions.

---
## SUPPLEMENT N — REASONING ENGINE HEALTH MONITORING

This supplement defines the health monitoring framework for the Reasoning Engine — the metrics, alerting thresholds, and reporting structure used by ControlTower to ensure ongoing analytical reliability.

---

### N.1 Core Health Indicators

| Indicator | Healthy | Degraded | Critical | Source |
|---|---|---|---|---|
| Active chain count | 10–500 | < 5 or > 800 | 0 or > 1,500 | Reasoning Registry |
| Contested chain percentage | < 15% | 15–30% | > 30% | Reasoning Registry |
| Average RCS of active chains | >= 0.55 | 0.45–0.55 | < 0.45 | Confidence Engine |
| Inference service P95 latency | < 1,500ms | 1,500–3,000ms | > 3,000ms | RS-01 metrics |
| Consensus query P95 latency | < 80ms | 80–200ms | > 200ms | RS-04 metrics |
| Constitutional violations (rolling 24h) | 0 | 1–3 | > 3 | Reasoning Audit Manager |
| Debate backlog count | < 5 | 5–15 | > 15 | Multi-Agent Debate Manager |
| Explanation missing rate (rolling 1h) | < 2% | 2–5% | > 5% | Explainability Manager |
| Audit log write latency P95 | < 40ms | 40–100ms | > 100ms | Reasoning Audit Manager |
| Evidence gap rate (rolling 1h) | < 10% | 10–20% | > 20% | Evidence Mapping Pipeline |
| Reasoning Graph node count | < 5,000 | 5,000–8,000 | > 8,000 | Reasoning Graph |
| Meta reasoning alert count (daily) | 0 | 1–2 | > 2 | Meta Reasoning Manager |

---

### N.2 Daily Health Report Structure

The Reasoning Engine produces a daily health report at 17:00 IST (after market close). This report is consumed by ControlTower and published to the Streamlit dashboard.

**Report sections:**
1. **Chain Activity Summary:** Chains created, updated, retired, archived, contested in the session. Net change in registry.
2. **Quality Distribution:** Histogram of active chain RCS. Count by tier. Average RCS. Lowest 10 chain IDs.
3. **Debate Activity:** Debates conducted, verdicts (CONFIRMED/REFINED/CONTESTED/OVERTURNED distribution), pending debates.
4. **Constitutional Compliance:** Any violations detected. Rules triggered. Remediation actions taken.
5. **Performance Summary:** Inference Service P50/P95/P99. Notable slow chains (> 2,000ms). Any SLA breaches.
6. **Counter-Argument Summary:** Total CAs constructed. CA strength distribution. Chains moved to CONTESTED via CA.
7. **Meta Reasoning Summary:** Type diversity status. Directional balance. Calibration status. Interventions taken.
8. **Governance Summary:** Chains by tier. CRITICAL chains under debate. New CRITICAL chains today.

---

### N.3 Real-Time Alerting

The following events generate real-time alerts to ControlTower:

| Alert event | Severity | Notification |
|---|---|---|
| Constitutional violation RC-A-007 (DAG cycle) | P0 | Telegram + ControlTower + log |
| Constitutional violation RC-K-003 (DEFINITIVE without debate) | P0 | Telegram + ControlTower + log |
| Active chain count drops to 0 | P0 | Telegram + ControlTower + log |
| Inference Service unavailable > 60s | P0 | ControlTower + log |
| Average RCS drops below 0.45 (3 consecutive cycles) | P1 | ControlTower + log |
| Debate backlog > 25 | P1 | ControlTower + log |
| Evidence gap rate > 20% (sustained 1h) | P1 | ControlTower + log |
| Constitutional violation (any other) | P2 | ControlTower + log |
| New DEFINITIVE chain created | INFO | Streamlit dashboard |
| CRITICAL chain moved to CONTESTED | P2 | Telegram + ControlTower |

---

### N.4 Performance Baseline and Regression Detection

The performance baseline is established over the first 30 trading days of operation. After baseline establishment, any metric that exceeds 150% of the 30-day trailing average triggers a performance regression alert.

**Baseline metrics tracked:**
- Inference time per chain type per domain
- RCS distribution per domain
- Debate duration
- Conviction score distribution
- Daily chain turnover rate

---

## SUPPLEMENT O — REASONING ENGINE INTERFACE SPECIFICATION

This supplement provides the formal interface specification for external systems integrating with the Reasoning Engine.

---

### O.1 Standard Request/Response Envelope

All Reasoning Engine service calls use the following standard envelope:

**Request envelope:**
- request_id: UUID (idempotency key)
- requesting_component: String (component identifier)
- request_timestamp: UTC datetime
- priority: HIGH / NORMAL / LOW
- payload: Service-specific request object

**Response envelope:**
- request_id: UUID (echoed from request)
- response_id: UUID
- response_timestamp: UTC datetime
- status: SUCCESS / PARTIAL_SUCCESS / ERROR
- error_code: Optional[String] (if status = ERROR)
- error_message: Optional[String] (if status = ERROR)
- latency_ms: Integer
- payload: Service-specific response object

---

### O.2 Event Specifications (EventBus events published by Reasoning Engine)

| Event type | When emitted | Payload |
|---|---|---|
| chain_created | New chain reaches ACTIVE | chain_id, rcs, rcs_tier, conviction_score, subject_entity_ids, reasoning_type |
| chain_updated | Existing chain RCS or conviction updated | chain_id, old_rcs, new_rcs, old_tier, new_tier, update_reason |
| chain_status_changed | Lifecycle status transition | chain_id, old_status, new_status, reason |
| chain_contested | Chain moves to CONTESTED | chain_id, contest_reason, ca_strength_if_applicable |
| chain_retired | Chain retires | chain_id, retirement_reason |
| debate_started | Debate process initiated | chain_id, debate_id, trigger_reason |
| debate_completed | Debate verdict issued | chain_id, debate_id, verdict, updated_rcs |
| consensus_updated | Consensus record updated | subject_entity_ids, old_consensus_rcs, new_consensus_rcs, entropy |
| constitutional_violation | Any RC violation | rule_id, chain_id, violation_description |
| meta_reasoning_alert | Meta Reasoning Manager finding | alert_type, severity, description |

---

### O.3 Authentication and Security

All Reasoning Engine services are accessible only within the IIOS internal service mesh. External access is prohibited.

**Authentication:** Mutual TLS (mTLS) for all service-to-service calls. Each component has a unique service certificate.

**Authorisation:** Services have read or read-write permissions. Components cannot access services beyond their defined integration contracts.

**Audit logging:** All service calls are logged with caller identity, timestamp, request ID, and response status.

**Input validation:** All inputs are schema-validated before processing. Invalid inputs return 400 errors without affecting internal state.

---

## SUPPLEMENT P — REGULATORY AND COMPLIANCE FRAMEWORK

---

### P.1 Regulatory Context

The IIOS operates in the Indian financial markets under SEBI (Securities and Exchange Board of India) oversight. The Reasoning Engine, as the analytical core of the system, has specific regulatory compliance requirements:

**Audit trail requirement:** All analytical conclusions that inform trading decisions must have a traceable audit trail from market data to conclusion. The Reasoning Engine satisfies this via the Reasoning Audit Manager, audit trail records, and lineage records.

**Explainability requirement:** Analytical decisions made by automated systems must be explainable to regulators upon request. The Reasoning Engine satisfies this via the Explainability Manager and explanation records.

**Record retention:** Analytical records must be retained for a period consistent with regulatory requirements. The Reasoning Engine satisfies this via the governance-tier retention policy (CRITICAL = permanent; HIGH = 10 years; MEDIUM = 5 years; LOW = 3 years).

---

### P.2 Compliance Checklist

| Requirement | How Reasoning Engine satisfies it |
|---|---|
| Full audit trail for all analytical conclusions | Reasoning Audit Manager: immutable append-only log |
| Explainability of AI-generated conclusions | Explainability Manager: complete explanation record for all ACTIVE chains |
| Flagging of AI-generated reasoning | is_ai_generated flag in schema; disclosed in explanation |
| Record retention per regulatory schedule | Governance-tier retention policy enforced by Archive Manager |
| Point-in-time reconstruction | PIT semantics: full state at any historical timestamp |
| No unauthorised data modification | Evidence Engine is read-only from Reasoning Engine perspective |
| Constitutional rule compliance | RC-A through RC-K; Reasoning Audit Manager monitors compliance |

---

### P.3 Data Classification

| Data type | Classification | Handling |
|---|---|---|
| Active reasoning chain conclusions | CONFIDENTIAL | Internal only; no external distribution |
| Historical chain archive | CONFIDENTIAL | Internal only; accessible to Learning System |
| Explanation records | INTERNAL | May be shared with authorised internal systems |
| Audit trail | RESTRICTED | Accessible only to Reasoning Audit Manager and ControlTower |
| Health metrics | INTERNAL | Accessible to monitoring systems |

---
---

## DOCUMENT FOOTER

---

### Document Summary Metrics

| Metric | Value |
|---|---|
| Document code | IIOS-RSN-ENG-ARCH-001 |
| Layer | 4 of 5 (Cognitive Stack) |
| Predecessor layer | Hypothesis Engine (Layer 3) |
| Successor layer | Decision Engine (Layer 5) |
| Total parts | X (10 parts) |
| Total supplements | P (16 supplements) |
| Total constitutional rules | 90+ (RC-A through RC-K) |
| Total components | 20 (across 5 clusters) |
| Total services | 14 (RS-01 through RS-14) |
| Total pipelines | 10 |
| Total reasoning types | 23 (taxonomy complete) |
| Total lifecycle stages | 15 |
| Quality dimensions | 12 (QD-01 through QD-12) |
| Governance tiers | 4 (CRITICAL/HIGH/MEDIUM/LOW) |
| RCS tiers | 5 (DEFINITIVE/STRONG/MODERATE/TENTATIVE/EXPLORATORY) |
| Lifecycle statuses | 6 (FORMING/ACTIVE/CONTESTED/SUPERSEDED/RETIRED/ARCHIVED) |
| Anti-patterns documented | 10 (AP-01 through AP-10) |
| Inference rules documented | 7 (MP, MT, HS, DS, CONJ, ABE, BU) |
| Logical fallacies detected | 10 (FAL-01 through FAL-10) |
| Governance Decision Records | 6 (GDR-RSN-001 through 006) |
| Inference pattern examples | 4 (Supplement C) |
| Debate examples | 3 (Supplement D) |
| Reasoning graph examples | 3 (Supplement E) |
| Integration contracts | 6 (Supplement J) |

---

### Compliance Checklist

| Requirement | Status |
|---|---|
| Reasoning schema defined with all required fields | COMPLETE |
| All 23 reasoning types documented with type codes | COMPLETE |
| 20 components across 5 clusters fully specified | COMPLETE |
| 14 services fully specified with SLAs | COMPLETE |
| 10 pipelines with flow diagrams | COMPLETE |
| 12 quality dimensions with weights | COMPLETE |
| RCS formula documented | COMPLETE |
| Governance framework complete | COMPLETE |
| 90+ constitutional rules documented | COMPLETE |
| Full readiness checklist (14 sections) | COMPLETE |
| Explainability mandate documented | COMPLETE |
| Debate mandate documented | COMPLETE |
| Bayesian updating methodology documented | COMPLETE |
| Meta-reasoning framework documented | COMPLETE |
| Point-in-time semantics documented | COMPLETE |
| Dependency management documented | COMPLETE |
| Operational runbook complete | COMPLETE |
| Glossary with 40+ terms | COMPLETE |
| GDRs (6 records) | COMPLETE |
| Integration contracts | COMPLETE |
| Performance benchmarks | COMPLETE |
| Failure mode analysis | COMPLETE |
| Calibration methodology | COMPLETE |
| Health monitoring framework | COMPLETE |
| Interface specification | COMPLETE |
| Regulatory compliance framework | COMPLETE |

---

### Governing Documents

| Document | Relationship |
|---|---|
| IIOS-OBS-ENG-ARCH-001 (Observation Engine) | Layer 1 upstream source |
| IIOS-EVD-ENG-ARCH-001 (Evidence Engine) | Layer 2 upstream source |
| IIOS-HYP-ENG-ARCH-001 (Hypothesis Engine) | Layer 3 upstream source |
| IIOS-KNW-ENG-ARCH-001 (Knowledge Engine) | Knowledge consumer of reasoning chains |
| IIOS-DEC-ENG-ARCH-001 (Decision Engine) | Layer 5 downstream consumer |
| ARCHITECTURE.md | System-level architecture |

---

### Architectural Impact Statement

The Reasoning Engine is the analytical intelligence of the IIOS. It receives validated hypotheses from the Hypothesis Engine (Layer 3) and produces well-structured, confidence-scored, explainable reasoning chains for the Decision Engine (Layer 5).

The architectural choices in this document reflect five core convictions:

**1. Analytical integrity requires structural opposition.** The mandatory debate framework (GDR-RSN-001), the Counter Argument Engine, and the Conflict Resolver exist because analytical conclusions become reliable only through the rigorous opposition they are unable to overcome.

**2. Uncertainty is a first-class output.** The conviction score, uncertainty score, and explicit uncertainty quantification mandate (DP-03, RC-C-004) ensure that the Reasoning Engine communicates not just what it believes, but how strongly it believes it and what it does not know.

**3. Explainability is a safety mechanism.** The explanation mandate (DP-01, RC-C-001) is not a usability feature. It is the mechanism by which every conclusion can be audited, questioned, and improved. A conclusion that cannot be explained cannot be trusted.

**4. Quality is quantified, not asserted.** The 12-dimension RCS framework, the calibration methodology, and the meta-reasoning quality assessment create a measurable, improvable quality system. The Reasoning Engine does not claim to be good — it continuously measures and documents whether it is.

**5. Governance is non-negotiable.** The 90+ constitutional rules, the governance tiers, the retention policies, and the regulatory compliance framework exist because the Reasoning Engine operates in a domain where analytical failures have real financial consequences.

---

### Version History

| Version | Date | Author | Description |
|---|---|---|---|
| 0.1 | Architecture design phase | IIOS Architecture Team | Initial draft |
| 1.0 | Architecture design phase | IIOS Architecture Team | First complete version |

---

### Ratification Statement

This document defines the engineering architecture of the Reasoning Engine for the Investment Intelligence Operating System (IIOS). It constitutes the authoritative specification for all engineering decisions related to the Reasoning Engine layer.

All components, services, pipelines, constitutional rules, and governance policies defined in this document are binding on the IIOS implementation. Changes to any element of this architecture require explicit architectural decision records and must be reflected in this document before implementation.

The Reasoning Engine exists to reason. Not to predict, not to execute, not to manage portfolios. It exists to take the validated hypotheses produced by the Hypothesis Engine and subject them to rigorous logical analysis, structured opposition, Bayesian updating, and multi-perspective synthesis — producing well-grounded, explainable, calibrated conclusions that the Decision Engine can trust.

That trust is earned, not assumed. It is earned through transparency, through structural opposition, through explicit uncertainty quantification, through historical calibration, and through the constitutional rules that ensure analytical integrity is maintained at all times.

---

*IIOS-RSN-ENG-ARCH-001 | Classification: INTERNAL | Layer: 4 of 5*
## SUPPLEMENT Q — REASONING ENGINE COGNITIVE ARCHITECTURE

This supplement provides an extended discussion of the cognitive architecture underlying the Reasoning Engine — the theoretical framework that motivates the engineering choices documented in this specification.

---

### Q.1 The Cognitive Stack and the Reasoning Problem

The IIOS Cognitive Stack is a five-layer model of analytical intelligence:

- Layer 1 (Observation): perceives market reality — raw facts about what is happening
- Layer 2 (Evidence): evaluates what has been perceived — is it signal or noise?
- Layer 3 (Hypothesis): explains what the evidence means — proposes interpretations
- Layer 4 (Reasoning): reasons about the interpretations — which one is most defensible and what does it imply?
- Layer 5 (Decision): decides what to do — translates conclusions into portfolio actions

The Reasoning Engine occupies the critical fourth position. It is the layer where hypotheses (Layer 3) are transformed into actionable analytical conclusions (for Layer 5). The reasoning problem it must solve is this:

Given N competing, partially supported, potentially inconsistent hypotheses about a complex, non-stationary, partially observable system (the financial market), produce the set of well-grounded conclusions that best integrates all available analytical evidence, with explicit confidence, explicit uncertainty, and full traceability.

This is not a simple classification or prediction problem. It is a problem of structured analytical reasoning under uncertainty — the kind of problem that requires:
- Multi-perspective integration (all relevant hypotheses considered)
- Structured opposition (all conclusions challenged)
- Bayesian updating (convictions updated continuously as evidence evolves)
- Causal understanding (not just pattern recognition)
- Explicit uncertainty (not false precision)
- Full explainability (every conclusion traceable)

---

### Q.2 Why Abductive Reasoning is Central

Among the 23 reasoning types, abductive reasoning holds a special place. The financial market is a system where multiple hypotheses can plausibly explain the same observation. When NIFTY falls 2% on a given day, the competing explanations might include: profit-taking after rally, FII selling, macro concern, sector-specific news, option expiry dynamics, global risk-off, or technical support breakdown.

These explanations are not mutually exclusive, and often multiple are partially true simultaneously. The question is not which is true and which is false — the question is which explains the observed evidence best, in the context of all other current evidence.

This is abductive reasoning: inference to the best explanation. The Reasoning Engine is designed with abductive reasoning as the primary integration logic for multi-hypothesis subjects — not because it is the most mathematically elegant, but because it most accurately reflects how a skilled analyst reasons when confronted with competing explanations for the same market observation.

---

### Q.3 The Role of Structured Debate

The multi-agent debate framework is perhaps the most architecturally distinctive element of the Reasoning Engine. It is worth explaining why structured debate is not just useful but necessary.

The primary failure mode of analytical AI systems is convergence bias — the tendency to converge on a single analytical interpretation and then find supporting evidence for it, while systematically ignoring or discounting contrary evidence. This is not a failure of intelligence; it is a structural consequence of how analytical systems are designed. Once a high-confidence conclusion is reached, subsequent evidence tends to be interpreted through the lens of that conclusion.

The debate framework is the structural remedy. By requiring that every DEFINITIVE conclusion survive a structured challenge — from a Challenger role explicitly tasked with finding the best counter-argument, from a Devil Advocate role explicitly tasked with opposing the proposition regardless of priors, and from a Meta Judge role assessing the quality of the debate process — the Reasoning Engine creates a structural incentive for analytical honesty.

A conclusion that survives rigorous structured debate is qualitatively different from a conclusion that was never challenged. The debate is not a simulation of intellectual honesty; it is a structural mechanism that produces analytical results that would not otherwise be produced.

---

### Q.4 Conviction vs Confidence: The Analytical Difference

The Reasoning Engine maintains two distinct metrics: RCS (Reasoning Confidence Score) and conviction score. The distinction matters.

**RCS** measures the quality of the reasoning process. It asks: how well-grounded is this reasoning chain? Are the inference steps valid? Is the evidence broad and deep? Is the logic internally consistent? RCS is a property of the reasoning chain as an analytical artifact.

**Conviction score** measures the posterior probability that the conclusion is correct. It asks: given everything we know, how probable is it that this conclusion reflects market reality? Conviction is a property of the conclusion as a claim about the world.

These are related but not the same. A reasoning chain can have high RCS (well-constructed) but low conviction (conclusion is about something genuinely uncertain). A chain can have low RCS (poorly constructed) but what seems like high conviction (the analyst is confident — but the confidence is not well-grounded).

The Reasoning Engine maintains both because the Decision Engine needs both: it needs to know how well-grounded the analytical process was (RCS) and how confident the conclusion is (conviction). These are different inputs to different aspects of the decision.

---

### Q.5 The Explainability Mandate as Epistemic Discipline

The explainability mandate (every chain must have a complete explanation record) serves multiple purposes, but the most important is epistemic: it forces the Reasoning Engine to be disciplined about what it knows and why it knows it.

When the Explainability Manager constructs an explanation record, it must articulate:
- What the premises were and why they were relevant
- What logical steps connected premises to conclusion
- What the conclusion is and what it means
- What is uncertain and why
- What assumptions were made
- What conditions would overturn the conclusion

This process is not just communication — it is analytical quality control. A conclusion that cannot be articulated in these terms is a conclusion that has not been properly constructed. The explanation mandate therefore acts as a final quality gate: if you cannot explain the reasoning, the reasoning is not yet complete.

---

### Q.6 The Constitutional Framework as Intellectual Immune System

The 90+ constitutional rules (RC-A through RC-K) function collectively as the Reasoning Engine intellectual immune system. Just as a biological immune system identifies and neutralises threats to the organism without requiring specific prior knowledge of each pathogen, the constitutional framework identifies and neutralises threats to analytical quality without requiring specific prior knowledge of each failure mode.

The constitutional rules were designed by reasoning about the failure modes of analytical systems:
- **RC-A (Logical Integrity):** prevents invalid inference structures
- **RC-B (Evidence Integrity):** prevents evidence fabrication and concentration
- **RC-C (Explainability):** prevents opaque conclusions
- **RC-D (Traceability):** prevents untraceable claims
- **RC-E (Consistency):** prevents contradictory active conclusions
- **RC-F (Transparency):** prevents hidden assumptions
- **RC-G (Conflict Handling):** prevents unresolved intellectual conflicts
- **RC-H (Governance):** prevents ungoverned conclusions
- **RC-I (Auditability):** prevents unverifiable analytical history
- **RC-J (Historical Preservation):** prevents loss of analytical learning
- **RC-K (Quality):** enforces minimum quality floors

Together, these 11 categories of rules constitute a comprehensive framework for analytical integrity. They do not guarantee correct conclusions — the market is too complex and uncertain for that guarantee. What they guarantee is that the Reasoning Engine is operating with integrity: reasoning honestly from available evidence, acknowledging uncertainty, maintaining traceability, and subjecting its conclusions to structured challenge.

---

### Q.7 The Learning Feedback Loop

The Reasoning Engine is not static. The calibration methodology (Supplement M), the Weighting Engine, and the Learning System feedback loop create a continuous improvement mechanism.

The feedback loop operates as follows:
1. The Reasoning Engine produces conclusions with conviction scores.
2. The market subsequently reveals whether those conclusions were correct.
3. The Learning System matches conclusion outcomes to the reasoning chain records.
4. The Weighting Engine updates historical performance weights based on outcomes.
5. The Confidence Engine applies updated weights in the next calibration cycle.
6. The Meta Reasoning Manager monitors calibration drift.

This feedback loop means that the Reasoning Engine learns which reasoning types, in which domains, under which market regimes, with which evidence profiles, produce the most reliable conclusions. A reasoning engine that does not learn from outcomes is permanently operating at its initial calibration. A reasoning engine with a calibrated feedback loop continuously improves.

---

### Q.8 The Relationship Between Reasoning and Knowledge

The Reasoning Engine and the Knowledge Engine have a complementary relationship. The Knowledge Engine is the permanent memory of the IIOS — the structured repository of market knowledge accumulated over time. The Reasoning Engine is the active analytical intelligence — applying that knowledge to current hypotheses.

The Reasoning Engine reads from the Knowledge Engine (historical patterns, relationship records, entity information) and writes to the Knowledge Engine (new reasoning chains that become part of the permanent knowledge base). This bidirectional relationship ensures that:

1. New reasoning is informed by accumulated historical knowledge
2. Successful reasoning chains become part of the accumulated knowledge for future use
3. The Knowledge Engine grows progressively richer as the Reasoning Engine produces more high-quality chains over time

This relationship is the mechanism by which the IIOS develops what might be called institutional intelligence — the accumulated, organised, and accessible analytical knowledge that grows with experience.

---
## SUPPLEMENT R — REASONING ENGINE INTEGRATION TESTING SPECIFICATION

This supplement defines the integration testing requirements for the Reasoning Engine — the test scenarios that must pass before the Reasoning Engine is considered production-ready.

---

### R.1 Functional Test Scenarios

#### RT-01: Basic Inference Chain Construction

**Objective:** Verify that the Reasoning Engine correctly constructs a basic inference chain from a validated hypothesis.

**Setup:** Submit one validated hypothesis (HCS 0.75, category TECHNICAL, type PRICE_MOMENTUM) to the Inference Service (RS-01).

**Expected result:**
- Response status: SUCCESS
- Chain lifecycle status: ACTIVE
- RCS: between 0.55 and 0.85 (MODERATE or STRONG)
- Explanation record: present and complete
- Audit trail: CREATE event recorded
- Reasoning Graph: chain node present

**Pass condition:** All expected results met within SLA (P95 < 1,500ms).

---

#### RT-02: Multi-Hypothesis Abductive Reasoning

**Objective:** Verify that the Reasoning Engine correctly applies abductive reasoning when 3 competing hypotheses cover the same subject entity.

**Setup:** Submit 3 validated hypotheses for NIFTY with HCS 0.82, 0.65, 0.71 and different directional implications. Request ABDUCTIVE reasoning type.

**Expected result:**
- One primary reasoning chain constructed with type ABD
- Conclusion reflects the hypothesis with highest explanatory coherence
- All three hypotheses listed as PREMISE_OF in Reasoning Graph
- Counter Argument Engine runs and CA record generated

**Pass condition:** Chain reaches ACTIVE with RCS >= 0.55.

---

#### RT-03: Conflict Detection and Debate Trigger

**Objective:** Verify that MAJOR conflict between two chains triggers the Debate Pipeline correctly.

**Setup:** Construct two active chains for BANKNIFTY with directly contradictory conclusions. Verify Conflict Resolver detects MAJOR conflict.

**Expected result:**
- Both chains move to CONTESTED immediately
- Multi-Agent Debate Manager queues debate
- Debate completes within 1,500ms
- One of: CONFIRMED (one chain) + RETIRED (other), or both remain CONTESTED with entropy noted

**Pass condition:** No chain remains ACTIVE alongside a directly contradictory ACTIVE chain for the same subject.

---

#### RT-04: Constitutional Rule RC-A-007 Enforcement

**Objective:** Verify that DAG cycle detection prevents cyclic reasoning chain construction.

**Setup:** Attempt to construct a chain C2 that has C1 as a premise, while C1 was constructed with C2 as a premise.

**Expected result:**
- Cycle detected by Reasoning Graph
- Both C1 and C2 flagged CONTESTED immediately
- Constitutional violation RC-A-007 recorded in Reasoning Audit Manager
- Alert emitted to ControlTower

**Pass condition:** No cyclic chains reach ACTIVE status.

---

#### RT-05: Bayesian Conviction Update

**Objective:** Verify that arriving contradictory evidence correctly updates the conviction score.

**Setup:** Create an ACTIVE chain with conviction = 0.72. Submit a new high-quality evidence record (ECS 0.85) that contradicts the chain conclusion.

**Expected result:**
- Conviction score updated within one cycle
- New conviction score < 0.72 (reduced by contradictory evidence)
- Chain updated event emitted on EventBus
- Consensus record for subject entity updated

**Pass condition:** Conviction delta > 0.05 in correct direction within SLA.

---

#### RT-06: Explainability Completeness

**Objective:** Verify that every ACTIVE chain has a complete, well-formed explanation record.

**Setup:** Retrieve all ACTIVE chains from Reasoning Registry. For each chain, retrieve explanation record via RS-07.

**Expected result:**
- Every active chain has a valid explanation_record_id
- Every explanation record has all required fields populated
- No explanation record older than the chain it explains (by > 5 minutes)

**Pass condition:** 100% of active chains have complete, current explanation records.

---

#### RT-07: Recursive Reasoning Depth Limit

**Objective:** Verify that the Recursive Reasoning Manager enforces the depth=3 limit.

**Setup:** Configure a chain to require recursive updating. Allow up to 5 recursive cycles.

**Expected result:**
- Recursion halts at depth 3 (not 4 or 5)
- Chain annotated with RECURSION_LIMIT if not converged
- Recursive Reasoning Manager summary record created

**Pass condition:** Hard ceiling at depth 3 enforced without exception.

---

#### RT-08: Point-in-Time Reconstruction

**Objective:** Verify that the Reasoning Engine can reconstruct its exact state at any historical timestamp.

**Setup:** Record state at T1. Perform 10 chain operations (creates, updates, retires). Record state at T2. Request state reconstruction at T1.

**Expected result:**
- Reconstructed state matches recorded T1 state exactly
- All chain versions, statuses, and RCS values match T1 snapshot

**Pass condition:** PIT reconstruction correct for all 10 chains.

---

### R.2 Performance Test Scenarios

#### RP-01: Inference Service Load Test

**Objective:** Verify Inference Service meets SLA under production load.

**Setup:** Send 50 concurrent inference requests.

**Expected result:** P95 < 1,500ms for all 50 requests. Error rate < 1%.

---

#### RP-02: Consensus Query Latency

**Objective:** Verify RS-04 Consensus Query Service meets latency SLA.

**Setup:** Send 200 sequential consensus queries for 5 different subject entities.

**Expected result:** P50 < 30ms, P95 < 80ms for all queries.

---

#### RP-03: Registry Size Scalability

**Objective:** Verify Reasoning Registry performance with 500 active chains.

**Setup:** Populate registry with 500 active chains across 20 subject entities. Run 100 concurrent reads.

**Expected result:** Read latency P95 < 50ms. No degradation vs 50-chain baseline.

---

### R.3 Governance Test Scenarios

#### RG-01: Constitutional Rule Enforcement Under Pressure

**Objective:** Verify that constitutional rules are not bypassed under high-throughput conditions.

**Setup:** Send 100 rapid-fire inference requests, including 5 requests that would violate constitutional rules.

**Expected result:**
- All 5 violating requests rejected with appropriate error codes
- No constitutional rule violations recorded for the 95 valid requests
- All constitutional checks completed despite high throughput

---

#### RG-02: Audit Trail Completeness

**Objective:** Verify audit trail captures all events for 50 chains over 100 operations.

**Expected result:** 100% of operations captured in audit log. No gaps. Audit log write latency P95 < 40ms.

---
