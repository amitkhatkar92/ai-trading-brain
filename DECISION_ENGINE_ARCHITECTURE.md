# DECISION ENGINE ARCHITECTURE
## Investment Intelligence Operating System (IIOS)

**Document code:** IIOS-DEC-ENG-ARCH-001
**Classification:** INTERNAL
**Cognitive layer:** 5 of 5
**Predecessor layer:** Reasoning Engine (Layer 4)
**Successor system:** Execution Engine
**Status:** AUTHORITATIVE

---

## Parent Documents

| Document | Role |
|---|---|
| INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md | System authority |
| MASTER_KNOWLEDGE_ARCHITECTURE.md | Knowledge authority |
| ENGINEERING_STANDARDS.md | Engineering standards |
| CORE_FRAMEWORK_ARCHITECTURE.md | Framework authority |
| DATABASE_PERSISTENCE_ARCHITECTURE.md | Persistence layer |
| KNOWLEDGE_ENGINE_ARCHITECTURE.md | Knowledge layer |
| ENTITY_ENGINE_ARCHITECTURE.md | Entity layer |
| RELATIONSHIP_ENGINE_ARCHITECTURE.md | Relationship layer |
| EVENT_ENGINE_ARCHITECTURE.md | Event layer |
| INFORMATION_ENGINE_ARCHITECTURE.md | Information layer |
| OBSERVATION_ENGINE_ARCHITECTURE.md | Layer 1 (perceive) |
| EVIDENCE_ENGINE_ARCHITECTURE.md | Layer 2 (evaluate) |
| HYPOTHESIS_ENGINE_ARCHITECTURE.md | Layer 3 (explain) |
| REASONING_ENGINE_ARCHITECTURE.md | Layer 4 (reason) |

---

## IIOS Cognitive Stack

`
+===============================================================+
|  LAYER 1: OBSERVATION ENGINE                                  |
|  Perceives — converts raw market data into structured         |
|  observations                                                 |
+===============================================================+
|  LAYER 2: EVIDENCE ENGINE                                     |
|  Evaluates — assesses observation quality and significance    |
+===============================================================+
|  LAYER 3: HYPOTHESIS ENGINE                                   |
|  Explains — proposes interpretations of evidence patterns     |
+===============================================================+
|  LAYER 4: REASONING ENGINE                                    |
|  Reasons — evaluates hypotheses, builds conviction,           |
|  resolves conflicts                                           |
+===============================================================+
|  >>>>>>> LAYER 5: DECISION ENGINE [THIS DOCUMENT] <<<<<<<    |
|  Decides — converts reasoning chains into governed,           |
|  risk-aware, approved, execution-ready Decision Packages      |
+===============================================================+
              |
              v DECISION PACKAGE
+===============================================================+
|  EXECUTION ENGINE                                             |
|  Executes — converts Decision Packages into orders            |
+===============================================================+
`

---

## Information Flow

`
[Reasoning Engine]
(reasoning chains, consensus records, conviction scores)
        |
        v
[Decision Engine]
        |
  +-----+----------------------------------------------+
  |                                                    |
  v                                                    v
[Risk Evaluation]                         [Policy Evaluation]
(risk-aware assessment)                  (governance constraints)
  |                                                    |
  +-----+--------------+-----------------------------+-+
                        |
                        v
                 [Approval Workflow]
                        |
                        v
               [Decision Generation]
                        |
                        v
               [Decision Packaging]
                        |
                        v
            [Execution Engine input]
                 + [Knowledge Engine]
                 + [Learning System]
                 + [Dashboard + Telegram]
`

---

## Table of Contents

`
PART I   — Decision Philosophy
PART II  — Decision Taxonomy
PART III — Core Components
PART IV  — Decision Lifecycle
PART V   — Decision Services
PART VI  — Processing Pipelines
PART VII — Quality Framework
PART VIII — Governance
PART IX  — Decision Constitution
PART X   — Readiness Checklist

SUPPLEMENT A — Decision Taxonomy Reference
SUPPLEMENT B — Decision Package Structure
SUPPLEMENT C — Approval Matrix
SUPPLEMENT D — Risk Matrix
SUPPLEMENT E — Decision Flow Examples
SUPPLEMENT F — Anti-Patterns
SUPPLEMENT G — Operational Runbook
SUPPLEMENT H — Glossary
SUPPLEMENT I — Governance Decision Records
SUPPLEMENT J — Integration Contracts
SUPPLEMENT K — Performance Benchmarks
SUPPLEMENT L — Failure Mode Analysis
SUPPLEMENT M — Calibration Methodology

DOCUMENT FOOTER
`

---

## PART I — DECISION PHILOSOPHY

### 1.1 What is a Decision?

A decision is the act of committing to a specific course of action, or to a deliberate and reasoned non-action, in the face of uncertainty. A decision is not a recommendation and it is not a prediction. A decision is a commitment — it allocates analytical authority to a defined action or defined inaction.

Within the IIOS, a Decision is the authoritative analytical output that determines whether, what, and how the Execution Engine is permitted to act. Every Decision is a governed, traceable, explainable, and risk-evaluated analytical commitment that:

1. Identifies a specific subject entity and a specific action type
2. Evaluates the risk-reward profile of that action
3. Assigns a Decision Confidence Score (DCS) reflecting how well-grounded the commitment is
4. Documents full rationale traceable to reasoning chains and underlying evidence
5. Has passed all required policy checks and approval conditions
6. Is packaged as a complete, self-contained Decision Package ready for the Execution Engine

A Decision that has not satisfied all five of these conditions is not yet a Decision — it is a Decision candidate still being evaluated.

---

### 1.2 Why Decisions Exist

The Reasoning Engine (Layer 4) produces well-grounded analytical conclusions. These conclusions are powerful — they represent the integrated, challenged, calibrated output of the full IIOS cognitive stack. But analytical conclusions are not actionable by themselves. A conclusion such as "NIFTY is in a high-probability bull trend continuation phase with conviction 0.75" does not tell the Execution Engine what to do, with what capital, under what risk constraints, with what timing, and with what approval.

The Decision Engine exists to bridge the gap between analytical intelligence and executable action. It takes the Reasoning Engine output and transforms it into:

- A specific, typed action (BUY/SELL/HOLD/REDUCE/etc.)
- A risk-evaluated, policy-compliant, approved decision
- A fully documented, explainable rationale
- A self-contained execution-ready Decision Package

Without the Decision Engine, the analytical intelligence of the IIOS would have no governed, risk-aware, approved pathway to the Execution Engine. The Decision Engine is therefore not a bureaucratic layer — it is the accountability layer. It is where analytical intelligence is converted into committed, governed, accountable action.

---

### 1.3 Conceptual Distinctions

The following 20 conceptual distinctions are fundamental to understanding the Decision Engine architecture. Each term has a precise meaning within the IIOS that must not be confused with adjacent concepts.

---

#### 1.3.1 Observation vs Evidence

**Observation:** A raw, unvalidated fact about the market. "NIFTY price = 24,103.50 at 10:32 IST." An observation is perceived by the Observation Engine (Layer 1). It is not yet evaluated.

**Evidence:** A validated, quality-assessed observation or derived signal. Evidence has an ECS (Evidence Confidence Score) and has been assessed for reliability, freshness, and analytical significance. Evidence is evaluated by the Evidence Engine (Layer 2).

**Decision Engine relationship:** The Decision Engine never interacts with raw observations. It receives reasoning chains that trace to evidence, and through evidence to observations. This traceability is preserved in every Decision Package.

---

#### 1.3.2 Evidence vs Hypothesis

**Evidence:** A validated signal that something is true about the current market state.

**Hypothesis:** An interpretive proposition that explains what the evidence means. "NIFTY breadth is declining while price makes new highs" is evidence. "NIFTY is showing distribution and is at elevated reversal risk" is a hypothesis that interprets that evidence.

**Decision Engine relationship:** Hypotheses, with their HCS scores, are the premises of the reasoning chains received by the Decision Engine. The Decision Engine evaluates conclusions about hypotheses — it does not generate hypotheses.

---

#### 1.3.3 Hypothesis vs Reasoning

**Hypothesis:** A proposed interpretation of evidence. Multiple competing hypotheses may exist for the same subject.

**Reasoning:** The structured analytical process of evaluating which hypothesis is most defensible, what it implies, and with what confidence. Reasoning chains are the output of the Reasoning Engine (Layer 4).

---

#### 1.3.4 Reasoning vs Recommendation

**Reasoning:** An analytical conclusion about what the market is doing or what conditions prevail. "NIFTY is in a bull trend continuation phase, conviction 0.75" is a reasoning conclusion.

**Recommendation:** An advisory suggestion about what action to consider. A recommendation says "you should consider buying." A recommendation lacks the authority and accountability of a Decision.

**Decision Engine relationship:** The Decision Engine does not produce recommendations. It produces Decisions. Decisions carry full accountability — they have been risk-evaluated, policy-checked, and approved. A recommendation is advice; a Decision is a commitment.

---

#### 1.3.5 Recommendation vs Decision

**Recommendation:** Advisory, non-binding, may lack risk evaluation, policy check, or approval.

**Decision:** Binding, risk-evaluated, policy-compliant, approved, accountable, traceable, executable.

**Constitutional constraint:** The Decision Engine must never produce a recommendation when a Decision is required. Ambiguous outputs that look like recommendations but lack full Decision Package structure are a constitutional violation (DC-A-001).

---

#### 1.3.6 Decision vs Execution

**Decision:** The authoritative analytical commitment to a course of action. "BUY RELIANCE: quantity X, price Y, conditions Z, approved, risk-assessed, DCS 0.82."

**Execution:** The operational act of converting a Decision into a market order. The Execution Engine is responsible for execution, not the Decision Engine.

**Constitutional constraint:** The Decision Engine must never initiate order placement. It produces Decision Packages; the Execution Engine converts them into orders.

---

#### 1.3.7 Prediction vs Decision

**Prediction:** A probabilistic statement about what will happen. "NIFTY has a 68% probability of reaching 24,500 within 5 sessions."

**Decision:** A commitment to action. "BUY NIFTY futures: quantity 1 lot, approved, risk evaluated, DCS 0.82."

A Decision may be informed by predictions embedded in reasoning chains, but a Decision is not itself a prediction. The Decision Engine does not predict.

---

#### 1.3.8 Conviction vs Confidence

**Conviction:** The posterior probability that a reasoning chain conclusion is correct. Produced by the Reasoning Engine. Conviction is about the reasoning conclusion.

**Confidence (DCS):** The quality score of the Decision itself — how well-grounded is the decision-making process? DCS reflects evidence quality, reasoning quality, risk evaluation completeness, policy compliance, and approval integrity. Confidence is about the Decision as an analytical artifact.

High conviction can produce a low-confidence Decision (if risk or policy issues are identified). A low-conviction reasoning chain can still produce a valid Decision (if the Decision is appropriately sized and risk-managed for the conviction level).

---

#### 1.3.9 Confidence vs Probability

**Confidence (DCS):** A quality score [0,1] measuring how well-grounded the Decision is.

**Probability:** A frequency or Bayesian probability estimate about market outcomes.

DCS is not a probability. A DCS of 0.82 does not mean "82% probability of profit." It means the Decision was constructed with high quality across all evaluated dimensions.

---

#### 1.3.10 Risk vs Reward

**Risk:** The potential adverse outcome — loss of capital, adverse price movement, drawdown, liquidity risk, execution slippage, and governance risk (regulatory or policy consequences of a Decision).

**Reward:** The potential favourable outcome — capital gain, risk-adjusted return, or analytical learning value.

The Decision Engine evaluates both. A Decision is not approved unless its risk-reward profile is acceptable given the current market regime, portfolio state, and applicable risk policies.

---

#### 1.3.11 Approval vs Commitment

**Approval:** The process of verifying that a Decision candidate has met all required conditions — policy compliance, risk limits, confidence thresholds — before it becomes an active Decision.

**Commitment:** The state of an approved Decision — the IIOS is committed to this action pending execution.

The Approval Manager manages the approval process. A Decision that has not been approved is not committed.

---

#### 1.3.12 Commitment vs Intent

**Commitment:** A firm, approved Decision ready for execution.

**Intent:** An analytical inclination or directional preference that has not yet completed the Decision lifecycle. "The Reasoning Engine indicates a bullish bias for NIFTY" is intent. It becomes a commitment only after the Decision Engine completes the full lifecycle.

---

#### 1.3.13 Decision Package

A Decision Package is the complete, self-contained output artifact of the Decision Engine. It contains everything the Execution Engine needs to act — and everything the audit trail needs for accountability. The Decision Package schema is defined in full in Part II and Supplement B.

A Decision Package is not just the Decision — it is the Decision plus its full rationale, risk assessment, approval record, policy compliance record, lineage trace, and execution parameters.

---

#### 1.3.14 Decision Context

The market and portfolio state at the time the Decision is generated. A Decision made in a BULL_TREND regime with VIX at 12 is analytically different from a Decision made in a CRISIS regime with VIX at 45, even if the underlying reasoning is identical. The Decision Context is permanently attached to the Decision Package.

---

#### 1.3.15 Decision Boundary

The defined limits within which the Decision Engine is authorised to operate. Decision Boundaries include:
- Capital allocation limits (maximum capital per decision type)
- Position concentration limits
- Sector exposure limits
- Instrument type limits
- Time-of-day restrictions
- Regime-conditional restrictions

The Decision Policy Manager enforces Decision Boundaries. Decisions that exceed Decision Boundaries are not approved.

---

#### 1.3.16 Decision Authority

The defined authority level required to approve a Decision. Decision Authority is tiered:
- TIER-1 AUTHORITY: AI-autonomous; Decision Engine approves directly within strict parameters
- TIER-2 AUTHORITY: Human review required; AI generates Decision candidate, human approves
- TIER-3 AUTHORITY: Human-only; AI provides analysis but human makes the decision
- EMERGENCY AUTHORITY: Special escalation path for crisis conditions

---

#### 1.3.17 Decision Responsibility

The accountability chain for a Decision. Who or what is responsible if the Decision is executed and produces an adverse outcome? The Decision Engine documents responsibility through:
- governance_tier: the accountability level
- domain_owner: the responsible analytical domain
- approval_record: who or what approved the decision
- audit_trail: the complete event history

---

#### 1.3.18 Decision Traceability

The ability to trace a Decision backwards through the entire IIOS cognitive stack:
Decision → Reasoning Chain → Hypothesis → Evidence → Observation → Raw Data

Full traceability is a constitutional requirement (DC-D-001). No Decision may be approved without a complete lineage record.

---

#### 1.3.19 Decision Accountability

The obligation to justify and explain every Decision upon request. The Decision Engine satisfies accountability through:
- Complete explanation records (Explainability Manager)
- Complete audit trails (Audit Manager)
- Point-in-time reconstruction capability
- Versioned Decision records

---

#### 1.3.20 Human Override

The authoritative right of a human operator to override, modify, cancel, or hold any Decision or Decision candidate at any point in the lifecycle. Human override is absolute and unconditional (DC-L-001). The Decision Engine must always provide a mechanism for human override.

---

### 1.4 Design Principles

The Decision Engine is governed by 8 immutable design principles:

**DP-01: Authority, Not Advice.** The Decision Engine produces governed, approved, risk-evaluated Decisions. It never produces recommendations, suggestions, or advice.

**DP-02: Risk-Aware by Architecture.** Risk evaluation is not optional. Every Decision must pass a risk evaluation before approval. A Decision that has not been risk-evaluated cannot be committed.

**DP-03: Explainability is Non-Negotiable.** Every Decision must have a complete, human-readable rationale that traces to reasoning chains and underlying evidence.

**DP-04: Human Override is Absolute.** Human operators can override any Decision at any time without restriction.

**DP-05: Separation from Execution.** The Decision Engine never initiates order placement. It produces Decision Packages; the Execution Engine acts on them.

**DP-06: Governance is Non-Negotiable.** Constitutional rules, approval workflows, and policy constraints cannot be bypassed for any reason.

**DP-07: Conservative Default.** When uncertain, the Decision Engine defaults to HOLD or MONITOR decisions rather than action. Action requires affirmative evidence; inaction is the default.

**DP-08: Continuous Learning.** The Decision Engine learns from Decision outcomes via the Learning System feedback loop, continuously improving its calibration and quality.

---
## PART II — DECISION TAXONOMY

### 2.1 Decision Schema

Every Decision produced by the Decision Engine conforms to this canonical schema.

**Canonical ID format:** `DEC-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`

Example: `DEC-EQT-BUY-20260703-00000001`

| Field | Type | Required | Description |
|---|---|---|---|
| decision_id | String | Yes | Canonical globally unique Decision ID |
| decision_type | Enum | Yes | From taxonomy in Part II |
| category_code | String | Yes | Category code from taxonomy |
| version_number | Integer | Yes | Starts at 1; incremented on every update |
| lifecycle_status | Enum | Yes | CANDIDATE/PENDING_APPROVAL/APPROVED/COMMITTED/EXECUTED/HELD/CANCELLED/RETIRED/ARCHIVED |
| subject_entity_ids | List[String] | Yes | Target entity canonical IDs |
| subject_domain | Enum | Yes | Domain (EQUITY/DERIVATIVE/INDEX/MACRO/PORTFOLIO) |
| action_type | Enum | Yes | BUY/SELL/HOLD/REDUCE/INCREASE/EXIT/AVOID/MONITOR/REBALANCE/HEDGE |
| action_direction | Enum | Yes | LONG/SHORT/NEUTRAL/REDUCE_LONG/REDUCE_SHORT |
| execution_parameters | ExecutionParameters | Yes | Quantity, price type, timing, conditions |
| premise_reasoning_chain_ids | List[String] | Yes | Reasoning chains from Layer 4 (min 1) |
| dcs | Float [0,1] | Yes | Decision Confidence Score |
| dcs_tier | Enum | Yes | DEFINITIVE/STRONG/MODERATE/TENTATIVE/EXPLORATORY |
| conviction_score | Float [0,1] | Yes | Inherited conviction from Reasoning Engine |
| risk_assessment_id | UUID | Yes | Risk evaluation record |
| risk_tier | Enum | Yes | CRITICAL/HIGH/MEDIUM/LOW |
| expected_return | Float | No | Estimated return in % (if applicable) |
| max_adverse_excursion | Float | No | Maximum expected adverse movement |
| stop_condition | String | No | Conditions under which Decision is reversed |
| target_condition | String | No | Conditions under which Decision objective is met |
| policy_check_record_id | UUID | Yes | Policy compliance verification record |
| approval_record_id | UUID | Yes | Approval workflow completion record |
| approval_authority | Enum | Yes | TIER-1-AI/TIER-2-HUMAN/TIER-3-HUMAN-ONLY/EMERGENCY |
| approved_by | String | No | Human approver identity (if TIER-2 or TIER-3) |
| approval_timestamp | UTC datetime | No | When approval was granted |
| decision_timestamp | UTC datetime | Yes | When Decision was generated |
| creation_timestamp | UTC datetime | Yes | When record was created |
| context_record_id | UUID | Yes | Market context at decision_timestamp |
| governance_tier | Enum | Yes | CRITICAL/HIGH/MEDIUM/LOW |
| domain_owner | String | Yes | Responsible domain team |
| explanation_record_id | UUID | Yes | Explanation record pointer |
| lineage_record_id | UUID | Yes | Full ancestry lineage pointer |
| audit_trail_id | UUID | Yes | Audit trail pointer |
| is_ai_generated | Boolean | Yes | True if generated autonomously by AI |
| is_human_override | Boolean | Yes | True if human has overridden AI recommendation |
| portfolio_impact_id | UUID | No | Portfolio impact assessment record |
| composite_decision_id | UUID | No | Parent Decision ID if part of composite |
| conditional_trigger_id | UUID | No | Trigger condition ID if conditional decision |
| expiry_timestamp | UTC datetime | No | When Decision expires if not executed |
| meta_assessment | JSON | No | Meta quality assessment record |

---

### 2.2 Decision Lifecycle Statuses

| Status | Meaning |
|---|---|
| CANDIDATE | Decision being constructed; not yet risk-evaluated or policy-checked |
| PENDING_APPROVAL | Risk and policy checks complete; awaiting approval |
| APPROVED | All checks passed; approved for commitment |
| COMMITTED | Firm committed decision; package delivered to Execution Engine |
| EXECUTED | Execution Engine confirms execution began |
| HELD | Temporarily suspended pending new information or market condition change |
| CANCELLED | Cancelled before execution; reason documented |
| RETIRED | Superseded by a new Decision or no longer valid |
| ARCHIVED | Preserved for historical record; no longer active |

---

### 2.3 Execution Parameters Schema

| Field | Description |
|---|---|
| quantity_type | FIXED / PERCENT_OF_BUDGET / PERCENT_OF_PORTFOLIO |
| quantity_value | Numeric quantity or percentage |
| price_type | MARKET / LIMIT / STOP / STOP_LIMIT |
| limit_price | Float (if LIMIT or STOP_LIMIT) |
| stop_price | Float (if STOP or STOP_LIMIT) |
| time_in_force | DAY / GTC / IOC / GTD |
| execution_timing | IMMEDIATE / NEXT_OPEN / INTRADAY_VWAP / CONDITIONAL |
| conditions | JSON list of preconditions for execution |
| max_slippage_bps | Maximum acceptable slippage in basis points |
| expiry_condition | Condition under which this Decision expires unexecuted |

---

### 2.4 Decision Type Taxonomy

#### 2.4.1 Buy Decision (CAT: BUY)

**Definition:** A committed, approved decision to acquire a long position in a subject entity. Buy Decisions range from initial position establishment to adding to an existing position.

**Sub-types:**
- BUY-INITIAL: First entry into a subject entity — no existing position
- BUY-ADD: Adding to an existing long position
- BUY-SCALE-IN: Systematic scaling into a position across multiple entry points
- BUY-RECOVERY: Re-entry after exiting a prior position

**Risk consideration:** Buy Decisions commit capital. They must pass capital allocation policy checks, concentration checks, and regime-appropriate risk evaluation. In CRISIS or BEAR_TREND regimes, the bar for Buy Decisions is raised by policy (see Decision Policy Manager).

**Canonical type codes:** BUY-EQT, BUY-DRV, BUY-IDX, BUY-ETF
**Governance tier default:** HIGH (initial positions), MEDIUM (adds to existing)

---

#### 2.4.2 Sell Decision (CAT: SEL)

**Definition:** A committed, approved decision to sell (exit or reduce) a long position or to initiate a short position.

**Sub-types:**
- SEL-FULL-EXIT: Complete exit from a long position
- SEL-PARTIAL: Partial reduction of a long position
- SEL-SHORT-INIT: Initiating a new short position
- SEL-SHORT-ADD: Adding to an existing short position

**Risk consideration:** Full exit and short initiation carry significant decision weight. SEL-SHORT-INIT requires elevated approval authority in most regimes.

**Canonical type codes:** SEL-EQT, SEL-DRV, SEL-IDX
**Governance tier default:** HIGH (full exits, short initiations), MEDIUM (partial sells)

---

#### 2.4.3 Hold Decision (CAT: HLD)

**Definition:** A deliberate, reasoned decision to maintain the current position without change. A Hold Decision is NOT inaction by default — it is an active analytical conclusion that the current position remains appropriate given the prevailing evidence.

**Sub-types:**
- HLD-CORE: Core position hold — conviction-backed; position remains appropriate
- HLD-MONITORED: Hold under monitoring — confidence has declined; position maintained but under watch
- HLD-PENDING: Hold pending new information — waiting for a specific data event

**Canonical type codes:** HLD-EQT, HLD-DRV, HLD-IDX, HLD-PORTFOLIO
**Governance tier default:** MEDIUM

---

#### 2.4.4 Reduce Decision (CAT: RED)

**Definition:** A decision to reduce position size below current level but not exit completely. Reduce Decisions are risk management moves — reducing exposure without full commitment to exit.

**Canonical type codes:** RED-EQT, RED-DRV, RED-IDX, RED-PORTFOLIO
**Governance tier default:** MEDIUM

---

#### 2.4.5 Increase Decision (CAT: INC)

**Definition:** A decision to increase position size above current level. Increase Decisions differ from BUY-ADD in that they are triggered by improved conviction rather than initial entry logic.

**Risk consideration:** Increasing into a position that is already in profit (pyramiding) carries different risk profile from adding to a position at loss. The Risk Evaluation Engine treats these differently.

**Canonical type codes:** INC-EQT, INC-DRV, INC-IDX
**Governance tier default:** MEDIUM to HIGH

---

#### 2.4.6 Exit Decision (CAT: EXT)

**Definition:** A complete exit from all exposure in a subject entity — both long and short positions closed. Exit Decisions are typically triggered by: conviction collapse, stop-loss breach, regime change, or portfolio rebalancing.

**Sub-types:**
- EXT-CONVICTION: Exit because conviction has fallen below threshold
- EXT-STOP: Exit because stop-loss condition has been triggered
- EXT-REGIME: Exit because market regime change has invalidated the original thesis
- EXT-FORCED: Forced exit by risk governance protocol

**Canonical type codes:** EXT-EQT, EXT-DRV, EXT-IDX, EXT-PORTFOLIO
**Governance tier default:** HIGH (all exit types)

---

#### 2.4.7 Avoid Decision (CAT: AVD)

**Definition:** A deliberate decision NOT to enter a subject entity despite analytical signals suggesting opportunity. Avoid Decisions are made when: risk conditions are unfavourable, policy constraints prohibit entry, conviction is insufficient, or the decision falls outside current portfolio mandate.

**Avoid Decisions are positive analytical outputs.** They document the reasoning for non-action, which is as important analytically as the reasoning for action. An undocumented non-action is an invisible failure mode.

**Canonical type codes:** AVD-EQT, AVD-DRV, AVD-IDX, AVD-REGIME
**Governance tier default:** LOW to MEDIUM

---

#### 2.4.8 Monitor Decision (CAT: MON)

**Definition:** A decision to actively monitor a subject entity without taking a position. Monitor Decisions are the Decision Engine output when conviction is building but has not yet reached the threshold for a Buy or Sell decision.

Monitor Decisions are analytically valuable — they document the developing thesis, track conviction evolution, and provide the pre-decision history for audit and learning purposes.

**Canonical type codes:** MON-EQT, MON-DRV, MON-IDX, MON-MACRO
**Governance tier default:** LOW

---

#### 2.4.9 Rebalance Decision (CAT: RBL)

**Definition:** A portfolio-level decision to adjust position sizes to restore target allocation weights. Rebalance Decisions are typically triggered by portfolio drift (positions have grown or shrunk relative to target allocations) rather than by individual entity conviction.

**Canonical type codes:** RBL-PORTFOLIO, RBL-SECTOR, RBL-FACTOR
**Governance tier default:** MEDIUM to HIGH (large rebalances)

---

#### 2.4.10 Hedge Decision (CAT: HDG)

**Definition:** A decision to acquire a protective position designed to reduce the risk of adverse movement in an existing position. Hedge Decisions are risk management decisions, not return-generating decisions.

**Hedge types:**
- HDG-PUT-BUY: Buy put options to protect long equity position
- HDG-FUTURES-SHORT: Short futures to hedge physical equity
- HDG-SECTOR-HEDGE: Use sector ETF/futures to hedge sector exposure
- HDG-CURRENCY-HEDGE: Currency hedge for FX exposure

**Canonical type codes:** HDG-PUT, HDG-FUTURES, HDG-SECTOR, HDG-CURRENCY
**Governance tier default:** HIGH (all hedge types require explicit approval)

---

#### 2.4.11 Portfolio Decision (CAT: PRT)

**Definition:** A decision that acts on the portfolio as a whole rather than on individual entities. Portfolio Decisions include risk budget allocation, strategy weight adjustments, and aggregate exposure changes.

**Canonical type codes:** PRT-RISK-BUDGET, PRT-STRATEGY-WEIGHT, PRT-EXPOSURE-LIMIT
**Governance tier default:** CRITICAL

---

#### 2.4.12 Risk Decision (CAT: RSK)

**Definition:** A decision triggered specifically by risk conditions — portfolio drawdown, VIX spike, margin proximity, or Risk Guardian activation. Risk Decisions override normal analytical priority with risk management priority.

**Sub-types:**
- RSK-REDUCE-ALL: Reduce all positions (partial de-risking)
- RSK-HALT: Halt all new decisions pending risk review
- RSK-STOP-ALL: Full position close (emergency de-risking)

**Canonical type codes:** RSK-REDUCE, RSK-HALT, RSK-STOP
**Governance tier default:** CRITICAL (all risk decisions)
**Approval authority override:** Risk Decisions automatically receive TIER-1-AI authority within defined thresholds; above thresholds, EMERGENCY authority applies.

---

#### 2.4.13 Capital Allocation Decision (CAT: CAP)

**Definition:** A decision that explicitly allocates capital budgets across strategies, sectors, or entity categories. Capital Allocation Decisions determine how much of the total portfolio budget is available for each allocation bucket.

**Canonical type codes:** CAP-STRATEGY, CAP-SECTOR, CAP-INSTRUMENT
**Governance tier default:** CRITICAL

---

#### 2.4.14 AI Decision (CAT: AID)

**Definition:** A Decision generated fully autonomously by the Decision Engine AI without human input. AI Decisions are only permitted within TIER-1 authority parameters — defined capital limits, risk limits, and regime conditions.

**Canonical type codes:** AID-EQT, AID-DRV, AID-IDX
**Governance tier default:** Based on action type and size.
**Constitutional constraint:** AI Decisions above TIER-1 parameters are automatically escalated to TIER-2 (DC-L-002).

---

#### 2.4.15 Human Decision (CAT: HUM)

**Definition:** A Decision made entirely by a human operator, with the Decision Engine providing analytical support but not generating the decision autonomously. The Decision Engine documents, validates, packages, and routes Human Decisions through the same lifecycle as AI Decisions.

**Canonical type codes:** HUM-OVERRIDE, HUM-DIRECTIVE, HUM-INSTRUCTION
**Governance tier default:** Based on action type.
**Key property:** Human Decisions may bypass AI conviction thresholds, but they cannot bypass risk governance rules. A Human Decision that exceeds risk limits requires explicit risk override with documented justification.

---

#### 2.4.16 Hybrid Decision (CAT: HYB)

**Definition:** A Decision constructed through the collaboration of AI analytical output and human judgment. The AI generates the analytical basis and recommended parameters; the human reviews, may modify, and approves.

**Canonical type codes:** HYB-AI-REVIEW, HYB-HUMAN-MODIFIED
**Governance tier default:** Based on action type.

---

#### 2.4.17 Emergency Decision (CAT: EMR)

**Definition:** A Decision generated under emergency conditions — market crisis, system failure, or Risk Guardian activation. Emergency Decisions may bypass normal approval timelines (but not risk governance rules).

**Emergency conditions that trigger EMR Decisions:**
- Portfolio daily loss > 2% (Risk Guardian threshold)
- VIX > 45 (system halt condition)
- Execution Engine connectivity failure
- Broker API failure
- Exchange circuit breaker

**Canonical type codes:** EMR-HALT, EMR-LIQUIDATE, EMR-REDUCE
**Governance tier default:** CRITICAL
**Approval:** Emergency Decisions are pre-approved via standing emergency protocols. No new approval required within defined emergency parameters.

---

#### 2.4.18 Conditional Decision (CAT: CON)

**Definition:** A Decision that is committed but not yet actionable — its execution is conditional on a specific market event or price condition. Conditional Decisions are pre-approved decisions held pending trigger.

**Examples:**
- "BUY RELIANCE IF price crosses 1,420 from below (breakout trigger)"
- "SELL BANKNIFTY FUTURES IF daily close below 52,000"
- "EXIT POSITION IF VIX crosses 30 from below"

**Canonical type codes:** CON-PRICE, CON-EVENT, CON-TIME, CON-RISK
**Governance tier default:** MEDIUM (same as parent decision type)

---

#### 2.4.19 Scheduled Decision (CAT: SCH)

**Definition:** A Decision whose execution is scheduled for a specific time rather than immediate. Scheduled Decisions are used for pre-market setup, options expiry management, and systematic rebalancing.

**Canonical type codes:** SCH-REBALANCE, SCH-EXPIRY, SCH-PREMARKET
**Governance tier default:** MEDIUM

---

#### 2.4.20 Composite Decision (CAT: CMP)

**Definition:** A Decision that is composed of multiple coordinated sub-decisions that must be executed together as a unit. A Composite Decision represents a multi-leg strategy or a coordinated portfolio adjustment.

**Examples:**
- Options spread: BUY NIFTY 24000 CALL + SELL NIFTY 24200 CALL (bull call spread)
- Pairs trade: BUY HDFC + SELL ICICI (relative value)
- Portfolio rebalance with 5 simultaneous position adjustments

**Canonical type codes:** CMP-OPTIONS-SPREAD, CMP-PAIRS, CMP-REBALANCE
**Governance tier default:** HIGH to CRITICAL
**Constraint:** All sub-decisions must be approved before the Composite Decision is committed.

---

### 2.5 DCS Tier Definitions

| Tier | DCS Range | Meaning | Execution Engine treatment |
|---|---|---|---|
| DEFINITIVE | 0.85–1.00 | Highest-quality Decision; all checks passed at highest level | Full execution parameters honoured |
| STRONG | 0.70–0.84 | Well-constructed Decision; substantive quality | Execution parameters honoured with monitoring |
| MODERATE | 0.55–0.69 | Adequately constructed; some gaps noted | Execution with reduced position size (50–80% of target) |
| TENTATIVE | 0.40–0.54 | Minimally viable Decision; significant gaps | Minimal position; high monitoring frequency |
| EXPLORATORY | 0.00–0.39 | Below minimum standard for execution | Not delivered to Execution Engine |

---
## PART III — CORE COMPONENT ARCHITECTURE

The Decision Engine is decomposed into 20 components across 5 functional clusters. Each component has defined inputs, outputs, dependencies, and failure modes.

---

### 3.1 Cluster Layout

| Cluster | Number | Components | Role |
|---|---|---|---|
| Cluster 1: Registry and Catalog | 2 | Decision Registry, Decision Catalog | Storage, indexing, retrieval |
| Cluster 2: Construction | 4 | Decision Builder, Decision Evaluator, Decision Validator, Decision Ranking Engine | Building and evaluating Decision candidates |
| Cluster 3: Risk and Policy | 4 | Decision Risk Engine, Decision Policy Manager, Decision Approval Manager, Decision Confidence Engine | Risk, policy, approval, confidence |
| Cluster 4: Context and Governance | 4 | Decision Context Manager, Decision Dependency Manager, Decision Governance Manager, Decision Version Manager | Context, dependencies, governance, versioning |
| Cluster 5: Oversight | 6 | Decision Audit Manager, Decision Archive Manager, Decision Distribution Manager, Decision Explainability Manager, Decision Monitoring Manager, Decision Health Manager | Audit, archive, distribution, explainability, monitoring, health |

---

### 3.2 Cluster 1 — Registry and Catalog

#### 3.2.1 Decision Registry

**Purpose:** The central operational store for all ACTIVE, PENDING_APPROVAL, APPROVED, COMMITTED, and HELD Decisions. The single source of truth for the current Decision Engine analytical state.

**Responsibilities:**
- Accept and validate new Decision candidates from the Decision Builder
- Maintain lifecycle status transitions across all active decisions
- Enforce canonical ID uniqueness
- Provide low-latency read access to active decisions for all downstream consumers
- Emit lifecycle change events to the EventBus
- Maintain HELD status tracking for paused decisions
- Enforce expiry of decisions that have not been executed within their expiry window

**Inputs:**
- New Decision candidates (from Decision Builder)
- Status change notifications (from Approval Manager, Monitoring Manager, Risk Engine)
- Archive requests (from Decision Archive Manager)

**Outputs:**
- Active and pending decisions (to Decision Catalog, Execution Engine, Explainability Manager)
- Lifecycle events (to EventBus)
- Query responses (to all authorised consumers)

**Dependencies:**
- Storage layer (primary operational database)
- EventBus (lifecycle notifications)
- Decision Catalog (indexing)

**Failure modes:**
- Write failure: Decision not persisted; circuit-breaker pattern; chain held in CANDIDATE until write succeeds
- Read latency spike: consumers receive stale data; mitigated by read replica
- Expiry processing failure: expired decisions not auto-retired; mitigated by scheduled reconciliation audit

**Monitoring metrics:**
- Active decision count by type and governance tier
- Write latency (P50, P95, P99)
- Lifecycle transition rate
- Expiry processing lag

---

#### 3.2.2 Decision Catalog

**Purpose:** The search and discovery layer — multi-dimensional indexing of all Decisions across all statuses.

**Responsibilities:**
- Maintain multi-dimensional index: entity, domain, type, status, DCS tier, governance tier, timestamp, conviction tier
- Serve complex queries (e.g., "all COMMITTED BUY decisions for equities with DCS >= STRONG in past 7 days")
- Provide Decision lineage maps (which decisions reference which reasoning chains)
- Maintain Decision version tracking
- Provide analytical summaries: type distribution, DCS distribution, governance tier distribution

**Inputs:**
- All Decisions (from Decision Registry via change feed)
- Index rebuild requests

**Outputs:**
- Query results (to any authorised component)
- Lineage maps
- Distribution summaries

**Failure modes:**
- Index drift: catalog out of sync with registry; reconciliation triggered by Audit Manager
- Query timeout: complex multi-dimensional query; mitigated by query complexity limits

---

### 3.3 Cluster 2 — Construction

#### 3.3.1 Decision Builder

**Purpose:** The primary factory for Decision candidates. Takes incoming reasoning chains from the Reasoning Engine and constructs well-formed Decision candidates.

**Responsibilities:**
- Accept reasoning chain bundles from the Reasoning Engine (Reasoning Engine Layer 4 output)
- Translate reasoning chain conclusions into typed Decision candidates (BUY/SELL/HOLD/etc.)
- Apply decision type selection logic based on: reasoning conclusion direction, current portfolio state, subject entity type
- Instantiate the Decision Schema (Part II) with all required fields
- Delegate to Decision Context Manager for market context capture
- Coordinate with Decision Dependency Manager to check for conflicting or dependent decisions
- Validate the completed candidate structure before risk evaluation

**Decision type selection logic:**
- ACTIVE bullish reasoning chain + no existing position → BUY-INITIAL candidate
- ACTIVE bullish reasoning chain + existing long position → HLD or INC candidate
- ACTIVE bearish reasoning chain + existing long position → SELL or REDUCE candidate
- ACTIVE bearish reasoning chain + no position + short-eligible → SEL-SHORT-INIT candidate
- CONTESTED reasoning chain → MONITOR candidate (insufficient conviction)
- EXPLORATORY reasoning chain → AVOID candidate (below minimum threshold)

**Inputs:**
- Reasoning chain bundles (from Reasoning Engine; must be ACTIVE status, RCS >= 0.40)
- Portfolio state (current positions, allocations)
- Context record (from Decision Context Manager)

**Outputs:**
- Decision candidates (to Decision Registry as CANDIDATE status)
- Construction errors (to Decision Audit Manager)

**Failure modes:**
- Schema validation failure: incomplete candidate; not submitted; error logged
- Type selection failure: ambiguous reasoning direction; default to MONITOR candidate
- Portfolio state unavailable: Decision Builder paused until portfolio state recoverable

---

#### 3.3.2 Decision Evaluator

**Purpose:** Evaluates the quality and completeness of a Decision candidate before it enters risk evaluation. The Decision Evaluator is the internal quality gate.

**Responsibilities:**
- Verify that the reasoning chain supporting the candidate has RCS >= threshold for the decision type
- Verify that conviction score meets minimum conviction for the action type
- Assess the analytical completeness: are all analytical dimensions relevant to the action type addressed?
- Evaluate the reasoning type diversity: is the conclusion supported by multiple reasoning types?
- Score the candidate on completeness (0–1)
- Provide an evaluation report to the Decision Confidence Engine

**Minimum RCS thresholds by decision type:**

| Decision type | Minimum RCS | Minimum conviction |
|---|---|---|
| BUY-INITIAL | 0.55 (MODERATE) | 0.55 |
| BUY-ADD | 0.60 | 0.60 |
| SEL-FULL-EXIT | 0.50 | 0.50 |
| SEL-SHORT-INIT | 0.65 | 0.65 |
| EXT-STOP | 0.40 | 0.40 |
| HLD-CORE | 0.50 | 0.50 |
| REDUCE | 0.45 | 0.45 |
| AVOID | 0.30 | No minimum |
| MONITOR | 0.35 | No minimum |
| PORTFOLIO decisions | 0.60 | 0.60 |
| RISK decisions | No minimum (risk-triggered) | No minimum |
| EMERGENCY | No minimum | No minimum |

**Failure modes:**
- Minimum threshold not met: Decision candidate blocked; returned to CANDIDATE status; Audit Manager notified
- Analytical completeness below 0.50: Decision candidate flagged; completeness flag added to decision record

---

#### 3.3.3 Decision Validator

**Purpose:** Independently validates the logical and structural integrity of a Decision candidate.

**Responsibilities:**
- Validate that the action_type is consistent with the reasoning chain conclusion direction
- Validate that execution_parameters are internally consistent (e.g., limit price below market for BUY LIMIT)
- Validate that the subject entity canonical IDs are valid and the entity is currently tradeable
- Validate the temporal consistency: reasoning chains must not be older than threshold (max age by decision type)
- Detect decision type conflicts with existing active decisions for the same entity
- Enforce constitutional rules DC-A-001 through DC-A-010

**Validation outputs:**
- VALID: All structural checks pass
- MINOR_DEFECT: Recoverable issues; proceed with DCS cap
- MAJOR_DEFECT: Fundamental structural issues; candidate rejected; return to Decision Builder

**Failure modes:**
- False negative: invalid candidate passes validation; caught by Audit Manager periodic reconciliation
- Entity not tradeable: candidate blocked; alert raised; AVOID decision automatically generated as substitute

---

#### 3.3.4 Decision Ranking Engine

**Purpose:** When multiple Decision candidates exist for the same subject entity or for competing capital allocation, the Ranking Engine prioritises them.

**Responsibilities:**
- Rank competing Decision candidates by DCS, conviction, risk-adjusted expected return, and portfolio fit
- When capital is insufficient for all candidates: rank by priority and allocate available capital to highest-priority candidates
- Detect redundant decisions: two candidates for the same entity in the same direction at similar size
- Produce a ranked priority list with allocation recommendations for the Approval Manager
- Support regime-conditional ranking: in BULL_TREND, BUY decisions rank above HEDGE; in CRISIS, defensive decisions rank above all

**Ranking formula:**
$$Rank_i = w_1 \cdot DCS_i + w_2 \cdot Conviction_i + w_3 \cdot RiskAdj_i + w_4 \cdot PortFit_i$$

Where:
- DCS_i = Decision Confidence Score
- Conviction_i = Conviction score from Reasoning Engine
- RiskAdj_i = Risk-adjusted expected return (if available)
- PortFit_i = Portfolio fit score (how well this decision fits current portfolio state)
- Weights: 0.30, 0.30, 0.25, 0.15 (regime-calibrated)

**Failure modes:**
- Ranking deadlock: two candidates with identical rank scores; resolved by decision_timestamp tiebreak (earlier = higher rank)
- Capital exhaustion: all capital allocated; remaining candidates queued for next cycle

---

### 3.4 Cluster 3 — Risk and Policy

#### 3.4.1 Decision Risk Engine

**Purpose:** Evaluates the risk profile of every Decision candidate before approval. The Decision Risk Engine is not the portfolio risk manager — it is the decision-level risk assessor.

**Responsibilities:**
- Compute the expected risk of the proposed action: maximum adverse excursion, stop-loss proximity, volatility-adjusted risk
- Assess position concentration risk: will this decision create overconcentration in a single entity, sector, or strategy?
- Assess liquidity risk: is the proposed quantity executable without material market impact?
- Assess regime risk: is the proposed action consistent with the current market regime?
- Assess portfolio correlation risk: will this decision increase correlation to existing positions?
- Produce a comprehensive risk assessment record
- Compute a risk tier (CRITICAL/HIGH/MEDIUM/LOW) for the decision
- Pass/fail the decision against defined risk limits (from Decision Policy Manager)

**Risk dimensions evaluated:**
| Dimension | Description | Fail condition |
|---|---|---|
| Position size | Size vs policy limit | > policy limit |
| Concentration | Entity/sector/strategy share after decision | > concentration limit |
| Liquidity | Decision size vs ADV (average daily volume) | > 5% ADV |
| Regime alignment | Is action type consistent with regime? | Misaligned in CRISIS |
| Drawdown budget | Will this decision push portfolio drawdown close to limit? | < 0.50% remaining budget |
| Stop proximity | Is current price very close to stop condition? | Within 1% of stop |
| Correlation | Portfolio correlation delta post-decision | Increases correlation > 0.15 |

**Risk assessment record schema:**
- risk_assessment_id: UUID
- decision_candidate_id: Decision ID being assessed
- risk_tier: CRITICAL/HIGH/MEDIUM/LOW
- dimension_scores: JSON (per risk dimension: score and pass/fail)
- position_size_check: PASS/FAIL
- concentration_check: PASS/FAIL
- liquidity_check: PASS/FAIL
- regime_alignment_check: PASS/FAIL
- overall_risk_verdict: PASS/FAIL/CONDITIONAL
- conditional_notes: String (if CONDITIONAL: what modifications would make it PASS)
- assessed_timestamp: UTC

**Failure modes:**
- Portfolio state unavailable: risk assessment cannot complete; decision held in CANDIDATE; alert raised
- Regime classification unavailable: regime alignment check skipped; WARN flag added to decision
- Risk Engine timeout: decision held; risk re-attempted on next cycle

---

#### 3.4.2 Decision Policy Manager

**Purpose:** Evaluates every Decision candidate against all applicable operational policies, governance rules, and trading constraints.

**Responsibilities:**
- Maintain the complete policy repository: trading hour policies, instrument restrictions, capital limits, regime policies
- Evaluate each Decision candidate against all applicable policies
- Categorise policy results: PASS / WARN / FAIL
- For WARN results: allow decision to proceed with warning annotation
- For FAIL results: block decision; generate policy violation record; alert Audit Manager
- Support regime-conditional policies (different policy set activates based on regime)
- Update policy enforcement immediately when new policies are loaded

**Key policy categories:**
| Category | Examples |
|---|---|
| Trading hours | No new positions after 15:00 IST; no decisions during circuit breaker |
| Instrument restrictions | No individual stock options without elevated approval |
| Capital limits | Max 10% portfolio per single equity; max 25% per sector |
| Regime policies | No new BUY-INITIAL in CRISIS regime; no SHORT-INIT in CIRCUIT_BREAKER |
| Concentration limits | Max 5 positions per sector; max 20 equity positions total |
| Drawdown limits | No new BUY if portfolio daily loss > 1.5% |
| Strategy budget | Each strategy has a defined capital budget; decisions cannot exceed budget |

**Policy check record:**
- policy_check_id: UUID
- decision_candidate_id: String
- policies_evaluated: List of policy IDs
- policy_results: List of {policy_id, result: PASS/WARN/FAIL, reason}
- overall_verdict: PASS/WARN/FAIL
- blocking_policies: List of failed policy IDs
- evaluated_timestamp: UTC

**Failure modes:**
- Policy repository unavailable: all decisions held in CANDIDATE until policy store recoverable; no approval without policy check
- Policy conflict: two policies produce contradictory verdicts for same decision; conservative policy wins; both recorded; Audit Manager alerted

---

#### 3.4.3 Decision Approval Manager

**Purpose:** Orchestrates the approval workflow — routing Decision candidates to the appropriate approval authority and managing the approval decision.

**Responsibilities:**
- Determine the approval authority tier for each Decision candidate (TIER-1-AI/TIER-2-HUMAN/TIER-3-HUMAN-ONLY/EMERGENCY)
- For TIER-1-AI: auto-approve if risk and policy checks passed
- For TIER-2-HUMAN: generate approval request; route to human operator; wait for response
- For TIER-3-HUMAN-ONLY: AI provides analytical summary; human makes the decision
- For EMERGENCY: apply pre-approved emergency protocols
- Record all approval events in the approval record
- Handle approval rejections: document reason; return to CANDIDATE or RETIRED
- Handle approval timeouts: decision held; alert issued; escalation path

**Approval authority assignment logic:**

| Condition | Approval authority |
|---|---|
| DCS < 0.60 | TIER-2-HUMAN (insufficient AI confidence) |
| DCS >= 0.60 AND risk_tier <= MEDIUM AND governance_tier <= HIGH | TIER-1-AI |
| governance_tier = CRITICAL | TIER-2-HUMAN |
| action = SEL-SHORT-INIT | TIER-2-HUMAN |
| action = EMR-* | EMERGENCY |
| Human operator has set manual review flag | TIER-2-HUMAN |
| Position size > 5% portfolio | TIER-2-HUMAN |

**Approval record schema:**
- approval_record_id: UUID
- decision_candidate_id: String
- approval_authority: Enum
- approval_result: APPROVED/REJECTED/ESCALATED/TIMED_OUT
- approved_by: String (human ID if applicable)
- approval_timestamp: UTC
- rejection_reason: String (if rejected)
- conditions: String (conditions attached to approval)

**Failure modes:**
- Human approver unavailable: decision held in PENDING_APPROVAL; time-bounded hold; if exceeded → escalate or TIER-1-AI downgrade (if policy permits)
- Approval system timeout: alert raised; decisions held; no approvals proceed without system
- Incorrect tier assignment: caught by Audit Manager reconciliation; corrected retrospectively

---

#### 3.4.4 Decision Confidence Engine

**Purpose:** Computes the Decision Confidence Score (DCS) for every Decision candidate — integrating reasoning quality, risk evaluation quality, policy compliance, completeness, and approval integrity.

**Responsibilities:**
- Aggregate quality dimension scores into the DCS
- Apply evidence quality weighting (inherited from reasoning chain ECS)
- Apply risk evaluation weighting
- Apply policy compliance weighting
- Apply completeness weighting
- Compute final DCS and assign DCS tier
- Update DCS when Decision is updated (e.g., after approval, after new evidence)

**DCS Formula:**

$$DCS = w_1 \cdot RCS_{basis} + w_2 \cdot Risk_{score} + w_3 \cdot Policy_{score} + w_4 \cdot Completeness + w_5 \cdot Approval_{quality}$$

Where:
- RCS_basis = RCS of the primary reasoning chain basis
- Risk_score = Risk evaluation quality score (1.0 = all dimensions PASS, 0 = FAIL)
- Policy_score = Policy compliance score (1.0 = all policies PASS, 0 = any blocking FAIL)
- Completeness = Decision candidate completeness score
- Approval_quality = Approval process quality score (1.0 = clean approval, lower if conditions attached)
- Default weights: 0.35, 0.25, 0.20, 0.10, 0.10

**Failure modes:**
- DCS computation error: NaN result; fallback DCS = 0.40 (TENTATIVE); annotated in meta_assessment
- Component score unavailable: affected dimension defaults to 0.50 (neutral); INCOMPLETE flag added

---

### 3.5 Cluster 4 — Context and Governance

#### 3.5.1 Decision Context Manager

**Purpose:** Captures and supplies the market and portfolio context at the time a Decision is generated.

**Responsibilities:**
- Capture current market context snapshot at decision construction time
- Capture current portfolio state: positions, allocations, drawdown, available capital
- Supply context records to Decision Builder, Decision Risk Engine, and Explainability Manager
- Support context comparison: comparing decision context to contexts of historical decisions

**Decision context record schema:**

| Field | Description |
|---|---|
| context_id | UUID |
| capture_timestamp | UTC |
| market_regime | BULL_TREND / BEAR_TREND / RANGE / CRISIS / RECOVERY / DISTRIBUTION |
| vix_level | Float |
| vix_percentile | Float [0,1] |
| nifty_level | Float |
| session | PRE_MARKET / MARKET_HOURS / POST_MARKET |
| calendar_position | PRE_EXPIRY / EXPIRY / POST_EXPIRY / BUDGET / EARNINGS_SEASON / NORMAL |
| portfolio_drawdown_pct | Float (current intraday drawdown) |
| available_capital_pct | Float (% of total capital unallocated) |
| active_position_count | Integer |
| sector_exposure | JSON (sector: allocation pct) |
| strategy_budget_remaining | JSON (strategy: remaining budget) |
| risk_guardian_status | NORMAL / ELEVATED / CRITICAL |
| macro_backdrop | JSON |
| event_flags | List of active events affecting context |

**Failure modes:**
- Stale context: context > 5 minutes old; CONTEXT_STALE flag; DCS reduced by 0.05
- Portfolio state unavailable: Decision held until portfolio state recoverable

---

#### 3.5.2 Decision Dependency Manager

**Purpose:** Manages inter-decision dependencies — when decisions for different entities or at different lifecycle stages depend on each other.

**Responsibilities:**
- Detect when a pending decision is logically dependent on another (e.g., a hedge decision is dependent on the position it hedges)
- Enforce execution ordering for dependent decisions (hedge must execute after position)
- Propagate cancellation: if a parent decision is cancelled, dependent decisions are also cancelled
- Detect conflicting decisions: two decisions that cannot be simultaneously executed
- Maintain the decision dependency graph

**Dependency types:**
| Type | Description |
|---|---|
| REQUIRES_PRIOR | This decision requires another to have been executed first |
| INVALIDATED_BY | This decision is invalidated if another executes |
| SAME_ENTITY_CONFLICT | Two decisions for the same entity in opposite directions |
| CAPITAL_DEPENDENCY | This decision requires capital freed by another |
| COMPOSITE_DEPENDENCY | This decision is a sub-decision of a Composite Decision |

**Failure modes:**
- Dependency cycle: two decisions each depend on the other; blocked; alert raised; human resolution required
- Orphaned dependency: parent decision cancelled but dependent still active; dependent auto-cancelled with documentation

---

#### 3.5.3 Decision Governance Manager

**Purpose:** Ensures that all Decision records comply with the governance framework — correct tier assignment, correct domain ownership, and correct retention policy.

**Responsibilities:**
- Assign governance tier (CRITICAL/HIGH/MEDIUM/LOW) to every Decision candidate
- Assign domain ownership
- Verify governance tier consistency with action type and decision size
- Enforce retention periods per governance tier
- Produce daily governance summary report
- Alert on governance tier misassignments

**Governance tier assignment logic:**
- RSK-* decisions → CRITICAL
- CAP-* decisions → CRITICAL
- EMR-* decisions → CRITICAL
- PRT-* decisions → CRITICAL
- BUY/SEL decisions > 5% portfolio → CRITICAL
- BUY/SEL decisions > 2% portfolio → HIGH
- HLD/REDUCE/INC/INCREASE decisions → MEDIUM
- MON/AVD decisions → LOW

---

#### 3.5.4 Decision Version Manager

**Purpose:** Manages the versioning of Decisions — ensuring that every update to a Decision creates a new version while preserving the full version history.

**Responsibilities:**
- Assign version numbers (starting at 1, incrementing on every update)
- Preserve all prior versions in the archive
- Provide version-specific retrieval for audit and historical analysis
- Detect version conflicts: two simultaneous updates to the same Decision
- Maintain version lineage: which version superseded which

**Version triggers (events that increment version):**
- Approval granted/rejected
- Risk assessment updated
- Execution parameters modified by human
- Status change
- DCS recalculation

**Failure modes:**
- Version conflict: two simultaneous updates; pessimistic locking prevents conflict; last-write-wins with conflict log

---

### 3.6 Cluster 5 — Oversight

#### 3.6.1 Decision Audit Manager

**Purpose:** The compliance and integrity layer — recording all Decision events and validating constitutional rule compliance.

**Responsibilities:**
- Record every Decision creation, update, status change, approval, rejection, and deletion event
- Validate constitutional rule compliance on a rolling basis
- Maintain immutable, cryptographically signed audit trail
- Support point-in-time reconstruction at any historical timestamp
- Produce daily audit summary report
- Alert on constitutional violations immediately

**Audit event types:**
CREATE / UPDATE / STATUS_CHANGE / APPROVAL / REJECTION / RISK_EVAL / POLICY_CHECK / PACKAGE_DELIVERED / EXECUTION_CONFIRMED / CANCELLED / ARCHIVED / VIOLATION

**Failure modes:**
- Audit write failure: Decision held in current status until audit write succeeds
- Audit log corruption: hash chain detection; immediate P0 alert

---

#### 3.6.2 Decision Archive Manager

**Purpose:** Manages the archive lifecycle for Decisions, ensuring complete historical preservation.

**Responsibilities:**
- Move RETIRED and CANCELLED decisions to ARCHIVED status on schedule
- Enforce retention periods by governance tier
- Maintain archive completeness: no Decision ever permanently deleted within retention period
- Support Learning System read access for performance attribution
- Provide archive search capability

**Retention periods:**
| Tier | Retention |
|---|---|
| CRITICAL | Permanent |
| HIGH | 10 years |
| MEDIUM | 5 years |
| LOW | 3 years |

---

#### 3.6.3 Decision Distribution Manager

**Purpose:** Manages the distribution of approved, committed Decisions to all consuming systems.

**Responsibilities:**
- Deliver COMMITTED Decision Packages to the Execution Engine
- Publish Decision events to EventBus for all registered consumers
- Deliver Decision summaries to Streamlit dashboard
- Send significant Decision notifications to Telegram bot
- Deliver Decision records to Knowledge Engine for archival
- Deliver Decision outcomes to Learning System for performance tracking
- Manage delivery confirmation: resend if Execution Engine does not acknowledge

**Distribution priority:**
- RSK-* and EMR-* decisions: URGENT delivery (< 100ms)
- BUY/SEL COMMITTED: HIGH priority (< 500ms)
- HLD/MON/AVD: NORMAL priority (< 2,000ms)
- Archive and learning: BATCH (asynchronous)

**Failure modes:**
- Execution Engine unreachable: Decision held as COMMITTED; retry queue; alert raised
- EventBus unavailable: local buffer; replay when EventBus recovers

---

#### 3.6.4 Decision Explainability Manager

**Purpose:** Generates the human-readable explanation for every committed or significant Decision.

**Responsibilities:**
- Generate explanation records covering: premise summary, reasoning narrative, risk rationale, policy rationale, conviction level, uncertainty statement, alternative considered, conditions for reversal
- Maintain explanation versioning
- Supply explanations to dashboard, Telegram bot, and Execution Engine annotation

**Explanation schema:**
| Field | Description |
|---|---|
| explanation_id | UUID |
| decision_id | Decision this explains |
| decision_version | Version number |
| premise_summary | Key reasoning chain conclusions in plain language |
| reasoning_narrative | Why this action makes analytical sense |
| risk_rationale | Why the risk profile is acceptable |
| policy_rationale | Policy conditions satisfied |
| conviction_statement | Plain language conviction level |
| uncertainty_statement | What is uncertain and why |
| alternative_considered | What alternative action was considered and why rejected |
| conditions_for_reversal | What would trigger a reversal decision |
| generated_timestamp | UTC |

---

#### 3.6.5 Decision Monitoring Manager

**Purpose:** Monitors active committed decisions for trigger conditions, expiry, and material changes that would warrant review or reversal.

**Responsibilities:**
- Monitor all COMMITTED and EXECUTED decisions for conditional triggers (for CON decisions)
- Monitor all positions for stop-loss conditions
- Monitor reasoning chain status: if the underlying reasoning chain is RETIRED or CONTESTED, flag the dependent decision for review
- Detect expiry: if a COMMITTED decision reaches expiry_timestamp without execution, auto-retire
- Generate monitoring alerts for any material change
- Trigger review pipeline when material change detected

**Monitoring frequencies:**
- RSK/EMR decisions: continuous (every tick available)
- BUY/SEL COMMITTED: every cycle (intraday)
- HLD/REDUCE: every cycle
- MON/AVD: once per session

---

#### 3.6.6 Decision Health Manager

**Purpose:** Returns the operational health status of the Decision Engine and all sub-components.

**Responsibilities:**
- Aggregate health status from all components
- Provide real-time health endpoint (RS-12 Health Service)
- Detect degraded performance (P95 latency breaches)
- Generate health alerts for ControlTower
- Produce daily health summary

**Health levels:** HEALTHY / DEGRADED / CRITICAL / UNKNOWN

---
## PART IV — DECISION LIFECYCLE

### 4.1 Overview

The Decision Engine processes reasoning chains through a 13-stage lifecycle. Each stage produces a defined artifact and has defined timing constraints, guard conditions, and failure paths.

---

### 4.2 Lifecycle Stages

#### Stage 1: Reasoning Intake

**Description:** The Decision Engine receives validated reasoning chains from the Reasoning Engine. Only chains with lifecycle status ACTIVE and RCS >= 0.40 are accepted.

**Input:** Reasoning chain bundle (1..N chains with linked evidence, conviction scores, explanation records)
**Output:** Intake record with reasoning chain IDs, intake timestamp, subject entity mapping
**Timing constraint:** < 50ms
**Guard conditions:** Reasoning chain status must be ACTIVE. RCS >= 0.40. Reasoning chain must not be expired.
**Failure handling:** CONTESTED chains accepted as lower-priority input; explicit CONTESTED flag carried forward.

---

#### Stage 2: Context Capture

**Description:** The Decision Context Manager captures the full market and portfolio context.

**Input:** Intake record
**Output:** Decision context record (full schema from Part III)
**Timing constraint:** < 40ms
**Guard:** Context data < 5 minutes old; portfolio state < 2 minutes old.

---

#### Stage 3: Decision Type Selection

**Description:** The Decision Builder analyses the reasoning chain conclusions, current portfolio state, and subject entity profile to determine the appropriate Decision type.

**Input:** Reasoning chain conclusions + portfolio state + context
**Output:** Decision type selection record (type, sub-type, action_direction)
**Timing constraint:** < 20ms
**Key logic:** If reasoning is ambiguous (CONTESTED basis) → default to MONITOR or HOLD type.

---

#### Stage 4: Decision Candidate Construction

**Description:** The Decision Builder instantiates the full Decision Schema and assembles the decision candidate.

**Input:** Type selection record + execution parameters from Decision Policy Manager defaults + context record
**Output:** Decision candidate (status = CANDIDATE)
**Timing constraint:** < 100ms
**Key notes:** Execution parameters populated with policy-compliant defaults; may be refined by human operator before approval.

---

#### Stage 5: Decision Evaluation

**Description:** The Decision Evaluator assesses the quality and analytical completeness of the decision candidate.

**Input:** Decision candidate
**Output:** Evaluation report (completeness score, minimum threshold check)
**Timing constraint:** < 50ms
**Failure path:** Below minimum threshold → CANDIDATE blocked; audit event; Decision Builder notified

---

#### Stage 6: Risk Evaluation

**Description:** The Decision Risk Engine evaluates the risk profile of the decision candidate.

**Input:** Decision candidate + context record + portfolio state
**Output:** Risk assessment record (risk tier, dimension scores, overall verdict)
**Timing constraint:** < 150ms
**Failure path:** FAIL risk verdict → Decision not approved; risk failure record created; human notification if governance tier HIGH+

---

#### Stage 7: Policy Evaluation

**Description:** The Decision Policy Manager checks the candidate against all applicable policies.

**Input:** Decision candidate + current policy set + context record
**Output:** Policy check record (policy results, overall verdict)
**Timing constraint:** < 80ms
**Failure path:** FAIL policy verdict → Decision blocked; policy violation record created; Audit Manager alerted

---

#### Stage 8: Confidence Scoring

**Description:** The Decision Confidence Engine computes the DCS.

**Input:** Decision candidate + evaluation report + risk assessment + policy check
**Output:** DCS value, DCS tier, conviction score (inherited)
**Timing constraint:** < 40ms
**Key note:** DCS tier determines approval authority tier.

---

#### Stage 9: Decision Ranking

**Description:** The Decision Ranking Engine ranks the candidate against other pending candidates for the same or competing capital allocation.

**Input:** Decision candidate + all other CANDIDATE/PENDING_APPROVAL decisions
**Output:** Priority rank, capital allocation recommendation
**Timing constraint:** < 60ms
**Key note:** Low-ranked candidates may be held (HOLD status) if capital is committed to higher-priority decisions.

---

#### Stage 10: Approval

**Description:** The Decision Approval Manager routes the decision to the appropriate approval authority.

**Input:** Decision candidate (all evaluation records complete) + approval authority tier
**Output:** Approval record (APPROVED / REJECTED / HELD / TIMED_OUT)
**Timing constraint (TIER-1-AI):** < 30ms
**Timing constraint (TIER-2-HUMAN):** < 30 minutes (alert if approaching limit)
**Status transition:** PENDING_APPROVAL → APPROVED or REJECTED or HELD

---

#### Stage 11: Decision Packaging

**Description:** The APPROVED decision is assembled into the complete Decision Package.

**Input:** Approved decision + all linked records (context, risk, policy, explanation, lineage)
**Output:** Decision Package (complete, self-contained artifact)
**Timing constraint:** < 100ms
**Key requirement:** Decision Package must be self-contained — the Execution Engine must be able to process it without additional queries.

---

#### Stage 12: Distribution

**Description:** The COMMITTED Decision Package is delivered to the Execution Engine and all registered consumers.

**Input:** Decision Package
**Output:** Delivery confirmations from Execution Engine and all consumers
**Timing constraint (urgent decisions):** < 100ms
**Status transition:** APPROVED → COMMITTED (after package sealed) → EXECUTED (after Execution Engine confirms)

---

#### Stage 13: Archive

**Description:** RETIRED and CANCELLED decisions are moved to ARCHIVED status after retention check.

**Input:** RETIRED or CANCELLED decision record
**Output:** ARCHIVED decision record with retention expiry timestamp
**Timing constraint:** Asynchronous; within 1 hour of retirement/cancellation

---

### 4.3 Lifecycle Stage Summary

| Stage | Name | Max Latency | Output |
|---|---|---|---|
| 1 | Reasoning Intake | 50ms | Intake record |
| 2 | Context Capture | 40ms | Context record |
| 3 | Type Selection | 20ms | Type selection |
| 4 | Candidate Construction | 100ms | Decision candidate (CANDIDATE) |
| 5 | Decision Evaluation | 50ms | Evaluation report |
| 6 | Risk Evaluation | 150ms | Risk assessment |
| 7 | Policy Evaluation | 80ms | Policy check record |
| 8 | Confidence Scoring | 40ms | DCS + tier |
| 9 | Decision Ranking | 60ms | Priority rank |
| 10 | Approval | 30ms (AI) | Approval record |
| 11 | Packaging | 100ms | Decision Package |
| 12 | Distribution | 100ms | Delivery confirmations |
| 13 | Archive | Async | ARCHIVED record |

**Total lifecycle latency (AI approval, happy path):** < 770ms
**With human approval:** minutes to hours (human-bounded)
**With risk failure:** Decision blocked immediately (< 300ms total)

---

### 4.4 State Machine

```
[INTAKE]
    |
    v
[CANDIDATE]
    |── evaluation failure ──> [ERROR] (rebuilt or discarded)
    |── risk FAIL ──────────> [REJECTED] (documented)
    |── policy FAIL ─────────> [REJECTED] (documented)
    |
    v (all evaluations PASS)
[PENDING_APPROVAL]
    |── TIER-1-AI ──────────> [APPROVED] (< 30ms)
    |── TIER-2-HUMAN ────────> [PENDING_APPROVAL] (waiting)
    |   |── human APPROVE ──> [APPROVED]
    |   |── human REJECT ───> [REJECTED]
    |   |── timeout ────────> [HELD]
    |── TIER-3-HUMAN-ONLY ──> [PENDING_APPROVAL] (human decides)
    |── EMERGENCY ───────────> [APPROVED] (emergency protocol)
    |
[APPROVED]
    |── package complete ────> [COMMITTED]
    |── human HOLD ─────────> [HELD]
    |── human CANCEL ────────> [CANCELLED]
    |
[COMMITTED]
    |── Execution Engine ACK -> [EXECUTED]
    |── Execution failure ───> [COMMITTED] (retry)
    |── human CANCEL ────────> [CANCELLED]
    |── expiry reached ──────> [RETIRED]
    |── reasoning chain RETIRED -> [REVIEW] → HOLD or CANCEL
    |
[EXECUTED]
    |── position closed ─────> [RETIRED]
    |── superseded ──────────> [RETIRED]
    |
[RETIRED] ──────────────────────> [ARCHIVED]
[CANCELLED] ────────────────────> [ARCHIVED]
[HELD] ─────────> reviewed ─────> [PENDING_APPROVAL] or [CANCELLED]
```

---

### 4.5 Point-in-Time Semantics

All Decisions support full point-in-time (PIT) querying. The Decision Engine maintains complete state history:
- Every status transition recorded with UTC timestamp
- Every approval event recorded
- Every risk evaluation recorded
- All Decision Package versions preserved
- PIT queries supported for regulatory audit and Learning System attribution

---

### 4.6 Decision Review Cycle

Committed and executed decisions are subject to ongoing review:

| Review type | Trigger | Action |
|---|---|---|
| Reasoning chain status change | Underlying reasoning chain RETIRED or CONTESTED | Flag decision for review; may trigger HOLD |
| Market regime change | Regime changes materially | Review alignment of existing decisions |
| Risk limit proximity | Drawdown budget < 0.5% remaining | Review all active BUY/INC decisions |
| Conviction score drop | Conviction drops > 0.20 from approval level | Flag for review |
| Stop condition triggered | Price approaches stop condition | Generate EXIT candidate |
| Expiry approaching | Decision expiry < 30 minutes away | Alert; extend or retire |

---
## PART V — DECISION SERVICES

The Decision Engine exposes 12 canonical services. Each service is the public contract for accessing Decision Engine capabilities.

---

### DS-01 — Decision Generation Service

**Service identifier:** DS-01
**Service name:** Decision Generation Service
**Service type:** Synchronous computation

**Purpose:** End-to-end Decision generation — receives reasoning chains and returns a completed, confidence-scored Decision candidate or committed Decision.

**Interface:**
- Input: DecisionGenerationRequest {reasoning_chain_ids: List[String], requested_decision_type: Optional[Enum], priority: HIGH/NORMAL/LOW, human_parameters: Optional[ExecutionParameters]}
- Output: DecisionGenerationResponse {decision_id: String, decision_type: Enum, dcs: Float, dcs_tier: Enum, lifecycle_status: Enum, approval_authority: Enum, next_action: String}

**SLA:** P50 < 600ms (AI approval), P95 < 1,200ms
**Callers:** MasterOrchestrator (primary), Reasoning Engine notification handler
**Idempotency:** Same reasoning chain IDs + same context → same decision candidate ID

---

### DS-02 — Validation Service

**Service identifier:** DS-02
**Service name:** Decision Validation Service
**Service type:** Synchronous validation

**Purpose:** Validates a Decision candidate for structural and logical integrity.

**Interface:**
- Input: ValidationRequest {decision_id: String or decision_draft: DecisionDraft}
- Output: ValidationResponse {verdict: VALID/MINOR_DEFECT/MAJOR_DEFECT, defect_list: List[Defect]}

**SLA:** P50 < 60ms, P95 < 120ms

---

### DS-03 — Risk Evaluation Service

**Service identifier:** DS-03
**Service name:** Risk Evaluation Service
**Service type:** Synchronous evaluation

**Purpose:** Evaluates the risk profile of a Decision candidate.

**Interface:**
- Input: RiskEvaluationRequest {decision_id: String, force_recompute: Boolean}
- Output: RiskEvaluationResponse {risk_assessment_id: UUID, risk_tier: Enum, overall_verdict: PASS/FAIL/CONDITIONAL, dimension_scores: JSON}

**SLA:** P50 < 100ms, P95 < 200ms, P99 < 400ms
**Callers:** Decision Builder, Manual validation workflows

---

### DS-04 — Approval Service

**Service identifier:** DS-04
**Service name:** Approval Service
**Service type:** Synchronous (TIER-1-AI) or Asynchronous (TIER-2/3 HUMAN)

**Purpose:** Routes Decision candidates to appropriate approval authority and manages the approval process.

**Interface:**
- Input: ApprovalRequest {decision_id: String, requested_authority: Optional[Enum], human_comment: Optional[String]}
- Output (synchronous): ApprovalResponse {approval_record_id: UUID, result: APPROVED/REJECTED/HELD, conditions: Optional[String]}
- Output (async): {approval_request_id: UUID, status: PENDING_APPROVAL, estimated_timeout_minutes: Integer}

**SLA (TIER-1-AI):** P50 < 20ms, P95 < 50ms
**SLA (TIER-2/3 HUMAN):** Human-bounded; timeout = 30 minutes default

---

### DS-05 — Confidence Service

**Service identifier:** DS-05
**Service name:** Decision Confidence Service
**Service type:** Synchronous computation

**Purpose:** Computes or recomputes the DCS for a Decision.

**Interface:**
- Input: ConfidenceRequest {decision_id: String, recompute: Boolean}
- Output: ConfidenceResponse {dcs: Float, dcs_tier: Enum, conviction_score: Float, dcs_components: JSON}

**SLA:** P50 < 30ms, P95 < 80ms

---

### DS-06 — Policy Service

**Service identifier:** DS-06
**Service name:** Decision Policy Service
**Service type:** Synchronous check

**Purpose:** Evaluates a Decision candidate against all applicable policies.

**Interface:**
- Input: PolicyCheckRequest {decision_id: String, policy_set: FULL/ABBREVIATED}
- Output: PolicyCheckResponse {policy_check_id: UUID, overall_verdict: PASS/WARN/FAIL, blocking_policies: List[String]}

**SLA:** P50 < 50ms, P95 < 100ms, P99 < 200ms

---

### DS-07 — Distribution Service

**Service identifier:** DS-07
**Service name:** Decision Distribution Service
**Service type:** Asynchronous publish

**Purpose:** Delivers committed Decisions to all consuming systems.

**Interface:**
- Input: DistributionRequest {decision_id: String, priority: URGENT/HIGH/NORMAL/BATCH}
- Output: DistributionResponse {distribution_id: UUID, delivered_to: List[String], failed_delivery: List[String]}

**SLA (URGENT):** P95 < 100ms
**SLA (HIGH):** P95 < 500ms
**SLA (NORMAL):** P95 < 2,000ms

---

### DS-08 — Decision Monitoring Service

**Service identifier:** DS-08
**Service name:** Decision Monitoring Service
**Service type:** Continuous background + synchronous query

**Purpose:** Monitors active committed decisions for trigger conditions, expiry, and review events.

**Interface (query):**
- Input: MonitoringQueryRequest {decision_id: String or decision_ids: List[String]}
- Output: MonitoringStatusResponse {monitoring_records: List[MonitoringRecord], active_alerts: List[Alert]}

**SLA (query):** P50 < 30ms, P95 < 80ms
**Background monitoring cycle:** Every 30 seconds for all COMMITTED decisions

---

### DS-09 — Decision Audit Service

**Service identifier:** DS-09
**Service name:** Decision Audit Service
**Service type:** Write (append-only) + read

**Purpose:** Records Decision audit events and supports audit trail queries.

**Interface:**
- Input (write): AuditEvent {decision_id, event_type, actor, previous_state, new_state}
- Input (read): AuditQuery {decision_id, event_type_filter, time_range, page_size}
- Output (read): AuditTrail {events: List[AuditRecord], total_count}

**SLA (write):** P50 < 12ms, P95 < 30ms
**SLA (read):** P50 < 50ms, P95 < 150ms

---

### DS-10 — Decision Search Service

**Service identifier:** DS-10
**Service name:** Decision Search Service
**Service type:** Synchronous query

**Purpose:** Multi-dimensional search across all Decisions (active, archived, historical).

**Interface:**
- Input: DecisionSearchRequest {entity_ids: Optional, domain: Optional, type: Optional, dcs_min: Optional, status: Optional, time_range: Optional, governance_tier: Optional, as_of_timestamp: Optional}
- Output: DecisionSearchResponse {decisions: List[DecisionSummary], total_count, query_latency_ms}

**SLA:** P50 < 80ms, P95 < 250ms, P99 < 600ms

---

### DS-11 — Decision Archive Service

**Service identifier:** DS-11
**Service name:** Decision Archive Service
**Service type:** Asynchronous write + synchronous read

**Purpose:** Archives retired/cancelled decisions and provides access to historical archive.

**Interface:**
- Input (archive): ArchiveRequest {decision_id, reason}
- Input (read): ArchiveReadRequest {decision_id, version: Optional, as_of_timestamp: Optional}
- Output (read): ArchivedDecision (full decision record)

**SLA (read):** P50 < 200ms

---

### DS-12 — Health Service

**Service identifier:** DS-12
**Service name:** Decision Engine Health Service
**Service type:** Synchronous health check

**Purpose:** Returns the operational health status of the Decision Engine.

**Interface:**
- Input: HealthCheckRequest {include_components: Boolean}
- Output: HealthResponse {overall_status: HEALTHY/DEGRADED/CRITICAL, component_statuses: List, key_metrics: JSON}

**SLA:** P50 < 20ms (cached health state)
**Callers:** ControlTower, MasterOrchestrator, Streamlit dashboard

---
## PART VI — PROCESSING PIPELINES

The Decision Engine operates through 9 primary processing pipelines.

---

### Pipeline 1: Reasoning-to-Decision Pipeline

**Purpose:** The primary end-to-end pipeline — from reasoning chain intake to COMMITTED Decision Package.

**Trigger:** New ACTIVE reasoning chain notification from Reasoning Engine

**Flow:**

```
[Reasoning Engine]
(ACTIVE reasoning chain, RCS >= 0.40)
        |
        v (reasoning chain bundle)
[Decision Builder] <── [Decision Context Manager] (context record)
        |                <── [Portfolio State] (current positions)
        v (decision candidate CANDIDATE)
[Decision Evaluator]
        |── below threshold ──> [REJECTED candidate; rebuild or discard]
        |
        v (evaluation PASS)
[Decision Validator]
        |── MAJOR_DEFECT ──> [REJECTED; rebuild]
        |── MINOR_DEFECT ──> proceed with DCS cap
        |
        v (VALID)
[Decision Risk Engine] <── [Portfolio State] (risk context)
        |── FAIL ──────────> [REJECTED; risk failure documented]
        |── CONDITIONAL ───> proceed with conditions noted
        |
        v (PASS / CONDITIONAL)
[Decision Policy Manager]
        |── FAIL ──────────> [REJECTED; policy violation recorded]
        |── WARN ──────────> proceed with warnings noted
        |
        v (PASS / WARN)
[Decision Confidence Engine] (DCS computed)
        |
        v
[Decision Ranking Engine] (priority assigned)
        |
        v (PENDING_APPROVAL)
[Decision Approval Manager]
        |── TIER-1-AI ──────> [APPROVED] (< 30ms)
        |── TIER-2-HUMAN ───> [PENDING; human review]
        |── REJECTED ───────> [REJECTED; documented]
        |
        v (APPROVED)
[Decision Packaging Pipeline]
        |
        v
[COMMITTED Decision Package]
        |
[Distribution Pipeline]
        |
        v
[Execution Engine] + [EventBus consumers]
```

---

### Pipeline 2: Risk Evaluation Pipeline

**Purpose:** Dedicated risk assessment pipeline for all Decision candidates.

**Trigger:** Decision candidate reaches Stage 6 (Risk Evaluation)

**Flow:**

```
[Decision candidate]
        |
        v
[Decision Risk Engine]
        |
  +-----+----------------------------------------------------------+
  |     |                |                |                |        |
  v     v                v                v                v        v
[Size] [Concentration] [Liquidity] [Regime alignment] [Drawdown] [Correlation]
check  check            check       check              check       check
  |     |                |                |                |        |
  +-----+----------------+----------------+----------------+--------+
                               |
                    +----------+----------+
                    |                     |
              ALL PASS               ANY FAIL
                    |                     |
                    v                     v
          [Risk assessment:          [Risk assessment:
           risk_tier assigned]        FAIL verdict]
                    |                     |
                    v                     v
          [Policy Evaluation]      [REJECTED; risk
                                    failure record]
```

---

### Pipeline 3: Approval Pipeline

**Purpose:** Routes Decision candidates to appropriate approval authority.

**Flow:**

```
[Decision candidate: PENDING_APPROVAL]
        |
        v
[Decision Approval Manager]
        |
  [Authority Tier Determination]
        |
  +-----+--------------+------------------+------------------+
  |                    |                  |                  |
  v TIER-1-AI          v TIER-2-HUMAN     v TIER-3-HUMAN-ONLY v EMERGENCY
  |                    |                  |                  |
  v < 30ms             v human review     v human decides    v emergency
[Auto-approve         [Approval request  [AI provides        [Pre-approved
 if risk+policy        to human UI;       analysis only;      protocol;
 PASS]                 30-min timeout]    human generates]    immediate]
  |                    |                  |                  |
  +--------------------+------------------+------------------+
                               |
                    +----------+----------+
                    |                     |
              APPROVED                REJECTED/HELD
                    |                     |
                    v                     v
          [Approval record]       [Rejection record;
          [Status: APPROVED]       notification]
```

---

### Pipeline 4: Decision Packaging Pipeline

**Purpose:** Assembles the complete self-contained Decision Package from an APPROVED decision and all linked records.

**Flow:**

```
[APPROVED decision]
        |
        v
[Decision Package assembler]
        |
  +-----+----+--------+-------+--------+-----------+
  |          |        |       |        |           |
  v          v        v       v        v           v
[Decision  [Risk    [Policy [Context [Reasoning  [Explanation
 record]    assess.] check]  record]  chain refs]  record]
  |          |        |       |        |           |
  +----------+--------+-------+--------+-----------+
                               |
                    v (all records linked)
             [Package completeness check]
                    |── any record missing ──> HOLD; alert
                    |── all present ──────────> COMPLETE
                               |
                    v
             [Decision Package sealed]
             [Status: COMMITTED]
             [Lineage record created]
             [Audit event: PACKAGE_SEALED]
```

---

### Pipeline 5: Distribution Pipeline

**Purpose:** Delivers COMMITTED Decision Packages to all consuming systems.

**Flow:**

```
[COMMITTED Decision Package]
        |
        v
[Decision Distribution Manager]
        |
  [Priority classification]
        |
  +-----+----------+-----------+----------+
  |                |           |          |
  v URGENT         v HIGH      v NORMAL   v BATCH
  |                |           |          |
[Execution Engine  [Execution  [Dashboard [Learning
 direct; < 100ms]   then others] + Telegram] System +
                                           Knowledge]
        |
        v (from all paths)
[Delivery acknowledgment collection]
        |── Execution Engine ACK ──> [Status: EXECUTED]
        |── Execution Engine NAK ──> [Retry queue; alert]
        |── Other consumers ───────> [EventBus; best-effort]
```

---

### Pipeline 6: Monitoring Pipeline

**Purpose:** Continuous monitoring of all COMMITTED and EXECUTED decisions.

**Flow:**

```
[All COMMITTED/EXECUTED decisions]
        |
        v (every 30s background cycle)
[Decision Monitoring Manager]
        |
  +-----+----------+----------+----------+----------+
  |                |           |          |          |
  v                v           v          v          v
[Conditional    [Expiry     [Reasoning [Stop     [Conviction
 trigger check]  check]      chain      condition  drop
                             status     check]     check]
  |                |           |          |          |
  +----------------+-----------+----------+----------+
                               |
                    +----------+----------+
                    |                     |
               No alerts            Alert generated
                    |                     |
              [Continue]          [Alert event;
                                   Review pipeline
                                   triggered]
```

---

### Pipeline 7: Review Pipeline

**Purpose:** Reviews decisions flagged by the Monitoring Pipeline or by human operators.

**Flow:**

```
[Review trigger (monitoring alert or human request)]
        |
        v
[Decision Governance Manager] (review classification)
        |
  [Review type classification]
        |
  +-----+----------+-----------+
  |                |            |
  v MINOR          v MODERATE   v MAJOR
  |                |            |
[Annotation;    [DCS           [HOLD decision;
 continue]       recompute;     human review;
                 notify human]  risk re-eval]
        |                |            |
        +----------------+------------+
                         |
                         v
               [Review record created]
               [Audit Manager notified]
               [Possible: HELD, CANCELLED, or continued]
```

---

### Pipeline 8: Audit Pipeline

**Purpose:** Records all Decision events in the immutable audit trail.

**Flow:**

```
[Any Decision event (from any component)]
        |
        v
[Decision Audit Manager]
        |
  [Event classification and validation]
        |
        v
[Audit record construction]
  {decision_id, event_type, actor, previous_state, new_state,
   timestamp, constitutional_rules_checked}
        |
        v
[Append-only audit log write]
  |── write success ──> [Hash chain updated; ACK returned]
  |── write failure ──> [Retry 3x; circuit breaker; P0 alert]
        |
        v (write success)
[Constitutional compliance check]
  |── violation detected ──> [Violation record; alert; remediation]
  |── no violation ───────> [Clean audit event]
```

---

### Pipeline 9: Storage Pipeline

**Purpose:** Ensures durable, consistent storage of all Decision records.

**Flow:**

```
[Any Decision record or update]
        |
        v
[Storage Layer] (primary write)
        |
        v (write confirmed)
[Parallel updates]
        |
  +-----+-------+----------+------+
  |             |           |      |
  v             v           v      v
[Decision     [Decision  [Decision [Audit
 Registry]     Catalog]   Version   Manager]
               (index     Manager]
               update)    (version
                           recorded)
        |
        v
[EventBus] (change event emitted)
        |
        v (fan-out)
[All registered consumers notified]
```

---
## PART VII — DECISION QUALITY FRAMEWORK

### 7.1 Overview

The Decision Confidence Score (DCS) is the primary quality metric of every Decision. It integrates 12 quality dimensions into a composite score [0,1]. The DCS determines the decision tier, the approval authority tier, and the execution position sizing.

---

### 7.2 The 12 Quality Dimensions

#### QD-01: Correctness

**Definition:** The degree to which the decision action type and direction are logically correct given the underlying reasoning chain conclusions.

**Measurement:** Direction consistency check — does the action type match the conclusion direction? (BUY for bullish conclusion, SELL for bearish, HOLD for ambiguous)

**Weight in DCS:** 0.20 (highest — a directionally wrong decision has no value regardless of other quality)

**Degradation triggers:**
- Decision direction inconsistent with reasoning chain direction → -0.25 (blocking defect)
- Decision type inconsistent with conviction level (DEFINITIVE conclusion mapped to EXPLORATORY action) → -0.10

---

#### QD-02: Consistency

**Definition:** The degree to which the decision is consistent with prior active decisions for the same subject entity and with the overall portfolio direction.

**Measurement:** Conflict check against active decisions; portfolio direction alignment score.

**Weight in DCS:** 0.15

**Degradation triggers:**
- Active decision for same entity in opposite direction (unresolved conflict) → -0.15
- Decision inconsistent with portfolio regime bias → -0.05

---

#### QD-03: Risk Awareness

**Definition:** The degree to which the decision reflects adequate risk assessment and is appropriately sized given the risk profile.

**Measurement:** Risk evaluation completeness score × risk dimension pass rate.

**Weight in DCS:** 0.15

**Degradation triggers:**
- Any risk dimension FAIL → -0.10 per failed dimension (max -0.30)
- Risk evaluation not completed → DCS cap at TENTATIVE (0.54)

---

#### QD-04: Explainability

**Definition:** The degree to which the decision has a complete, human-readable explanation record with all required fields populated.

**Measurement:** Explanation record completeness checklist score.

**Weight in DCS:** 0.10

**Constitutional constraint:** DEFINITIVE-tier decisions without complete explanation records cannot be delivered to Execution Engine (DC-C-001).

---

#### QD-05: Completeness

**Definition:** The degree to which all required decision fields are populated and all evaluation stages have been completed.

**Measurement:** Schema completeness fraction (required fields populated / total required fields).

**Weight in DCS:** 0.10

---

#### QD-06: Traceability

**Definition:** The ability to trace the decision through the full IIOS cognitive stack: Decision → Reasoning → Hypothesis → Evidence → Observation.

**Measurement:** Lineage completeness score — all ancestry links present and valid.

**Weight in DCS:** 0.08

---

#### QD-07: Governance

**Definition:** The degree to which the decision has been properly governed — correct tier assignment, domain ownership, retention policy, and constitutional rule compliance.

**Measurement:** Governance checklist score.

**Weight in DCS:** 0.07

---

#### QD-08: Confidence Calibration

**Definition:** The historical accuracy of the DCS tier assigned to similar decisions. Calibrated by the Learning System.

**Measurement:** Historical accuracy rate for decisions of the same type, domain, and tier.

**Weight in DCS:** 0.06

---

#### QD-09: Robustness

**Definition:** The stability of the decision under reasonable variations in the premises — if conviction drops by 0.20, does the decision still hold?

**Measurement:** Robustness test: reduce all premise conviction scores by 0.20 and recompute recommended action. If action is unchanged, robustness = HIGH.

**Weight in DCS:** 0.04

---

#### QD-10: Policy Compliance

**Definition:** The degree to which all applicable policies were checked and the decision is compliant.

**Measurement:** Policy check completeness × pass rate.

**Weight in DCS:** 0.03

**Constitutional constraint:** Any blocking policy FAIL → DCS cap at TENTATIVE regardless of other scores.

---

#### QD-11: Timeliness

**Definition:** The degree to which the decision was produced within the required time window given its priority and market context.

**Measurement:** Decision latency vs SLA for the priority level.

**Weight in DCS:** 0.01

**Degradation:** Late decisions (> 2x SLA) → -0.02

---

#### QD-12: Auditability

**Definition:** The completeness and integrity of the audit trail for this decision.

**Measurement:** Audit event count vs expected event count; hash chain integrity check.

**Weight in DCS:** 0.01

---

### 7.3 DCS Formula Reference

$$DCS = \sum_{d=1}^{12} w_d \cdot Q_d - \sum_{p} penalty_p$$

Subject to:
- $DCS \in [0.00, 1.00]$
- $\sum_{d=1}^{12} w_d = 1.00$
- Directional inconsistency (QD-01 failure): hard cap DCS ≤ 0.20
- Any risk FAIL (QD-03): cap DCS ≤ 0.54 (TENTATIVE max)
- Blocking policy FAIL (QD-10): cap DCS ≤ 0.54 (TENTATIVE max)
- Explanation missing (QD-04): cap DCS ≤ 0.69 (MODERATE max)

---

### 7.4 Quality Monitoring

| Metric | Alert threshold | Action |
|---|---|---|
| Average active decision DCS < 0.55 | Sustained 3+ cycles | Governance Manager review |
| Risk failure rate > 15% of candidates | Daily avg | Risk Engine calibration review |
| Policy failure rate > 10% | Daily avg | Policy Manager review |
| Explanation missing rate > 5% | Daily count | Explainability Manager health check |
| Human approval timeout rate > 20% | Daily avg | Human operator availability review |
| DCS calibration drift (actual accuracy vs tier target) > 10% | Weekly | Learning System calibration review |

---

## PART VIII — DECISION GOVERNANCE

### 8.1 Governance Tiers

| Tier | Definition | Examples |
|---|---|---|
| CRITICAL | Decisions that can significantly affect portfolio risk, capital allocation, or activate risk protocols | RSK-*, EMR-*, CAP-*, PRT-*, large position decisions |
| HIGH | Core tactical decisions on major indices and high-capital positions | Index BUY/SEL, positions > 2% portfolio, SEL-SHORT-INIT |
| MEDIUM | Standard tactical decisions on individual equities | Standard BUY/SEL/REDUCE/INC/HLD for equities < 2% portfolio |
| LOW | Non-action decisions and monitoring | MON, AVD, HLD-MONITORED |

---

### 8.2 Governance Matrix

| Dimension | CRITICAL | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| Approval required | TIER-2-HUMAN | TIER-1-AI or TIER-2 | TIER-1-AI | TIER-1-AI |
| DCS minimum | 0.55 | 0.50 | 0.40 | No minimum |
| Explanation required | Always | Always | Yes | Best effort |
| Risk evaluation | Full | Full | Standard | Abbreviated |
| Policy evaluation | Full | Full | Standard | Key policies |
| Retention | Permanent | 10 years | 5 years | 3 years |
| Audit record | Immutable | Immutable | Standard | Standard |
| Review cycle | Intraday | Daily | Weekly | Monthly |

---

### 8.3 Naming Standards

**Decision ID format:** `DEC-{CAT_CODE}-{TYPE_CODE}-{YYYYMMDD}-{SEQ:08d}`

Examples:
- `DEC-BUY-EQT-20260703-00000001` — Buy equity decision
- `DEC-SEL-SHORT-DRV-20260703-00000002` — Short derivative sell
- `DEC-RSK-HALT-20260703-00000001` — Risk halt decision
- `DEC-EMR-LIQUIDATE-20260703-00000001` — Emergency liquidation

---

### 8.4 Versioning Standards

- Version numbers start at 1
- Every material change increments the version
- Material changes: approval status change, risk reassessment, execution parameter modification, human override
- Non-material changes (annotation, comment additions) do not increment version
- All versions permanently preserved

---

### 8.5 Security and Confidentiality

| Control | Implementation |
|---|---|
| Access control | Service mesh mTLS authentication; role-based access |
| Encryption at rest | AES-256 for all persisted decision records |
| Encryption in transit | TLS 1.3 for all inter-service communication |
| Audit log integrity | Cryptographic hash chain |
| Input validation | All inputs schema-validated |
| Rate limiting | Maximum 500 Decision Generation Service calls per minute |
| Execution isolation | Decision Engine cannot initiate order placement directly |
| Human override always available | Technical mechanism never disabled |

---

### 8.6 Compliance

The Decision Engine produces decisions that may inform regulated trading activity. Compliance requirements:

| Requirement | Implementation |
|---|---|
| Trade decision audit trail | Immutable audit log with full event history |
| Algorithmic decision disclosure | is_ai_generated flag; explanation record |
| Human oversight capability | Human override always available; TIER-2/3 authority tiers |
| Best execution consideration | Execution parameters (price type, slippage limits) documented |
| Record retention | Per governance tier; CRITICAL = permanent |

---
## PART IX — DECISION CONSTITUTION

The Decision Engine Constitution defines the non-negotiable rules governing every Decision produced by the IIOS. Constitutional rules are coded as **DC-{Category}-{Number}**.

---

### Category DC-A: Decision Integrity

**DC-A-001** Every Decision output must be a complete, governed, risk-evaluated, policy-checked Decision. The Decision Engine must not produce advisory outputs, suggestions, or recommendations. Only complete Decisions are valid outputs.

**DC-A-002** The decision action type must be directionally consistent with the primary reasoning chain conclusion. A BUY decision based on a bearish reasoning chain is a constitutional violation.

**DC-A-003** Every Decision must have at least one premise reasoning chain with status ACTIVE. Decisions without active reasoning chain support cannot reach APPROVED status.

**DC-A-004** Decisions must not be constructed from CONTESTED reasoning chains as their sole basis. A CONTESTED chain may contribute to a Decision, but a non-contested chain must also be present.

**DC-A-005** Every Decision must have a valid subject entity. Decisions for invalid, non-existent, or delisted entities are prohibited.

**DC-A-006** Execution parameters must be internally consistent at all times. A LIMIT BUY with a limit price above the current market price without justification is a structural violation.

**DC-A-007** Every Decision must have a declared expiry condition or expiry timestamp. Open-ended Decisions with no expiry are prohibited.

**DC-A-008** Decisions for the same subject entity in directly opposing directions must not both be in COMMITTED status simultaneously. The Conflict Resolver must ensure only one direction is COMMITTED at any time.

**DC-A-009** No Decision may reference its own outcome as a premise (decision-outcome circularity is prohibited).

**DC-A-010** A Decision that has been REJECTED due to a structural defect must not be resubmitted unchanged. The defect must be corrected before resubmission.

---

### Category DC-B: Risk Integrity

**DC-B-001** Every Decision of governance tier HIGH or CRITICAL must undergo a complete risk evaluation before approval. Abbreviated risk evaluation is not permitted for these tiers.

**DC-B-002** A Decision must not be APPROVED if any risk dimension returns FAIL unless an explicit risk override is documented with justification and human approval.

**DC-B-003** Position size limits are non-negotiable. No APPROVED decision may specify a quantity that would cause the portfolio to exceed defined concentration limits.

**DC-B-004** When the portfolio daily drawdown exceeds 1.5%, no new BUY or INCREASE decisions may be approved without explicit TIER-2-HUMAN approval.

**DC-B-005** When the Risk Guardian signals ELEVATED or CRITICAL status, all new BUY and INCREASE decisions are automatically held pending Risk Guardian clearance.

**DC-B-006** Decisions that would reduce the remaining drawdown budget below 0.5% are prohibited without TIER-2-HUMAN approval.

**DC-B-007** No decision may explicitly disable or bypass the Decision Risk Engine evaluation. Risk evaluation is mandatory for all decisions of governance tier MEDIUM and above.

**DC-B-008** Risk decisions (RSK-* type) are always granted CRITICAL governance tier regardless of their stated size. Risk decisions are never downgraded in tier.

**DC-B-009** Emergency decisions (EMR-* type) may bypass normal risk evaluation timelines but must be retrospectively risk-evaluated and the record updated within 4 hours of execution.

**DC-B-010** Hedge decisions (HDG-*) must reference the position they are hedging. Unanchored hedges (hedges without a referenced position) are prohibited.

---

### Category DC-C: Explainability

**DC-C-001** Every COMMITTED Decision must have a complete explanation record before delivery to the Execution Engine. Decisions without explanation records cannot be COMMITTED.

**DC-C-002** The explanation record must include all required fields: premise_summary, reasoning_narrative, risk_rationale, conviction_statement, uncertainty_statement, conditions_for_reversal. Any missing field is a constitutional violation.

**DC-C-003** Explanation records must be refreshed within one processing cycle of any decision update. Stale explanations trigger a governance violation.

**DC-C-004** The uncertainty statement must explicitly quantify what is uncertain. A generic "uncertainty exists" statement is insufficient.

**DC-C-005** The conditions_for_reversal field must specify at least two concrete conditions. Generic or vacuous conditions are prohibited.

**DC-C-006** AI-generated decisions (is_ai_generated = True) must explicitly disclose this in the explanation record.

---

### Category DC-D: Traceability

**DC-D-001** Every Decision must have a complete lineage record tracing: Decision → Reasoning Chain → Hypothesis → Evidence → Observation. Missing lineage records are a constitutional violation.

**DC-D-002** The Decision Engine must support point-in-time reconstruction of its state at any historical timestamp. All state transitions must be recorded with UTC timestamps.

**DC-D-003** Every Decision version must be preserved. No version may be permanently deleted within the governance tier retention period.

**DC-D-004** When a Decision is superseded, the new Decision must reference the lineage of the prior Decision.

**DC-D-005** The audit trail must record every state transition with: actor, timestamp, previous state, new state, and reason for change. Incomplete audit records are a constitutional violation.

---

### Category DC-E: Consistency

**DC-E-001** Two directly contradictory Decisions for the same subject entity must not both be in COMMITTED status. The Dependency Manager must detect and resolve this within one cycle.

**DC-E-002** A Composite Decision must not be delivered to the Execution Engine with any sub-decision in REJECTED or CANCELLED status. The full composite must be complete.

**DC-E-003** Scheduled Decisions must be consistent with the market context at the time of their scheduled execution. A Scheduled Decision constructed in BULL_TREND that is to execute in CRISIS regime must be reviewed before execution.

**DC-E-004** The DCS tier must be consistent with the DCS value at all times. The Confidence Engine must enforce this. A DCS value of 0.82 with a tier of MODERATE is a constitutional violation.

---

### Category DC-F: Governance

**DC-F-001** Every Decision must have a governance tier assigned before PENDING_APPROVAL status. Untiered decisions are not eligible for approval.

**DC-F-002** Every Decision must have a domain owner assigned. Ownerless decisions are not eligible for approval.

**DC-F-003** Governance tier cannot be downgraded to avoid approval requirements. A CRITICAL decision cannot be re-tiered to MEDIUM to bypass TIER-2-HUMAN approval.

**DC-F-004** The Decision Engine must produce a daily governance summary report. Any day without a governance report is a constitutional violation.

**DC-F-005** Constitutional violations must be recorded in the Audit Manager within one processing cycle of detection.

---

### Category DC-G: Approval Integrity

**DC-G-001** The approval authority tier must be correctly assigned. Under-assigning authority (e.g., routing a CRITICAL decision to TIER-1-AI) is a constitutional violation.

**DC-G-002** TIER-2-HUMAN and TIER-3-HUMAN-ONLY approval records must contain the identity of the approving human. Anonymous human approvals are prohibited.

**DC-G-003** Approval records are immutable after creation. Approval records may not be amended to change a REJECTED outcome to APPROVED retroactively.

**DC-G-004** Approval timeout does not equal approval. A decision that has not received explicit approval within the timeout period remains in HELD status — it does not automatically become APPROVED.

**DC-G-005** Pre-approved emergency protocols must be reviewed and confirmed at minimum quarterly. Stale emergency protocols (> 90 days without review) are a constitutional violation.

---

### Category DC-H: Security

**DC-H-001** The Decision Engine must never initiate order placement directly. All decisions reach the Execution Engine via the Distribution Service only. No direct Execution Engine calls from Decision Engine components.

**DC-H-002** All inter-component communication must use authenticated service mesh connections. Unauthenticated component calls are prohibited.

**DC-H-003** Decision records must be encrypted at rest using AES-256.

**DC-H-004** The audit log must use a cryptographic hash chain. Any tampering must be immediately detectable.

**DC-H-005** Input validation must be applied to all Decision Generation Service inputs. Invalid inputs must be rejected before affecting internal state.

---

### Category DC-I: Auditability

**DC-I-001** The audit log is append-only. No audit record may be modified or deleted after creation.

**DC-I-002** Every decision creation, update, approval, rejection, and delivery event must be recorded in the audit log. No gap in the audit trail is acceptable.

**DC-I-003** Audit records must be cryptographically signed.

**DC-I-004** The audit log must support point-in-time reconstruction of the Decision Engine state at any historical timestamp.

**DC-I-005** Audit records must be stored in a physically separate location from the Decision Registry. A single storage failure must not destroy both.

---

### Category DC-J: Historical Preservation

**DC-J-001** Every Decision ever generated must be preserved in the archive for the governance tier retention period.

**DC-J-002** Archived decisions must be readable by the Learning System for performance attribution without data loss.

**DC-J-003** All versions of every Decision must be retrievable by version number.

**DC-J-004** The archive must survive system reboots, deployments, and schema migrations.

---

### Category DC-K: Quality

**DC-K-001** The minimum DCS for a Decision delivered to the Execution Engine is 0.40 (TENTATIVE minimum).

**DC-K-002** The average DCS of committed decisions must not fall below 0.50 for more than three consecutive cycles.

**DC-K-003** DEFINITIVE-tier decisions must have: complete explanation, full risk evaluation, full policy check, and complete lineage. Any missing requirement blocks DEFINITIVE tier assignment.

**DC-K-004** The Decision Engine must not produce more than 50 COMMITTED decisions per trading session without human operator review of the aggregate pattern.

---

### Category DC-L: Human Override

**DC-L-001** Human override of any Decision is absolute and unconditional. No component may block, delay, or condition a human override instruction.

**DC-L-002** Any AI-generated Decision above TIER-1 authority parameters is automatically escalated to TIER-2-HUMAN. AI authority is never self-extended.

**DC-L-003** Human override events must be recorded in the audit trail immediately, with the identity of the overriding operator and the reason for override.

**DC-L-004** When a human cancels a COMMITTED Decision, the Execution Engine must be immediately notified. The notification must arrive at the Execution Engine before order placement.

**DC-L-005** The human operator interface (Telegram bot, Streamlit dashboard) must always provide the mechanism for override, hold, and cancel for any COMMITTED Decision.

---

### Category DC-M: AI Collaboration

**DC-M-001** When AI and human are collaborating on a decision (Hybrid type), the AI analytical contribution and the human modification must both be documented in the decision record.

**DC-M-002** The AI must not misrepresent the basis of a decision. If the AI analytical basis is weak, the explanation record must acknowledge this.

**DC-M-003** AI decisions must not contradict explicit human instructions received via the policy system or override mechanism.

---

### Category DC-N: Policy Compliance

**DC-N-001** No COMMITTED Decision may violate any active policy. Policy compliance is non-negotiable for commitment.

**DC-N-002** Policy changes take effect immediately upon loading. Decisions in-flight at the time of a policy change must be re-evaluated against the new policy before approval.

**DC-N-003** Policy override for CRITICAL situations must be explicitly documented with justification, human approval, and audit record. Policies cannot be silently bypassed.

**DC-N-004** Regime-conditional policies activate automatically when the regime classification changes. The Policy Manager is responsible for real-time policy switching.

---
## PART X — DECISION READINESS CHECKLIST

The Decision Readiness Checklist (DRC) is the gate between the Decision Engine and the Execution Engine. Before any Decision transitions from APPROVED to COMMITTED, the DRC performs 14 sequential verification passes. Any FAIL in a mandatory check blocks COMMITTED status.

---

### DRC Section 1: Reasoning Foundation Complete

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 1.1 | At least one ACTIVE reasoning chain linked | Yes | Yes |
| 1.2 | Primary reasoning chain conclusion direction matches decision action direction | Yes | Yes |
| 1.3 | RCS (Reasoning Confidence Score) of primary chain >= 0.35 | Yes | Yes |
| 1.4 | No CONTESTED reasoning chain as sole basis | Yes | Yes |
| 1.5 | Reasoning chain produced within valid recency window for this priority level | Yes | Yes |

---

### DRC Section 2: Risk Evaluation Complete

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 2.1 | Risk evaluation status = PASS or CONDITIONAL_PASS | Yes | Yes |
| 2.2 | All 6 risk dimensions evaluated (size, concentration, liquidity, regime, drawdown, correlation) | Yes | Yes |
| 2.3 | No risk dimension in FAIL state | Yes | Yes |
| 2.4 | Drawdown budget not exceeded by this decision | Yes | Yes |
| 2.5 | Position size within portfolio concentration limit | Yes | Yes |
| 2.6 | Risk Guardian status not CRITICAL | Yes | Yes |

---

### DRC Section 3: Confidence Score Valid

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 3.1 | DCS >= 0.40 (minimum TENTATIVE threshold) | Yes | Yes |
| 3.2 | DCS tier consistent with DCS value | Yes | Yes |
| 3.3 | DCS computation timestamp < 5 minutes ago (not stale) | Yes | Yes |
| 3.4 | Confidence tier matches governance tier minimum requirements | Yes | Yes |
| 3.5 | No quality dimension in hard-blocking failure state | Yes | Yes |

---

### DRC Section 4: Policy Compliance Verified

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 4.1 | Policy evaluation status = PASS or WARN | Yes | Yes |
| 4.2 | No blocking policy in FAIL state | Yes | Yes |
| 4.3 | All regime-conditional policies evaluated for current regime | Yes | Yes |
| 4.4 | Entity-specific policies checked | Yes | Yes |
| 4.5 | Session-level position limits not exceeded | Yes | Yes |

---

### DRC Section 5: Approval Complete

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 5.1 | Approval record present | Yes | Yes |
| 5.2 | Approval status = APPROVED | Yes | Yes |
| 5.3 | Correct approval authority tier was used | Yes | Yes |
| 5.4 | Approval record timestamp < SLA max age | Yes | Yes |
| 5.5 | TIER-2/TIER-3 approvals include approver identity | Yes | Yes |

---

### DRC Section 6: Decision Package Complete

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 6.1 | All required Decision schema fields populated | Yes | Yes |
| 6.2 | Execution parameters complete (action, size, price, expiry) | Yes | Yes |
| 6.3 | Decision expiry set to future timestamp | Yes | Yes |
| 6.4 | Counter-arguments record populated | Yes | Yes |
| 6.5 | Risk conditions record populated | Yes | Yes |
| 6.6 | Explanation record present | Yes | Yes |
| 6.7 | All explanation fields populated | Yes (for HIGH/CRITICAL) | Yes |
| 6.8 | Package completeness check score >= 0.95 | Yes | Yes |

---

### DRC Section 7: Traceability Complete

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 7.1 | Lineage record present | Yes | Yes |
| 7.2 | Decision lineage traces to at least one Observation | Yes | Yes |
| 7.3 | All referenced entity IDs resolve to valid entities | Yes | Yes |
| 7.4 | Decision canonical ID is unique | Yes | Yes |

---

### DRC Section 8: Governance Valid

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 8.1 | Governance tier assigned | Yes | Yes |
| 8.2 | Domain owner assigned | Yes | Yes |
| 8.3 | Retention policy assigned | Yes | Yes |
| 8.4 | Governance tier consistent with decision type | Yes | Yes |

---

### DRC Section 9: Audit Trail Complete

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 9.1 | At least 4 audit events recorded (CREATED, EVALUATED, RISK_EVALUATED, APPROVED) | Yes | Yes |
| 9.2 | Audit hash chain intact | Yes | Yes |
| 9.3 | No audit gap (missing state transitions) | Yes | Yes |

---

### DRC Section 10: Archive Verification (conditional)

Applies only when COMMITTED decisions for the same entity exist in the archive at DEFINITIVE tier.

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 10.1 | New decision does not contradict archive pattern for entity | No | No |
| 10.2 | Historical performance attribution record for entity is current | No | No |
| 10.3 | Learning System has confirmed no systematic errors in similar decisions | No | No (warn only) |

---

### DRC Section 11: Counter-Arguments Considered

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 11.1 | Counter-argument generation was attempted | Yes | No |
| 11.2 | Strongest counter-argument documented | Yes | Yes (for DEFINITIVE tier) |
| 11.3 | Response to strongest counter-argument documented | Yes | Yes (for DEFINITIVE tier) |
| 11.4 | Counter-argument has not changed recommended action (or override noted) | Yes | No (warn) |

---

### DRC Section 12: Execution Parameters Valid

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 12.1 | action_type is a valid Decision type code | Yes | Yes |
| 12.2 | entry_price_type is a valid enum value | Yes | Yes |
| 12.3 | If LIMIT type: limit_price is set | Yes | Yes |
| 12.4 | quantity > 0 for BUY/SELL/INCREASE types | Yes | Yes |
| 12.5 | max_slippage_pct within permitted range | Yes | Yes |

---

### DRC Section 13: Ready for Execution Engine

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 13.1 | Execution Engine availability check PASS | Yes | Yes |
| 13.2 | No active human hold flag on this entity | Yes | Yes |
| 13.3 | Market is open OR this is a scheduled decision for next open | Yes | Yes |
| 13.4 | Risk Guardian status is NORMAL or MONITORING | Yes | Yes |
| 13.5 | No active portfolio kill-switch | Yes | Yes |
| 13.6 | Execution Engine circuit breaker is CLOSED | Yes | Yes |
| 13.7 | No superseding Decision received in last processing cycle | Yes | Yes |
| 13.8 | Decision not already in EXECUTED or CANCELLED state | Yes | Yes |

---

### DRC Section 14: Use-Case Readiness Matrix

The following matrix summarizes the minimum DRC pass rate required for different trading use cases:

| Use Case | Min DCS | Required Sections | Approval Required |
|---|---|---|---|
| Automated equity trading | 0.50 | 1-9, 12, 13 | TIER-1-AI |
| Automated derivative trading | 0.55 | 1-9, 11-13 | TIER-1-AI or TIER-2 |
| Emergency risk halt | 0.30 (special) | 2, 5, 9, 13 | EMERGENCY protocol |
| Human-assisted trading | 0.40 | 1-9, 11, 12, 13 | TIER-2-HUMAN |
| Portfolio rebalancing | 0.50 | 1-9, 12, 13 | TIER-1-AI |
| Capital allocation | 0.60 | 1-9, 11-13 | TIER-2-HUMAN |

---
---

## SUPPLEMENT A — FULL DECISION TAXONOMY REFERENCE

### A.1 Overview

The IIOS Decision Engine recognises 20 canonical Decision types organised into 6 categories. This supplement provides the complete reference for each type including sub-types, canonical codes, governance defaults, minimum DCS, approval authority, and applicable market regimes.

---

### A.2 Category ENTRY — Position Entry Decisions

| Code | Name | Sub-types | Min DCS | Default Tier | Approval |
|---|---|---|---|---|---|
| BUY | Buy | BUY-EQT, BUY-DRV, BUY-IDX, BUY-ETF | 0.50 | HIGH | TIER-1-AI |
| SEL | Sell/Short | SEL-CLOSE, SEL-SHORT-INIT, SEL-SHORT-ADD | 0.50 | HIGH | TIER-1-AI |

**BUY — Buy Decision**

Purpose: Directs the Execution Engine to acquire a long position in the specified entity.

Required fields beyond base schema: entry_price_type, limit_price (if LIMIT), quantity, stop_loss_price, take_profit_price.

Sub-type governance:
- BUY-EQT: Standard equity long. Governance tier HIGH.
- BUY-DRV: Derivative (option) long. Governance tier HIGH. Requires DCS >= 0.55.
- BUY-IDX: Index instrument long (futures, ETF). Governance tier HIGH.
- BUY-ETF: Exchange traded fund long. Governance tier MEDIUM.

Applicable regimes: All regimes permitted, but CRISIS regime requires DCS >= 0.65 and TIER-2-HUMAN approval.

Constitutional constraints: BUY decisions during active drawdown > 1.5% require DC-B-004 compliance check.

---

**SEL — Sell/Short Decision**

Purpose: Directs the Execution Engine to close a long position or initiate/add to a short position.

Sub-type governance:
- SEL-CLOSE: Close existing long position. Governance tier MEDIUM.
- SEL-SHORT-INIT: Initiate new short position. Governance tier HIGH. DCS >= 0.55.
- SEL-SHORT-ADD: Add to existing short position. Governance tier HIGH.

Applicable regimes: SEL-SHORT-INIT is prohibited in STRONG_BULL_TREND regime unless explicitly flagged as hedging decision.

---

### A.3 Category POSITION — Position Management Decisions

| Code | Name | Sub-types | Min DCS | Default Tier | Approval |
|---|---|---|---|---|---|
| HLD | Hold | HLD-CONFIRMED, HLD-MONITORED, HLD-PENDING_REVIEW | 0.30 | LOW | TIER-1-AI |
| RED | Reduce | RED-PARTIAL, RED-SCALE | 0.40 | MEDIUM | TIER-1-AI |
| INC | Increase | INC-SCALE, INC-PYRAMID | 0.50 | MEDIUM | TIER-1-AI |
| EXT | Exit | EXT-SL, EXT-TP, EXT-MANAGED, EXT-EMERGENCY | 0.35 | MEDIUM | TIER-1-AI |

**HLD — Hold Decision**

Purpose: Explicitly documents the decision to continue holding a position. A documented HOLD is an active decision, not an absence of decision.

Sub-types:
- HLD-CONFIRMED: High-conviction hold. Premises remain valid, position thesis intact.
- HLD-MONITORED: Hold with monitoring flag. Premises partially weakened; monitoring for change.
- HLD-PENDING_REVIEW: Hold pending upcoming event (earnings, policy announcement).

Constitutional note: HLD-PENDING_REVIEW must have an explicit review trigger timestamp or event.

---

**RED — Reduce Decision**

Purpose: Directs Execution Engine to reduce an existing position without closing it.

Sub-types:
- RED-PARTIAL: Reduce by a fixed quantity.
- RED-SCALE: Reduce by a percentage of current holding.

Minimum information: must specify reduction quantity or percentage, and document the reason for partial reduction vs full exit.

---

**INC — Increase Decision**

Purpose: Directs Execution Engine to add to an existing position (pyramiding or scaling in).

Sub-types:
- INC-SCALE: Proportional add based on conviction increase.
- INC-PYRAMID: Pyramid add — smaller add as price moves in favour.

Constitutional note: INC decisions must pass concentration check — the increased position must not exceed concentration limits post-increase.

---

**EXT — Exit Decision**

Purpose: Directs Execution Engine to close an entire position.

Sub-types:
- EXT-SL: Stop loss triggered exit. Minimum DCS 0.30 (speed is priority).
- EXT-TP: Take profit triggered exit.
- EXT-MANAGED: Managed exit based on changing thesis.
- EXT-EMERGENCY: Emergency exit, often triggered by Risk Guardian or EMR decision.

---

### A.4 Category TACTICAL — Tactical and Strategic Decisions

| Code | Name | Sub-types | Min DCS | Default Tier | Approval |
|---|---|---|---|---|---|
| AVD | Avoid | AVD-CONFIRMED, AVD-WATCHLIST | 0.30 | LOW | TIER-1-AI |
| MON | Monitor | MON-PASSIVE, MON-ACTIVE, MON-ALERT | 0.20 | LOW | TIER-1-AI |
| RBL | Rebalance | RBL-SCHEDULED, RBL-TACTICAL | 0.45 | MEDIUM | TIER-1-AI |
| HDG | Hedge | HDG-PORTFOLIO, HDG-POSITION | 0.50 | HIGH | TIER-1-AI |
| PRT | Protect | PRT-SL, PRT-TRAILING, PRT-COLLAR | 0.40 | HIGH | TIER-1-AI |

**AVD — Avoid Decision**

Purpose: Explicit decision NOT to enter a position in the specified entity. Documents the reasoning for avoidance, creating a record that prevents repeated evaluation without new information.

Constitutional note: AVD decisions expire when the reasoning premises change materially.

---

**MON — Monitor Decision**

Purpose: Initiates a monitoring watch on an entity without a position. Directs the system to continue tracking the entity for entry conditions.

Sub-types:
- MON-PASSIVE: Standard background monitoring.
- MON-ACTIVE: Elevated monitoring with alert thresholds.
- MON-ALERT: Pre-entry monitoring with specific trigger conditions.

---

**RBL — Rebalance Decision**

Purpose: Portfolio-level rebalancing decision. May involve multiple simultaneous position adjustments.

Composite decision: RBL decisions may generate multiple child BUY/SEL/RED decisions. The parent RBL decision governs the composite.

---

**HDG — Hedge Decision**

Purpose: Initiates a hedging position to reduce risk exposure of an existing position or the overall portfolio.

Constitutional note DC-B-010: Every HDG decision must reference the position being hedged (hedged_position_id). Unanchored hedges are prohibited.

---

**PRT — Protect Decision**

Purpose: Establishes or modifies protective mechanisms for existing positions (stop-loss orders, trailing stops, protective collars).

---

### A.5 Category RISK — Risk Management Decisions

| Code | Name | Sub-types | Min DCS | Default Tier | Approval |
|---|---|---|---|---|---|
| RSK | Risk action | RSK-REDUCE, RSK-HALT, RSK-PROTOCOL | 0.30 | CRITICAL | TIER-2-HUMAN |
| CAP | Capital | CAP-ALLOCATE, CAP-WITHDRAW, CAP-RESEREVE | 0.55 | CRITICAL | TIER-2-HUMAN |

**RSK — Risk Decision**

Purpose: Activates risk management actions at the portfolio level. The most consequential decision type in terms of immediate impact.

Sub-types:
- RSK-REDUCE: Reduce overall portfolio risk (reduce multiple positions).
- RSK-HALT: Halt all new position entry activity.
- RSK-PROTOCOL: Activate a named risk protocol (e.g., drawdown recovery protocol).

Constitutional note: RSK decisions are always CRITICAL tier (DC-B-008). They cannot be downgraded.

---

**CAP — Capital Decision**

Purpose: Directs changes to capital allocation buckets.

Sub-types:
- CAP-ALLOCATE: Allocate capital to a strategy or domain.
- CAP-WITHDRAW: Reduce capital allocation.
- CAP-RESERVE: Reserve capital for upcoming opportunities.

---

### A.6 Category OVERRIDE — Human Override and AI Override Decisions

| Code | Name | Sub-types | Min DCS | Default Tier | Approval |
|---|---|---|---|---|---|
| AID | AI directive | AID-FORCE, AID-BLOCK | 0.40 | HIGH | TIER-2-HUMAN |
| HUM | Human | HUM-OVERRIDE, HUM-INSTRUCTION | Any | HIGH | TIER-3-HUMAN-ONLY |
| HYB | Hybrid | HYB-AI_BASE, HYB-HUMAN_MOD | 0.40 | HIGH | TIER-2-HUMAN |

**HUM — Human Decision**

Purpose: Decision generated entirely by a human operator. The AI provides analysis and context but the human generates the decision.

Constitutional note: HUM decisions require TIER-3-HUMAN-ONLY approval. AI cannot approve its own override.

---

### A.7 Category SPECIAL — Special Regime Decisions

| Code | Name | Sub-types | Min DCS | Default Tier | Approval |
|---|---|---|---|---|---|
| EMR | Emergency | EMR-LIQUIDATE, EMR-HALT, EMR-PARTIAL_LIQ | 0.20 | CRITICAL | EMERGENCY |
| CON | Contingency | CON-SCENARIO_A, CON-SCENARIO_B | 0.40 | CRITICAL | EMERGENCY |
| SCH | Scheduled | SCH-PRE_MARKET, SCH-EOD, SCH-WEEKLY | 0.40 | MEDIUM | TIER-1-AI |
| CMP | Composite | CMP-PORTFOLIO, CMP-STRATEGY | 0.50 | HIGH | TIER-1-AI or TIER-2 |

**EMR — Emergency Decision**

Purpose: Activated in response to extreme market conditions, circuit breaker triggers, or Risk Guardian CRITICAL status.

Constitutional note: EMR decisions use EMERGENCY pre-approved protocols. They bypass normal approval timelines but must be retrospectively documented within 4 hours (DC-B-009).

---

**SCH — Scheduled Decision**

Purpose: Pre-constructed decision for deferred execution at a future timestamp or market event.

Constitutional note: Scheduled decisions must be re-evaluated against current market context before execution if their construction timestamp is > 4 hours before scheduled execution.

---

**CMP — Composite Decision**

Purpose: Parent decision that governs a set of related child decisions. Used for complex multi-leg strategies.

Constitutional note: All child decisions must reach COMMITTED status before the Composite is delivered to the Execution Engine (DC-A-008).

---

### A.8 DCS Minimum by Regime

| Decision Category | STRONG_BULL | BULL_TREND | SIDEWAYS | BEAR_TREND | CRISIS |
|---|---|---|---|---|---|
| ENTRY BUY | 0.45 | 0.50 | 0.55 | 0.60 | 0.70 |
| ENTRY SEL (short) | 0.60 | 0.55 | 0.50 | 0.45 | 0.40 |
| POSITION MGMT | 0.35 | 0.35 | 0.35 | 0.40 | 0.50 |
| TACTICAL | 0.30 | 0.30 | 0.30 | 0.30 | 0.35 |
| RISK | 0.25 | 0.25 | 0.25 | 0.25 | 0.20 |
| SPECIAL-EMR | 0.20 | 0.20 | 0.20 | 0.20 | 0.20 |

---
## SUPPLEMENT B — DECISION PACKAGE STRUCTURE

### B.1 Overview

The Decision Package is the primary output artifact of the Decision Engine. It is a self-contained, structured record that encapsulates everything the Execution Engine needs to place orders, and everything required for audit, compliance, and learning purposes.

The Decision Package is sealed at the moment a Decision transitions to COMMITTED status. It is immutable after sealing.

---

### B.2 Decision Package Top-Level Structure

`
Decision Package
 |
 +-- [Header Block]            Identification, type, status, timestamps
 |
 +-- [Subject Block]           Entity being decided on
 |
 +-- [Execution Block]         Parameters for the Execution Engine
 |
 +-- [Confidence Block]        DCS score, tier, supporting metrics
 |
 +-- [Reasoning Reference]     Linked reasoning chains and their key outputs
 |
 +-- [Risk Block]              Risk evaluation record
 |
 +-- [Policy Block]            Policy check record
 |
 +-- [Approval Block]          Approval record, approver, timestamp
 |
 +-- [Explanation Block]       Human-readable explanation record
 |
 +-- [Counter-Arguments Block] Documented challenges and responses
 |
 +-- [Conditions Block]        Active conditions, expiry conditions, review triggers
 |
 +-- [Lineage Block]           Full ancestry: observation → evidence → hypothesis → reasoning → decision
 |
 +-- [Governance Block]        Tier, owner, retention, constitutional rules checked
 |
 +-- [Audit Reference Block]   List of audit event IDs for this decision
 |
 +-- [Version Block]           Version number, change history
`

---

### B.3 Header Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| decision_id | string | Yes | Canonical ID: DEC-{CAT}-{TYPE}-{DATE}-{SEQ:08d} |
| package_version | int | Yes | Version of this Decision Package (starts at 1) |
| schema_version | string | Yes | Schema version: "2026.1" |
| created_at | datetime (UTC) | Yes | Creation timestamp |
| committed_at | datetime (UTC) | Yes | Seal timestamp (set at COMMITTED status) |
| decision_type | enum | Yes | See Supplement A type codes |
| decision_category | enum | Yes | ENTRY, POSITION, TACTICAL, RISK, OVERRIDE, SPECIAL |
| status | enum | Yes | Lifecycle status at package creation |
| priority | enum | Yes | URGENT, HIGH, NORMAL, LOW, BACKGROUND |
| governance_tier | enum | Yes | CRITICAL, HIGH, MEDIUM, LOW |
| is_ai_generated | bool | Yes | True if generated by Decision Builder AI |
| is_human_modified | bool | Yes | True if human has modified the AI decision |
| has_emergency_protocol | bool | Yes | True if EMR type using emergency protocol |
| domain | string | Yes | Domain classification (INDEX, EQUITY, DERIVATIVES, etc.) |
| domain_owner | string | Yes | Owning module/agent identity |
| session_id | string | Yes | Trading session ID this decision belongs to |
| parent_decision_id | string | No | Parent decision ID (for composite sub-decisions) |
| supersedes_id | string | No | ID of decision this supersedes |
| superseded_by_id | string | No | ID of decision that supersedes this one |

---

### B.4 Subject Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| entity_id | string | Yes | Canonical entity ID from Entity Engine |
| entity_type | enum | Yes | EQUITY, DERIVATIVE, INDEX, ETF, PORTFOLIO |
| entity_name | string | Yes | Human-readable name (e.g., "NIFTY 50") |
| exchange | string | Yes | Exchange code (NSE, BSE, NFO) |
| instrument_token | string | No | Broker instrument token (if known at decision time) |
| current_price_at_decision | float | No | LTP at time of decision construction |
| current_price_timestamp | datetime | No | Timestamp of the price used |
| current_position_size | int | No | Current position size (0 if no position) |
| current_position_direction | enum | No | LONG, SHORT, NONE |

---

### B.5 Execution Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| action_type | enum | Yes | Execution action (BUY, SELL, HOLD, EXIT, etc.) |
| entry_price_type | enum | Yes | MARKET, LIMIT, SL, SL-M |
| limit_price | float | No | Limit price (required if LIMIT) |
| trigger_price | float | No | Trigger price (required if SL or SL-M) |
| quantity | int | Yes (for entry/exit) | Number of shares / lots / contracts |
| quantity_unit | enum | Yes | SHARES, LOTS, CONTRACTS, PCT_OF_POSITION |
| max_slippage_pct | float | Yes | Maximum acceptable slippage as % |
| time_in_force | enum | Yes | DAY, GTC, IOC, GTD |
| stop_loss_price | float | No | Stop loss level (for new entries) |
| take_profit_price | float | No | Take profit level (for new entries) |
| stop_loss_type | enum | No | HARD, TRAILING, DYNAMIC |
| expiry_at | datetime | No | Decision expiry timestamp |
| expiry_condition | string | No | Expiry condition description |
| pre_conditions | list[string] | No | Conditions that must be true before execution |
| post_conditions | list[string] | No | Actions to take after execution |
| execution_notes | string | No | Free-text notes for the Execution Engine |

---

### B.6 Confidence Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| dcs | float | Yes | Decision Confidence Score [0.0, 1.0] |
| dcs_tier | enum | Yes | DEFINITIVE, CONFIRMED, MODERATE, TENTATIVE, EXPLORATORY |
| dcs_computed_at | datetime | Yes | DCS computation timestamp |
| dcs_weights_used | dict | Yes | Weights applied in DCS computation |
| quality_dimension_scores | dict | Yes | Score for each of the 12 quality dimensions |
| quality_dimension_failures | list | No | Any quality dimensions with degradation |
| primary_rcs | float | Yes | RCS of the primary reasoning chain |
| conviction_level | enum | Yes | From reasoning chain conclusion |
| uncertainty_sources | list[string] | Yes | Sources of uncertainty |
| calibration_reference | string | No | Historical calibration record ID |

---

### B.7 Reasoning Reference Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| primary_chain_id | string | Yes | ID of the primary reasoning chain |
| primary_chain_status | enum | Yes | Status of primary chain at decision time |
| primary_chain_conclusion | string | Yes | Conclusion text from primary chain |
| primary_chain_direction | enum | Yes | BULLISH, BEARISH, NEUTRAL, AMBIGUOUS |
| supporting_chain_ids | list[string] | No | Additional supporting reasoning chains |
| contesting_chain_ids | list[string] | No | Contesting reasoning chains (if any) |
| reasoning_summary | string | Yes | 1-3 sentence human-readable reasoning summary |
| key_premises | list[string] | Yes | Top 3-5 premises from primary chain |
| weakest_premise | string | Yes | Most uncertain premise |

---

### B.8 Risk Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| risk_evaluation_id | string | Yes | ID of the risk evaluation record |
| risk_verdict | enum | Yes | PASS, CONDITIONAL_PASS, FAIL |
| risk_tier | enum | Yes | VERY_HIGH, HIGH, MEDIUM, LOW, MINIMAL |
| dimension_results | dict | Yes | Results for all 6 risk dimensions |
| risk_conditions | list[string] | No | Conditions from CONDITIONAL_PASS |
| drawdown_budget_remaining_pct | float | Yes | % drawdown budget remaining |
| position_size_as_pct_portfolio | float | Yes | Proposed position as % of portfolio |
| concentration_check | bool | Yes | True if concentration check passed |
| regime_alignment | enum | Yes | ALIGNED, NEUTRAL, MISALIGNED |
| risk_guardian_status | enum | Yes | NORMAL, MONITORING, ELEVATED, CRITICAL |

---

### B.9 Approval Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| approval_authority_tier | enum | Yes | TIER-1-AI, TIER-2-HUMAN, TIER-3-HUMAN-ONLY, EMERGENCY |
| approval_status | enum | Yes | APPROVED, REJECTED, HELD |
| approved_at | datetime | No | Approval timestamp |
| approved_by | string | No | Approver identity (required for TIER-2/3) |
| approval_basis | string | No | Basis for approval |
| rejection_reason | string | No | Required if REJECTED |
| override_record | dict | No | Human override record (if applicable) |

---

### B.10 Explanation Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| explanation_id | string | Yes | Canonical explanation record ID |
| premise_summary | string | Yes | Brief summary of key premises |
| reasoning_narrative | string | Yes | Narrative of the reasoning process |
| risk_rationale | string | Yes | Why the risk is acceptable |
| conviction_statement | string | Yes | What drives conviction in this decision |
| uncertainty_statement | string | Yes | What remains uncertain and why |
| conditions_for_reversal | list[string] | Yes | At least 2 concrete conditions for reversal |
| decision_logic | string | Yes | Step-by-step logic connecting premises to decision |
| plain_language_summary | string | Yes | Summary readable by non-specialist human |
| explanation_generated_at | datetime | Yes | Timestamp |

---

### B.11 Lineage Block (Annotated Schema)

| Field | Type | Required | Description |
|---|---|---|---|
| lineage_id | string | Yes | Canonical lineage record ID |
| decision_id | string | Yes | Back-reference to decision |
| reasoning_chain_ids | list[string] | Yes | All linked reasoning chains |
| hypothesis_ids | list[string] | Yes | All linked hypotheses |
| evidence_ids | list[string] | No | Linked evidence records (if available) |
| observation_ids | list[string] | No | Root observations |
| lineage_completeness_score | float | Yes | 0.0-1.0; must be >= 0.80 for COMMITTED |
| lineage_constructed_at | datetime | Yes | Timestamp |

---
## SUPPLEMENT C — APPROVAL AUTHORITY MATRIX

### C.1 Overview

The Approval Authority Matrix defines the approval tier required for every combination of decision type, governance tier, and market regime. Approval authority can only be escalated, never reduced. If multiple matrix rows apply, the highest tier governs.

---

### C.2 Base Approval Matrix by Governance Tier

| Governance Tier | Default Approval | In SIDEWAYS | In BEAR_TREND | In CRISIS |
|---|---|---|---|---|
| CRITICAL | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| HIGH | TIER-1-AI | TIER-1-AI | TIER-2-HUMAN | TIER-2-HUMAN |
| MEDIUM | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-2-HUMAN |
| LOW | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-1-AI |

---

### C.3 Override Rules

The following rules escalate approval authority beyond the base matrix:

| Rule | Trigger | Escalation |
|---|---|---|
| C-OVR-001 | Position size > 2% portfolio | Escalate to next tier |
| C-OVR-002 | New short position (SEL-SHORT-INIT) | Escalate to TIER-2-HUMAN minimum |
| C-OVR-003 | DCS < 0.50 (TENTATIVE tier) | Escalate to TIER-2-HUMAN |
| C-OVR-004 | Risk Guardian status ELEVATED | Escalate all HIGH to TIER-2-HUMAN |
| C-OVR-005 | Portfolio daily drawdown > 1.5% | Escalate all BUY/INC to TIER-2-HUMAN |
| C-OVR-006 | EMR type decision | Use EMERGENCY protocol |
| C-OVR-007 | HUM type decision | Always TIER-3-HUMAN-ONLY |
| C-OVR-008 | Capital decision (CAP-*) | TIER-2-HUMAN minimum |
| C-OVR-009 | Risk decision (RSK-*) | TIER-2-HUMAN minimum |
| C-OVR-010 | Weekend or holiday pre-market | Escalate all CRITICAL to TIER-3 |

---

### C.4 Decision Type Approval Matrix

| Decision Type | Normal | BEAR_TREND | CRISIS | Risk Guardian ELEVATED |
|---|---|---|---|---|
| BUY-EQT | TIER-1-AI | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| BUY-DRV | TIER-1-AI | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| SEL-CLOSE | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-1-AI |
| SEL-SHORT-INIT | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| HLD | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-1-AI |
| RED-PARTIAL | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-1-AI |
| INC | TIER-1-AI | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| EXT-SL | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-1-AI |
| EXT-EMERGENCY | EMERGENCY | EMERGENCY | EMERGENCY | EMERGENCY |
| AVD | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-1-AI |
| MON | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-1-AI |
| RBL | TIER-1-AI | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| HDG | TIER-1-AI | TIER-1-AI | TIER-2-HUMAN | TIER-2-HUMAN |
| PRT | TIER-1-AI | TIER-1-AI | TIER-1-AI | TIER-1-AI |
| RSK-REDUCE | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| RSK-HALT | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| CAP-ALLOCATE | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| AID | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN | TIER-2-HUMAN |
| HUM | TIER-3-HUMAN | TIER-3-HUMAN | TIER-3-HUMAN | TIER-3-HUMAN |
| EMR | EMERGENCY | EMERGENCY | EMERGENCY | EMERGENCY |

---

### C.5 Approval Timeout Policies

| Approval Tier | Normal Timeout | URGENT Priority | After Timeout |
|---|---|---|---|
| TIER-1-AI | < 30ms | < 30ms | Reject if fail |
| TIER-2-HUMAN | 30 minutes | 10 minutes | HELD; alert human |
| TIER-3-HUMAN-ONLY | 60 minutes | 20 minutes | HELD; escalation alert |
| EMERGENCY | Pre-approved; < 500ms | < 500ms | Fallback protocol |

---

## SUPPLEMENT D — RISK EVALUATION MATRIX

### D.1 Overview

The Decision Risk Engine evaluates 6 risk dimensions for every Decision candidate. This supplement documents the thresholds and assessment logic for each dimension across all decision types and market regimes.

---

### D.2 Risk Dimension Reference

#### Dimension R-01: Position Size

**Definition:** The proposed position size as a percentage of portfolio net asset value.

| Assessment | Threshold | Verdict |
|---|---|---|
| MINIMAL | < 0.5% of NAV | PASS |
| LOW | 0.5% - 1.0% of NAV | PASS |
| MEDIUM | 1.0% - 2.0% of NAV | PASS |
| HIGH | 2.0% - 3.0% of NAV | CONDITIONAL_PASS; TIER-2-HUMAN escalation |
| VERY_HIGH | > 3.0% of NAV | FAIL |

In CRISIS regime, HIGH threshold reduces to 1.5% - 2.0%, VERY_HIGH to > 2.0%.

---

#### Dimension R-02: Concentration

**Definition:** The resulting concentration in any single entity, sector, or index after the proposed decision.

| Scope | Max Allowed | In CRISIS |
|---|---|---|
| Single entity (equity) | 5% NAV | 3% NAV |
| Single entity (derivative) | 3% NAV | 2% NAV |
| Sector total | 20% NAV | 15% NAV |
| Index instruments | 25% NAV | 20% NAV |

Any proposed decision that would cause a breach → FAIL.

---

#### Dimension R-03: Liquidity

**Definition:** Assessment of whether the decision can be executed at the specified size without causing material market impact.

| ADV Fraction | Assessment | Verdict |
|---|---|---|
| < 0.5% of 20-day ADV | VERY_LIQUID | PASS |
| 0.5% - 2.0% ADV | LIQUID | PASS |
| 2.0% - 5.0% ADV | MODERATE_LIQUIDITY | CONDITIONAL_PASS |
| 5.0% - 10.0% ADV | LOW_LIQUIDITY | CONDITIONAL_PASS; warn |
| > 10.0% ADV | ILLIQUID | FAIL |

ADV = Average Daily Volume.

---

#### Dimension R-04: Regime Alignment

**Definition:** Whether the decision direction is aligned with the current market regime.

| Decision Direction | Current Regime | Alignment | Verdict |
|---|---|---|---|
| BUY (long) | STRONG_BULL or BULL_TREND | ALIGNED | PASS |
| BUY (long) | SIDEWAYS | NEUTRAL | CONDITIONAL_PASS |
| BUY (long) | BEAR_TREND | MISALIGNED | CONDITIONAL_PASS; DCS penalised |
| BUY (long) | CRISIS | STRONGLY_MISALIGNED | FAIL for new entries |
| SELL (short) | CRISIS | ALIGNED | PASS |
| SELL (short) | BULL_TREND | MISALIGNED | CONDITIONAL_PASS |
| EXIT | Any regime | N/A | PASS (always) |

---

#### Dimension R-05: Drawdown Budget

**Definition:** Whether executing this decision would cause the portfolio daily drawdown to exceed defined limits.

| Daily P&L | Budget Remaining | BUY/INC Verdict | SELL/EXIT Verdict |
|---|---|---|---|
| Positive | > 2.0% remaining | PASS | PASS |
| Slightly negative | 1.0% - 2.0% remaining | PASS | PASS |
| Negative | 0.5% - 1.0% remaining | CONDITIONAL_PASS | PASS |
| Negative | < 0.5% remaining | FAIL | PASS |
| Loss > 1.5% day | Any | FAIL for BUY/INC | PASS |
| Loss > 2.0% day | Any | FAIL all new entries | PASS |

---

#### Dimension R-06: Correlation

**Definition:** Whether the proposed decision increases portfolio correlation to an unacceptable level.

| Scenario | Assessment | Verdict |
|---|---|---|
| New position correlation with portfolio < 0.30 | LOW_CORR | PASS |
| New position correlation 0.30 - 0.60 | MODERATE_CORR | PASS |
| New position correlation 0.60 - 0.80 | HIGH_CORR | CONDITIONAL_PASS; warn |
| New position correlation > 0.80 | VERY_HIGH_CORR | FAIL |
| Portfolio correlation (aggregate) > 0.85 | CONCENTRATED | FAIL for BUY |

---

### D.3 Composite Risk Tier Assignment

After evaluating all 6 dimensions:

| Composite Score | Risk Tier | Effect on DCS |
|---|---|---|
| All 6 PASS | MINIMAL to LOW | No DCS penalty |
| 1-2 CONDITIONAL_PASS, rest PASS | MEDIUM | DCS penalty -0.03 per conditional |
| 3+ CONDITIONAL_PASS | HIGH | DCS penalty -0.05 per conditional |
| Any FAIL | VERY_HIGH | Decision REJECTED by Risk Engine |

---
## SUPPLEMENT E — DECISION FLOW EXAMPLES

### E.1 Example 1: BUY NIFTY 50 Futures Decision

**Scenario:** The Reasoning Engine has produced an ACTIVE reasoning chain concluding BULLISH on NIFTY 50 for the current session. RCS = 0.74. The conclusion direction is BULLISH. The system processes this into a BUY decision for NIFTY 50 FUT (front month).

---

**Stage 1: Decision Builder receives reasoning chain**

Input received:
- Reasoning chain ID: RSN-CAT-MACRO-20260703-00000012
- Status: ACTIVE
- Conclusion: BULLISH on NIFTY 50, conviction level MODERATE_HIGH
- RCS: 0.74
- Key premises: (1) S&P 500 closed +0.9% overnight; (2) India VIX at 13.2 (low); (3) FII net buyers 3 consecutive sessions; (4) NIFTY holding above 20-day MA; (5) No major domestic event risk today.

Decision Builder actions:
1. Queries Entity Engine for NIFTY 50 FUT entity record
2. Queries Portfolio State: current position = 0 (no existing NIFTY position)
3. Queries Context Manager: session = regular trading day, regime = BULL_TREND
4. Determines decision type = BUY-IDX
5. Sets governance tier = HIGH (index instrument)
6. Calculates preliminary quantity: 1 lot (50 shares per lot) at 1.2% NAV (within 2% limit)
7. Creates Decision candidate with status CANDIDATE

---

**Stage 2: Decision Evaluator**

Evaluator runs 8-point evaluation:
- Direction check: BUY + BULLISH conclusion = ALIGNED (PASS)
- Conviction match: MODERATE_HIGH conviction = MODERATE tier decision (PASS)
- Context match: BULL_TREND regime + BUY = ALIGNED (PASS)
- Entity valid: NIFTY 50 FUT is active entity (PASS)
- Quantity valid: 1 lot > 0 (PASS)
- Expiry set: session expiry = 15:30 today (PASS)
- No active conflicting decision (PASS)
- RCS meets minimum: 0.74 >= 0.40 (PASS)

Result: VALID. Decision proceeds to Validator.

---

**Stage 3: Decision Validator**

Validator checks schema completeness:
- All required Header fields: PASS
- Subject entity linked: PASS
- Execution parameters present: PASS (entry_price_type=MARKET, quantity=50, stop_loss=set)
- Explanation stub created: PASS

Schema completeness score: 1.00. No defects. Proceed.

---

**Stage 4: Risk Engine**

R-01 Size: 1.2% NAV = LOW tier = PASS
R-02 Concentration: 1.2% NAV, no existing position; index instruments 1.2% total = well within 25% limit = PASS
R-03 Liquidity: NIFTY 50 FUT is extremely liquid; proposed 1 lot << 0.01% ADV = VERY_LIQUID = PASS
R-04 Regime alignment: BULL_TREND + BUY = ALIGNED = PASS
R-05 Drawdown budget: Current P&L = +0.3% (positive); > 2.0% remaining = PASS
R-06 Correlation: NIFTY FUT has 1.00 correlation with index; portfolio currently 0% index; net portfolio correlation increase = acceptable = PASS

Risk verdict: PASS. Risk tier: LOW.

---

**Stage 5: Policy Manager**

Policy checks:
- Market hours: 10:15 IST; within market hours = PASS
- Entity policy: NIFTY 50 FUT is in approved instrument list = PASS
- Regime policy: BULL_TREND does not restrict BUY-IDX = PASS
- Session position count: Currently 2 positions; limit = 6; PASS
- Max BUY size: 1.2% NAV < 2% per-trade limit = PASS

Policy verdict: PASS. No warnings.

---

**Stage 6: Confidence Engine**

DCS computation:
- QD-01 Correctness: 1.00 (perfect direction alignment)
- QD-02 Consistency: 1.00 (no existing conflicts)
- QD-03 Risk Awareness: 1.00 (all risk dimensions PASS)
- QD-04 Explainability: 0.90 (explanation stub; narrative not yet complete)
- QD-05 Completeness: 1.00 (all fields populated)
- QD-06 Traceability: 0.95 (full lineage to reasoning chain)
- QD-07 Governance: 1.00 (correct tier, owner assigned)
- QD-08 Calibration: 0.88 (historical BUY-IDX accuracy = 88%)
- QD-09 Robustness: 0.90 (decision holds if premise conviction reduced 0.20)
- QD-10 Policy: 1.00 (all policies PASS)
- QD-11 Timeliness: 1.00 (within SLA)
- QD-12 Auditability: 1.00 (audit trail complete)

Weighted DCS = 0.97 (approximately)
DCS tier: DEFINITIVE (>= 0.85)

---

**Stage 7: Ranking Engine**

Priority assigned: HIGH (BULL_TREND regime BUY-IDX with DEFINITIVE DCS)
Rank among active pending decisions: 1 (highest DCS in queue)

---

**Stage 8: Approval Manager**

Approval authority: TIER-1-AI (HIGH governance tier, BULL_TREND regime, no override rules triggered)
AI auto-approval: Checks all approval criteria. Risk PASS + Policy PASS + DCS >= 0.50.
Approval status: APPROVED in 12ms.
Approver: DECISION_ENGINE_AI_TIER1

---

**Stage 9: Decision Packaging**

All records linked:
- Decision record
- Risk evaluation record
- Policy check record
- Reasoning chain reference
- Explanation record (completed by Explainability Manager)
- Counter-arguments record (generated: 2 counter-arguments documented)
- Lineage record

Completeness check: 1.00. Package sealed.
Status: COMMITTED. Decision ID: DEC-BUY-IDX-20260703-00000001

---

**Stage 10: Distribution**

Priority: HIGH
Execution Engine: notified first.
Execution Engine acknowledges: Decision delivered.
Dashboard: updated.
EventBus: DECISION_COMMITTED event emitted.

Total elapsed time from reasoning chain receipt to COMMITTED: 312ms.

---

### E.2 Example 2: EXIT on Stop-Loss Trigger

**Scenario:** The monitoring pipeline detects that TATASTEEL has crossed below its stop-loss price. An active BUY-EQT decision with stop_loss_price = 164.00 is in EXECUTED status. Current LTP = 163.40.

---

**Monitoring Pipeline Detection:**

Monitoring Manager scans all EXECUTED decisions every 30 seconds.
Condition check: stop_loss_price = 164.00; current LTP = 163.40; LTP < stop_loss_price = True.
Alert generated: STOP_LOSS_TRIGGERED for DEC-BUY-EQT-20260703-00000042.

---

**EXT-SL Decision Generation:**

Decision Builder receives stop-loss alert.
Determines: EXT-SL decision required.
Sets minimum DCS threshold = 0.30 (EXT-SL speed priority).
Creates Decision candidate: EXT-SL, quantity = full position, entry_price_type = MARKET.

Risk Engine: abbreviated check (EXT decisions are always low risk):
- R-05 Drawdown budget: EXIT improves drawdown position = PASS
- No other checks required for EXT-SL.

Policy Manager: abbreviated check for EXT-SL = PASS.
Confidence Engine: DCS = 0.82 (CONFIRMED tier) — clean exit, no risk issues.
Approval: TIER-1-AI auto-approved in 8ms.
Packaged and committed in 89ms total.

Execution Engine delivers: market sell order for TATASTEEL.

---

### E.3 Example 3: Emergency Risk Halt

**Scenario:** At 14:22 IST, India VIX spikes from 14 to 38 within 90 seconds. The Risk Guardian detects this and signals CRITICAL status. The Decision Engine must generate an RSK-HALT decision.

---

**Risk Guardian Integration:**

Risk Guardian emits: RISK_STATUS_CRITICAL event.
Decision Engine receives event via EventBus.
Emergency protocol: PROTOCOL-RSK-HALT-001 is pre-approved and pre-loaded.

RSK-HALT Decision generation (using emergency protocol):
- Decision type: RSK-HALT
- Governance tier: CRITICAL
- DCS minimum override: 0.20 (emergency protocol)
- Approval: EMERGENCY (pre-approved protocol activated)

Content:
- Action: HALT all new BUY, INC, SEL-SHORT-INIT decisions
- Existing positions: continue monitoring for EXT signals
- Conditions for lift: VIX returns below 25 AND sustained for 15 minutes

Decision COMMITTED in 180ms.

Distribution: URGENT priority.
Execution Engine: halt flag set.
Policy Manager: regime policies updated to CRISIS preset.
Telegram bot: immediate notification.

Retrospective risk evaluation: completed within 4 hours per DC-B-009.

---

### E.4 Example 4: Human Override of AI Decision

**Scenario:** The AI has generated a BUY-EQT for INFY with DCS = 0.81 (CONFIRMED). The human operator sees a news alert about an upcoming INFY earnings miss consensus estimate and manually overrides to cancel the decision before execution.

---

**Human Override Flow:**

Human operator sends Telegram command: /override cancel DEC-BUY-EQT-20260703-00000089

Telegram bot routes to Decision Approval Manager.
DC-L-001: Human override is absolute and unconditional.
Decision Approval Manager:
1. Immediately sets decision status to HELD (no execution)
2. Notifies Execution Engine: cancel any pending order for this decision
3. Records override: operator = HUMAN_OPERATOR_01, reason = "earnings miss risk", timestamp = 14:45:33 UTC
4. Sets decision status to CANCELLED
5. Audit Manager records: HUMAN_OVERRIDE event

Human operator is confirmed: decision DEC-BUY-EQT-20260703-00000089 cancelled.

The override is irrevocable. The AI cannot re-generate this exact decision without new premise basis.

---
## SUPPLEMENT F — DECISION ANTI-PATTERNS

### F.1 Overview

The following anti-patterns represent the most common and dangerous failure modes in decision-making systems. Each anti-pattern is documented with: name, symptoms, root cause, constitutional violations, and remediation.

---

### Anti-Pattern F-01: Approval Bypass

**Name:** Approval Bypass (also: "authority laundering")

**Description:** A decision that requires TIER-2-HUMAN approval is re-classified, split, or restructured to avoid the approval requirement. For example, a single 3% position BUY is split into three sequential 1% BUYs to stay below the TIER-2-HUMAN trigger.

**Symptoms:**
- Unusual clustering of decisions just below approval escalation thresholds
- Multiple sequential decisions for the same entity in the same direction within one session
- Governance tier assignments inconsistent with the effective economic impact

**Root cause:** Misaligned incentives; overly rigid approval thresholds without aggregate impact checking; missing cumulative position monitoring.

**Constitutional violations:** DC-F-003 (governance tier cannot be downgraded), DC-A-003 (must not misrepresent decision nature).

**Remediation:**
- Cumulative position tracking: the Consistency Manager must aggregate concurrent and same-session decisions for the same entity
- Alert on 3+ same-entity same-direction decisions in same session
- Governance tier must reflect the effective aggregate impact, not per-decision size

---

### Anti-Pattern F-02: Phantom Conviction

**Name:** Phantom Conviction (also: "DCS inflation")

**Description:** A decision receives a high DCS not because the underlying reasoning is strong, but because the formal quality checks all pass on paper while the substantive basis is weak. The premises are present but shallow; the risks are noted but not genuinely weighed.

**Symptoms:**
- High DCS on decisions that subsequently fail (DCS vs outcome correlation diverging)
- Explanation records that are complete in structure but vacuous in content
- Identical conviction statements across multiple decisions for different entities
- Quality dimensions scoring 1.00 across the board routinely

**Root cause:** Quality dimension scoring that checks presence, not substance; lack of calibration feedback from outcomes.

**Constitutional violations:** DC-A-002 (directional consistency is form-based, not substance-based), DC-C-004 (uncertainty statement must genuinely quantify uncertainty).

**Remediation:**
- DCS calibration feedback: regularly compare committed DCS tiers with actual outcomes
- Explanation record quality review: human spot-check on high-DCS decisions
- Conviction statement uniqueness check: flag template-like identical statements
- QD-08 calibration weight increases over time as calibration data accumulates

---

### Anti-Pattern F-03: Zombie Decision

**Name:** Zombie Decision (also: "stale commitment")

**Description:** A COMMITTED decision is no longer relevant because its premise reasoning chain has been REFUTED, EXPIRED, or INACTIVE, but the decision continues to circulate as COMMITTED because no expiry check was triggered.

**Symptoms:**
- COMMITTED decisions referencing reasoning chains with REFUTED or EXPIRED status
- Execution Engine receiving decisions with reasoning chains that have been contradicted
- Audit trail showing a gap between the reasoning chain expiry and the decision review

**Root cause:** Monitoring pipeline not checking reasoning chain status frequently enough; no automatic expiry propagation from reasoning chain to decision.

**Constitutional violations:** DC-A-003 (decision must be supported by at least one ACTIVE reasoning chain at commitment time), DC-E-003 (scheduled decisions must reflect current context).

**Remediation:**
- Monitoring pipeline must check referenced reasoning chain status every 30 seconds for COMMITTED decisions
- When a referenced reasoning chain becomes REFUTED: immediately flag the linked decision for REVIEW
- Auto-HOLD any decision whose primary reasoning chain status is no longer ACTIVE

---

### Anti-Pattern F-04: Orphaned Hedge

**Name:** Orphaned Hedge

**Description:** A hedge decision (HDG) was created to protect a position, but the original position has since been closed (EXT decision executed). The hedge remains active and is now an unanchored speculative position, consuming capital and adding risk rather than reducing it.

**Symptoms:**
- HDG decisions with hedged_position_id referencing positions that are closed
- Risk evaluation of the overall portfolio showing unexpected derivative positions
- Mismatch between equity position count and outstanding hedge count

**Root cause:** No automatic cascade when a position closes; Dependency Manager not propagating closure to linked hedge decisions.

**Constitutional violations:** DC-B-010 (HDG decisions must reference the position being hedged; unanchored hedges are prohibited).

**Remediation:**
- When any EXT decision is executed, Dependency Manager must automatically flag all linked HDG decisions for review
- Orphaned hedges (hedge with no linked active position) auto-transition to HELD pending human review
- Portfolio reconciliation routine checks for position-hedge balance daily

---

### Anti-Pattern F-05: Cascading Cancellation

**Name:** Cascading Cancellation

**Description:** A parent composite decision (CMP) is cancelled by the human operator, but the cancellation does not propagate to the child sub-decisions. Child decisions proceed to execution independently, resulting in partial portfolio changes the human operator did not intend.

**Symptoms:**
- Post-cancellation audit trail showing some sub-decisions in EXECUTED status after the parent was CANCELLED
- Unexplained partial positions following a user-initiated cancellation
- Dependency Manager logs showing incomplete cascade

**Root cause:** Parent-child decision cancellation propagation not implemented or incomplete; race condition between human operator cancel and Execution Engine delivery.

**Constitutional violations:** DC-L-004 (Execution Engine must be notified before order placement; human cancel must propagate immediately), DC-A-008 (composite consistency).

**Remediation:**
- Composite cancellation must lock all child decisions atomically before notifying any consumer
- Execution Engine must check parent decision status before executing child decisions
- Testing must include composite cancellation race condition scenarios

---

### Anti-Pattern F-06: False Precision in DCS

**Name:** False Precision in DCS (also: "decimal theatre")

**Description:** The DCS is reported to 6 decimal places (e.g., 0.847392) despite the quality dimension scores being subjective assessments with much lower precision. The false precision creates an illusion of scientific rigour in what is inherently a judgment-weighted score.

**Symptoms:**
- DCS values reported to more than 2 decimal places in decision records
- Approval decisions made based on DCS differences of < 0.01 between competing candidates
- Decision ranking algorithms treating DCS as a precise interval scale

**Root cause:** Computing and displaying DCS with floating-point precision inherited from the underlying multiplication; no rounding guidance.

**Remediation:**
- DCS is always rounded to 2 decimal places for display and for all threshold comparisons
- DCS threshold comparisons use 0.05 increments as the meaningful precision boundary
- Documentation and explanation records show DCS to 2 decimal places only

---

### Anti-Pattern F-07: Conviction Without Consideration of Counter-Arguments

**Name:** Conviction Without Doubt (also: "asymmetric reasoning import")

**Description:** The Decision Builder accepts the conclusion of a strongly BULLISH reasoning chain and generates a BUY without checking whether contesting reasoning chains exist or whether the counter-argument record is populated.

**Symptoms:**
- DEFINITIVE tier decisions with empty counter-arguments blocks
- High DCS decisions where QD-09 (robustness) has not been tested
- Pattern of decisions that consistently benefit from bullish framing while ignoring bearish signals

**Root cause:** Decision Builder imports the conclusion without checking for contesting chains; Reasoning Engine debate function results not included in the decision reference block.

**Constitutional violations:** DC-A-004 (cannot use CONTESTED chain as sole basis without addressing contest).

**Remediation:**
- Decision Builder must query for contesting reasoning chains before finalizing decision
- Counter-arguments record is mandatory for DEFINITIVE tier (DC-C-001 extended)
- QD-09 robustness test is mandatory for HIGH governance tier

---

### Anti-Pattern F-08: Decision Flooding

**Name:** Decision Flooding (also: "decision spam")

**Description:** The system generates hundreds of COMMITTED decisions in a single session, overwhelming the human operator review interface and making it impossible to distinguish high-quality from low-quality decisions.

**Symptoms:**
- Session decision count > 50 (DC-K-004 trigger)
- Human operator ignoring Telegram notifications due to volume
- Execution Engine queue depth growing continuously
- Average DCS of committed decisions falling below 0.50

**Root cause:** Insufficient quality filtering; no session-level decision budget; reasoning engine generating too many chains which each produce a decision.

**Remediation:**
- Session decision count limit enforced: alert at 30, hard limit at 50 (DC-K-004)
- Decision ranking must apply session-level budget; surplus candidates are held not committed
- Duplicate detection: decisions for the same entity within 15 minutes require new information to justify

---

### Anti-Pattern F-09: Post-Hoc Rationalization

**Name:** Post-Hoc Rationalization (also: "retro-fitting the explanation")

**Description:** The decision is effectively made at the reasoning stage, and the explanation record is constructed to justify the predetermined conclusion rather than documenting the actual reasoning process.

**Symptoms:**
- Explanation records constructed with timestamps after the decision was already APPROVED
- Explanation narrative inconsistent with the actual premises listed
- DCS high despite weak premises (Phantom Conviction accompanies this anti-pattern)

**Root cause:** Explainability Manager generating explanations from the decision artifact rather than from the reasoning process; explanation generated after approval rather than before.

**Remediation:**
- Explanation record must be linked to the reasoning chain directly, not just to the Decision artifact
- Explanation record timestamp must precede the Approval record timestamp
- Explanation completeness check runs before the Approval stage, not after

---

### Anti-Pattern F-10: Silent Policy Drift

**Name:** Silent Policy Drift

**Description:** The Policy Manager loads updated regime policies (e.g., CRISIS policies are activated) but in-flight decisions that were being evaluated under the previous policies are approved under the old policy framework rather than the new one.

**Symptoms:**
- Decisions approved under superseded policy evaluations during regime transitions
- Policy evaluation timestamps that predate the policy change event
- CRISIS regime policies not being applied to decisions that entered the pipeline during the regime transition

**Root cause:** Policy evaluation is stamped at the time of evaluation, not at approval time; pipeline does not re-evaluate against updated policies.

**Constitutional violations:** DC-N-002 (policy changes take effect immediately; in-flight decisions must be re-evaluated).

**Remediation:**
- Policy change event triggers re-evaluation of all decisions currently in PENDING_APPROVAL or HELD states
- Decisions must check policy version at approval time, not evaluation time
- Policy version is stamped on each decision record for audit traceability

---
## SUPPLEMENT G — OPERATIONAL RUNBOOK

### G.1 Overview

This runbook documents the standard operating procedures for the Decision Engine: startup, shutdown, recovery, performance monitoring, and capacity management.

---

### G.2 Startup Procedure

**Step 1: Pre-startup checks (automated)**

The Decision Engine Health Manager performs all pre-startup checks before any component is activated.

| Check | Expected | Failure action |
|---|---|---|
| Storage Layer reachable | Response within 200ms | Abort startup; page operator |
| Registry loadable | Decision Registry responds | Abort startup |
| Audit log integrity | Hash chain valid | Abort startup; security alert |
| Policy Manager | Policy files loaded | Abort startup |
| Reasoning Engine upstream | Heartbeat received | Warn; continue with degraded mode |
| Execution Engine downstream | Heartbeat received | Warn; HOLD all decisions until confirmed |
| Risk Guardian | Heartbeat received | Abort startup (risk check is mandatory) |
| EventBus | Connected | Warn; retry 3x |

---

**Step 2: State restoration**

1. Load all active Decision records from Decision Registry (status: COMMITTED, PENDING_APPROVAL, HELD)
2. Validate all COMMITTED decisions: check that referenced reasoning chains are still ACTIVE
3. Flag COMMITTED decisions with expired or INACTIVE reasoning chains for immediate review
4. Restore Approval Manager queue: any PENDING_APPROVAL decisions awaiting human are flagged
5. Restore Monitoring Manager state: re-register all COMMITTED decisions for monitoring

---

**Step 3: Component activation sequence**

Activate in this order (each step confirmed before proceeding):

`
1.  Decision Storage Layer
2.  Decision Audit Manager (must be active before any decision operations)
3.  Decision Registry
4.  Decision Catalog
5.  Decision Version Manager
6.  Decision Context Manager
7.  Decision Policy Manager
8.  Decision Risk Engine
9.  Decision Confidence Engine
10. Decision Validator
11. Decision Evaluator
12. Decision Ranking Engine
13. Decision Builder
14. Decision Approval Manager
15. Decision Governance Manager
16. Decision Dependency Manager
17. Decision Distribution Manager
18. Decision Explainability Manager
19. Decision Monitoring Manager
20. Decision Archive Manager
    [All 20 components active]
21. Decision Health Manager (self-monitors all components)
22. Open inbound port: Reasoning Engine notifications
23. Emit: DECISION_ENGINE_STARTED event to EventBus
`

---

**Step 4: Post-startup validation**

1. Generate test Decision candidate (synthetic; DCS target 0.80) and run through full lifecycle without distribution
2. Confirm all 13 lifecycle stages complete without error
3. Check audit trail for test decision: 13+ audit events
4. Destroy test decision record

Startup is complete when test decision lifecycle completes successfully.

---

### G.3 Graceful Shutdown Procedure

**Trigger:** SIGTERM signal, operator command, or scheduled shutdown.

**Step 1:** Emit DECISION_ENGINE_SHUTDOWN_INITIATED event to EventBus.

**Step 2:** Stop accepting new reasoning chain notifications (close inbound port).

**Step 3:** Allow in-flight decisions to complete (drain queue) — maximum 60-second drain window.

**Step 4:** For any decisions remaining in PENDING_APPROVAL at shutdown: transition to HELD with note "system_shutdown". Human operator notified.

**Step 5:** Flush all pending audit events to storage.

**Step 6:** Flush all pending Decision record writes to storage.

**Step 7:** Deactivate components in reverse order of activation (monitoring, archiving, approval, etc.).

**Step 8:** Emit DECISION_ENGINE_SHUTDOWN_COMPLETE event to EventBus.

**Step 9:** Release all ports and connections.

---

### G.4 Recovery Procedures

#### Recovery Procedure G-REC-001: Storage Layer Failure

**Scenario:** Storage Layer becomes unreachable mid-operation.

**Immediate response:**
1. Decision Engine transitions to READ-ONLY mode
2. All new Decision generation pauses
3. In-memory state preserved
4. Health Manager: P0 alert to operator
5. EventBus: DECISION_ENGINE_DEGRADED event

**Recovery steps:**
1. Diagnose storage failure (network, disk, schema error)
2. Restore storage connectivity
3. Replay any in-memory pending writes to storage (write-ahead log)
4. Validate audit hash chain after replay
5. Resume normal operations
6. Audit recovery event in audit log

---

#### Recovery Procedure G-REC-002: Reasoning Engine Upstream Failure

**Scenario:** Reasoning Engine stops sending notifications.

**Immediate response:**
1. Continue monitoring all COMMITTED decisions
2. New decision generation pauses (no new reasoning chains)
3. HELD queue remains active
4. Alert sent after 5 minutes of no reasoning chain activity

**Recovery steps:**
1. Confirm Reasoning Engine status via healthcheck
2. On Reasoning Engine recovery: request replay of any missed notifications
3. Process replayed notifications; duplicates filtered by reasoning chain ID

---

#### Recovery Procedure G-REC-003: Execution Engine Downstream Failure

**Scenario:** Execution Engine does not acknowledge COMMITTED decisions.

**Immediate response:**
1. COMMITTED decisions enter retry queue
2. Retry 3x at 30-second intervals
3. After 3 retries: decision transitions to HELD with flag execution_engine_unavailable
4. Human operator notified

**Recovery steps:**
1. Confirm Execution Engine status
2. On Execution Engine recovery: re-deliver HELD decisions in priority order
3. Human operator reviews and approves re-delivery of HELD queue

---

#### Recovery Procedure G-REC-004: Risk Guardian Failure

**Scenario:** Risk Guardian becomes unreachable.

**Immediate response:**
1. All new BUY and INC decisions immediately transition to HELD
2. EXT and CLOSE decisions continue to be processed (exit decisions always permitted)
3. Human operator notified: RISK GUARDIAN OFFLINE

**Recovery steps:**
1. Confirm Risk Guardian recovery
2. Human operator: explicit approval to resume BUY/INC decision processing
3. Risk Engine performs fresh portfolio risk evaluation on recovery

---

#### Recovery Procedure G-REC-005: Audit Log Hash Chain Breach

**Scenario:** Audit hash chain integrity check fails.

**Immediate response:**
1. Decision Engine transitions to EMERGENCY READ-ONLY mode
2. All decision generation pauses immediately
3. Security alert: P0 escalation
4. Operator notification: audit integrity compromised

**Recovery steps:**
1. Isolate affected audit log segment
2. Security team review of chain breach
3. Formal incident report
4. Recovery: restore from last verified backup + replay from event log
5. Operations resume only after security team sign-off

---

### G.5 Performance Targets

| Metric | Target | Critical threshold |
|---|---|---|
| Decision generation (full lifecycle) | < 500ms | > 2,000ms |
| Decision Builder stage | < 50ms | > 200ms |
| Risk Engine evaluation | < 100ms | > 500ms |
| Policy Manager check | < 30ms | > 150ms |
| TIER-1-AI approval | < 30ms | > 100ms |
| Package assembly | < 50ms | > 200ms |
| Distribution to Execution Engine | < 100ms | > 500ms |
| Audit event write | < 20ms | > 100ms |
| Monitoring cycle (all COMMITTED decisions) | 30s interval | > 60s |
| Session decision count | < 30 | > 50 alert |
| Average DCS of committed decisions | > 0.55 | < 0.50 |

---

### G.6 Capacity Reference

| Dimension | Normal | Peak |
|---|---|---|
| Active reasoning chains processed per session | 40-100 | 200 |
| Decision candidates generated per session | 80-150 | 300 |
| COMMITTED decisions per session | 15-30 | 50 (hard limit) |
| Active monitoring watches | 20-30 | 60 |
| Audit events per session | 500-1,000 | 2,500 |
| Decision archive entries per year | ~5,000 | ~12,000 |
| Storage per committed decision (full package) | ~4KB | ~12KB |

---
## SUPPLEMENT H — GLOSSARY

This glossary defines all key terms used in the Decision Engine Architecture. Terms are presented alphabetically.

---

**Action Type**
The classification of what the Decision Engine is directing the Execution Engine to do. Examples: BUY, SELL, EXIT, HOLD, MONITOR. The action type is always one of the 20 canonical Decision type codes (see Supplement A).

**Approval Authority Tier**
The level of approval authority required for a Decision. Four tiers: TIER-1-AI (automated AI approval), TIER-2-HUMAN (human approval required), TIER-3-HUMAN-ONLY (human generates; AI provides analysis only), EMERGENCY (pre-approved protocol activation).

**Archive Manager**
The Decision Engine component responsible for long-term storage of Decision records and packages. Distinct from the Decision Registry (which holds live decisions). The Archive stores completed, expired, and cancelled decisions for the governance tier retention period.

**Audit Manager**
The Decision Engine component responsible for maintaining the immutable, cryptographically-linked audit trail. Every decision event is recorded by the Audit Manager. The audit trail is the source of truth for compliance and regulatory review.

**Audit Hash Chain**
A cryptographic hash chain applied to the decision audit log. Each audit record includes a hash of the previous record. This makes any tampering immediately detectable.

**Candidate Status**
The initial lifecycle status of a newly constructed Decision. A Decision in CANDIDATE status has been built by the Decision Builder but has not yet been evaluated.

**Capital Decision (CAP)**
A Decision type directing changes to portfolio capital allocation. Always CRITICAL governance tier. Always TIER-2-HUMAN approval.

**Commitment**
The act of a Decision transitioning from APPROVED to COMMITTED status. A COMMITTED Decision has passed all readiness checks and is ready for delivery to the Execution Engine.

**Composite Decision (CMP)**
A Decision type that acts as a parent to multiple child decisions. The Composite Decision governs the full multi-leg strategy. All child decisions must be COMMITTED before the Composite is delivered.

**Conditions Block**
A section of the Decision Package documenting: active conditions (from risk CONDITIONAL_PASS), expiry conditions (when the decision expires), and review triggers (conditions that cause a review alert).

**Confidence Engine**
The Decision Engine component responsible for computing the DCS for each Decision. The Confidence Engine integrates 12 quality dimensions into a single composite score.

**Constitutional Rule**
A non-negotiable rule governing Decision Engine behaviour. Constitutional rules are coded DC-{Category}-{Number}. Violations are immediately flagged to the Audit Manager.

**Context Manager**
The Decision Engine component responsible for providing portfolio state context, market context, and session context to the Decision Builder and other components.

**Counter-Arguments Block**
A section of the Decision Package documenting the strongest objections to the decision and the Decision Engine response to each. Mandatory for DEFINITIVE tier decisions.

**Conviction Level**
An assessment of how strongly the reasoning chain supports its conclusion. Imported from the Reasoning Engine. Values: MINIMAL, LOW, MODERATE, MODERATE_HIGH, HIGH, DEFINITIVE.

**DCS (Decision Confidence Score)**
The primary quality metric of a Decision. Ranges [0.0, 1.0]. Computed by the Confidence Engine from 12 quality dimensions. Five tiers: EXPLORATORY (<0.40), TENTATIVE (0.40-0.54), MODERATE (0.55-0.69), CONFIRMED (0.70-0.84), DEFINITIVE (0.85-1.00).

**DCS Calibration**
The process of verifying whether historical DCS tier assignments accurately predicted decision quality (as measured by outcomes). Performed by the Learning System and used to adjust quality dimension weights.

**DCS Tier**
The qualitative tier corresponding to a DCS value. See DCS definition. Used to set approval authority, position sizing, and governance requirements.

**Decision Archive**
The long-term storage layer for completed decisions. Distinct from the Decision Registry. Managed by the Archive Manager.

**Decision Builder**
The Decision Engine component responsible for constructing Decision candidates from incoming reasoning chains and portfolio context.

**Decision Candidate**
A newly-built Decision in CANDIDATE status, before evaluation begins.

**Decision Catalog**
The indexed registry of all Decisions enabling fast lookup by entity, type, status, date range, and DCS tier.

**Decision Constitution**
The 90+ non-negotiable rules governing all Decision Engine operations. Coded as DC-{Category}-{Number}.

**Decision Dependency Manager**
The Decision Engine component responsible for managing inter-decision dependencies, detecting conflicts, and cascading updates (e.g., when a position closes, linked hedges are flagged).

**Decision Distribution Manager**
The Decision Engine component responsible for delivering COMMITTED Decision Packages to all consuming systems in priority order.

**Decision Engine**
Layer 5 of the IIOS cognitive architecture. The subsystem that converts Reasoning Engine outputs (reasoning chains) into governed, risk-evaluated, policy-checked, approved, execution-ready Decision Packages. The Decision Engine does not execute trades, predict markets, or collect observations.

**Decision Evaluator**
The Decision Engine component responsible for evaluating Decision candidates for structural validity, direction consistency, and basic quality.

**Decision Explainability Manager**
The Decision Engine component responsible for generating human-readable explanation records for every committed Decision.

**Decision Governance Manager**
The Decision Engine component responsible for assigning governance tiers, domain ownership, retention policies, and monitoring constitutional compliance.

**Decision Health Manager**
The Decision Engine component responsible for monitoring the health of all other Decision Engine components and the overall quality of decision output.

**Decision Lifecycle**
The 13-stage sequence through which every Decision passes: CANDIDATE, EVALUATING, VALIDATED, RISK_EVALUATING, POLICY_EVALUATING, CONFIDENCE_COMPUTING, RANKING, PENDING_APPROVAL, APPROVED, PACKAGING, COMMITTED, EXECUTED, CLOSED.

**Decision Monitoring Manager**
The Decision Engine component responsible for continuously monitoring all COMMITTED and EXECUTED decisions for expiry, condition triggers, and reasoning chain status changes.

**Decision Package**
The primary output artifact of the Decision Engine. A self-contained, structured record containing all information required by the Execution Engine plus all audit, compliance, and learning records. Sealed at COMMITTED status. Immutable after sealing.

**Decision Policy Manager**
The Decision Engine component responsible for loading, evaluating, and enforcing all trading policies against Decision candidates.

**Decision Ranking Engine**
The Decision Engine component responsible for assigning priority scores and ordering competing Decision candidates.

**Decision Readiness Checklist (DRC)**
The 14-section gate check between APPROVED and COMMITTED. Any FAIL in a mandatory check blocks the COMMITTED transition.

**Decision Registry**
The primary operational store of all active Decision records. Distinct from the Decision Archive.

**Decision Risk Engine**
The Decision Engine component responsible for evaluating 6 risk dimensions for every Decision candidate: size, concentration, liquidity, regime alignment, drawdown budget, correlation.

**Decision Validator**
The Decision Engine component responsible for schema validation, constitutional rule checking, and structural defect detection.

**Decision Version Manager**
The Decision Engine component responsible for recording every version of every Decision, preserving the full edit history.

**Domain Owner**
The subsystem, agent, or role responsible for a particular Decision. Every committed Decision must have a domain owner assigned.

**Emergency Decision (EMR)**
The most urgent Decision type, activated by Risk Guardian CRITICAL status or extreme market conditions. Uses pre-approved emergency protocols. Bypasses normal approval timelines but must be retrospectively documented.

**Execution Block**
The section of the Decision Package containing all parameters needed by the Execution Engine: action type, price type, quantity, stop-loss, take-profit, time in force, expiry.

**Execution Engine**
Layer 11 of the IIOS cognitive architecture. The consumer of Decision Packages produced by the Decision Engine. Responsible for order placement. The Execution Engine is never directly contacted by Decision Engine components — only via the Distribution Manager.

**Explanation Record**
A structured narrative record documenting: premise summary, reasoning narrative, risk rationale, conviction statement, uncertainty statement, conditions for reversal, decision logic, plain-language summary.

**Governance Tier**
The governance classification of a Decision: CRITICAL, HIGH, MEDIUM, or LOW. Determines approval authority, DCS minimums, retention, and audit requirements.

**Human Override**
The unconditional right of a human operator to cancel, modify, or hold any Decision. Human override is absolute (DC-L-001). No component may block it.

**Hybrid Decision (HYB)**
A Decision type generated by AI but modified by human input. Both the AI basis and the human modification are documented.

**Lineage Block**
The section of the Decision Package containing the full ancestry trace: Decision, Reasoning Chain, Hypothesis, Evidence, Observation.

**Orphaned Hedge**
A hedge Decision whose referenced position has been closed, making the hedge an unanchored speculative position. An anti-pattern (Supplement F-04).

**Policy Manager**
See Decision Policy Manager.

**RCS (Reasoning Confidence Score)**
The quality metric of a Reasoning Chain, produced by the Reasoning Engine. Imported into the Decision Engine as the basis for QD-01 through QD-03 quality dimensions.

**Regime**
The current market regime classification: STRONG_BULL_TREND, BULL_TREND, SIDEWAYS, BEAR_TREND, CRISIS. Affects DCS minimums, approval authority, and policy activation.

**Retention Period**
The minimum period for which a Decision record must be preserved: CRITICAL tier = permanent; HIGH = 10 years; MEDIUM = 5 years; LOW = 3 years.

**Risk Guardian**
Layer 9 of the IIOS cognitive architecture. The final kill-switch. The Decision Engine defers to Risk Guardian status at all times. When Risk Guardian signals CRITICAL, all new BUY and INC decisions are immediately held.

**Supersession**
The act of one Decision replacing a prior Decision for the same subject entity and direction. The new Decision references the superseded Decision's ID, and the superseded Decision is marked CANCELLED.

**Version Manager**
See Decision Version Manager.

**Zombie Decision**
A COMMITTED Decision whose premise reasoning chain has been REFUTED or EXPIRED, but which continues to circulate as COMMITTED. An anti-pattern (Supplement F-03).

---

## SUPPLEMENT I — GOVERNING DESIGN RECORDS (GDRs)

### I.1 Overview

Governing Design Records (GDRs) document the key architectural decisions made for the Decision Engine. Each GDR records the decision context, options considered, the decision made, and the rationale.

---

### GDR-DEC-001: Human Override is Absolute and Unconditional

**Context:** The Decision Engine is an AI-generated decision-making system. There must be a clear and unambiguous mechanism for human operators to override any AI decision.

**Options considered:**
- Option A: Human override subject to AI risk review (rejected — AI could block override)
- Option B: Human override allowed unless portfolio safety would be compromised (rejected — creates ambiguous boundary)
- Option C: Human override is absolute and unconditional, with no exceptions (selected)

**Decision:** Option C. DC-L-001 codifies this as a constitutional rule. No component may block, delay, or condition a human override instruction.

**Rationale:** In a trading system, human judgment must be the final authority. Any mechanism that allows AI to override human intent — even for "safety" — creates unacceptable risk. Human operators are responsible for the consequences of their overrides.

**Status:** ACTIVE. Permanent.

---

### GDR-DEC-002: Conservative Default (HOLD/MONITOR when uncertain)

**Context:** When the Decision Engine encounters ambiguous or low-confidence reasoning, it must have a clearly defined default behaviour.

**Options considered:**
- Option A: Default to the most recent decision direction (rejected — perpetuates stale positions)
- Option B: Default to no action (no decision generated) (partially selected)
- Option C: Explicitly generate a HOLD or MONITOR decision to document the uncertainty (selected)

**Decision:** Option C. Explicitly generating HOLD or MONITOR decisions is preferred over silence. A documented HOLD is more useful than an absence of decision — it creates an audit record and clearly communicates the system state.

**Rationale:** The Decision Engine must always produce a documented output. Silence is ambiguous and cannot be audited.

**Status:** ACTIVE. Permanent.

---

### GDR-DEC-003: DCS Weight Defaults

**Context:** The DCS must integrate multiple quality dimensions. Initial weight defaults must be set.

**Options considered:**
- Option A: Equal weights (1/12 each) — rejected; directional correctness is disproportionately important
- Option B: Correctness-dominant weighting — selected

**Decision:** Default weights: QD-01 Correctness = 0.20, QD-02 Consistency = 0.15, QD-03 Risk = 0.15, QD-04 Explainability = 0.10, QD-05 Completeness = 0.10, QD-06 Traceability = 0.08, QD-07 Governance = 0.07, QD-08 Calibration = 0.06, QD-09 Robustness = 0.04, QD-10 Policy = 0.03, QD-11 Timeliness = 0.01, QD-12 Auditability = 0.01.

**Rationale:** A decision that is directionally wrong has no value regardless of how complete or well-documented it is. Correctness and risk awareness dominate.

**Status:** ACTIVE. Weights are subject to calibration by the Learning System; defaults apply when calibration data is insufficient.

---

### GDR-DEC-004: Decision Engine Does Not Execute Trades

**Context:** The boundary between the Decision Engine and the Execution Engine must be clearly defined to prevent scope creep and ensure auditability.

**Decision:** The Decision Engine never initiates order placement. All Decisions reach the Execution Engine via the Distribution Manager only. This boundary is enforced by DC-H-001.

**Rationale:** Preserving this boundary ensures a clear audit checkpoint between the decision-making process and the execution process. It also allows the Execution Engine to apply its own validation before order placement.

**Status:** ACTIVE. Permanent architectural constraint.

---

### GDR-DEC-005: Emergency Decisions Use Pre-Approved Protocols

**Context:** Emergency conditions (VIX spike, circuit breaker, drawdown limit breach) require immediate action faster than normal approval timelines allow.

**Decision:** Emergency Decisions (EMR-*) use pre-approved protocols that activate automatically on emergency triggers. The protocols are reviewed and confirmed at minimum quarterly. Emergency decisions must be retrospectively documented within 4 hours.

**Rationale:** Emergency response time (< 500ms) is incompatible with TIER-2-HUMAN approval latency (30 minutes). Pre-approved protocols allow immediate action while maintaining accountability through retrospective documentation.

**Status:** ACTIVE. Quarterly review required.

---

### GDR-DEC-006: All Decisions Must Have Explicit Expiry

**Context:** Open-ended decisions that never expire create stale commitments and risk the Decision Zombie anti-pattern.

**Decision:** Every Decision must have either an explicit expiry timestamp or an expiry condition. Decisions without expiry are rejected by the Decision Validator.

**Rationale:** Time-bounded decisions force periodic reassessment. An expiry is a commitment that the decision basis will be re-evaluated before the decision can continue to hold.

**Status:** ACTIVE. Permanent.

---
## SUPPLEMENT J — INTEGRATION CONTRACTS

### J.1 Overview

Integration contracts define the precise interface between the Decision Engine and its upstream and downstream system partners. Each contract specifies: trigger, payload, response, error handling, and SLA.

---

### J.2 Contract: Decision Engine ← Reasoning Engine

**Direction:** Upstream integration (Reasoning Engine delivers to Decision Engine)

**Trigger:** Reasoning Engine produces a new ACTIVE reasoning chain with RCS >= 0.35.

**Payload:** Reasoning chain bundle containing:
- reasoning_chain_id (canonical ID)
- status (must be ACTIVE)
- rcs (Reasoning Confidence Score, float [0.0, 1.0])
- conclusion_direction (BULLISH, BEARISH, NEUTRAL, AMBIGUOUS)
- conclusion_text (string, max 500 chars)
- conviction_level (enum)
- premises_summary (list of up to 10 premise summaries)
- subject_entity_id (canonical entity ID)
- created_at (UTC datetime)
- expiry_at (UTC datetime)

**Decision Engine response:**
- ACK: reasoning chain received, decision candidate being constructed
- REJECT: reasoning chain below minimum threshold (RCS < 0.35 or status != ACTIVE)

**SLA:** Decision Engine must ACK or REJECT within 500ms.

**Error handling:** If Decision Engine does not ACK within 500ms, Reasoning Engine retries once after 1 second. After 2 failures, Reasoning Engine logs dropped reasoning chain and continues.

**Constitutional constraint:** Decision Engine may not modify reasoning chain content. It only reads and references.

---

### J.3 Contract: Decision Engine → Execution Engine

**Direction:** Downstream integration (Decision Engine delivers to Execution Engine)

**Trigger:** Decision transitions to COMMITTED status.

**Payload:** Complete Decision Package (see Supplement B for full schema).

**Execution Engine obligations:**
- ACK within 200ms of receipt
- If ACK not received: Decision Distribution Manager retries 3x at 30-second intervals
- After 3 failures: decision transitions to HELD; human operator notified

**Decision Engine obligations:**
- Must not deliver the same Decision Package twice (idempotency key = decision_id + version)
- Must deliver in priority order (URGENT first)
- Must include all required Execution Block fields

**SLA:** Decision Package delivered within 100ms of COMMITTED transition.

**Human override integration:** When human cancels a COMMITTED decision, Decision Engine must notify Execution Engine within 500ms. Execution Engine must halt any pending order for that decision_id.

---

### J.4 Contract: Decision Engine ← Risk Guardian

**Direction:** Risk Guardian signals to Decision Engine

**Events received:**
- RISK_STATUS_NORMAL: all clear; no restrictions
- RISK_STATUS_MONITORING: elevated monitoring; continue normally
- RISK_STATUS_ELEVATED: all new BUY and INC decisions auto-escalated to TIER-2-HUMAN
- RISK_STATUS_CRITICAL: all new BUY and INC decisions auto-HELD; EMR protocols activated

**Decision Engine response to CRITICAL:**
1. Immediate halt on all new BUY and INC decisions
2. COMMITTED decisions in queue: re-evaluate risk before delivery
3. Activate EMR pre-approved protocols if applicable
4. Human operator notification: RISK_GUARDIAN_CRITICAL

**SLA:** Decision Engine must process RISK_STATUS events within 1 second of receipt.

---

### J.5 Contract: Decision Engine ↔ Learning System

**Direction:** Bidirectional

**Decision Engine → Learning System:**
- Every COMMITTED decision is delivered to Learning System for performance tracking
- Delivery: EventBus event DECISION_COMMITTED with full package
- SLA: within 5 seconds of COMMITTED transition

**Learning System → Decision Engine:**
- DCS calibration updates: revised quality dimension weights based on outcome data
- Performance attribution: entity-level performance summaries
- Systematic error flags: if Learning System detects pattern of bad decisions for a specific type

**Decision Engine response to systematic error flag:**
1. Governance Manager reviews flagged decision type
2. If confirmed: DCS minimum for flagged type increased by 0.05
3. Human operator notified

---

### J.6 Contract: Decision Engine → Knowledge Engine

**Direction:** Outgoing (Decision Engine enriches Knowledge Engine)

**Events published:**
- DECISION_COMMITTED: full decision package summary
- DECISION_CANCELLED: decision cancellation record
- HUMAN_OVERRIDE: override record
- DECISION_OUTCOME: outcome record (won/lost/stopped)

**Purpose:** Knowledge Engine builds entity-level decision history, improving future reasoning and evidence assessment.

---

### J.7 Contract: Decision Engine ↔ ControlTower

**Direction:** Bidirectional (monitoring, telemetry, dashboard)

**Decision Engine → ControlTower:**
- Health metrics every 30 seconds (component status, decision count, DCS averages)
- P0 alerts: immediate push for any constitutional violation, audit chain breach, or system failure
- Session summaries at end of trading session

**ControlTower → Decision Engine:**
- Configuration updates (policy changes, threshold updates)
- Operator commands (hold specific decision, cancel specific decision)

---

## SUPPLEMENT K — PERFORMANCE BENCHMARKS

### K.1 Baseline Performance Targets

All benchmarks measured on standard production hardware. Benchmarks are validated quarterly.

| Benchmark | Target | Warning | Critical |
|---|---|---|---|
| End-to-end decision lifecycle (full) | < 500ms | > 1,000ms | > 2,000ms |
| Decision Builder stage | < 50ms | > 100ms | > 200ms |
| Decision Evaluator | < 15ms | > 50ms | > 100ms |
| Decision Validator | < 10ms | > 30ms | > 100ms |
| Risk Engine (full 6 dimensions) | < 100ms | > 200ms | > 500ms |
| Policy Manager check | < 30ms | > 80ms | > 150ms |
| Confidence Engine (DCS compute) | < 20ms | > 50ms | > 100ms |
| Ranking Engine | < 10ms | > 30ms | > 100ms |
| TIER-1-AI approval | < 30ms | > 60ms | > 100ms |
| Package assembly | < 50ms | > 100ms | > 200ms |
| Distribution to Execution Engine | < 100ms | > 200ms | > 500ms |
| Audit event write | < 20ms | > 50ms | > 100ms |

---

### K.2 Throughput Benchmarks

| Metric | Expected | Maximum supported |
|---|---|---|
| Reasoning chains processed per hour | 60-120 | 500 |
| Decision candidates per hour | 80-200 | 600 |
| COMMITTED decisions per session (daily) | 15-30 | 50 (hard limit) |
| Concurrent active decisions in monitoring | 20-40 | 100 |
| Audit events written per hour | 200-500 | 2,000 |

---

### K.3 Quality Benchmarks

| Metric | Target | Minimum acceptable |
|---|---|---|
| Average DCS of committed decisions per session | > 0.60 | > 0.50 |
| DEFINITIVE tier decisions as % of committed | 30-50% | > 20% |
| CONFIRMED tier decisions as % of committed | 30-50% | > 30% |
| TENTATIVE tier decisions as % of committed | < 15% | < 25% |
| Risk Engine FAIL rate (% of candidates rejected for risk) | < 10% | < 20% |
| Policy FAIL rate (% of candidates rejected for policy) | < 5% | < 10% |
| Human approval requested as % of approved | < 15% | < 25% |
| DCS tier vs outcome accuracy (CONFIRMED tier) | > 65% | > 55% |
| DCS tier vs outcome accuracy (DEFINITIVE tier) | > 75% | > 65% |

---

## SUPPLEMENT L — FAILURE MODE ANALYSIS

### L.1 Critical Failure Modes

| Failure Mode | Severity | Probability | Detection | Mitigation |
|---|---|---|---|---|
| DCS consistently inflated (phantom conviction) | CRITICAL | LOW | DCS calibration check | Calibration feedback from Learning System |
| Approval bypass (authority laundering) | CRITICAL | LOW | Aggregate position monitoring | Cumulative position tracking (Supplement F-01) |
| Risk Engine bypass or failure | CRITICAL | VERY LOW | Health Manager | Risk Engine is mandatory; DCS cap on missing evaluation |
| Audit hash chain breach | CRITICAL | VERY LOW | Hash chain integrity check | Immediate halt; security review |
| Decision Zombie proliferation | HIGH | LOW | Monitoring pipeline chain status check | Auto-HOLD on INACTIVE primary chain |
| Emergency protocol stale > 90 days | HIGH | MEDIUM | Protocol age check | Quarterly review required (DC-G-005) |
| Policy drift on regime change | HIGH | MEDIUM | Policy version tracking | In-flight re-evaluation on policy change (DC-N-002) |
| Orphaned hedges accumulating | MEDIUM | MEDIUM | Portfolio reconciliation | Auto-flag on position close (Supplement F-04) |
| Storage Layer failure | CRITICAL | LOW | Storage health check | READ-ONLY mode + write-ahead log replay |
| Execution Engine delivery failure | HIGH | LOW | ACK monitoring | Retry queue + HELD transition |
| Human approval timeout | MEDIUM | MEDIUM | Timeout monitoring | HELD + operator alert |
| Decision flooding (> 50 per session) | HIGH | LOW | Session count | Hard limit at 50 (DC-K-004) |

---

## SUPPLEMENT M — CALIBRATION METHODOLOGY

### M.1 Overview

DCS Calibration ensures that the Decision Confidence Score accurately predicts decision quality as measured by outcomes. Calibration is performed by the Learning System and feeds updated weights back to the Confidence Engine.

---

### M.2 Outcome Attribution

For each COMMITTED decision, the Learning System records:
- Outcome type: WON (target achieved), LOST (stop-loss hit), STOPPED (risk halt), EXPIRED (time expiry), OVERRIDDEN (human override)
- Outcome score: +1.00 for WON, -1.00 for LOST, 0.00 for others (adjusted for size)

The DCS tier is compared to the outcome:
- DEFINITIVE tier decision + WON outcome = calibration point: correct
- DEFINITIVE tier decision + LOST outcome = calibration point: incorrect

---

### M.3 Calibration Frequency

| Calibration type | Frequency |
|---|---|
| DCS tier vs outcome accuracy report | Weekly |
| Quality dimension weight adjustment (minor) | Monthly |
| Quality dimension weight adjustment (major) | Quarterly (manual review) |
| Full DCS methodology review | Annually |

---

### M.4 Weight Adjustment Constraints

To prevent overcorrection:
- Any individual weight may not change by more than 0.05 in a single monthly adjustment
- Total weights must always sum to 1.00
- QD-01 (Correctness) minimum weight: 0.15 (cannot be reduced below this)
- QD-03 (Risk Awareness) minimum weight: 0.10

---

### M.5 Calibration Report Format

Monthly calibration report includes:
1. DCS tier accuracy table (actual win rate per tier)
2. Quality dimension weight changes applied
3. Regime-adjusted accuracy breakdown (BULL vs BEAR vs CRISIS)
4. Entity type accuracy breakdown (INDEX vs EQUITY vs DERIVATIVE)
5. Recommendation: any decision types with persistently low accuracy should have DCS minimum raised

---
## SUPPLEMENT N — HEALTH MONITORING

### N.1 Overview

The Decision Engine Health Manager continuously monitors all 20 components, the overall decision quality, and the integration contract health. This supplement documents the monitoring architecture, health metrics, alert thresholds, and dashboard.

---

### N.2 Component Health Metrics

Each Decision Engine component reports health via a heartbeat every 30 seconds. The following metrics are collected per component:

| Metric | Description | Alert condition |
|---|---|---|
| last_heartbeat_age | Seconds since last heartbeat | > 60s (WARN), > 120s (CRIT) |
| queue_depth | Current items waiting for processing | > 10 (WARN), > 30 (CRIT) |
| error_rate_5m | Errors per minute (5-min window) | > 0.5/min (WARN), > 2/min (CRIT) |
| processing_latency_p95 | 95th percentile processing time | Per-component SLA threshold |
| circuit_breaker_status | CLOSED / HALF_OPEN / OPEN | HALF_OPEN (WARN), OPEN (CRIT) |
| backlog_age | Age of oldest item in queue | > 60s (WARN), > 300s (CRIT) |

---

### N.3 Decision Quality Health Metrics

In addition to component metrics, the Health Manager tracks decision quality metrics in real time:

| Metric | Target | WARN | CRIT |
|---|---|---|---|
| Average DCS of last 10 committed decisions | >= 0.60 | < 0.55 | < 0.50 |
| DEFINITIVE tier decision rate (session) | >= 25% | < 20% | < 10% |
| Risk Engine FAIL rate (rolling 30 min) | < 8% | > 12% | > 20% |
| Policy FAIL rate (rolling 30 min) | < 4% | > 8% | > 15% |
| TIER-2-HUMAN approval requests (session) | < 10% | > 15% | > 25% |
| Approval timeout rate (session) | < 5% | > 10% | > 20% |
| Decision generation latency p95 | < 500ms | > 1,000ms | > 2,000ms |
| Monitoring cycle lag | < 35s | > 60s | > 120s |
| Session decision count (total committed) | < 30 | 30-50 | > 50 |
| Zombie decision detection count | 0 | 1-2 | > 2 |
| Orphaned hedge count | 0 | 1 | > 1 |
| Constitutional violation count (session) | 0 | 1 | > 1 |

---

### N.4 Integration Health Metrics

The Health Manager monitors all 6 integration contracts:

| Integration | Metric | WARN | CRIT |
|---|---|---|---|
| Reasoning Engine upstream | Reasoning chains received (30 min window) | 0 chains for > 10 min | 0 chains for > 30 min |
| Execution Engine downstream | Delivery ACK rate | < 95% | < 90% |
| Execution Engine downstream | Delivery latency | > 200ms | > 500ms |
| Risk Guardian | Heartbeat age | > 30s | > 60s |
| Risk Guardian | Status ELEVATED | Active | Active for > 30 min |
| Learning System | Calibration update age | > 14 days | > 30 days |
| Knowledge Engine | EventBus event delivery rate | < 98% | < 95% |

---

### N.5 Audit Health Metrics

| Metric | Target | Alert |
|---|---|---|
| Audit hash chain integrity | Valid at all times | Any breach = P0 immediate |
| Audit write latency | < 20ms | > 100ms = WARN |
| Audit log size (daily growth) | Within expected range | > 2x expected = WARN |
| Missing audit events (gap detection) | 0 | Any gap = CRIT |
| Audit backup age | < 24h | > 24h = WARN, > 48h = CRIT |

---

### N.6 Health Dashboard

The Health Manager produces a health dashboard viewable via ControlTower. The dashboard shows:

**Summary Panel:**
`
Decision Engine Health: [HEALTHY / DEGRADED / CRITICAL]
Components Active:      20 / 20
Last Full Lifecycle:    312ms (HEALTHY)
Session DCS Average:    0.74 (HEALTHY)
Session Decisions:      12 committed (HEALTHY)
Upstream (RE):          CONNECTED
Downstream (EE):        CONNECTED
Risk Guardian:          NORMAL
`

**Component Status Panel:**

`
Component                    Status    Queue  Latency-P95  Last-HB
Decision-Registry            HEALTHY   0      8ms          12s ago
Decision-Catalog             HEALTHY   0      4ms          12s ago
Decision-Builder             HEALTHY   1      45ms         12s ago
Decision-Evaluator           HEALTHY   0      12ms         12s ago
Decision-Validator           HEALTHY   0      9ms          12s ago
Decision-Ranking-Engine      HEALTHY   0      7ms          12s ago
Decision-Risk-Engine         HEALTHY   0      88ms         12s ago
Decision-Policy-Manager      HEALTHY   0      25ms         12s ago
Decision-Approval-Manager    HEALTHY   0      15ms         12s ago
Decision-Confidence-Engine   HEALTHY   0      18ms         12s ago
Decision-Context-Manager     HEALTHY   0      11ms         12s ago
Decision-Dependency-Manager  HEALTHY   0      8ms          12s ago
Decision-Governance-Manager  HEALTHY   0      6ms          12s ago
Decision-Version-Manager     HEALTHY   0      5ms          12s ago
Decision-Audit-Manager       HEALTHY   0      17ms         12s ago
Decision-Archive-Manager     HEALTHY   0      9ms          12s ago
Decision-Distribution-Mgr    HEALTHY   0      85ms         12s ago
Decision-Explainability-Mgr  HEALTHY   0      22ms         12s ago
Decision-Monitoring-Manager  HEALTHY   0      14ms         12s ago
Decision-Health-Manager      HEALTHY   --     --           self
`

---

### N.7 Alert Routing

| Severity | Examples | Routing |
|---|---|---|
| P0 (immediate) | Audit hash chain breach, storage failure, Risk Guardian CRITICAL | Telegram + ControlTower + log |
| P1 (within 5 min) | Component CRIT state, DCS average below 0.50, Execution Engine delivery failure | Telegram + ControlTower |
| P2 (within 30 min) | Component WARN state, approval timeout spike, zombie decision detected | ControlTower + log |
| P3 (daily summary) | Quality metrics, calibration status, session performance | Email summary |

---

## SUPPLEMENT O — INTERFACE SPECIFICATION

### O.1 Decision Generation Service (DS-01) Full Interface

`
Input:
  reasoning_chain_id : string (required)
  override_params    : dict   (optional — human-initiated decision overrides)
  priority_override  : enum   (optional — URGENT/HIGH/NORMAL/LOW)
  session_id         : string (optional — links decision to session)

Output:
  decision_id        : string (canonical ID of new decision)
  status             : enum   (CANDIDATE / REJECTED)
  estimated_lifecycle_ms : int (estimated time to COMMITTED)

Error codes:
  ERR-DGS-001 : reasoning_chain_id not found
  ERR-DGS-002 : reasoning chain status != ACTIVE
  ERR-DGS-003 : RCS below minimum threshold (< 0.35)
  ERR-DGS-004 : session_id invalid
  ERR-DGS-005 : override_params schema invalid

SLA: ACK within 500ms; COMMITTED within 2,000ms (URGENT priority)
`

---

### O.2 Decision Query Service (DS-02) Full Interface

`
Input:
  decision_id        : string (optional — direct lookup)
  entity_id          : string (optional — filter by entity)
  status             : enum   (optional — filter by status)
  action_type        : enum   (optional — filter by type)
  dcs_min            : float  (optional — minimum DCS filter)
  session_id         : string (optional — filter by session)
  date_from          : date   (optional)
  date_to            : date   (optional)
  limit              : int    (optional, default 100, max 1000)
  include_archived   : bool   (optional, default false)

Output:
  decisions          : list[DecisionSummary]
  total_count        : int
  query_latency_ms   : int

SLA: < 100ms for single ID lookup; < 500ms for filtered queries
`

---

### O.3 Decision Override Service (DS-05) Full Interface

`
Input:
  decision_id        : string (required)
  override_type      : enum   (CANCEL / HOLD / MODIFY / APPROVE / FORCE_COMMIT)
  operator_id        : string (required — human operator identity)
  reason             : string (required)
  modified_params    : dict   (optional — for MODIFY type)

Output:
  success            : bool
  new_status         : enum (updated decision status)
  override_record_id : string
  audit_event_id     : string

Error codes:
  ERR-OVR-001 : decision_id not found
  ERR-OVR-002 : decision not in modifiable state
  ERR-OVR-003 : operator_id invalid
  ERR-OVR-004 : reason empty
  ERR-OVR-005 : modified_params schema invalid

Constitutional note: This service implements DC-L-001 (human override is absolute).
SLA: Override applied within 500ms; Execution Engine notified within additional 500ms.
`

---

### O.4 Decision Status Service (DS-08) Full Interface

`
Input:
  decision_id        : string (required)
  include_history    : bool   (optional, default false)
  include_package    : bool   (optional, default false)

Output:
  decision_id        : string
  current_status     : enum
  current_dcs        : float
  current_dcs_tier   : enum
  approval_status    : enum
  execution_status   : enum (if applicable)
  monitoring_status  : enum
  last_updated_at    : datetime
  status_history     : list[StatusEvent] (if include_history=true)
  full_package       : DecisionPackage  (if include_package=true)

SLA: < 50ms
`

---

### O.5 Decision Approval Service (DS-04) Full Interface

`
Input:
  decision_id        : string (required)
  approval_action    : enum   (APPROVE / REJECT / HOLD / ESCALATE)
  approver_id        : string (required for TIER-2/TIER-3)
  approval_basis     : string (optional)
  rejection_reason   : string (required if REJECT)

Output:
  success            : bool
  new_approval_status: enum
  approval_record_id : string
  audit_event_id     : string
  next_step          : string (description of what happens next)

Error codes:
  ERR-APR-001 : decision_id not found
  ERR-APR-002 : decision not in PENDING_APPROVAL state
  ERR-APR-003 : approver_id required for TIER-2/3
  ERR-APR-004 : rejection_reason required for REJECT action
  ERR-APR-005 : approval authority insufficient for this decision tier

SLA: < 100ms (for TIER-1-AI); < 30 minutes (for TIER-2-HUMAN)
`

---
## SUPPLEMENT P — REGULATORY COMPLIANCE

### P.1 Overview

The Decision Engine produces decisions that inform trading activity. This supplement documents compliance requirements, audit obligations, and the mechanisms the Decision Engine provides to satisfy them.

---

### P.2 Regulatory Obligations Addressed

| Regulation Domain | Obligation | Decision Engine Mechanism |
|---|---|---|
| Algorithmic trading disclosure | Document that trades are AI-initiated | is_ai_generated flag in Decision Package header |
| Audit trail completeness | Full record of all decisions and their basis | Immutable audit log with hash chain |
| Human oversight | Ability for human to override automated decisions | DC-L-001 human override; TIER-2/TIER-3 approval |
| Risk management documentation | Document risk assessment for each trade decision | Risk Block in Decision Package |
| Best execution | Document price, slippage, and execution parameters | Execution Block in Decision Package |
| Record retention | Preserve records for required periods | Governance tier retention policy |
| Conflict detection | Identify and resolve conflicting instructions | Decision Dependency Manager conflict resolution |

---

### P.3 Audit Trail Regulatory Compliance

The Decision Engine audit trail is designed to satisfy trading system audit requirements:

**Completeness:** Every material event in the decision lifecycle is recorded. No decision reaches the Execution Engine without a complete audit trail.

**Immutability:** The audit log is append-only with a cryptographic hash chain. Tampering is immediately detectable.

**Accessibility:** Audit records can be queried by decision_id, date range, actor, event type, and entity.

**Retention:** Audit records are retained for the same periods as the decisions they reference.

**Export:** Audit records can be exported in structured format for regulatory review.

---

### P.4 AI Decision Transparency

All AI-generated decisions carry:
- is_ai_generated = True (explicit flag)
- Plain-language summary in explanation record (readable by non-specialist)
- Conviction statement and uncertainty statement (acknowledges AI limitations)
- Conditions for reversal (AI does not claim certainty)
- Decision logic narrative (step-by-step reasoning documented)

---

### P.5 Human Oversight Mechanisms

The Decision Engine provides the following human oversight mechanisms:

1. **TIER-2-HUMAN approval:** High-value or high-risk decisions require explicit human approval before commitment.

2. **TIER-3-HUMAN-ONLY:** Human generates the decision; AI provides analysis and context only.

3. **Override at any time:** Human can cancel, hold, or modify any COMMITTED decision before execution via Telegram bot or Streamlit dashboard.

4. **Emergency halt:** Human can activate RSK-HALT to stop all new decisions immediately.

5. **Session decision review:** Human can review the full list of COMMITTED decisions for any session.

6. **Audit trail access:** Human can inspect the complete audit trail for any decision.

---

## SUPPLEMENT Q — COGNITIVE ARCHITECTURE INTEGRATION

### Q.1 The IIOS Cognitive Stack (Decision Engine Context)

The Decision Engine (Layer 5) sits at the apex of the IIOS cognitive knowledge stack, receiving from the Reasoning Engine and delivering to the Execution Engine.

`
Cognitive Layer Stack (simplified)

Layer 1: OBSERVATION ENGINE
  (collects raw market signals)
        |
Layer 2: EVIDENCE ENGINE
  (validates and weights observations)
        |
Layer 3: HYPOTHESIS ENGINE
  (generates and ranks hypotheses)
        |
Layer 4: REASONING ENGINE
  (reasons, infers, debates, produces reasoning chains)
        |
Layer 5: DECISION ENGINE   <-- This document
  (decides, governs, packages execution-ready decisions)
        |
Layer 6: EXECUTION ENGINE
  (places orders with broker)
`

---

### Q.2 Decision Engine Cognitive Position

The Decision Engine occupies a unique position in the cognitive stack:

**Input:** Completed reasoning chains (already through the full cognitive process)

**Responsibility:** Adding three cognitive layers that the Reasoning Engine deliberately does not handle:
1. **Risk consciousness** — evaluating not just what to do, but whether the portfolio can tolerate it
2. **Governance** — applying rules, policies, and approval authority
3. **Package completeness** — ensuring the downstream consumer (Execution Engine) has everything it needs

**Output:** Not recommendations, not predictions, not analyses — **decisions**. The Decision Engine is the point in the IIOS where the system commits to a course of action.

---

### Q.3 What the Decision Engine Is NOT

Clarity on cognitive scope boundaries:

| Role | Owner | NOT Decision Engine |
|---|---|---|
| Market data collection | Observation Engine | Not Decision Engine |
| Evidence assessment | Evidence Engine | Not Decision Engine |
| Hypothesis generation | Hypothesis Engine | Not Decision Engine |
| Reasoning and inference | Reasoning Engine | Not Decision Engine |
| Order placement | Execution Engine | Not Decision Engine |
| Market regime classification | Market Intelligence Layer | Not Decision Engine |
| Position monitoring | Trade Monitor | Not Decision Engine |
| Learning from outcomes | Learning System | Not Decision Engine |

The Decision Engine receives outputs from all upstream layers and packages them into governance-ready, execution-ready decisions. It does not replicate any upstream function.

---

### Q.4 Cognitive Handoffs

**From Reasoning Engine to Decision Engine:**
- The Reasoning Engine completes its job when it produces an ACTIVE reasoning chain with an RCS-scored conclusion.
- The Reasoning Engine does NOT decide whether to trade — it reasons about the market.
- The Decision Engine receives the reasoning chain and decides: given this reasoning, what should the portfolio do?

**From Decision Engine to Execution Engine:**
- The Decision Engine completes its job when it seals a COMMITTED Decision Package.
- The Decision Engine does NOT place orders — it produces governed, risk-checked, approved decisions.
- The Execution Engine receives the Decision Package and implements it in the market.

This separation of cognitive responsibilities is intentional and permanent.

---

## SUPPLEMENT R — INTEGRATION TESTING FRAMEWORK

### R.1 Overview

The Decision Engine integration testing framework validates all integration contracts, end-to-end lifecycle completeness, and constitutional rule enforcement.

---

### R.2 End-to-End Lifecycle Tests

| Test | Description | Expected result |
|---|---|---|
| T-E2E-001 | Full lifecycle: reasoning chain → COMMITTED | COMMITTED in < 500ms |
| T-E2E-002 | Full lifecycle with TIER-2-HUMAN approval | Held until human approves |
| T-E2E-003 | Full lifecycle with Risk Engine FAIL | Decision REJECTED; audit event |
| T-E2E-004 | Full lifecycle with Policy FAIL | Decision REJECTED; audit event |
| T-E2E-005 | Emergency decision lifecycle | COMMITTED in < 500ms using protocol |
| T-E2E-006 | Human override of COMMITTED decision | CANCELLED + Execution Engine notified |
| T-E2E-007 | Composite decision with child cancellation | All children CANCELLED |
| T-E2E-008 | Zombie decision detection and HOLD | HOLD within 30s monitoring cycle |
| T-E2E-009 | Orphaned hedge detection and HOLD | HOLD within one monitoring cycle |
| T-E2E-010 | Policy change re-evaluation of in-flight | In-flight decisions re-evaluated |

---

### R.3 Constitutional Rule Enforcement Tests

| Test | Rule tested | Expected result |
|---|---|---|
| T-CONST-001 | DC-A-002 directional consistency | Decision REJECTED if direction wrong |
| T-CONST-002 | DC-B-003 position size limit | Decision REJECTED if exceeds limit |
| T-CONST-003 | DC-C-001 explanation required | Decision BLOCKED from COMMITTED if missing |
| T-CONST-004 | DC-D-001 lineage required | Decision BLOCKED from COMMITTED if missing |
| T-CONST-005 | DC-L-001 human override absolute | Override applied; not blockable by any component |
| T-CONST-006 | DC-K-004 session limit 50 | Alert at 30; hard HOLD at 50 |
| T-CONST-007 | DC-A-007 expiry required | Decision REJECTED if no expiry set |
| T-CONST-008 | DC-B-008 RSK always CRITICAL | RSK decision cannot be downgraded |
| T-CONST-009 | DC-N-002 policy change immediate | In-flight decision re-evaluated after policy change |
| T-CONST-010 | DC-G-003 approval records immutable | REJECTED approval cannot be changed to APPROVED |

---

### R.4 Quality Dimension Tests

| Test | Dimension | Description |
|---|---|---|
| T-QD-001 | QD-01 Correctness | BUY with BEARISH conclusion = DCS penalised by 0.25 |
| T-QD-002 | QD-02 Consistency | Active opposing decision = DCS penalised |
| T-QD-003 | QD-03 Risk | FAIL risk dimension = DCS cap at TENTATIVE |
| T-QD-004 | QD-04 Explainability | Missing explanation = DCS cap at MODERATE |
| T-QD-005 | QD-09 Robustness | Premise conviction -0.20 changes action = robustness LOW |

---
---

## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document code | IIOS-DEC-ENG-ARCH-001 |
| Document title | Decision Engine Architecture |
| IIOS Layer | Layer 5 (of 5 cognitive stack layers) |
| Status | RATIFIED |
| Decision types defined | 20 canonical types (6 categories, 40+ sub-types) |
| Decision Engine components | 20 (across 5 clusters) |
| Services defined | 12 (DS-01 through DS-12) |
| Processing pipelines | 9 |
| Decision lifecycle stages | 13 |
| Constitutional rules | 90+ (14 categories: DC-A through DC-N) |
| Quality dimensions | 12 (QD-01 through QD-12) |
| DCS tiers | 5 (EXPLORATORY, TENTATIVE, MODERATE, CONFIRMED, DEFINITIVE) |
| Approval authority tiers | 4 (TIER-1-AI, TIER-2-HUMAN, TIER-3-HUMAN-ONLY, EMERGENCY) |
| Governance tiers | 4 (CRITICAL, HIGH, MEDIUM, LOW) |
| Anti-patterns documented | 10 (Supplement F) |
| Recovery procedures | 5 (Supplement G) |
| Integration contracts | 6 (Supplement J) |
| GDRs (design decisions) | 6 (Supplement I) |
| Supplements | 18 (A through R) |

---

### Part Summary Table

| Part | Title | Key content |
|---|---|---|
| Part I | Decision Philosophy | 20 distinctions, 8 design principles, conservative default |
| Part II | Decision Schema | 40-field schema, 20 decision types, DCS tier definitions |
| Part III | Components | 20 components across 5 clusters with full specifications |
| Part IV | Lifecycle | 13-stage lifecycle, state machine, PIT semantics |
| Part V | Services | 12 services DS-01 through DS-12 with interfaces and SLAs |
| Part VI | Pipelines | 9 processing pipelines with ASCII flow diagrams |
| Part VII | Quality Framework | 12 quality dimensions, DCS formula, quality monitoring |
| Part VIII | Governance | Governance tiers, matrix, security, compliance |
| Part IX | Constitution | 90+ rules across 14 categories DC-A through DC-N |
| Part X | Readiness Checklist | 14-section DRC with 80+ checks |

---

### Supplement Summary Table

| Supplement | Title | Key content |
|---|---|---|
| A | Decision Taxonomy | All 20 types with sub-types, DCS minimums, regime matrix |
| B | Decision Package | Complete annotated schema for all 11 package blocks |
| C | Approval Matrix | Approval authority by type, regime, and override rules |
| D | Risk Matrix | All 6 risk dimensions with thresholds and verdicts |
| E | Flow Examples | 4 worked examples (BUY, EXIT-SL, Emergency, Override) |
| F | Anti-Patterns | 10 anti-patterns with root cause and remediation |
| G | Operational Runbook | Startup, shutdown, 5 recovery procedures, capacity |
| H | Glossary | 45+ terms defined |
| I | GDRs | 6 Governing Design Records |
| J | Integration Contracts | 6 contracts with full payload and SLA specs |
| K | Performance Benchmarks | Latency, throughput, quality benchmarks |
| L | Failure Mode Analysis | 12 failure modes with mitigation |
| M | Calibration | DCS calibration methodology |
| N | Health Monitoring | Component, quality, integration, audit health metrics |
| O | Interface Specification | Full interface specs for 5 key services |
| P | Regulatory Compliance | Audit trail, AI transparency, human oversight |
| Q | Cognitive Architecture | IIOS stack context, cognitive boundaries |
| R | Integration Testing | E2E tests, constitutional tests, QD tests |

---

### Compliance Checklist

| Requirement | Status | Notes |
|---|---|---|
| All 20 decision types documented | PASS | Supplement A |
| All 20 components documented | PASS | Part III |
| All 12 services documented | PASS | Part V |
| All 9 pipelines documented | PASS | Part VI |
| All 13 lifecycle stages documented | PASS | Part IV |
| All 12 quality dimensions documented | PASS | Part VII |
| DCS formula documented | PASS | Part VII, Section 7.3 |
| Constitutional rules: 90+ | PASS | Part IX |
| Decision Readiness Checklist documented | PASS | Part X |
| Decision Package schema documented | PASS | Supplement B |
| Anti-patterns documented | PASS | Supplement F |
| Integration contracts documented | PASS | Supplement J |
| Operational runbook documented | PASS | Supplement G |
| Glossary documented | PASS | Supplement H |
| Governing Design Records documented | PASS | Supplement I |
| Performance benchmarks documented | PASS | Supplement K |
| Failure mode analysis documented | PASS | Supplement L |
| Calibration methodology documented | PASS | Supplement M |
| Health monitoring documented | PASS | Supplement N |
| Regulatory compliance documented | PASS | Supplement P |
| Cognitive architecture position documented | PASS | Supplement Q |
| Integration testing framework documented | PASS | Supplement R |

---

### Governing Documents

This document must be read in conjunction with the following:

| Document | Relationship |
|---|---|
| REASONING_ENGINE_ARCHITECTURE.md | Upstream producer of reasoning chains (IIOS-RSN-ENG-ARCH-001) |
| HYPOTHESIS_ENGINE_ARCHITECTURE.md | Produces hypotheses that feed reasoning chains |
| EVIDENCE_ENGINE_ARCHITECTURE.md | Produces evidence that supports hypotheses |
| OBSERVATION_ENGINE_ARCHITECTURE.md | Produces observations at the base of the knowledge stack |
| ARCHITECTURE.md | Master system architecture for the full IIOS |
| KILL_SWITCH.md | Documents the hard kill-switch conditions enforced by Risk Guardian |

---

### Architectural Impact Statement

The Decision Engine is the final cognitive layer before the market. Every decision it produces is potentially executed as a real trade. The architectural principles of this document are designed to ensure:

1. **Safety over speed.** A delayed good decision is preferable to a fast bad one. The 500ms decision lifecycle target is a performance target, not a safety trade-off.

2. **Auditability over convenience.** The full audit trail, explanation record, and lineage are mandatory requirements, not optional enhancements. The system cannot be "streamlined" by removing these.

3. **Human authority is always supreme.** The Technical mechanisms of this architecture never, under any circumstances, prevent a human operator from overriding, holding, or cancelling a decision. This is the most fundamental invariant of the system.

4. **Conservative default principle.** When the system encounters uncertainty, it defaults to HOLD or MONITOR. It never defaults to action. The burden of proof is always on acting, not on refraining.

5. **Risk evaluation is non-negotiable.** No Decision of governance tier MEDIUM or above can reach COMMITTED status without a complete risk evaluation. This cannot be bypassed, disabled, or "skipped for speed."

These five principles are the architectural soul of the Decision Engine. Any proposed modification to this architecture must be evaluated against all five principles before implementation.

---

### Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-07-01 | IIOS Architecture Team | Initial draft: Parts I-III |
| 0.2 | 2026-07-02 | IIOS Architecture Team | Parts IV-VI: lifecycle and pipelines |
| 0.3 | 2026-07-03 | IIOS Architecture Team | Parts VII-X: quality, governance, constitution |
| 1.0 | 2026-07-03 | IIOS Architecture Team | Complete document: all parts and supplements. RATIFIED. |

---

### Ratification Statement

This document defines the complete architecture for the IIOS Decision Engine (Layer 5). It has been reviewed against the full IIOS architecture, the Reasoning Engine Architecture (IIOS-RSN-ENG-ARCH-001), and the master ARCHITECTURE.md. It is consistent with all upstream and downstream architectural contracts.

**Document Code:** IIOS-DEC-ENG-ARCH-001

**Status:** RATIFIED

**Human override is absolute and unconditional (DC-L-001). This statement is the most important sentence in this document.**

---

*End of Document — IIOS-DEC-ENG-ARCH-001 — Decision Engine Architecture*

---
---

## SUPPLEMENT S — DECISION DEBATE RECORD EXAMPLES

### S.1 Overview

For HIGH and CRITICAL governance tier decisions, the Decision Engine may invoke a structured debate procedure to test the decision quality before the Confidence Engine assigns the final DCS. This supplement provides four detailed debate records demonstrating the structured challenge-and-response pattern.

---

### S.2 Debate Record S-DBT-001: BUY NIFTY 50 Futures — Bullish Case

**Decision under debate:** DEC-BUY-IDX-20260703-00000001

**Proposition (from Decision Builder):** Buy 1 lot of NIFTY 50 FUT (front month). Basis: BULL_TREND regime confirmed; FII net buyers 3 sessions; S&P +0.9% overnight; VIX at 13.2.

**Round 1 — Challenge from Risk Advocate:**
Challenge: VIX at 13.2 may indicate complacency, not genuine bullish confidence. Low VIX sometimes precedes sharp corrections. The overnight S&P gain was driven by a single tech earnings report — this is not broad-based bullish sentiment.

Response from Proposition: VIX below 14 has historically corresponded with sustained uptrends in NIFTY on 68% of observed occasions (calibration reference: CAL-VIX-NIFTY-LOW-REGIME). The S&P driver is tech sector, which has limited direct correlation to NIFTY mid-cap segment. FII net buying is a more India-specific indicator and carries greater weight here.

**Round 2 — Challenge from Regime Analyst:**
Challenge: BULL_TREND regime classification was assigned 36 hours ago. There have been no regime updates since then. The regime may be stale.

Response from Proposition: Regime update cycle is 6 hours. The most recent regime assessment was 4 hours ago (within cycle). BULL_TREND confirmed in that assessment. No intraday regime signal has been received since.

**Round 3 — Challenge from Portfolio Manager:**
Challenge: The portfolio already has 1.8% NAV in equities with high NIFTY correlation. Adding a NIFTY FUT position increases effective beta exposure above 2.5% NAV for the session. This approaches the high-concentration warning threshold.

Response from Proposition: The proposed position is 1.2% NAV. After the addition, total NIFTY-correlated exposure = 3.0% NAV. This is within the 5% single-entity limit and within the 25% index instrument limit. The concentration risk dimension returns CONDITIONAL_PASS at HIGH tier, which will reduce DCS by 0.05. Accepted.

**Debate verdict:** Proposition prevails with one concession (concentration DCS penalty accepted). Decision proceeds to Risk Engine.

---

### S.3 Debate Record S-DBT-002: SEL-SHORT-INIT on HDFCBANK — Bearish Case

**Decision under debate:** DEC-SEL-SHORT-DRV-20260703-00000012

**Proposition:** Initiate a short position on HDFCBANK via put options. Basis: BEAR_TREND regime; HDFCBANK showing bearish divergence in RSI; banking sector under pressure from rising rates; FII sellers for 2 sessions in banking names.

**Round 1 — Challenge from Contrarian:**
Challenge: HDFCBANK is a defensive holding for many institutions. Short positions in high-weight Nifty constituents carry significant short-squeeze risk. Two sessions of FII selling is insufficient to establish a bearish trend — this is noise.

Response from Proposition: The position is initiated via put options — defined risk, maximum loss is premium paid. A short-squeeze affects futures positions, not long put positions. The downside risk is fully bounded. Two sessions of selling is consistent with the developing BEAR_TREND regime signal. The hypothesis supporting this decision has ECS of 0.72 (strong bearish evidence).

**Round 2 — Challenge from Risk Advocate:**
Challenge: Put options in HDFCBANK may have wide bid-ask spreads, creating liquidity risk. The effective execution cost (including spread) may erode the expected return on this trade.

Response from Proposition: HDFCBANK is the largest weight constituent on NSE. Near-the-money put options trade with bid-ask spreads typically below 0.3% of premium. Liquidity risk dimension: MODERATE_LIQUIDITY — CONDITIONAL_PASS, not a block. The trade remains viable.

**Round 3 — Challenge from Regime Analyst:**
Challenge: The BEAR_TREND regime classification is only 18 hours old. Initiating a short in a regime less than 24 hours established carries higher regime reversal risk.

Response from Proposition: The BEAR_TREND regime classification is supported by: (1) Nifty 3% below 20-day MA; (2) Market breadth below 35% (negative). These are not weak signals. However, the counter-argument is valid. The DCS will reflect this uncertainty via QD-09 robustness test. If conviction on primary premises reduces by 0.20, does the action change? No — the reasoning chain direction remains BEARISH even with reduced conviction. Robustness = HIGH.

**Debate verdict:** Proposition prevails. Short position proceeds with noted conditions: defined-risk options structure required; monitor regime status closely; review at 24-hour mark.

---

### S.4 Debate Record S-DBT-003: RSK-HALT — Emergency Regime

**Decision under debate:** DEC-RSK-HALT-20260703-00000001

**Proposition:** Activate RSK-HALT. Halt all new BUY and INC decisions. Basis: India VIX spiked from 14 to 38 in 90 seconds. Risk Guardian status: CRITICAL.

**Round 1 — Challenge from Operations:**
Challenge: A VIX spike of this magnitude may be a data feed error. Before halting all new decisions, should we verify the VIX data from a secondary source?

Response from Proposition: The RSK-HALT emergency protocol is triggered when Risk Guardian signals CRITICAL. The Risk Guardian independently verifies VIX data using two sources before signalling CRITICAL. The verification is already done. Halting first and verifying second is the correct order — the cost of a false halt is low (missed opportunities for minutes); the cost of a false continue is high (real losses in a genuine spike).

**Round 2 — Challenge from Portfolio Manager:**
Challenge: We have 3 existing positions. The RSK-HALT does not close these. Should we also generate EXT decisions for existing positions?

Response from Proposition: RSK-HALT halts new BUY and INC decisions. Existing positions are monitored for EXT signals via the monitoring pipeline. The stop-loss levels for existing positions will trigger EXT-SL decisions automatically if crossed. Preemptively closing all positions in a VIX spike without confirmed price movement at the stop-loss level would lock in unnecessary losses if VIX normalises quickly. Protocol: halt new entries; let stops handle existing.

**Debate verdict:** Proposition prevails. RSK-HALT committed immediately using emergency protocol.

---

### S.5 Debate Record S-DBT-004: HLD-MONITORED on INFOSYS — Uncertainty Case

**Decision under debate:** DEC-HLD-MONITORED-20260703-00000034

**Proposition:** Hold existing INFOSYS long position with elevated monitoring (HLD-MONITORED). Basis: Earnings announcement in 72 hours. Current position is profitable. Reasoning chain is NEUTRAL with weak conviction.

**Round 1 — Challenge from Trader:**
Challenge: If conviction is NEUTRAL/WEAK, why not exit now and re-enter after earnings uncertainty is resolved? The risk/reward of holding through a binary event with weak conviction is unfavourable.

Response from Proposition: The position is currently profitable. The alternative to HLD-MONITORED is EXT-MANAGED. An EXT-MANAGED decision would also require NEUTRAL/WEAK conviction to justify taking profit now. The asymmetry: staying requires a reason to stay; exiting also requires a reason to exit. Neither is clearly superior with NEUTRAL conviction. HLD-MONITORED with a review trigger set to earnings date is the appropriate uncertainty response per the conservative default principle (GDR-DEC-002): when uncertain, document the hold explicitly rather than acting.

**Round 2 — Challenge from Risk Advocate:**
Challenge: Earnings events carry gap-risk. A gap-down at earnings would breach the stop-loss at open, potentially at a much worse price than the stop-loss level. Binary event risk is not fully captured by the stop-loss.

Response from Proposition: Valid point. The conditions block for this HLD-MONITORED decision will include: (1) If earnings consensus surprise > -5%, trigger review; (2) If LTP gaps below stop-loss by > 1.5%, escalate to human operator for override decision. The gap risk is documented but is accepted at the current position size (0.8% NAV).

**Debate verdict:** Proposition prevails with modifications. HLD-MONITORED with earnings-specific conditions and gap-risk escalation rule. Decision proceeds.

---

---

## SUPPLEMENT T — DECISION STATE MACHINE REFERENCE

### T.1 Complete State Transition Table

The following table documents every valid state transition in the Decision Engine lifecycle, the actor responsible, the trigger condition, and the resulting audit event.

| From State | To State | Actor | Trigger | Audit Event |
|---|---|---|---|---|
| (none) | CANDIDATE | Decision Builder | Reasoning chain received | CREATED |
| CANDIDATE | EVALUATING | Decision Evaluator | Candidate enters queue | EVALUATION_STARTED |
| EVALUATING | VALIDATED | Decision Validator | Evaluator PASS | VALIDATED |
| EVALUATING | REJECTED | Decision Evaluator | Evaluator FAIL | REJECTED |
| VALIDATED | RISK_EVALUATING | Decision Risk Engine | Validator PASS | RISK_EVALUATION_STARTED |
| RISK_EVALUATING | POLICY_EVALUATING | Decision Policy Manager | Risk PASS or CONDITIONAL | RISK_EVALUATED |
| RISK_EVALUATING | REJECTED | Decision Risk Engine | Risk FAIL | REJECTED |
| POLICY_EVALUATING | CONFIDENCE_COMPUTING | Confidence Engine | Policy PASS or WARN | POLICY_EVALUATED |
| POLICY_EVALUATING | REJECTED | Decision Policy Manager | Policy blocking FAIL | REJECTED |
| CONFIDENCE_COMPUTING | RANKING | Ranking Engine | DCS computed | DCS_ASSIGNED |
| RANKING | PENDING_APPROVAL | Approval Manager | Priority assigned | PENDING_APPROVAL |
| PENDING_APPROVAL | APPROVED | Approval Manager | Approval granted | APPROVED |
| PENDING_APPROVAL | HELD | Approval Manager | Timeout or explicit hold | HELD |
| PENDING_APPROVAL | REJECTED | Approval Manager | Approval rejected | REJECTED |
| APPROVED | COMMITTED | Package assembler | DRC all checks pass | COMMITTED |
| APPROVED | HELD | Human operator | Human hold instruction | HUMAN_HELD |
| COMMITTED | EXECUTED | Execution Engine | Order placed | EXECUTED |
| COMMITTED | CANCELLED | Human operator | Human cancel instruction | HUMAN_CANCELLED |
| COMMITTED | HELD | Human operator | Human hold instruction | HUMAN_HELD |
| EXECUTED | CLOSED | Monitoring Manager | Position closed or expiry | CLOSED |
| EXECUTED | CANCELLED | Human operator | Human cancel post-execution | HUMAN_OVERRIDE_POST_EXEC |
| HELD | PENDING_APPROVAL | Approval Manager | Hold released | HOLD_RELEASED |
| HELD | CANCELLED | Human operator | Human cancel while held | CANCELLED |
| Any state | EXPIRED | Monitoring Manager | Expiry timestamp reached | EXPIRED |
| REJECTED | (terminal) | — | — | — |
| CANCELLED | (terminal) | — | — | — |
| EXPIRED | (terminal) | — | — | — |
| CLOSED | (terminal) | — | — | — |

---

### T.2 Terminal States

The following states are terminal — no further transitions are possible:

| Terminal State | Description | Transition from |
|---|---|---|
| REJECTED | Decision failed evaluation, risk, policy, or approval | EVALUATING, RISK_EVALUATING, POLICY_EVALUATING, PENDING_APPROVAL |
| CANCELLED | Decision cancelled (human or system) | COMMITTED, HELD, PENDING_APPROVAL, EXECUTED |
| EXPIRED | Decision reached expiry without execution | Any non-terminal state |
| CLOSED | Decision fully executed and position closed | EXECUTED |

---

### T.3 State Duration Expectations

| State | Expected Duration | Max Before Alert |
|---|---|---|
| CANDIDATE | < 10ms | 30ms |
| EVALUATING | < 20ms | 60ms |
| VALIDATED | < 10ms | 30ms |
| RISK_EVALUATING | < 100ms | 300ms |
| POLICY_EVALUATING | < 30ms | 100ms |
| CONFIDENCE_COMPUTING | < 20ms | 60ms |
| RANKING | < 10ms | 30ms |
| PENDING_APPROVAL (TIER-1-AI) | < 30ms | 100ms |
| PENDING_APPROVAL (TIER-2-HUMAN) | < 30 min | 30 min |
| APPROVED | < 100ms | 300ms |
| COMMITTED | Immediate delivery | 200ms |
| EXECUTED | Duration of position | Until stop-loss or take-profit |
| CLOSED | Terminal | — |

---

### T.4 Monitoring Alerts Based on State Age

| State | Alert condition | Alert type | Action |
|---|---|---|---|
| PENDING_APPROVAL | > 30 min (TIER-2-HUMAN) | P2 | Notify human operator |
| COMMITTED | > 5 min without Execution Engine ACK | P1 | Retry delivery |
| HELD | > 4 hours without human action | P2 | Escalation alert |
| VALIDATED (not progressing) | > 60s | P1 | Pipeline blockage investigation |
| CANDIDATE (not progressing) | > 10s | P2 | Evaluator queue check |

---

*End of Supplement T*

---