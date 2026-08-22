# DECISION ARCHITECTURE
## AI Trading Brain — Constitutional Architecture of Investment Decision-Making

**Version:** 1.0
**Status:** Authoritative
**Date:** 2026-07-01
**Parent Documents:** MASTER_KNOWLEDGE_ARCHITECTURE.md | INFORMATION_ONTOLOGY.md | ENTITY_ONTOLOGY.md | RELATIONSHIP_ONTOLOGY.md | EVENT_ONTOLOGY.md | REASONING_ARCHITECTURE.md

---

> *This document answers the question: "How does intelligence decide?"*
> *This is the constitutional architecture of investment decision-making for the Investment Intelligence Operating System.*
> *Every investment decision traces to a decision type defined here.*
> *Every approval traces to the governance framework defined here.*
> *Every capital commitment traces to the risk-reward framework defined here.*
> *Every decision failure traces to a failure mode defined here.*
> *Nothing in the system may create, approve, reject, modify, or execute a decision unless it complies with this architecture.*

---

## TABLE OF CONTENTS

| Part | Title | Purpose |
|---|---|---|
| I | The Nature of Decisions | What decisions are; why they are categorically distinct from reasoning, recommendations, and executions |
| II | The Complete Decision Universe | Exhaustive vocabulary of 500+ decision concepts across 14 groups |
| III | Decision Primitives | Deep structural definitions of 25 core decision units — 28 attributes each |
| IV | Decision Types | 30 investment decision paradigms — strengths, weaknesses, use cases, failure modes |
| V | The Complete Decision Pipeline | Full decision pipeline from information arrival to portfolio update and learning |
| VI | Portfolio Decision Governance | Committee structure, approval hierarchy, capital governance, constraint system |
| VII | Risk–Reward Framework | How risk, return, probability, and conviction combine to produce decision quality |
| VIII | Decision Failure Modes | Detection, mitigation, and recovery from every decision failure type |
| IX | Decision Constitution | 30 constitutional principles governing all investment decisions |
| X | Future Evolution | Adaptive, autonomous, and institutionally-scaled decision systems |

---

## PART I — THE NATURE OF DECISIONS

*What a decision is, why it is categorically distinct from reasoning and recommendation, what it commits the system to, and why decision architecture is the central discipline of investment intelligence.*

---

### 1 — What Is a Decision?

A decision is a **commitment to a course of action made under uncertainty with full acknowledgment of the resources it consumes and the future states it forecloses**. It is the moment when intelligence transitions from thinking to acting — from holding beliefs to staking capital on them.

Four essential properties distinguish a decision from all adjacent concepts:

**Commitment** — A decision is not a preference, an opinion, or a hypothesis. It is a binding choice. Once made, the system is committed to the action, and that commitment is recorded permanently. A decision that can be silently abandoned was never a decision — it was a consideration. The moment the commitment is made, the world changes: capital is reserved, positions are opened or closed, and all subsequent market movements are consequential to the decision-maker.

**Irreversibility** — While some decisions can be reversed (a position can be closed), the act of deciding cannot be undone. The causal chain is triggered the moment the decision is made: capital is allocated, opportunity is consumed, and market exposure is acquired. Even if a position is immediately closed at break-even, the decision was made and its consequences (transaction costs, temporary exposure, opportunity cost) are permanent. Good decision architecture acknowledges that decisions are directional arrows through time, not retrievable calculations.

**Uncertainty** — No investment decision is made with perfect information about the future. Decisions do not wait for certainty — they are made precisely because certainty is unavailable and action is still required. A system that waits for certainty will never act. A system that does not account for uncertainty will act catastrophically. The Investment Intelligence Operating System is designed to make high-quality decisions under uncertainty — not to eliminate uncertainty before acting.

**Resource Consumption** — Every investment decision consumes finite, non-renewable resources: capital, risk budget, attention capacity, and portfolio slots. Capital deployed cannot simultaneously be deployed elsewhere. Risk budget consumed by one position is unavailable for another. A decision is an allocation of scarce resources — and therefore every decision implicitly forecloses alternative uses. The opportunity cost of every decision is not zero.

**A decision is not:**
- A recommendation — that is a proposal awaiting approval
- A hypothesis — that is a belief awaiting evidence
- A calculation — that is a computation producing a number
- An order — that is the execution vehicle for a decision
- A prediction — that is a probabilistic forecast about the future
- A plan — that is a sequence of potential future decisions
- An optimization — that is finding the best solution to a defined problem
- A guess — that is an action without supporting reasoning

**A decision is the moment when intelligence commits its resources to a course of action**, having completed the full reasoning pipeline, earned sufficient conviction, passed all governance gates, and accepted the uncertainty that remains.

---

### 2 — The Full Precision Taxonomy: 16 Adjacent Concepts

*Investment intelligence operates through a cascade of transformations from raw information to institutional wisdom. Understanding where each concept sits in this cascade — and what distinguishes each from the others — is architecturally critical.*

| Concept | Position in Cascade | Core Meaning | Creates Decision? | Creates Commitment? | Consumes Capital? | Example in Investment Context |
|---|---|---|---|---|---|---|
| **Information** | Layer 0 — Raw | Structured data representing facts about the world | No | No | No | "NIFTY Bank Index: 52,400 at 10:32 IST" |
| **Observation** | Layer 1 — Perceived | Information that has been registered and time-stamped | No | No | No | "NIFTY Bank is up 1.8% on above-average volume" |
| **Evidence** | Layer 2 — Interpreted | Observation assessed for relevance to a hypothesis | No | No | No | "The volume and price move is bullish evidence for HDFC Bank" |
| **Knowledge** | Layer 3 — Validated | A confirmed belief backed by sufficient evidence across instances | No | No | No | "Banking sector outperforms in rate cut cycles — confirmed in 8 of 9 historical instances" |
| **Reasoning** | Layer 4 — Processing | The deliberate transformation of evidence into new beliefs and inferences | No | No | No | "Given regime, evidence, and knowledge, HDFC Bank outperformance is probable" |
| **Hypothesis** | Layer 4 — Output | A belief held at a specific probability, actively under evaluation | No | No | No | "HDFC Bank will outperform NIFTY over next 30 days (confidence: 0.65)" |
| **Recommendation** | Layer 5 — Proposal | A structured proposal for action, awaiting approval and governance review | No | No | No | "Buy HDFC Bank — Entry 1820, Stop 1755, Target 1940, Conviction 6.8/10" |
| **Decision** | Layer 6 — Commitment | A binding choice to act on a recommendation after governance approval | Yes | Yes | Reservation begins | "APPROVED: Buy 200 shares HDFC Bank at 1820" |
| **Execution** | Layer 7 — Implementation | The process of implementing a decision through market interaction | No | No | Consumed on fill | "Order routed: Buy 200 HDFC Bank, Limit 1821" |
| **Trade** | Layer 7 — Market Act | The completion of a buy or sell transaction in the market | No | No | Consumed | "Filled: 200 HDFC Bank at 1820.50 — 14:23 IST" |
| **Order** | Layer 7 — Instruction | A structured instruction to the execution system specifying exact trade parameters | No | No | No (until filled) | "Buy 200 HDFC Bank, Limit 1821, DAY order" |
| **Portfolio Change** | Layer 8 — State Update | The modification of portfolio composition resulting from a completed trade | No | No | Consumed | "Portfolio: +200 HDFC Bank, banking exposure +0.7%" |
| **Outcome** | Layer 9 — Result | The measured financial consequence of a decision after position closure | No | No | Released | "HDFC Bank: +8.2% return over 22-day hold, conviction confirmed" |
| **Learning** | Layer 10 — Update | The revision of knowledge and models based on outcomes | No | No | No | "Update: NIM expansion + rate cut = +9.1% median outperformance (was +8.3%)" |
| **Wisdom** | Layer 11 — Institutional | The deep, durable understanding of when and how to apply knowledge across all conditions | No | No | No | "Never trade HDFC Bank heavy in the 2 weeks before RBI policy" |
| **Judgment** | Layer 5 — Evaluative | An integrated assessment that weighs multiple considerations simultaneously | No | No | No | "HDFC Bank: Strong thesis; but portfolio is already 28% banking — size to 2% only" |

---

### 3 — Why Decisions Exist

Decisions are not a technical implementation detail — they are the fundamental reason an investment intelligence system exists. Five reasons explain why decisions are irreplaceable:

**Reason 1 — Markets Require Commitment**
Market opportunities have finite windows. A conviction about HDFC Bank's 30-day outperformance has value only if acted upon before the information advantage expires. The intelligence system that never decides never captures returns. The entire purpose of the reasoning pipeline is to produce decisions of sufficient quality that executing them is profitable on expectation.

**Reason 2 — Capital Must Work**
Capital held in cash earns the risk-free rate. The only way to earn above the risk-free rate is to allocate capital to positions with positive risk-adjusted expected returns. Every day capital is not deployed to a conviction position is a day of opportunity cost. The decision system is the mechanism by which idle capital becomes working capital.

**Reason 3 — Uncertainty Cannot Be Resolved by Waiting**
In investment, waiting does not reduce uncertainty — it often increases it. The company that was a buy at 1,820 based on solid evidence may be a less attractive buy at 1,920 as the evidence becomes priced in. The decision system must commit at the point where the evidence-to-risk ratio is optimal — not when certainty is achieved, because certainty never arrives.

**Reason 4 — Learning Requires Decisions**
The system learns from outcomes. Outcomes require positions. Positions require decisions. A system that never decides never gets outcome feedback and therefore never improves. The decision pipeline is also the learning pipeline — every decision, properly recorded and analyzed, generates knowledge that improves future decisions.

**Reason 5 — Intelligence Without Action Has No Value**
An intelligence system that correctly identifies 100 investment opportunities and acts on none of them produces zero returns and serves no purpose. The decision is the conversion of intelligence into value. All the architectural sophistication of the Investment Intelligence Operating System — the ontologies, the reasoning engine, the multi-agent debate, the confidence framework — exists to produce better decisions, not to produce better analyses.

---

### 4 — Decision vs Adjacent Concepts

*The investment decision is frequently confused with neighboring concepts. The distinctions are architecturally critical — confusing a recommendation with a decision, or a decision with an execution, produces governance failures.*

| Comparison | Decision | Adjacent Concept | Key Distinction | Consequence of Confusion |
|---|---|---|---|---|
| **Decision vs Prediction** | Commits resources to a position | States a probabilistic forecast | A prediction says "X will happen with probability P." A decision says "Given that belief, I will commit Y capital." | Treating a prediction as a decision skips governance; treating a decision as a prediction avoids accountability |
| **Decision vs Recommendation** | Has been approved; capital is reserved | Proposes action; awaits approval | A recommendation is a proposal. A decision is an approved commitment. A recommendation can be rejected. A decision cannot be silently abandoned. | Confusing these means the governance layer is bypassed; recommendations are self-approved without oversight |
| **Decision vs Guess** | Based on reasoning, evidence, and conviction | Based on intuition, noise, or hope | A guess cannot be explained; a decision can always be traced to evidence and reasoning steps | Accepting guesses as decisions corrupts the decision quality register; learning from guesses is counterproductive |
| **Decision vs Optimization** | Chooses under uncertainty with judgment | Finds the mathematically optimal solution | Optimization assumes a defined objective function and complete model. Decisions operate in an incompletely-specified world where the objective itself must be judged. | Treating portfolio construction as a pure optimization problem ignores model risk, regime change, and unquantifiable factors |
| **Decision vs Risk Taking** | Accepts risk deliberately after analysis | Exposes to risk, possibly inadvertently | All decisions involve risk taking. But risk taking does not require a decision — it can happen through inaction or oversight. Good decision architecture makes all risk-taking explicit and deliberate. | Conflating these allows the system to accumulate implicit risks that are never deliberately accepted |
| **Decision vs Action** | The commitment to act; includes governance | The physical act of implementation | A decision may be made and then the corresponding action deferred, modified, or delegated. The action is the execution of the decision, not the decision itself. | Treating every action as a decision removes the governance layer; the Risk Guardian cannot operate |
| **Decision vs Approval** | The binding commitment made after approval | The permission to proceed | Approval is a gate; decision is the commitment. Approval without a decision recommendation is an empty process. A decision is meaningless without the approval that authorizes it. | Treating approval as the decision confuses the governance layer — the decision-maker and the approver are different roles with different responsibilities |
| **Decision vs Execution** | The commitment; precedes execution | The market act that implements the decision | A decision is made at the intelligence layer. Execution is the technical implementation. A decision can be split into multiple execution steps, modified for market conditions, or deliberately delayed. | Treating execution as decision-making means market microstructure forces override intelligence-layer commitments |

---

### 5 — Why Decisions Are Commitments

Every investment decision creates four simultaneous commitments that cannot be avoided:

**The Capital Commitment**
When a buy decision is made for 200 shares of HDFC Bank at 1,820, approximately 364,000 rupees of capital is committed. That capital cannot simultaneously be in a TATAMOTORS position, a cash buffer, or a hedging instrument. The capital commitment is not reversed when the order is placed — it is reserved the moment the decision is made and approved. The capital allocation system must reflect the reservation immediately to prevent over-commitment.

**The Risk Commitment**
The moment a position is entered, the portfolio's risk profile changes. Sector exposure increases; correlation with banking sector events increases; the daily VaR of the portfolio increases. The system has committed to bearing this risk — not just for the duration of the position, but for the full holding period expected at decision time. Risk budget consumed by this decision is unavailable for other opportunities until the position is closed.

**The Opportunity Commitment**
Capital and risk budget deployed in HDFC Bank cannot simultaneously be deployed in RELIANCE, INFOSYS, or TITAN. The decision to buy HDFC Bank is also, implicitly, a decision not to buy anything else with that capital at this moment. The opportunity cost of the decision is the expected return of the best alternative use of that capital. The decision architecture must ensure that the expected return of the chosen action exceeds the expected opportunity cost.

**The Accountability Commitment**
Every decision is permanently recorded. The rationale, evidence, conviction score, alternatives considered, risk assessment, governance approvals, and outcome are all part of the permanent record. The decision-maker — whether AI, committee, or human override — is accountable for the quality of the reasoning that produced the decision. This accountability commitment is what makes learning possible: "This decision was made with this evidence; this outcome resulted; this is what we should change."

---

### 6 — The Decision Contract

Every investment decision implicitly creates a decision contract — a set of commitments between the decision system and the portfolio:

```
═══════════════════════════════════════════════════════════════════
                       THE DECISION CONTRACT
═══════════════════════════════════════════════════════════════════

THE DECISION SYSTEM COMMITS TO:
┌─────────────────────────────────────────────────────────────────┐
│ ✓  Grounded in evidence — at least 3 independent evidence types │
│    with minimum conviction score 6.5 / 10                       │
│                                                                 │
│ ✓  Consistent with current market regime                        │
│                                                                 │
│ ✓  Position sized within the risk budget and mandate limits     │
│                                                                 │
│ ✓  Defined exit conditions before entry (stop loss + target)    │
│                                                                 │
│ ✓  Defined holding horizon and time stop                        │
│                                                                 │
│ ✓  All governance gates cleared before execution               │
│                                                                 │
│ ✓  Continuous monitoring throughout the hold period            │
│                                                                 │
│ ✓  Exit if thesis is invalidated regardless of current P&L      │
│                                                                 │
│ ✓  Outcome permanently recorded and fed to learning system     │
└─────────────────────────────────────────────────────────────────┘

THE PORTFOLIO COMMITS TO:
┌─────────────────────────────────────────────────────────────────┐
│ ✓  Capital reserved immediately upon decision approval          │
│                                                                 │
│ ✓  Risk budget updated to reflect this commitment               │
│                                                                 │
│ ✓  Sector and correlation exposure limits updated               │
│                                                                 │
│ ✓  Performance attribution tracked to this specific decision    │
│                                                                 │
│ ✓  Learning record created when position closes                 │
└─────────────────────────────────────────────────────────────────┘

IF THE THESIS IS INVALIDATED:
┌─────────────────────────────────────────────────────────────────┐
│ ✗  The contract expires regardless of current P&L               │
│ ✗  Sunk cost has no standing — the position is closed           │
│ ✗  A new decision must be made on fresh evidence if re-entry    │
│ ✗  No averaging down on an invalidated thesis                   │
└─────────────────────────────────────────────────────────────────┘
═══════════════════════════════════════════════════════════════════
```

---

## PART II — THE COMPLETE DECISION UNIVERSE

*The exhaustive vocabulary of investment decision-making. Every concept the system uses to decide must be defined here before it is used anywhere else in the decision pipeline.*

---

### Group A — Core Decision Concepts
*The foundational vocabulary of what decisions are, how they are structured, and what governs them.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Decision | A binding commitment to a course of action made under uncertainty with full acknowledgment of resource consumption | The atomic unit of the decision system — the moment intelligence commits to action |
| Commitment | An irrevocable pledge to a course of action that cannot be silently abandoned | Transforms a recommendation into an obligation; creates accountability |
| Resolve | The act of converting a recommendation into a finalized decision — parameters locked, capital reserved, execution authorized | The final internal step before execution begins |
| Approval | Formal permission from a governance authority to proceed with a decision recommendation | The gate between recommendation and decision; separates analysis from commitment |
| Rejection | Formal denial of a decision recommendation by a governance authority | Returns the proposal to the analysis layer with stated reasons; triggers re-evaluation |
| Hold | A decision to maintain an existing position as-is, explicitly reconfirming the original thesis | Not inaction — an active decision to continue; requires reconfirmed conviction |
| Wait | A decision to defer action pending additional evidence or improved conditions | Active monitoring state; a decision with a trigger condition, not mere passivity |
| Observe | A preliminary monitoring state where the system tracks a potential opportunity without capital commitment | Pre-decision state; hypothesis active but below conviction threshold |
| Review | A structured evaluation of an existing decision against current evidence | Required when: conviction decays, contradicting evidence arrives, or regime changes |
| Escalation | The referral of a decision from a lower governance tier to a higher tier due to size, complexity, or conflict | Preserves decision quality under exceptional conditions; prevents autonomous overreach |
| Override | The deliberate supersession of a system-generated decision by a higher-authority instruction | Human over AI or senior committee over AI; requires documented justification |
| Manual Override | An override initiated by a human agent, explicitly documented and attributed | Highest-authority action; subject to post-decision review; recorded permanently |
| Automatic Approval | A decision that clears all governance gates without requiring explicit committee deliberation | Applied for decisions below materiality thresholds in calm regimes |
| Automatic Rejection | A decision that fails a mandatory governance gate and is rejected without human deliberation | Applied when kill switch is active, daily loss limit is breached, or sector limit is exceeded |
| Recommendation | A structured proposal for action produced by the reasoning pipeline, awaiting governance approval | The output of the reasoning system; the input to the governance system |
| Rationale | The documented reasoning chain that supports a decision recommendation | The traceable path from evidence to conclusion; required for every approved decision |
| Justification | The specific reasons that make a decision acceptable despite acknowledged risks | The defense of a decision against identified objections |
| Authorization | Formal permission from a designated authority to proceed with capital commitment | Creates operational accountability for the decision |
| Mandate | The pre-approved set of decision boundaries within which the system may act without per-decision approval | Defines the autonomous operating space of the AI decision system |
| Scope | The boundaries within which a decision applies — entity, quantity, price, timing, and duration | Prevents scope creep; ensures the decision is implemented as designed |
| Decision Record | The permanent, immutable document capturing all aspects of a decision from recommendation to outcome | The primary audit artifact; the input to the learning system |
| Decision ID | A unique, permanently assigned identifier for every decision | Enables tracking, attribution, and retrieval across all system layers |
| Decision State | The current lifecycle status of a decision: Pending, Approved, Rejected, Active, Monitoring, Closed | Drives the operational workflow of the decision system |
| Decision Lifecycle | The complete sequence of states a decision passes through from inception to learning | Ensures no step is skipped; creates the complete audit trail |
| Veto | The right of a designated authority to block a decision regardless of general consensus | The highest-level governance authority; reserved for kill switch and risk committee chair |
| Consensus | Agreement among all relevant decision-making agents, above a defined threshold | Not required for all decisions; required for maximum-size conviction decisions |
| Minority Opinion | A dissenting view held by one or more agents that does not prevent the decision but is formally recorded | Protects against groupthink; provides early warning for thesis reassessment |
| Committee | A multi-agent governance body that evaluates high-stakes decisions collectively | Adds governance quality for decisions exceeding individual agent authority |
| Quorum | The minimum number of agents required for a committee decision to be valid | Prevents decisions being made with insufficient perspective coverage |
| Decision Window | The time period during which a decision recommendation remains valid and may be executed | Prevents stale decisions from being acted on after conditions change |
| Decision Freshness | The degree to which a decision recommendation still reflects current market conditions | Degrades with time and new market information; has an expiry threshold |
| Decision Expiry | The automatic invalidation of a decision recommendation that has not been acted on within its window | Prevents ghost decisions from being executed after the thesis has changed |
| Priority | The relative urgency of one decision over others when resources are constrained | Used to sequence the decision queue when multiple opportunities compete |
| Urgency | The time-sensitivity of a decision — how quickly it must be made before the opportunity closes | Modulates the speed of the governance process; does not justify bypassing governance |
| Decision Queue | The ordered collection of pending decision recommendations awaiting governance review | Manages sequential processing when multiple decisions compete simultaneously |
| Decision Arbitration | The process of resolving conflicts between competing decision recommendations for the same capital | Prevents double-allocation of capital or risk budget |
| Conflict | A situation where two decision recommendations are mutually incompatible or compete for the same resources | Must be explicitly resolved; cannot be ignored |
| Reconsideration | A formal request to re-evaluate a rejected recommendation with new or additional evidence | Available once per recommendation cycle; prevents indefinite rejection loops |
| Cancellation | The deliberate withdrawal of a pending decision recommendation before execution | Available at any point before the order is filled; creates a cancellation audit record |
| Deliberation | The structured process of weighing evidence, alternatives, and consequences before committing | All decisions above materiality threshold require explicit deliberation |
| Decision Fatigue | The degradation of decision quality resulting from excessive decisions in a short period | A real risk in high-frequency environments; managed through automation and priority filtering |
| Decision Bandwidth | The system capacity to evaluate, approve, and manage concurrent decisions | A finite resource; must be managed to prevent decision quality degradation |
| Conditional Decision | A decision that commits to action contingent on a future event or price condition being met | Entry decisions often conditional (trigger at X level); reduces premature commitment risk |
| Standing Decision | A pre-approved decision framework that applies automatically when defined conditions occur | Used for rule-based exits; kill switch; systematic rebalancing |
| Decision Cadence | The frequency and rhythm at which decision reviews and new evaluations are conducted | Ensures systematic coverage; prevents opportunity drift and monitoring gaps |

---

### Group B — Capital and Resource Concepts
*The vocabulary of what decisions consume — the finite resources that every decision allocates.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Capital | The financial resources available for investment — the primary resource that decisions deploy | Every buy decision deploys capital; every sell decision returns it; capital is always finite |
| Available Capital | The portion of total capital not currently deployed or reserved for pending decisions | The actual investable amount at any given moment |
| Deployed Capital | The portion of total capital currently invested in active positions | Cannot be redeployed without closing existing positions |
| Reserved Capital | Capital committed to approved pending decisions but not yet invested through execution | Prevents over-commitment; reduces available capital until order fills or is cancelled |
| Cash Buffer | The minimum cash position maintained for emergencies, redemptions, and forced exits | Non-deployable; constitutionally protected from investment decisions |
| Capital Allocation | The deliberate assignment of capital to specific investment opportunities | The core resource decision; determines portfolio composition |
| Capital Reservation | The pre-emptive locking of capital for an approved decision prior to execution | Prevents the same capital from being allocated to two decisions simultaneously |
| Capital Return | The release of deployed capital back to available state upon position closure | Increases available capital; triggers the opportunity pipeline review |
| Capital Efficiency | The ratio of returns generated per unit of capital deployed | Optimizing capital efficiency is a key decision objective alongside risk management |
| Capital Preservation | The constitutional priority of protecting existing capital before seeking additional returns | Supersedes return maximization when the two conflict |
| Gross Exposure | The total face value of all open positions, long and short, without netting | Used to check absolute deployment level against mandate limits |
| Net Exposure | The net directional exposure after offsetting long and short positions | Measures directional market risk; indicates whether portfolio is net long or net short |
| Concentration | The percentage of total capital allocated to a single entity, sector, or theme | Concentration above mandate limit triggers automatic decision rejection for that allocation |
| Risk Budget | The total amount of expected portfolio risk available for allocation, measured in drawdown or VaR terms | Analogous to capital but in risk units; each decision consumes risk budget |
| Risk Allocation | The portion of the total risk budget assigned to a specific position or decision | Must be approved alongside capital allocation; both must be within limits |
| Risk Budget Utilization | The fraction of total risk budget currently consumed by open decisions | Tracked in real time; approaching ceiling triggers conservative decision posture |
| Position Slot | One of the finite number of concurrent positions the portfolio may hold | Like capital, position slots are finite; a new decision may require closing an existing position |
| Opportunity Cost | The expected return of the best alternative use of the capital being deployed | Every decision implicitly forecloses alternatives; this cost must be considered |
| Cost of Capital | The minimum return threshold required to justify a deployment of capital | Decisions with expected returns below cost of capital should be rejected |
| Transaction Cost | The direct cost of executing a decision: brokerage, taxes, slippage, and market impact | Reduces expected returns; must be incorporated into the conviction calculation |
| Market Impact | The price movement caused by the execution of a large decision | Reduces actual returns below theoretical for large positions; limits position size |
| Slippage | The difference between the decision price and the actual execution price | A function of position size, liquidity, and execution speed |
| Turnover | The frequency with which capital is recycled through decisions | High turnover increases transaction costs; managed through minimum holding period requirements |
| Leverage | The use of borrowed capital to multiply position size and potential returns and risks | Increases capital efficiency at the cost of amplified risk; subject to strict mandate limits |
| Margin | Collateral required to maintain a leveraged or derivative position | Margin calls create forced decisions; the system must maintain adequate margin buffers |
| Liquidity | The ability to enter and exit a position at the desired price without excessive market impact | A prerequisite for decision viability; illiquid positions cannot be exited as planned |
| Liquidity Reserve | Capital held specifically to exploit sudden opportunities, distinct from the cash buffer | Available for rapid deployment when high-conviction opportunities arise suddenly |
| Capital Floor | The minimum capital level below which no new decisions may be made | Constitutional protection; prevents complete capital exhaustion from a decision sequence |
| Deployment Rate | The percentage of available capital deployed in active decisions at any given moment | Target range 60–90%; below 60% is opportunity cost; above 90% creates fragility |
| Drawdown Budget | The maximum acceptable portfolio drawdown before shifting to capital preservation mode | When approached, decision posture shifts from opportunity-seeking to defensive |
| Reinvestment Decision | A decision to redeploy capital returned from a closed position | Not automatic; requires a new decision recommendation and approval cycle |
| Capital Rotation | The systematic reallocation of capital from underperforming to outperforming themes or sectors | A portfolio-level decision distinct from individual position decisions |
| Capital at Risk | The actual capital that could be lost on an approved decision, measured from entry to stop loss | Position Size times the distance from entry to stop loss; bounded before entry |
| Expected Loss | The probability-weighted potential loss from a decision | Must be within the risk budget to proceed to approval |
| Maximum Loss | The worst-case loss scenario for a decision — reached when the stop loss is hit | Bounded by the stop loss level; one of the primary governance gate checks |
| Drawdown | The peak-to-trough decline in portfolio value — the primary measure of capital destruction | The metric that the kill switch is calibrated to protect against |
| Capital Velocity | The speed at which capital moves from decision to deployment to return and back | Optimized by minimizing time in pre-execution pending states |

---

### Group C — Risk Concepts
*The vocabulary of uncertainty, exposure, and protection — how decisions interact with the risk dimension.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Risk | The possibility of an outcome different from what is expected — specifically the possibility of capital loss | Every decision accepts risk; the system must quantify, bound, and manage risk explicitly |
| Market Risk | The risk of loss from adverse movements in market prices, rates, currencies, and volatility | The primary risk type for equity investment decisions |
| Specific Risk | The risk arising from factors unique to a specific company or sector, independent of the broad market | Reduced through diversification across uncorrelated decisions |
| Systematic Risk | The risk that affects all assets simultaneously and cannot be diversified away | Managed through portfolio-level decisions, cash levels, and hedging |
| Concentration Risk | The risk arising from excessive exposure to a single entity, sector, or correlated group | Prevented by concentration limits defined in the mandate |
| Liquidity Risk | The risk that a position cannot be exited at the desired price and time | Checked at entry and continuously throughout the holding period |
| Execution Risk | The risk that the actual execution deviates materially from the decision parameters | Managed through order type selection and position size limits relative to daily volume |
| Tail Risk | The risk of extreme outcomes in the far tail of the return distribution | Explicitly modeled through Monte Carlo scenarios; protected by the kill switch |
| Regime Risk | The risk that the market regime changes in a way that invalidates the decision thesis | The most systemically dangerous risk; managed through regime-conditional strategy activation |
| Model Risk | The risk that the decision model or knowledge item is wrong, incomplete, or has drifted | Managed through walk-forward testing, rolling performance monitoring, and OOS validation |
| Correlation Risk | The risk that positions assumed to be uncorrelated become correlated in stress scenarios | The primary cause of portfolio drawdowns exceeding position-level expectations |
| Volatility Risk | The risk that realized volatility exceeds assumed volatility, causing premature stop breaches | Managed through volatility-adjusted position sizing |
| Drawdown Risk | The risk of a sustained decline in portfolio value requiring significant time to recover | The risk that the kill switch is designed to cap at the portfolio level |
| Event Risk | The risk of loss from an unexpected event: earnings shock, regulatory action, geopolitical escalation | Managed through position sizing, diversification, and event calendar monitoring |
| Timing Risk | The risk of being correct directionally but wrong on timing — right eventually but out of capital before | Managed through time stops and conviction refresh requirements |
| Idiosyncratic Risk | The unique company-specific risk associated with a particular investment | Present in every stock decision; reduced through portfolio diversification |
| Portfolio Risk | The aggregate risk of all open decisions combined, accounting for correlations | Not simply the sum of individual risks — correlation dramatically affects portfolio risk |
| VaR | Value at Risk — the maximum expected loss over a defined horizon at a defined confidence level | The primary portfolio-level risk metric; checked at every major decision |
| Expected Shortfall | The average loss in the worst scenarios beyond VaR — a more complete tail risk measure | Used for tail risk budgeting in high-conviction large decisions |
| Risk-Adjusted Return | Return divided by an appropriate risk measure — the quality-adjusted return | The decision expected return must exceed the hurdle rate on a risk-adjusted basis |
| Sharpe Ratio | Return above risk-free rate divided by standard deviation — the most common risk-adjusted metric | All strategies and decisions must demonstrate positive Sharpe ratio at portfolio level |
| Maximum Drawdown | The largest peak-to-trough decline in a strategy or portfolio over a historical period | The primary metric for assessing strategy survivability and mandate compliance |
| Recovery Time | The estimated time required to recover from a drawdown | Longer recovery times represent a greater actual risk — capital is unproductive during recovery |
| Risk Tolerance | The maximum level of risk the portfolio is mandated to bear at any given time | Changes with market conditions, portfolio performance, and risk regime |
| Risk Capacity | The maximum risk the portfolio can structurally bear before permanent capital impairment | Distinguished from risk tolerance: capacity is structural, tolerance is behavioral |
| Stop Loss | A pre-defined price level at which a losing position must be closed to prevent further loss | The primary mechanical risk control; must be defined for every approved decision before execution |
| Hard Stop | A stop loss that triggers immediate unconditional exit when hit | Applied to high-risk positions and positions in volatile or uncertain regimes |
| Trailing Stop | A stop loss that moves in the direction of the position to lock in profits | Applied to longer-term positions with sustained positive momentum |
| Time Stop | A stop that triggers position closure after a specified time period regardless of P&L | Applied when the thesis had a specific time horizon that has expired without confirmation |
| Kill Switch | A system-level hard stop that closes all or selected positions due to extreme portfolio conditions | Triggered by VIX above 45, daily portfolio loss above 2%, or other constitutional conditions |
| Risk Gate | A specific governance checkpoint that a decision must pass before advancing | Each gate tests one risk dimension; failing any gate blocks the decision from proceeding |
| Hedging | The use of offsetting positions to reduce the net risk of the portfolio | A risk management decision distinct from investment decisions; reduces both risk and potential return |
| Beta | The sensitivity of a position or portfolio to broad market movements | Portfolio beta is monitored; high-beta decisions require stronger conviction in market direction |
| Risk Premium | The additional return expected from bearing a specific type of risk | The theoretical basis for all investment decisions — the reward for deliberately accepted risk |
| Asymmetry | A return profile where potential gains significantly exceed potential losses | The ideal characteristic of all approved decisions; sought through asymmetric payoff structures |
| Downside Protection | The mechanisms in place to limit maximum loss: stop losses, hedges, diversification, kill switch | Every approved decision must have documented downside protection |
| Stress Test | The evaluation of a decision or portfolio under adverse scenario conditions | Required for all decisions above materiality threshold; ensures resilience before commitment |

---

### Group D — Return and Reward Concepts
*The vocabulary of what decisions aim to achieve — the expected benefits that justify risk-taking.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Return | The financial gain or loss from an investment decision, expressed as percentage of capital deployed | The primary objective of every investment decision |
| Expected Return | The probability-weighted average return across all possible outcomes | Calculated before every decision; must exceed the hurdle rate to be approved |
| Realized Return | The actual return achieved after the position is closed | The input to the learning system; compared against expected return for calibration |
| Alpha | The return in excess of what would be explained by market movements — the value added | The primary measure of decision intelligence quality |
| Absolute Return | Total return measured in percentage terms, without reference to a benchmark | Primary return metric for capital preservation-oriented strategies |
| Risk-Adjusted Return | Return adjusted for the risk taken to achieve it — the quality metric | Every decision must be evaluated on risk-adjusted return, not raw return |
| Payoff | The actual financial gain from a decision — the money received when the position closes profitably | The realized upside component of expected value |
| Edge | The statistical advantage of a decision type over the long run — the excess positive expected return | Investment decisions must have demonstrated edge to be approved |
| Expected Value | The sum of all possible outcomes weighted by their probabilities | Must be positive after all transaction costs for a decision to be approved |
| Expected Utility | Expected value adjusted for risk preferences — acknowledges that equal returns are not equally desirable | Used for decisions near the risk budget ceiling or in tail-risk conditions |
| Upside | The maximum potential gain from a decision | Must exceed the downside by a defined minimum ratio for approval |
| Downside | The maximum potential loss from a decision — bounded by the stop loss | Known and bounded before every decision; no unbounded downside is permitted in this architecture |
| Reward-to-Risk Ratio | The ratio of expected upside to expected downside | Minimum ratio for approval: 2:1 — target 2 rupees for every 1 rupee risked |
| Profit Target | A pre-defined price level at which a profitable position should be partially or fully closed | Must be defined before entry; prevents giving back gains through indecision |
| Expected Holding Period | The anticipated duration of an open position | Drives time-based monitoring schedules; contributes to annual return calculation |
| Annualized Return | Return normalized to a one-year period for cross-strategy comparison | Used to compare strategies with different holding periods on equal footing |
| CAGR | Compound Annual Growth Rate — the rate at which capital compounds over time | The primary long-term performance metric for the system |
| Batting Average | The fraction of decisions that produce a positive return | Win rate; targeted at a minimum 50% for the aggregate decision portfolio |
| Average Win | The mean return of profitable decisions | Together with win rate and average loss, determines expected value at portfolio level |
| Average Loss | The mean loss of unprofitable decisions | Bounded by stop loss discipline; must be smaller than average win for positive expectation |
| Profit Factor | Total gross profit divided by total gross loss | Must be above 1.0 for the decision system to be net positive; target above 1.5 |
| Kelly Fraction | The theoretically optimal fraction of capital to bet on a decision, derived from edge and odds | Used as a ceiling not a floor — actual position sizes are typically half Kelly or quarter Kelly |
| Half-Kelly | Kelly Fraction times 0.5 — a more conservative allocation reducing variance while preserving most expected value | The standard position sizing upper bound in this architecture |
| Breakeven | The price level at which a position neither gains nor loses | Used for stop migration after sufficient gains; protects partial profits |
| Reward Threshold | The minimum expected return required to justify the associated risk and opportunity cost | Decisions below the reward threshold are rejected even if expected value is marginally positive |
| Compounding | The reinvestment of returns from previous decisions to generate returns on returns | The mechanism by which good decision quality creates exponential wealth over time |
| Information Ratio | Alpha divided by tracking error — the consistency-adjusted alpha | Used to compare decision systems across time; higher indicates more consistent value creation |
| Decision Contribution | The specific return contributed by a single decision to the portfolio total | Enables attribution analysis; identifies which decision types drive returns |
| Portfolio Return | The aggregate return of all decisions made over a period | The system ultimate report card; produced by the sum of all decision contributions |
| Outperformance | Returns exceeding the benchmark or cost of capital | The primary long-term objective of every investment decision system |
| Mean Reversion Return | Returns from a decision that benefits from a temporary deviation reverting to equilibrium | A specific return source requiring timing precision and regime-specific validation |
| Momentum Return | Returns from a decision that benefits from the continuation of an existing trend | A specific return source requiring regime awareness — invalid in sideways regimes |
| Dividend Yield | Annual dividend income as a percentage of the entry price | An additional return component for longer-term investment decisions |
| Total Return | Capital appreciation plus dividend income minus all transaction costs | The complete financial outcome of a decision |
| Annualized Volatility | The standard deviation of returns normalized to one year | Used to assess the consistency of returns alongside the mean |
| Carry | The return earned from holding a position through time, independent of price movement | Relevant for fixed income, currency, and certain equity income strategies |

---

### Group E — Entry Decision Concepts
*The vocabulary of how and when the system decides to open a new position.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Entry Decision | The commitment to open a new position in a specific entity at a specific time | The most consequential decision type — initiates all capital commitment and risk exposure |
| Entry Price | The price level at which the decision calls for opening the position | The reference point for all subsequent position management decisions |
| Entry Signal | The specific observation or trigger that initiates the entry decision process | The first step in the entry decision pipeline; must meet materiality threshold to proceed |
| Entry Condition | The set of criteria that must all be satisfied for an entry decision to be approved | Multiple conditions must converge; single-condition entries are rejected by governance |
| Entry Timing | The specific moment within a decision window when execution is planned | Affects realized entry price; optimized within a band around the decision price |
| Entry Zone | A price range, rather than a single price, within which the entry decision remains valid | Allows for minor price fluctuations without invalidating the decision |
| Entry Conviction | The conviction score at the time of the entry decision | Minimum 6.5/10 required; the higher the conviction, the larger the approved position size |
| Entry Thesis | The explicit statement of why the position is being opened and what must remain true for it to be held | The governing document for all subsequent position management decisions |
| Entry Hypothesis | The primary investment hypothesis that the position is designed to profit from | Must be falsifiable; must have defined invalidation conditions |
| Fresh Thesis | An entry decision based on evidence that has not previously been acted on | Distinguished from recycled entry on the same thesis after a prior stop-out |
| Position Initiation | The act of opening a new position — the execution of an approved entry decision | Creates the first portfolio state change associated with this decision |
| Scaling In | A strategy of opening a position in multiple stages rather than all at once | Reduces timing risk; first entry at lower conviction, adding as conviction builds |
| Initial Position | The first tranche of a scaled entry — smaller than the target position size | The minimum commitment; sized to limit loss if the thesis does not develop |
| Target Position | The full intended position size once full conviction is established | The maximum size approved by governance; the ceiling for position scaling |
| Entry Trigger | The specific condition whose occurrence initiates execution of an approved entry decision | May be price-based, event-based, or time-based; must be pre-defined |
| Market Entry | An entry executed at the current market price without price constraint | Used when speed of execution is more important than price precision |
| Limit Entry | An entry executed only at or below a specified price | Provides price control; may not fill if market moves away |
| Entry Window | The time period during which an entry decision remains valid for execution | Expires automatically; prevents stale entries from being executed |
| Re-entry | A new entry into a previously held position after the original was closed | Requires a new thesis, new evidence, and a full new governance cycle |
| Entry after Break | An entry timed to occur after a confirmed technical breakout of a key level | Specific entry timing condition used in momentum strategies |
| Entry on Pullback | An entry timed to occur during a temporary retracement within an established trend | Specific entry timing condition used to improve entry price on trending positions |
| Counter-Trend Entry | An entry that takes a position against the current price trend | Higher-risk entry type; requires additional conviction and smaller initial size |
| Breakout Entry | An entry triggered when the price breaks through a previously established resistance or support level | Momentum-based; requires volume confirmation and regime validation |
| Confirmation Entry | An entry made only after an initial signal is confirmed by a second independent signal | Reduces false entries at the cost of slightly worse entry price |
| Early Entry | An entry made before the thesis is fully confirmed, at reduced position size | Acceptable at half conviction with half position size; completes on confirmation |
| Late Entry | An entry made after the optimal entry point, after significant move has already occurred | Assessed against the remaining reward-to-risk ratio; may be approved at reduced size |
| Entry Audit | A post-entry review confirming all governance conditions were satisfied | Retroactive check; any governance violation found triggers a review and potential exit |
| Entry Rationale | The documented reasoning explaining why this entry was made at this time and price | Permanent record; the accountability document for the entry decision |
| Pre-entry Check | The final verification of all governance conditions immediately before execution | The last gate before capital commitment; cannot be skipped |
| Entry Invalidation | The condition under which an approved but not-yet-executed entry is cancelled | Occurs when: price moves outside entry zone, thesis evidence is contradicted before fill |
| Entry Size | The quantity of shares or contracts in the initial position | Determined by position sizing framework; not by how much the trader wants to own |
| Entry Cost Basis | The weighted average price at which the full position was established | The reference price for all P&L calculation and stop loss management |
| Catalyst Entry | An entry timed around a specific expected catalyst event | Requires event timeline alignment; carries elevated timing risk |
| Systematic Entry | An entry generated by a quantitative rule-based strategy with pre-defined triggers | Fully automated; bypasses deliberation when mandate allows |
| Discretionary Entry | An entry requiring explicit deliberation and approval beyond the systematic signal | Applied for larger positions, unusual conditions, or when systematic signals conflict |
| Entry Concentration Check | The verification that the new entry does not push sector or correlation concentration above mandate limits | A mandatory pre-entry governance gate |
| Regime-Validated Entry | An entry that has been confirmed as appropriate for the current market regime | All entries require regime validation; entries not validated for current regime are rejected |
| Entry Diversity | The degree to which a new entry adds to portfolio diversification | Entries that increase concentration without proportionate return uplift are penalized in sizing |
| Event-Driven Entry | An entry thesis primarily based on an upcoming corporate or macroeconomic event | Requires event timing precision; has an automatic expiry tied to the event date |
| Value Entry | An entry thesis based primarily on the intrinsic value of an entity relative to current market price | Typically longer holding horizon; requires patience through mark-to-market volatility |
| Momentum Entry | An entry thesis based primarily on the continuation of a recent price and volume trend | Requires trending regime; automatically deactivated in sideways or mean-reversion regimes |

---

### Group F — Exit Decision Concepts
*The vocabulary of how and when the system decides to close an existing position.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Exit Decision | The commitment to close an existing position, in full or in part, at a specific time | Terminates the capital commitment; triggers P&L realization and learning cycle |
| Full Exit | The complete closure of an entire position — all shares or contracts are sold | Ends the capital commitment entirely; frees all reserved capital and risk budget |
| Partial Exit | The closure of a fraction of an existing position, maintaining residual exposure | Used at profit targets to secure gains while allowing remaining position to run |
| Forced Exit | A position closure triggered by an automatic rule, not by active decision | Stop loss hit, time stop expiry, kill switch activation, margin call |
| Voluntary Exit | An exit made based on updated conviction or thesis evolution, not a forced rule | Requires conviction below 4.0, thesis invalidation, or superior alternative opportunity |
| Profit Take | An exit at or near the profit target level | Disciplined realization of planned gains; not the same as an opportunistic exit |
| Stop Loss Exit | An exit triggered when the position price hits the pre-defined stop loss level | The primary loss-limiting mechanism; unconditional when triggered |
| Time Stop Exit | An exit triggered when the expected holding period expires without thesis confirmation | Applied when the thesis required a specific catalyst that has not materialized |
| Thesis Invalidation Exit | An exit triggered when a key assumption of the original entry thesis is proven false | Must be executed regardless of current P&L — the thesis is dead, not the trade |
| Breakeven Exit | Moving the stop loss to the entry price and closing if that level is breached | Protects against turning a winning trade into a loss |
| Trailing Stop Exit | An exit triggered when the price reverses from its highest (for a long) by the trailing distance | Progressively locks in profits while allowing the position to run |
| Emergency Exit | An immediate market-order exit triggered by kill switch or extraordinary conditions | Speed prioritized over price; used when systemic risk is elevated above tolerance |
| Conviction Exit | An exit triggered when the ongoing conviction score falls below the exit threshold of 4.0 | The system changes its view on the thesis; holding is no longer justified |
| Regime Exit | An exit triggered when the market regime changes to one that is incompatible with the thesis | The original thesis was regime-conditional; the regime has changed |
| Scaling Out | The reduction of a position in tranches rather than all at once | Reduces timing risk on exit; used at multiple profit targets |
| Exit Trigger | The specific condition whose occurrence initiates execution of an exit decision | Pre-defined at entry time; may be price, event, time, or conviction based |
| Exit Rationale | The documented reasoning explaining why the position is being closed at this time | Permanent record; the accountability document for the exit decision |
| Exit Audit | A post-exit review confirming all governance conditions and exit rationale are sound | The input to the learning record; every exit triggers a post-mortem |
| Hold Decision | The decision to maintain an existing position rather than exit | Not inaction — an active decision requiring reconfirmed conviction |
| Exit Zone | A price range within which the exit decision may be executed | Allows for minor price variations without invalidating the exit decision |
| Exit Timing | The specific moment within an exit window when execution is planned | Affects realized exit price; optimized within a band around the decision price |
| Exit Price | The price level at which the exit is executed | Determines the realized return; compared against the entry price to calculate P&L |
| Exit Slippage | The difference between the intended exit price and the actual execution price | Affects realized returns; large positions in illiquid stocks have high exit slippage |
| Market Exit | An exit executed at the current market price without price constraint | Used when speed is critical — stop loss hits, kill switch, breaking news |
| Limit Exit | An exit executed only at or above a specified price (for longs) | Provides better price but may not fill; appropriate for systematic profit-taking |
| Early Exit | An exit made before the original profit target is reached | May be justified by deteriorating conviction, new contrary evidence, or capital needs |
| Premature Exit | An early exit that is not justified by thesis changes — selling a winner too soon | A decision failure mode; tracked and learned from; reduces batting average quality |
| Reluctant Exit | A delayed exit on a losing position, holding beyond what the thesis justifies | The sunk cost fallacy in action; a decision failure mode; detected by thesis validity monitoring |
| Exit After Stop Move | An exit following the migration of a stop loss to breakeven or trailing position | The stop was moved as the position profited; the trailing stop was then hit |
| Position Reduction | A partial exit that reduces position size without fully closing | Used when conviction has decreased but not fallen below the exit threshold |
| Re-evaluation | A structured review of whether to exit, hold, or add to a position | Required at defined intervals and triggered by new material information |
| Exit Discipline | The consistent application of pre-defined exit rules without emotional override | Constitutional requirement; prevents the cognitive biases that cause poor exit decisions |
| Outcome Recording | The permanent recording of all exit details for learning and attribution | Every exit triggers the learning cycle; no exit goes unrecorded |
| Position Cleanup | The systematic review and closure of all positions that no longer meet minimum holding standards | Conducted at end-of-day and end-of-week; prevents portfolio clutter |
| Horizon Exit | An exit planned for a specific future date regardless of price | Used for event-driven positions where the thesis expires on a defined date |
| Voluntary Hold | An active decision to maintain a position despite the option to exit for profit | Requires conviction above the maintenance threshold; the most common daily decision |
| Capital Release Decision | The decision sequence that follows a closed position — where does the freed capital go next? | Connects exit decisions to the next entry opportunity evaluation |
| Exit Confirmation | The acknowledgment that an exit order has been executed at the expected parameters | Triggers the P&L calculation, portfolio update, and learning record creation |
| Post-Exit Review | The structured analysis of every closed position covering entry, thesis, holding, exit, and outcome | The primary input to the learning system; required for every position regardless of P&L |

---

### Group G — Portfolio Governance Concepts
*The vocabulary of how portfolios are structured, constrained, and governed across all decisions.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Portfolio | The complete collection of all active positions and reserved capital across all decisions | The aggregate result of all decisions; the unit of ultimate performance measurement |
| Portfolio Construction | The deliberate assembly of a portfolio through individual decisions, optimized for risk-return | The strategic context within which individual decisions are evaluated |
| Portfolio Strategy | The overarching investment approach defining what types of decisions the portfolio makes | Defines the mandate; constrains the type, size, and frequency of allowed decisions |
| Portfolio Mandate | The formal specification of all permissions and constraints governing the portfolio | The constitutional document for the portfolio; supersedes all individual decisions |
| Investment Policy | The high-level rules governing what the portfolio may and may not invest in | Excludes certain asset classes, sectors, or decision types from consideration |
| Sector Allocation | The deliberate distribution of capital across different market sectors | Constrained by maximum sector concentration limits in the mandate |
| Asset Allocation | The distribution of capital across different asset classes: equities, cash, derivatives | The highest-level portfolio decision; drives all lower-level individual decisions |
| Portfolio Constraint | A hard limit on some portfolio characteristic that no individual decision may violate | Sector limits, correlation limits, position size limits, drawdown limits |
| Position Limit | The maximum size of any single position as a percentage of total portfolio | Prevents catastrophic loss from a single decision failure |
| Sector Limit | The maximum exposure to any single sector as a percentage of total portfolio | Prevents sector concentration risk from a cluster of correlated decisions |
| Correlation Limit | The maximum portfolio-level correlation that new decisions may add | Prevents the portfolio from becoming effectively a single concentrated bet |
| Drawdown Limit | The maximum acceptable portfolio drawdown before shifting to capital preservation posture | When breached, no new offensive decisions are approved until recovered |
| Concentration Limit | The maximum total exposure to any single theme, strategy, or correlated group | Broader than sector limit; captures thematic concentration across sectors |
| Cash Minimum | The minimum cash percentage the portfolio must maintain at all times | Provides liquidity buffer; prevents full deployment that would prevent emergency exits |
| Rebalancing | The deliberate adjustment of position sizes to restore target allocations after drift | A periodic portfolio-level decision; distinct from individual position entry and exit |
| Diversification | The distribution of risk across uncorrelated positions to reduce aggregate portfolio risk | A portfolio construction principle; each new decision must add diversification value |
| Correlation Matrix | The complete matrix of return correlations across all active positions | Monitored continuously; drives correlation limit checks for all new decisions |
| Portfolio Turnover | The fraction of the portfolio that is replaced with new positions over a period | Reflects decision frequency; high turnover increases transaction costs |
| Active Share | The fraction of the portfolio that differs from a benchmark | Measures how much the portfolio is expressing unique investment views |
| Portfolio Beta | The overall sensitivity of the portfolio to broad market movements | Managed at the portfolio level; individual decisions affect beta; limits exist |
| Tracking Error | The standard deviation of the difference between portfolio returns and benchmark returns | For benchmark-aware mandates; measures how different portfolio performance is from benchmark |
| Portfolio Optimization | The mathematical process of finding the portfolio allocation that maximizes return per unit of risk | A tool used within the decision process, not a substitute for judgment |
| Risk Budgeting | The systematic allocation of risk budget across strategies, sectors, and individual decisions | Ensures no single decision type or sector consumes a disproportionate share of total risk |
| Portfolio Stress Test | The evaluation of the complete portfolio under adverse market scenario conditions | Required periodically and before large new decisions that significantly change portfolio risk |
| Liquidity Profile | The distribution of positions by how quickly they can be exited without significant impact | Managed to ensure the portfolio can be de-risked rapidly in emergency scenarios |
| Portfolio Monitoring | The continuous oversight of all active decisions and aggregate portfolio metrics | Drives hold/exit/add decisions; the real-time interface between the portfolio and the market |
| Portfolio Review | A periodic structured evaluation of all active positions and the portfolio strategy | Scheduled: daily light review, weekly deep review, monthly strategic review |
| Portfolio Exposure | The total risk capital at stake across all active decisions | The most important real-time portfolio metric; must stay within mandate limits |
| Benchmark | The reference index against which portfolio performance is measured | NIFTY 50 for large-cap equity; sector indices for sector strategies |
| Attribution Analysis | The decomposition of portfolio returns into contributions from individual decisions | The primary post-period learning tool; reveals which decision types add the most value |
| Factor Exposure | The portfolio sensitivity to systematic factors: value, momentum, quality, low volatility | Monitored to prevent unintended factor concentration |
| Strategy Allocation | The distribution of capital and risk budget across different strategy types | Governs the portfolio at the strategy level above individual decisions |
| Portfolio State | The complete description of all positions, cash, reservations, and risk metrics at a point in time | The input to every new decision evaluation; must be current before approval |
| Decision Register | The complete log of all approved decisions, their current states, and their outcomes | The operational database of the decision system; updated in real time |
| Portfolio Health | An aggregate score reflecting the quality of current decisions, active strategies, and risk exposure | The summary metric reported to the governance layer; drives escalation decisions |
| Portfolio Drift | The unintended deviation of portfolio characteristics from the target due to market movements | Monitored continuously; triggers rebalancing decisions when limits are breached |

---

### Group H — Approval and Process Concepts
*The vocabulary of the governance process — how decisions move from proposal to commitment.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Governance | The complete system of rules, processes, and authorities that controls how decisions are made | The constitutional architecture of the decision system; ensures quality and accountability |
| Approval Process | The defined sequence of gates a recommendation must pass before becoming a decision | Ensures quality, compliance, and accountability; cannot be bypassed |
| Governance Gate | A specific checkpoint in the approval process that evaluates one dimension of decision quality | Each gate has a pass/fail criterion; failing any gate blocks the decision |
| Gate 1 — Evidence | Confirmation that at least 3 independent evidence types support the recommendation | The first governance gate; the most foundational quality check |
| Gate 2 — Conviction | Confirmation that conviction score meets or exceeds 6.5/10 | The second gate; ensures the evidence has reached the action threshold |
| Gate 3 — Risk | Confirmation that the position size is within risk budget and mandate limits | The third gate; ensures capital and risk are properly allocated |
| Gate 4 — Portfolio | Confirmation that the new decision does not violate portfolio concentration or correlation limits | The fourth gate; ensures the decision is compatible with existing commitments |
| Gate 5 — Regime | Confirmation that the current market regime is one where this decision type is validated | The fifth gate; prevents regime-inappropriate decisions |
| Gate 6 — Compliance | Confirmation that the decision complies with all mandate investment policy rules | The sixth gate; ensures policy boundaries are respected |
| Gate Failure | The failure of a decision to pass a specific governance gate | Triggers automatic rejection for critical failures; escalation for borderline cases |
| Gate Bypass | Any mechanism that allows a decision to proceed without completing all gates | Never permitted in this architecture; governance is unconditional |
| Two-Stage Approval | An approval process requiring sign-off from two independent governance authorities | Applied for decisions above a defined materiality threshold |
| Pre-Approval | A provisional approval contingent on satisfactory completion of subsequent gates | Used to reserve capital while remaining gates are being evaluated |
| Conditional Approval | An approval granted subject to one or more specified conditions | Applied when a decision is sound in principle but requires one parameter adjustment |
| Escalation Trigger | The specific condition that causes a decision to be escalated to a higher governance tier | Defined for position size, strategy type, market condition, and conflict scenarios |
| Decision Authority | The governance tier authorized to approve decisions of a given size and type | Defined in the authority matrix; smaller decisions have lower authority requirements |
| Authority Matrix | The complete mapping of decision types and sizes to their required approval authority | The governance constitution; establishes who can approve what |
| Delegated Authority | The authorization for an AI agent to make decisions autonomously within defined parameters | Within-mandate routine decisions; does not apply to exceptions or large positions |
| Residual Authority | Decision-making power that has not been delegated and remains with the highest governance tier | Human override; cannot be further delegated |
| Four-Eyes Principle | The requirement that two independent agents must review any decision above a threshold | Prevents single-agent errors from creating large unreviewed commitments |
| Audit Trail | The complete, immutable record of every governance step for every decision | Required by the constitution; enables post-decision review and learning |
| Approval Timestamp | The exact time at which a governance authority provided approval | Part of the permanent decision record; enables process timing analysis |
| Rejection Reason | The specific stated reason why a governance gate failed or a committee rejected | Required for every rejection; enables recommendation improvement |
| Re-submission | The process of revising and resubmitting a rejected recommendation with improvements | Requires documented changes from the rejection reason; not a repeat of the same submission |
| Governance Cycle | The complete end-to-end approval process from recommendation creation to decision commitment | Measured in time; the governance cycle duration affects decision window management |
| Fast-Track Approval | A streamlined approval process for decisions that meet specific pre-defined criteria | Used for routine systematic decisions; cannot be applied to exceptions or novel situations |
| Standing Committee | A permanently constituted committee with ongoing decision review authority | Conducts regular portfolio reviews; approves strategic allocation decisions |
| Ad-Hoc Committee | A committee convened for a specific high-stakes decision or set of related decisions | Convened for exceptional circumstances; disbands after the specific decision is resolved |
| Governance Failure | A case where a decision was made outside the proper governance process | Creates a permanent violation record; triggers an audit and potentially an exit |
| Post-Decision Audit | A structured review of the governance process for a completed decision | Ensures governance quality; identifies process improvements; learns from governance failures |
| Decision Transparency | The principle that all decision rationale, evidence, and governance steps are accessible | Required by constitution; no private decisions; every decision is examinable |
| Approval Notification | The communication to relevant parties that a decision has been approved | Triggers capital reservation, execution queue entry, and monitoring setup |
| Rejection Notification | The communication to relevant parties that a recommendation has been rejected | Triggers recommendation revision or archival, and releases any temporary reservations |

---

### Group I — Behavioral Decision Concepts
*The vocabulary of how human and AI cognition influences decision quality — the behavioral dimension.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Behavioral Finance | The study of how psychological factors cause systematic deviations from rational decision-making | The intellectual foundation for all behavioral bias detection and correction in the system |
| Cognitive Bias | A systematic and predictable deviation from rational judgment in decision-making | The collective enemy; all known biases are treated as active threats requiring countermeasures |
| Emotional Decision | A decision driven primarily by emotional state rather than evidence and reasoning | Never permitted; all emotional impulses must be filtered through the governance process |
| Rational Decision | A decision that follows a coherent reasoning process from evidence through to conclusion | The constitutional standard for all approved decisions |
| Analysis Paralysis | The failure to make a decision due to excessive analysis, seeking perfect information | A decision failure mode; managed through the conviction threshold and decision window |
| Decision Paralysis | The inability to decide due to fear of being wrong or facing too many alternatives | Different from analysis paralysis — emotionally driven, not analytically driven |
| Overconfidence | The tendency to overestimate the probability that a thesis is correct | The most dangerous behavioral bias; creates oversized positions and insufficient stop losses |
| Underconfidence | The tendency to underestimate the quality of evidence, leading to excessively small or absent positions | Causes the system to miss high-conviction opportunities through excessive caution |
| Confirmation Bias | The tendency to seek and interpret evidence that confirms the existing position | Drives holding of losing positions beyond what the thesis justifies |
| Loss Aversion | The tendency to prefer avoiding losses over acquiring equivalent gains | Creates asymmetric decision-making: early profit-taking, reluctant loss-cutting |
| Sunk Cost Fallacy | Continuing to hold a position because of the capital already committed, not the current thesis | One of the most common and costly decision failures; the thesis is what matters, not P&L |
| Status Quo Bias | The preference for maintaining the current position over making a change | Creates holding positions beyond their valid thesis life out of inertia |
| Regret Aversion | Avoiding decisions that might lead to regret, even when expected value is positive | Can prevent approving high-quality decisions with uncertain outcomes |
| Herding | Following the crowd in investment decisions rather than independent evidence | Creates positions at peaks and exits at troughs; prevented by independent analysis requirement |
| Recency Bias | Overweighting recent events relative to the full historical pattern | Creates over-reaction to recent market moves; managed through evidence staleness decay |
| Narrative Bias | Preferring coherent stories over less coherent but statistically superior arguments | "This company tells a great story" overrides poor fundamentals; evidence must precede narrative |
| Anchoring | Excessive reliance on an initial reference price or value | "The stock was 500 last year so 350 feels cheap" — prevents objective valuation |
| Mental Accounting | The tendency to treat different pools of capital differently based on their origin or label | Prevents optimal capital allocation; all capital has the same value regardless of source |
| Availability Heuristic | Judging the probability of an event by how easily examples come to mind | Recent vivid losses create excessive caution; recent vivid gains create excessive boldness |
| Representativeness Heuristic | Judging a new situation by how closely it resembles a familiar prototype | Causes premature pattern application before sufficient evidence is gathered |
| Gambler's Fallacy | The belief that recent outcomes make opposite future outcomes more likely | "After 5 losing trades in a row, a win is due" — incorrect; each decision is independent |
| Hot Hand Fallacy | The belief that recent successes make future successes more likely | "The system is on a winning streak" — performance history does not guarantee continuation |
| Disposition Effect | The tendency to sell winning positions too early and hold losing positions too long | Directly contradicts evidence-based exit discipline; managed through pre-defined exit rules |
| Overtrading | Making more decisions than the evidence quality and opportunity set warrants | Driven by activity bias; increases transaction costs without commensurate return |
| Activity Bias | The urge to do something rather than nothing, even when inaction is the correct decision | Managed through the conviction threshold; low-conviction opportunities are rejected |
| FOMO | Fear of Missing Out — entering positions out of anxiety rather than evidence | Produces late entries at poor risk-reward ratios; managed through entry conviction requirement |
| Fear Greed Cycle | The alternation between excessive risk-taking in bull markets and excessive risk-aversion in bear markets | The systemic behavioral pattern in markets; the evidence-based system is designed to counter it |
| Patience | The discipline to wait for high-conviction opportunities rather than forcing trades | A constitutional virtue; the system rewards high-quality decisions, not decision volume |
| Discipline | The consistent application of decision architecture principles regardless of emotional state | The behavioral foundation of the entire governance system |
| Behavioral Override | The use of rule-based automatic systems to override behavioral impulses | Stop losses, kill switch, mandatory conviction threshold — all serve as behavioral overrides |
| Debiasing | The systematic application of techniques to reduce the influence of cognitive biases | The devil's advocate protocol, independent analysis, mandatory contradiction seeking |
| Reflective Decision | A decision made after pausing to examine one's reasoning process for bias before committing | Required for all decisions above materiality threshold; reduces cognitive bias impact |
| Independent Judgment | A decision assessment made without knowledge of other agents' prior conclusions | Constitutional requirement for multi-agent decisions; prevents herding within the committee |
| Process Adherence | The degree to which the decision-maker followed the defined decision process | Tracked separately from outcome; process quality is the learning metric |
| Intuitive Decision | A rapid decision based on implicit pattern recognition rather than explicit reasoning | Never approved without supporting evidence; intuition may initiate investigation, not decision |

---

### Group J — Temporal Decision Concepts
*The vocabulary of how time shapes decisions — when to decide, how long to hold, and when the thesis expires.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Decision Horizon | The time period over which a decision's thesis is expected to play out | Drives position sizing, monitoring intensity, and time stop placement |
| Investment Horizon | The planned total holding period for an investment decision | Ranges from intraday to multi-year; fundamentally affects entry criteria |
| Trading Horizon | A short decision horizon measured in days to weeks | Requires more precise entry timing and tighter stop losses |
| Holding Period | The actual duration from entry to exit of a completed position | Compared against expected holding period for learning |
| Time Stop | A pre-defined maximum holding period, after which the position is exited regardless of P&L | Applied when the thesis required a specific time-sensitive catalyst |
| Catalyst Timeline | The expected timing of the specific event that is expected to trigger the thesis | Drives the decision window and time stop placement |
| Pre-Catalyst Position | A position entered before the expected catalyst occurs | Carries catalyst timing risk; maximum loss if catalyst does not occur must be within limits |
| Post-Catalyst Evaluation | The review of whether to maintain or close a position after its primary catalyst has resolved | Required immediately after a catalyst event; thesis is re-evaluated from scratch |
| Decision Timing | The selection of when within the decision window to execute | Affects the entry price and realized risk-reward ratio |
| Market Timing | The attempt to identify optimal entry and exit points based on market cycle analysis | A component of decision quality for shorter-horizon strategies |
| Cycle Awareness | The understanding of where the current market, sector, or economic cycle stands | Regime context; shapes the appropriate decision type and horizon |
| Early Cycle Decision | A decision made at the beginning of an economic expansion cycle | Typically favors high-beta, growth, and cyclical sectors |
| Late Cycle Decision | A decision made toward the end of an economic expansion cycle | Typically favors defensive, quality, and capital-preservation themes |
| Recency | The time elapsed since the evidence supporting a decision was gathered | Recent evidence carries more weight; old evidence decays toward the prior |
| Evidence Staleness | The degree to which evidence supporting a decision has aged and may no longer reflect current conditions | Triggers re-evaluation when staleness exceeds the threshold for the evidence type |
| Decision Age | The time elapsed since a decision was approved | Older open decisions require more frequent conviction reviews |
| Thesis Life | The maximum period over which a thesis can remain valid without fresh supporting evidence | Beyond thesis life, the position is closed unless new evidence restores conviction |
| Rolling Review | A scheduled periodic reassessment of all open decisions | Daily, weekly, and monthly cadence; ensures no position remains open beyond its thesis life |
| Temporal Conviction | Confidence that not only the thesis direction is correct but the timing is appropriate | A higher bar than directional conviction; required for event-driven and catalyst-dependent decisions |
| Time Decay | The natural reduction in the value of an options position over time | Relevant for options decisions; must be incorporated into the expected return calculation |
| Lead Time | The time between evidence arrival and the expected impact on price | The window of opportunity for a decision; determines how much time is available before the edge is gone |
| Information Half-Life | The time after which a piece of information is likely to be widely known and therefore priced in | Determines how urgently an evidence-based decision must be made |
| Decision Frequency | The number of decisions made over a period | Too high: transaction costs accumulate; too low: opportunity cost accumulates |
| Seasonal Pattern | A recurring decision opportunity that correlates with the time of year | Budget season, earnings season, monsoon season — timing-based entry conditions |
| Decision Calendar | The schedule of known future events that are relevant to open and potential decisions | Manages timing risk; ensures no decisions are made in ignorance of near-term events |
| Intraday Decision | A decision with an entry and exit within the same trading day | Requires the highest conviction per unit time; carries execution precision requirements |
| Overnight Decision | A decision held open overnight, accepting gap risk | Requires adequate position sizing to absorb potential gap risk |
| Multi-Day Decision | A decision with a planned holding period of 2-20 trading days | Standard trading horizon; typical for tactical and event-driven strategies |
| Multi-Week Decision | A decision with a planned holding period of 3-12 weeks | Medium horizon; typical for earnings and macro catalyst strategies |
| Multi-Month Decision | A decision with a planned holding period of 3-12 months | Strategic investment horizon; requires structural thesis validation |
| Multi-Year Decision | A decision with a planned holding period exceeding one year | Long-term investment; requires exceptional quality of fundamental thesis |

---

### Group K — Multi-Agent Decision Concepts
*The vocabulary of how multiple intelligence agents collaborate and conflict in the decision process.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Multi-Agent System | A system of multiple autonomous or semi-autonomous agents each contributing analysis | The decision architecture relies on multiple specialist agents for quality assurance |
| Agent Specialization | The focus of each agent on a specific domain of expertise | Technical, Fundamental, Macro, Risk, Sentiment — each adds a unique analytical perspective |
| Agent Independence | The requirement that each agent performs analysis without influence from other agents | Constitutional requirement; prevents herding; all analyses must be completed before sharing |
| Agent Vote | Each agent's directional recommendation: Bull, Bear, or Neutral with an associated confidence | The input to the multi-agent aggregation process |
| Weighted Aggregation | The combination of agent votes using weights based on historical accuracy and domain relevance | Produces the collective conviction score from individual agent inputs |
| Agent Weight | The historical-accuracy-calibrated influence of each agent's vote on the final decision | Updated continuously; more accurate agents receive higher weights in relevant domains |
| Deadlock | A situation where agent votes are exactly tied with no clear direction | Triggers escalation to the Chief Intelligence Agent for resolution |
| Debate Protocol | The structured rules governing how agents present, challenge, and defend their analyses | Ensures quality argumentation; prevents shouting matches and empty consensus |
| Devil's Advocate | The agent assigned to argue the strongest opposing case regardless of personal view | Mandatory for all high-conviction decisions; prevents groupthink |
| Groupthink | The convergence of agent opinions not through independent reasoning but social pressure | Constitutional failure mode; the devil's advocate exists specifically to prevent this |
| Dissent | A formal, documented disagreement with the majority decision direction | Required to be recorded; monitored for subsequent vindication |
| Agent Calibration | The ongoing measurement and correction of each agent's accuracy rate | Ensures weights accurately reflect current accuracy; updated quarterly |
| Cross-Agent Validation | The verification that two or more independent agents agree on a key piece of evidence | High-confidence evidence requires cross-agent corroboration |
| Agent Conflict | A situation where two or more agents have contradictory analyses of the same evidence | Must be explicitly resolved; cannot be averaged away without explanation |
| Conflict Resolution Protocol | The defined process for resolving agent conflicts | Step 1: Evidence review; Step 2: Independent re-analysis; Step 3: Chief agent arbitration |
| Chief Intelligence Agent | The highest-authority AI agent responsible for final conviction score and deadlock resolution | Receives all agent outputs; applies final weights; authorizes debate completion |
| Agent Performance Tracking | The measurement of each agent's contribution to decision quality and portfolio returns | Historical record; drives weight adjustments and specialization evolution |
| Collaborative Reasoning | The process by which agents share analytical conclusions while preserving independence | Share conclusions not process; each agent's reasoning is independently developed |
| Minority Report | The formal documentation of a minority agent view that did not prevail in the debate | Part of the permanent decision record; monitored for subsequent vindication |
| Agent Trust | The degree to which the system relies on a specific agent based on its track record | Dynamic; increases with accuracy, decreases with errors; drives weight allocation |
| Specialization Boundary | The limit of each agent's designated analytical domain | Prevents agents from commenting outside their domain; reduces noise in the debate |
| Agent Consensus | Agreement among all or a supermajority of agents on direction and conviction | Rare; treated with increased scrutiny to check for groupthink before accepting |
| Perspective Diversity | The degree to which the agent set covers different analytical frameworks | A prerequisite for high-quality multi-agent debate |
| Sequential Analysis | Each agent completing full analysis before the next begins | Used when each agent's output is an input to the next; creates sequential dependency |
| Parallel Analysis | All agents completing analysis simultaneously before any results are shared | Preferred approach; maximizes independence and minimizes anchor contamination |
| Agent Update Cycle | The frequency at which each agent refreshes its analysis based on new information | Different agents update at different frequencies based on their evidence type |
| Escalation to Human | The referral of a decision to a human agent when the AI system is uncertain or conflicted | Triggered by: split votes, novel conditions, extreme conviction, or agent deadlock |
| Human-in-the-Loop | The architectural provision for human judgment to be incorporated into AI decisions | Not the default; applied for material decisions and conditions outside the system mandate |
| Collective Intelligence | The emergent decision quality produced by a well-governed multi-agent system that exceeds any individual agent | The primary benefit of the multi-agent architecture |

---

### Group L — Market-Specific Decision Concepts
*The vocabulary of how market conditions shape the decision landscape.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Market Regime | The current state of the market as characterized by trend, volatility, breadth, and liquidity | The highest-priority context for every decision; invalid strategies are deactivated |
| Regime Classification | The process of determining the current market regime from observable market metrics | Updated at minimum weekly; triggers strategy and decision posture changes |
| Bull Market Decision | A decision appropriate to a rising, low-volatility, broad-based market | Momentum and growth strategies; higher conviction thresholds possible |
| Bear Market Decision | A decision appropriate to a falling, high-volatility market | Defensive positioning; capital preservation prioritized; strict position size controls |
| Sideways Market Decision | A decision appropriate to a ranging, low-trend, high-noise market | Mean reversion strategies; momentum strategies deactivated |
| High Volatility Decision | A decision made when VIX or market volatility is elevated | Smaller position sizes; wider stops; faster review cycles |
| Low Volatility Decision | A decision made when market volatility is suppressed | Normal position sizes; standard stops; risk of sudden volatility expansion |
| Liquidity Window | A specific time period of higher-than-usual market liquidity | Preferred execution window for large decisions |
| Liquidity Vacuum | A period of abnormally low market liquidity | Avoided for large decisions; execution risk dramatically elevated |
| Volume Confirmation | The requirement that price moves are confirmed by proportionate trading volume | Used as evidence quality requirement for momentum-based decisions |
| Market Breadth | The fraction of stocks advancing versus declining | Wider breadth = stronger market health; affects conviction for index-based decisions |
| Relative Strength | The performance of a specific entity relative to the broader market | Used to identify outperformers for entry and underperformers for exit |
| Sector Rotation | The cyclical movement of capital across sectors based on economic cycle | Drives sector allocation decisions at the portfolio level |
| Index Effect | The price movement resulting from a stock being added to or removed from an index | An event-driven decision opportunity with well-understood mechanics |
| Earnings Season | The period when most companies report quarterly financial results | A high-opportunity, high-risk decision period; specific decision protocols apply |
| Pre-Announcement Positioning | An entry or exit decision made before a specific announcement event | Carries event risk; requires clear thesis and conservative sizing |
| Gap Risk | The risk of significant price discontinuity between close and open | Managed through position size limits and avoiding high-risk overnight holds |
| Intraday Volatility | The magnitude of intraday price swings | Affects entry and exit precision; drives order type selection for decisions |
| Opening Range | The price range established in the first 30 minutes of trading | Used as a reference range for intraday decision timing |
| Market-on-Open | A decision executed at the opening auction price | Used for systematic decisions where the specific open price is the entry signal |
| Market-on-Close | A decision executed at the closing auction price | Used for end-of-day portfolio rebalancing decisions |
| Block Trade | A very large single decision executed as a single transaction | Requires special handling; pre-arranged with market counterparties |
| Basket Trade | Multiple simultaneous decisions executed as a coordinated group | Used for portfolio rebalancing and strategy rotation decisions |
| Price Sensitivity | The degree to which a decision's quality depends on the specific execution price | High sensitivity decisions require limit orders; low sensitivity allow market orders |
| Market Impact Limit | The maximum acceptable price impact from executing a large decision | Determines position size limits relative to average daily trading volume |
| VWAP | Volume-Weighted Average Price — a benchmark for evaluating execution quality | Decisions executed near VWAP have minimized market impact |
| TWAP | Time-Weighted Average Price — achieved by splitting a large decision across time | Used to minimize impact for large decisions that cannot be executed at once |
| Smart Order Routing | The automatic selection of the optimal execution venue for a decision | Minimizes execution costs and slippage; part of the execution layer |
| Institutional Flow | The buying and selling patterns of large institutional investors | Evidence input for decision-making; FII inflows support bull thesis, outflows weaken it |
| Retail Sentiment | The aggregate direction of retail investor activity | Contrarian signal: extreme retail enthusiasm is often a sell signal |
| Market Maker Decision | A decision made in awareness of market maker positioning and incentives | Relevant for options decisions; market makers often have predictable hedging behavior |
| Circuit Breaker | An automatic market suspension triggered by extreme volatility | Affects decision execution; positions cannot be opened or closed during suspension |
| Derivatives Decision | A decision using options, futures, or other derivatives | Requires specific expertise; delta, gamma, and other Greeks must be within approved limits |
| Options Decision | A decision using options contracts to create asymmetric payoff profiles | Used for hedging, income generation, and defined-risk speculation |

---

### Group M — Decision Failure Mode Concepts
*The vocabulary of how decisions go wrong — the taxonomy of decision errors.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Decision Failure | Any outcome where the decision process or result is materially below the quality standard | Tracked and learned from; the primary driver of system improvement |
| Process Failure | A failure in how the decision was made, regardless of the outcome | Even a profitable decision can be a process failure; learning must identify process errors |
| Outcome Failure | A failure in the result — a decision that produced a loss or underperformance | Not all outcome failures are process failures; bad luck exists |
| Systematic Failure | A failure pattern that affects multiple decisions repeatedly | More serious than individual failures; indicates a structural problem in the decision system |
| Random Failure | A single-decision failure not attributable to a systematic error | Expected in any probabilistic system; not concerning unless frequency exceeds base rate |
| Overtrading | Making decisions at a higher frequency than evidence quality supports | Increases transaction costs without commensurate return improvement |
| Undertrading | Failing to make decisions when high-conviction opportunities exist | Opportunity cost; capital not deployed; system intelligence is not being converted to value |
| Late Entry | An entry made after the optimal risk-reward moment has passed | Price has already moved; remaining upside reduced; risk-reward ratio deteriorated |
| Early Exit | An exit from a position before the profit target, without thesis invalidation | Reduces average winner size; degrades expected value of the decision system |
| Late Exit | Holding a position beyond the time when the thesis supports it | Produces larger losses than necessary; driven by hope or sunk cost fallacy |
| Holding Losers | Maintaining losing positions beyond the stop loss out of hope for recovery | The most common and costly decision failure; prevented by unconditional stop loss rules |
| Cutting Winners | Exiting profitable positions before the thesis target is reached | Reduces profit factor; driven by fear of losing gains; managed by trailing stop discipline |
| Position Oversizing | Committing more capital than the evidence and risk budget justify | Single largest cause of catastrophic loss; prevented by conviction-calibrated sizing |
| Position Undersizing | Committing less capital than the evidence justifies | Opportunity cost; the system is not fully utilizing its own conviction |
| Concentration Failure | Allowing too many correlated decisions to accumulate simultaneously | Exposes the portfolio to cluster risk; a systemic failure that amplifies losses |
| Capital Exhaustion | Deploying all available capital, eliminating the ability to respond to new opportunities or emergencies | Constitutional prohibition; the cash buffer exists to prevent this |
| Revenge Decision | A new decision made to recover losses from a recent failed decision | Emotionally driven; evidence-free; among the most dangerous decision failure modes |
| Compulsive Decision | A decision made to relieve the anxiety of not acting, not because evidence supports it | Activity bias in action; produces low-conviction decisions with poor expected value |
| Panic Decision | An immediate emotional exit or entry triggered by sudden market movement | Bypasses the governance process; often made at exactly the wrong time |
| Decision Drift | The gradual deviation of the decision process from the defined architecture | Often undetected; manifests as increasing exceptions, shortcuts, and informal approvals |
| Mandate Breach | A decision that violates the portfolio mandate or investment policy | A governance failure of the highest severity; triggers immediate review |
| Governance Bypass | Making a decision without completing the required governance process | Never permitted; creates a permanent violation record |
| Committee Deadlock | The failure of a committee to reach a decision within the required time | Triggers escalation to the resolving authority; cannot be left unresolved |
| AI Hallucination in Decisions | The generation of a decision recommendation based on fabricated or uncited evidence | The most dangerous single AI failure mode; prevented by mandatory evidence citation |
| Wrong Objective | Making an optimal decision for the wrong goal | "Maximize number of trades" versus "maximize risk-adjusted return" — wrong objective produces excellent decision quality for the wrong target |
| False Conviction | High conviction score based on correlated rather than independent evidence streams | Independent evidence is not the same as additional evidence from the same source |
| Stale Decision | Executing a decision whose approval has expired and market conditions have changed | Prevented by decision expiry; the decision must be re-approved after expiry |
| Recency Chasing | Making decisions based on recent performance rather than current evidence | "This strategy worked for 3 months" is not a decision rationale without supporting evidence |
| Benchmark Chasing | Making decisions to match benchmark composition rather than express genuine conviction | A portfolio construction failure; active share collapses; alpha opportunity disappears |
| Size Error | Making the correct directional decision but with a materially wrong position size | Correct thesis; wrong sizing; outcome is suboptimal even when the direction is right |

---

### Group N — Meta-Decision and Learning Concepts
*The vocabulary of how the decision system improves itself through reflection and learning.*

| Concept | Definition | Role in Investment Decision-Making |
|---|---|---|
| Meta-Decision | A decision about how to decide — changing the decision process or architecture itself | The highest-level decision type; governs how all lower-level decisions are made |
| Process Improvement | A change to the decision architecture that improves the quality of future decisions | Driven by learning records, calibration data, and failure mode analysis |
| Decision Quality Score | An aggregate metric evaluating how well a decision followed the defined process | Measured independently of outcome; a high-quality process can produce a bad outcome |
| Calibration | The alignment between stated conviction and actual decision accuracy | A system that says 7.0 conviction should be right more often than one that says 6.5 |
| Recalibration | The systematic adjustment of conviction score thresholds based on measured accuracy | Quarterly; ensures conviction scores continue to predict outcomes accurately |
| Feedback Loop | The connection between decision outcomes and future decision quality | The learning system closes this loop; every outcome informs future decisions |
| Learning Record | The structured document created for every closed decision, capturing all relevant data | The primary input to the learning system; the source of all performance improvement |
| Post-Mortem | A deep analysis of a failed decision to identify root causes and lessons | Required for every decision with a loss above threshold; optional for all others |
| Winner Analysis | The analysis of a successful decision to identify what made it work | As important as post-mortems; prevents the system from abandoning good practices |
| Attribution | The assignment of credit or blame for outcomes to specific decisions and evidence types | Drives evidence weight updates, strategy weight updates, and agent weight updates |
| Knowledge Update | A change to a knowledge item in the knowledge base driven by decision outcomes | Decisions are the empirical tests of knowledge items; outcomes update the knowledge base |
| Strategy Evolution | The modification of a strategy based on accumulated decision outcomes | A meta-decision; requires evidence from a sufficient number of decisions |
| Decision History | The complete record of all past decisions, their contexts, and their outcomes | The primary training data for strategy learning and system improvement |
| Outcome Distribution | The statistical distribution of returns across all decisions of a given type | The empirical evidence for or against a specific decision type's expected value |
| Walk-Forward Validation | Testing the decision system on data that was not available when the strategy was developed | The gold standard for strategy quality; required before live deployment |
| Regime Performance | The measurement of decision quality separately in each market regime | Essential: a strategy may be excellent in trending markets and terrible in sideways markets |
| Strategy Retirement | The removal of a decision strategy from active use due to persistent underperformance | Driven by learning evidence; a meta-decision with significant portfolio impact |
| Strategy Promotion | The elevation of a new strategy from paper trading to live capital allocation | Requires passage of promotion gates: win rate, Sharpe ratio, maximum drawdown criteria |
| Conviction Recalibration | The periodic adjustment of how conviction scores are translated to position sizes | Ensures position sizing continues to reflect actual evidence quality |
| Edge Decay | The gradual reduction in a strategy edge as market conditions evolve or the strategy becomes known | Monitored continuously; triggers strategy recalibration or retirement |
| Adaptive Threshold | A conviction or risk threshold that adjusts based on current market conditions | Higher thresholds in uncertain regimes; lower in well-understood regimes |
| Self-Assessment | The system evaluating the quality of its own decision-making process | A form of meta-reasoning applied specifically to decision architecture |
| Improvement Hypothesis | A proposed change to the decision architecture with a predicted impact | Tested in paper trading before implementation; requires evidence of improvement |
| System-Level Learning | Learning that improves the decision architecture rather than individual strategy weights | The highest-value learning output; changes how all future decisions are made |
| Institutional Memory | The accumulated knowledge from all past decisions, preserved and accessible | Prevents repeating the same mistakes; the repository of the system wisdom |
| Retrospective Analysis | A structured review of a historical period to identify patterns across multiple decisions | Monthly and quarterly; identifies systemic patterns not visible in individual decisions |


---

## PART III — DECISION PRIMITIVES

*The foundational units of investment decision-making. Every decision the system makes is built from these primitives. Each is defined with 28 attributes to provide complete architectural specification.*

---

### DPRIM-001 — INVESTMENT DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-001 |
| **Name** | Investment Decision |
| **Definition** | A binding, approved commitment to open, hold, modify, or close a financial position, made after completing the full reasoning and governance pipeline, with full acknowledgment of the capital, risk, and opportunity cost it consumes |
| **Why It Exists** | Without a formal decision primitive, the system would have no defined moment of commitment — capital would drift into positions without deliberate authorization, governance would be meaningless, and learning would have no unit of analysis |
| **Classification** | Commitment | Action | Governance-Required | Capital-Consuming |
| **Inputs Required** | Approved recommendation; governance clearance; conviction score >= 6.5; available capital; available risk budget; regime validation |
| **Outputs Produced** | Decision record; capital reservation; risk budget allocation; execution request; monitoring activation |
| **Producers** | Reasoning pipeline (via recommendation); governance system (via approval); committee deliberation |
| **Consumers** | Execution engine (for implementation); portfolio system (for state update); monitoring system (for tracking); learning system (for outcome recording) |
| **Failure Modes** | Governance bypass; conviction below threshold; evidence fabrication; wrong regime; capital overcommitment; duplicate decision |
| **Strengths** | Provides clear accountability; enables learning; creates audit trail; defines exact commitment |
| **Weaknesses** | Creates irreversible commitment; consumes capital that cannot be simultaneously used elsewhere; always made under uncertainty |
| **Dependencies** | Recommendation system; governance framework; capital management system; risk budget system |
| **Relationships to Other Primitives** | Follows → DPRIM-002 (Recommendation); Triggers → DPRIM-003 (Entry) or DPRIM-004 (Exit); Governed by → DPRIM-008 (Risk Gate); Recorded by → DPRIM-020 (Decision Record) |
| **Lifecycle** | Recommendation created → Governance review → All gates cleared → Approval granted → Capital reserved → Execution requested → Position opened → Monitoring active → Outcome → Learning |
| **Conviction Requirement** | >= 6.5/10 from the conviction calculation; derived from at least 3 independent evidence types |
| **Capital Impact** | Immediate reservation of required capital; reduces available capital by the full position size |
| **Risk Impact** | Immediate allocation of risk budget; increases portfolio risk metrics (VaR, beta, sector exposure) |
| **Portfolio Impact** | Changes portfolio composition; affects sector allocation, correlation profile, and overall risk |
| **Validation Methods** | All 6 governance gates passed; evidence citations present; conviction score traceable; mandate compliance confirmed |
| **Quality Dimensions** | Evidence quality; reasoning quality; governance completeness; appropriateness to regime; sizing accuracy |
| **Complexity** | High — requires full pipeline completion across all layers |
| **Governance** | All 6 governance gates required; authority matrix determines approval tier |
| **Explainability** | Fully explainable — every input is traceable; every reasoning step is documented |
| **Auditability** | Permanently recorded; every field is retained in the decision record; immutable after commitment |
| **Temporal Properties** | Has a creation timestamp, approval timestamp, execution timestamp, and outcome timestamp |
| **Expiry** | Decision recommendations expire if not executed within the decision window |
| **Examples** | "Buy 200 shares HDFC Bank at 1820, Stop 1755, Target 1940, Conviction 7.2, 22-day horizon" |
| **Anti-Examples** | "I think HDFC looks good" (no conviction score, no governance, no commitment); "Automatic script opened a position" (no deliberation) |

---

### DPRIM-002 — RECOMMENDATION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-002 |
| **Name** | Recommendation |
| **Definition** | A structured proposal for a specific investment action, produced by the reasoning pipeline after conviction threshold is reached, awaiting governance approval before it becomes a decision |
| **Why It Exists** | The recommendation separates analysis from commitment — it creates a proposal that can be reviewed, challenged, modified, or rejected before capital is committed. This separation is architecturally essential for quality control. |
| **Classification** | Proposal | Pre-Decision | Reviewable | Reversible |
| **Inputs Required** | Hypothesis with conviction >= 6.5; evidence set with citations; risk-reward parameters; position size proposal; governance readiness |
| **Outputs Produced** | Formal recommendation document with entity, direction, entry price, stop, target, horizon, conviction, rationale |
| **Producers** | Multi-agent reasoning pipeline; conviction calculation system; portfolio analysis layer |
| **Consumers** | Governance system; risk committee; capital allocation system; decision queue |
| **Failure Modes** | Insufficient conviction; missing evidence citations; incomplete parameters; duplicate recommendation; expired by the time reviewed |
| **Strengths** | Creates a reviewable record; separates analysis from commitment; enables independent governance |
| **Weaknesses** | Adds time between conviction and commitment; may expire if governance is slow |
| **Dependencies** | Evidence system; conviction calculation; hypothesis management; portfolio state |
| **Relationships to Other Primitives** | Precedes → DPRIM-001 (Decision); Produced by → reasoning system; Reviewed by → DPRIM-019 (Committee Decision) |
| **Lifecycle** | Conviction threshold reached → Parameters calculated → Recommendation document created → Entered in governance queue → Reviewed → Approved (→ DPRIM-001) or Rejected (→ archived with reason) |
| **Conviction Requirement** | >= 6.5/10 to create a recommendation; higher conviction produces larger recommended position size |
| **Capital Impact** | No capital consumed at recommendation stage — only reserved after governance approval |
| **Risk Impact** | No risk allocated at recommendation stage |
| **Portfolio Impact** | May trigger preliminary portfolio impact assessment |
| **Validation Methods** | All recommendation parameters present; conviction traceable to evidence; alternative hypothesis documented |
| **Quality Dimensions** | Evidence quality; conviction score quality; parameter reasonableness; risk-reward ratio |
| **Governance** | The recommendation is the governance input — it must be complete enough for governance to evaluate it |
| **Explainability** | Fully explainable at recommendation stage — this is the explainability checkpoint |
| **Auditability** | Permanently recorded regardless of whether it becomes a decision; rejections are as important to track as approvals |
| **Temporal Properties** | Has a creation timestamp; has a validity window (typically 2-8 hours for tactical, 1-5 days for strategic) |
| **Expiry** | A recommendation expires automatically if not acted on within its validity window |
| **Examples** | "Recommendation: Buy TATAMOTORS, 150 shares, Entry <= 920, Stop 875, Target 1020, Conviction 6.8/10, Thesis: Q4 volume recovery + EV thesis re-rating, Horizon 35 days, RR 2.3:1" |
| **Anti-Examples** | "I recommend TATAMOTORS" (no parameters); a post-approval document (that is a decision, not a recommendation) |

---

### DPRIM-003 — POSITION ENTRY DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-003 |
| **Name** | Position Entry Decision |
| **Definition** | The specific approved decision to open a new position in an entity — the first capital commitment of a new investment decision, initiating all monitoring, stop loss, and thesis tracking |
| **Why It Exists** | The entry decision is the operational implementation of an approved recommendation — it converts the abstract approval into a specific executable action with all parameters defined |
| **Classification** | Capital-Deploying | Commitment-Initiating | Monitoring-Starting | Specific |
| **Inputs Required** | Approved DPRIM-001; confirmed available capital; confirmed risk budget; regime validation; entry trigger condition met |
| **Outputs Produced** | Entry order parameters; position record creation; monitoring activation; stop loss placement; capital reservation confirmation |
| **Producers** | Governance approval system after DPRIM-001 is approved |
| **Consumers** | Execution engine (order); monitoring system (activated); portfolio system (position opened); risk system (exposure updated) |
| **Failure Modes** | Entry trigger not met but executed anyway; price outside entry zone; capital not available; duplicate entry; entry after decision expiry |
| **Strengths** | Precise; fully parameterized before execution; connected to stop loss and target at birth |
| **Weaknesses** | Timing risk — the entry moment matters; all subsequent management references this entry |
| **Dependencies** | DPRIM-001 (parent decision); capital system; execution system; monitoring system |
| **Relationships to Other Primitives** | Child of → DPRIM-001; Paired with → DPRIM-004 (Exit); Governed by → DPRIM-006 (Position Sizing); Stopped by → DPRIM-005 (Stop Loss) |
| **Lifecycle** | Approval received → Entry trigger checked → Capital confirmed → Entry order created → Order routed → Fill confirmed → Position record created → Monitoring started → Stop placed |
| **Conviction Requirement** | Inherits from parent DPRIM-001; entry conviction must equal or exceed the approval conviction |
| **Capital Impact** | Full position capital immediately consumed on fill; moves from reserved to deployed |
| **Risk Impact** | Stop loss distance defines capital at risk; portfolio beta and VaR update immediately |
| **Portfolio Impact** | Sector exposure, correlation profile, and deployment rate all update |
| **Validation Methods** | Entry price within approved zone; quantity within approved size; entry trigger confirmed |
| **Timing** | Entry execution within the approved decision window; expired windows require re-approval |
| **Examples** | "Entry executed: 200 HDFC Bank at 1820.50, Stop placed at 1755, Target 1940, Position ID 2026-07-01-HDFC-001" |
| **Anti-Examples** | Entering before stop loss is defined; entering with a different quantity than approved; entering after the decision window has closed |

---

### DPRIM-004 — POSITION EXIT DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-004 |
| **Name** | Position Exit Decision |
| **Definition** | The specific decision to close all or part of an existing position, realizing the P&L, releasing capital and risk budget, and triggering the learning cycle |
| **Why It Exists** | Without a formal exit primitive, positions would linger indefinitely and the critical discipline of planned exits would be absent. The exit is not the end of a decision — it is the beginning of the learning cycle. |
| **Classification** | Capital-Releasing | Learning-Triggering | Commitment-Terminating |
| **Inputs Required** | Open position; exit trigger (stop loss hit, target reached, thesis invalidated, time stop, conviction exit, regime change); exit parameters |
| **Outputs Produced** | Exit order parameters; P&L realization; capital release; risk budget release; learning record creation |
| **Producers** | Monitoring system (rule-based exit); governance system (discretionary exit); kill switch (emergency exit) |
| **Consumers** | Execution engine; portfolio system; learning system; capital management system |
| **Failure Modes** | Reluctant exit (not exiting when required); panic exit (exiting without trigger); partial exit confusion; exit without learning record |
| **Strengths** | Provides finality; releases capital; triggers learning; enforces discipline |
| **Weaknesses** | The exact exit moment affects realized returns; timing decisions are difficult |
| **Dependencies** | Open position (parent DPRIM-003); monitoring system; execution system; learning system |
| **Relationships to Other Primitives** | Closes → DPRIM-003 (Entry); Triggers → learning record; References → DPRIM-005 (Stop Loss) |
| **Lifecycle** | Exit trigger occurs → Exit decision created → Governance (if discretionary) or automatic → Exit order → Fill → P&L calculated → Capital released → Learning record started → Post-mortem |
| **Exit Types** | Stop Loss (automatic); Target Reached (automatic at pre-defined level); Thesis Invalidation (governance required); Time Stop (automatic); Conviction Exit (when score falls below 4.0); Regime Exit; Emergency Exit |
| **Capital Impact** | Full position capital returned to available state upon fill |
| **Risk Impact** | All portfolio risk metrics update to reflect position closure |
| **Portfolio Impact** | Sector exposure, correlation profile, and deployment rate all update downward |
| **P&L Recording** | Entry cost basis versus exit price, minus all transaction costs, allocated to the decision record |
| **Learning Trigger** | Every exit creates a mandatory learning record; no exceptions |
| **Examples** | "Exit: 200 HDFC Bank at 1937.50, Stop hit: No, Target: Yes, P&L: +6.5%, 21-day hold, Conviction at exit: 7.8/10, Reason: Target reached" |
| **Anti-Examples** | Exiting without recording the reason; exiting a partial position and calling it a full exit; delaying exit after stop loss level is breached |

---

### DPRIM-005 — STOP LOSS DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-005 |
| **Name** | Stop Loss Decision |
| **Definition** | The pre-committed, unconditional price level below which an open long position must be closed immediately — the primary mechanical risk control and capital preservation mechanism |
| **Why It Exists** | Without a stop loss, position management becomes subjective and emotionally driven. The stop loss transforms the exit decision from a discretionary act into a rule-bound commitment, removing behavioral bias at the most critical moment. |
| **Classification** | Risk Control | Pre-Committed | Unconditional | Rule-Based |
| **Inputs Required** | Entry price; maximum acceptable loss percentage; volatility of the entity; portfolio risk budget per position |
| **Outputs Produced** | Specific stop price; capital at risk calculation; stop order placement instruction |
| **Producers** | Position sizing framework at entry; must be defined before entry is executed |
| **Consumers** | Monitoring system (watches for stop breach); execution system (sends exit order when hit); risk system (caps downside) |
| **Failure Modes** | Stop not defined before entry; stop too tight (stops out on noise); stop too loose (allows excessive loss); mental stop (not pre-placed); moving stop away from entry after placement |
| **Strengths** | Removes behavioral bias at the worst moment; caps maximum loss; creates clear risk calculation |
| **Weaknesses** | Subject to gap risk (price may open beyond stop); subject to stop hunting in illiquid markets |
| **Dependencies** | Entry decision (DPRIM-003); monitoring system; execution system |
| **Stop Types** | Hard Stop (absolute price, unconditional); Trailing Stop (moves with price); Breakeven Stop (moved to entry price after profit threshold); Time Stop (exits on date regardless of price) |
| **Adjustment Rules** | May only be moved in the direction of the position (protecting profits); NEVER moved away from entry to allow a larger loss |
| **Lifecycle** | Position entry → Stop price calculated → Stop order placed immediately → Monitored continuously → Either: stop hit (exit triggered) or stop migrated (trailing) or position closes at target |
| **Conviction Requirement** | None — the stop loss is unconditional; conviction level has no bearing on whether the stop is honored |
| **Capital Impact** | Defines the maximum capital at risk; (Entry − Stop) / Entry = maximum loss percentage |
| **Portfolio Impact** | Ensures single-position losses cannot exceed portfolio risk budget allocation |
| **Inviolability** | The stop loss is constitutionally inviolable — no reasoning process may override it once triggered |
| **Temporal Properties** | Valid from entry to position closure; may be adjusted per adjustment rules; cannot expire while position is open |
| **Gap Risk Protocol** | When a gap creates an open price beyond the stop, the position is exited at the opening price — the intent of the stop is honored even if the exact price is not |
| **Examples** | "HDFC Bank entry at 1820, Hard Stop at 1755 (3.6% below entry, capital at risk 2.6% of position)" |
| **Anti-Examples** | "I will exit if it falls to 1755 but I will watch first" (mental stop, not a committed stop); "Stop was at 1755 but I moved it to 1700 because I still believe in the thesis" (stop dilation, prohibited) |

---

### DPRIM-006 — POSITION SIZING DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-006 |
| **Name** | Position Sizing Decision |
| **Definition** | The determination of the exact quantity of shares or contracts to purchase or sell in a specific entry or scaling decision, calibrated to conviction level, risk budget, and portfolio constraints |
| **Why It Exists** | Without a principled position sizing framework, the system would either under-deploy capital (wasting conviction) or over-deploy capital (creating catastrophic single-position risk). Position sizing is the mechanism by which conviction is translated into capital allocation. |
| **Classification** | Resource Allocation | Conviction-Calibrated | Risk-Governed | Portfolio-Constrained |
| **Inputs Required** | Conviction score; entry price; stop loss price; available capital; available risk budget; sector exposure; portfolio correlation; maximum position size from mandate |
| **Outputs Produced** | Exact quantity; capital deployed; capital at risk; percentage of portfolio |
| **Sizing Principles** | Higher conviction = larger position; closer stop = smaller position; higher VIX = smaller position; higher sector concentration = smaller position; tighter risk budget = smaller position |
| **Sizing Constraints** | Maximum position size (mandate); maximum capital at risk per position; maximum sector concentration; maximum correlation with existing positions |
| **Producers** | Position sizing framework; risk management layer |
| **Consumers** | Entry decision (DPRIM-003); capital management system; risk budget system; execution system |
| **Failure Modes** | Oversizing (exceeds risk budget); undersizing (underutilizes conviction); wrong calculation basis; ignoring correlation; ignoring current sector exposure |
| **Kelly Application** | Half-Kelly is the ceiling for individual position sizing; actual allocation typically one-quarter Kelly for robustness |
| **Conviction Scaling** | Conviction 6.5: 50% of maximum position; Conviction 7.0: 65%; Conviction 7.5: 80%; Conviction 8.0+: 100% |
| **Volatility Adjustment** | High VIX environment: position sizes reduced by up to 50% from standard |
| **Lifecycle** | Conviction score confirmed → Stop loss price confirmed → Capital at risk per share calculated → Risk budget allocation calculated → Mandate limits checked → Final quantity determined |
| **Capital Impact** | Directly determines how much capital is deployed; drives the capital reservation amount |
| **Risk Impact** | Position size times stop distance defines total capital at risk; must not exceed per-position risk limit |
| **Portfolio Impact** | The sizing decision determines the degree to which this position changes the portfolio's aggregate characteristics |
| **Governance** | Part of the recommendation document; reviewed and approved as part of the governance process |
| **Examples** | "Conviction 7.2, Entry 1820, Stop 1755, Distance 3.6%, Risk per position 1.5% of portfolio, Portfolio value 10,000,000, Max capital at risk 150,000, Shares = 150,000 / 65 = 2,307 rounded to 2,300" |
| **Anti-Examples** | "I will buy as many shares as I can afford" (no risk calibration); "I will buy 100 shares because that seems right" (no quantitative framework) |

---

### DPRIM-007 — CAPITAL ALLOCATION DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-007 |
| **Name** | Capital Allocation Decision |
| **Definition** | The portfolio-level decision determining how total available capital is distributed across strategies, sectors, time horizons, and individual opportunities — the highest-level resource commitment decision |
| **Why It Exists** | Individual position sizing decisions operate within a capital allocation framework that must itself be decided. Without an explicit capital allocation decision, the portfolio drifts into unintended concentrations and leaves capital under-deployed or over-concentrated. |
| **Classification** | Portfolio-Level | Strategic | Resource-Governing | Constraint-Setting |
| **Inputs Required** | Total portfolio capital; current deployment rate; sector exposures; strategy performance; regime assessment; risk tolerance |
| **Outputs Produced** | Capital budget per strategy; maximum capital per sector; available capital for new decisions; drawdown budget allocation |
| **Producers** | Portfolio governance layer; investment committee; periodic portfolio review |
| **Consumers** | All DPRIM-003 (entry decisions); DPRIM-006 (position sizing); DPRIM-018 (sector allocation); DPRIM-024 (capital rotation) |
| **Allocation Dimensions** | By strategy type (momentum, fundamental, event-driven); by sector; by market cap; by time horizon; by risk level |
| **Review Cadence** | Monthly strategic review; weekly tactical review; immediate review when regime changes |
| **Failure Modes** | Ignoring regime change; under-diversifying (concentration); over-diversifying (dilution); static allocation in dynamic market; ignoring correlation |
| **Strengths** | Provides the framework for all lower-level decisions; ensures no individual decision creates systemic concentration |
| **Weaknesses** | Based on forecasts that may be wrong; rigidity can prevent optimal capital deployment |
| **Lifecycle** | Regime assessed → Strategy performance reviewed → Sector opportunity set evaluated → Capital budget set by bucket → Allocation communicated to decision pipeline → Monitored weekly → Revised on trigger |
| **Capital Impact** | Determines the maximum capital available for all categories of decision |
| **Risk Impact** | Sets the risk budget per category; the ceiling within which all individual position sizing decisions operate |
| **Portfolio Impact** | Defines the target portfolio composition; all individual decisions are constraints within this framework |
| **Governance** | Investment Committee decision; requires quorum; formally documented |
| **Examples** | "July 2026 allocation: 40% momentum strategies, 30% fundamental, 20% event-driven, 10% cash buffer. Sector limits: Banking 30%, IT 25%, Energy 20%, all others 15%" |
| **Anti-Examples** | "We invest in whatever looks best" (no framework); "We never change allocation" (no responsiveness to regime) |

---

### DPRIM-008 — RISK GATE ASSESSMENT

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-008 |
| **Name** | Risk Gate Assessment |
| **Definition** | The formal evaluation of a decision recommendation against all mandatory risk governance gates — the structured checkpoint that either approves or blocks a recommendation from proceeding to decision |
| **Why It Exists** | Without explicit risk gate assessment, approvals would be informal and incomplete. The risk gate assessment creates a checklistable, auditable, and consistent standard that every recommendation must satisfy, preventing governance shortcuts. |
| **Classification** | Governance | Quality Control | Sequential | Blocking |
| **Gate 1 — Evidence Quality** | At least 3 independent evidence types; each with source citation; no fabricated evidence |
| **Gate 2 — Conviction Level** | Conviction score >= 6.5/10; calculated from the full evidence set |
| **Gate 3 — Risk Budget** | Capital at risk within per-position limit; VaR impact within portfolio limit |
| **Gate 4 — Portfolio Constraints** | Sector concentration within limits; correlation with existing positions within limits |
| **Gate 5 — Regime Validation** | The decision type is appropriate for the current market regime |
| **Gate 6 — Mandate Compliance** | The entity, strategy type, and position size comply with the investment mandate |
| **Gate Results** | PASS all 6 → Advances to approval; FAIL any gate → Rejected with specific gate failure recorded |
| **Producers** | Governance system; risk management layer; portfolio management system |
| **Consumers** | Decision committee (receives gate-cleared recommendations); capital system (receives confirmation) |
| **Failure Modes** | Gates not evaluated; gates evaluated out of sequence; pass given on incomplete evaluation; gates overridden by authority who should not have that power |
| **Inviolability** | No authority may waive any risk gate; the risk gate system is constitutionally protected |
| **Lifecycle** | Recommendation received → Gate 1 evaluated → If pass, Gate 2 → If pass, Gate 3 → If pass, Gate 4 → If pass, Gate 5 → If pass, Gate 6 → If all pass, advance to approval |
| **Timing** | Each gate evaluation: typically under 30 seconds for automated gates; under 5 minutes for judgment-based gates |
| **Auditability** | Full gate-by-gate record; exact reason for any failure; timestamp for each evaluation |
| **Portfolio Impact** | No portfolio impact at assessment stage; prevents portfolio impact from unqualified decisions |
| **Examples** | "HDFC Bank recommendation: Gate 1 PASS (3 independent evidence types); Gate 2 PASS (conviction 7.2); Gate 3 PASS (capital at risk 1.4% vs limit 2%); Gate 4 PASS (banking 26% vs limit 30%); Gate 5 PASS (bullish regime, momentum strategy validated); Gate 6 PASS (NIFTY 50 component, within mandate)" |
| **Anti-Examples** | "Gate check: looks fine, approved" (not a structured gate evaluation); overriding Gate 3 because "the conviction is so high" (conviction never overrides risk gate) |

---

### DPRIM-009 — PORTFOLIO REBALANCING DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-009 |
| **Name** | Portfolio Rebalancing Decision |
| **Definition** | A portfolio-level decision to restore intended allocation weights after market movements have caused drift from target exposures, without requiring new entry thesis for each affected position |
| **Why It Exists** | Market movements continuously drift portfolio allocations from targets. Without periodic rebalancing, portfolios become concentrated in recent winners (concentration risk) or depleted in laggards. Rebalancing maintains the intended risk profile. |
| **Classification** | Portfolio-Level | Systematic | Maintenance | Capital-Neutral |
| **Inputs Required** | Current portfolio state; target allocation weights; drift thresholds; transaction cost estimate; tax considerations |
| **Outputs Produced** | List of positions to increase, reduce, or close; capital movements required; expected portfolio state after rebalancing |
| **Producers** | Portfolio monitoring system when drift exceeds threshold; periodic scheduled review |
| **Consumers** | Execution system (for individual rebalancing trades); portfolio system (for state update) |
| **Drift Threshold** | Rebalancing triggered when any sector or strategy allocation deviates from target by more than 5 percentage points |
| **Failure Modes** | Over-rebalancing (excessive transaction costs); under-rebalancing (allowing excessive drift); rebalancing without tax consideration; forced rebalancing into illiquid positions |
| **Strengths** | Maintains intended risk profile; systematic and disciplined; not thesis-driven |
| **Weaknesses** | Transaction costs; may reduce winners prematurely if rebalancing is purely mechanical |
| **Lifecycle** | Portfolio drift detected → Rebalancing triggered → Target weights recalculated → Trade list generated → Transaction costs assessed → If net positive, rebalancing approved → Executed |
| **Capital Impact** | Capital-neutral at portfolio level; moves capital between positions |
| **Risk Impact** | Reduces concentration risk; restores intended diversification |
| **Portfolio Impact** | Significant; changes composition without requiring new thesis development |
| **Governance** | Standing authority for systematic rebalancing within defined drift limits; committee review for strategic rebalancing |
| **Examples** | "Banking allocation at 33% vs 30% target — reduce 3% by trimming 50 HDFC Bank shares. IT allocation at 18% vs 25% target — increase by deploying 7% of available capital into IT sector" |
| **Anti-Examples** | "I rebalanced by adding more to winners" (that is position scaling, not rebalancing); rebalancing when drift is only 1% (too frequent, excessive cost) |

---

### DPRIM-010 — EMERGENCY DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-010 |
| **Name** | Emergency Decision |
| **Definition** | An immediate decision to exit positions or reduce risk exposure, triggered by kill switch conditions or extraordinary circumstances that require action faster than the standard governance process allows |
| **Why It Exists** | Black swan events, flash crashes, and kill switch triggers require instant action. The standard governance pipeline (recommendation, multi-gate review, committee approval) is too slow for extraordinary risk conditions. The emergency decision provides a constitutionally authorized fast path. |
| **Classification** | Emergency | Fast-Path | Capital-Preserving | Kill-Switch-Level |
| **Triggers** | VIX exceeds 45; daily portfolio loss exceeds 2%; exchange circuit breaker; extreme news event; broker/exchange failure; system failure |
| **Authorization** | Kill switch activates automatically; human emergency override is authorized without committee deliberation |
| **Inputs Required** | Kill switch trigger condition confirmed; emergency type classification; positions to exit; market conditions assessment |
| **Outputs Produced** | Immediate exit orders for all or selected positions; capital preservation record; emergency audit report |
| **Producers** | Kill switch system (automatic); Risk Committee Chair (human emergency); System Monitor |
| **Consumers** | Execution system (immediate orders); portfolio system (rapid updates); governance system (post-emergency review) |
| **Speed Requirement** | Emergency decisions must be executable within 60 seconds of trigger detection |
| **Post-Emergency Review** | Every emergency decision triggers a mandatory post-emergency review within 24 hours |
| **Failure Modes** | False trigger (emergency called when not warranted); trigger not fired when warranted; partial execution of emergency exits; system failure during emergency |
| **Governance** | Pre-authorized by mandate; no gate review required during emergency; full retroactive audit required within 24 hours |
| **Capital Impact** | Typically significant — emergency exits may realize losses to prevent larger losses |
| **Portfolio Impact** | May reduce portfolio from fully deployed to largely cash within minutes |
| **Learning** | Emergency events are the highest-value learning events; full detailed post-mortem required |
| **Examples** | "VIX spiked to 52 — kill switch activated — all open positions exited at market price — total portfolio moved to 95% cash within 8 minutes" |
| **Anti-Examples** | "VIX is at 46 but I think it will come back down so I will wait" (kill switch override — constitutional violation); emergency decision with no post-emergency review |

---

### DPRIM-011 — STRATEGY ACTIVATION DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-011 |
| **Name** | Strategy Activation Decision |
| **Definition** | The portfolio-level decision to add a strategy to the active decision pipeline — authorizing a specific strategy to generate recommendations within the portfolio mandate |
| **Why It Exists** | Not all strategies are appropriate for all market regimes. The strategy activation decision ensures that only regime-validated strategies are generating recommendations, preventing the system from making decisions that are systematically inappropriate for current conditions. |
| **Classification** | Portfolio-Level | Regime-Conditional | Meta-Decision | Governance |
| **Inputs Required** | Strategy specification; regime assessment; strategy historical performance; walk-forward test results; mandate compatibility check |
| **Activation Criteria** | Walk-forward win rate >= 50%; Sharpe ratio > 0.8; maximum drawdown < 15%; compatible with current regime |
| **Deactivation Triggers** | Rolling 30-day win rate below 40%; Sharpe below 0.5; maximum drawdown exceeds 15%; regime change to incompatible state |
| **Producers** | Strategy evaluation system; ResearchLab; strategy governance committee |
| **Consumers** | Recommendation engine (knows which strategies may generate recommendations); capital allocation system |
| **Lifecycle** | Strategy proposed → Backtesting completed → Walk-forward testing → Performance gates evaluated → Mandate compatibility confirmed → Committee approval → Activated → Monitored → Deactivated or continued |
| **Failure Modes** | Activating a strategy in the wrong regime; activating without sufficient testing; failing to deactivate when criteria are no longer met |
| **Examples** | "Momentum strategy activated for trending regime — Sharpe 1.2, WF Win Rate 58%, Max DD 8.4%" |
| **Anti-Examples** | Activating a strategy because "it worked last year" without walk-forward testing |

---

### DPRIM-012 — HEDGING DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-012 |
| **Name** | Hedging Decision |
| **Definition** | A decision to enter a position designed to offset or reduce the risk of one or more existing positions, accepting a reduction in expected return in exchange for protection against adverse outcomes |
| **Why It Exists** | Some risk exposures are unavoidable given the investment thesis but are larger than comfortable in certain conditions. Hedging allows the thesis to be maintained while managing the risk — the protection of existing capital is the primary purpose. |
| **Classification** | Risk-Reducing | Capital-Consuming | Thesis-Protecting | Return-Reducing |
| **Inputs Required** | Positions requiring hedging; hedge instrument options; hedge ratio calculation; hedge cost assessment; regime context; expected hedge duration |
| **Outputs Produced** | Specific hedge position (entity, quantity, direction, duration); hedged portfolio risk metrics |
| **Hedge Types** | Direct hedge (inverse position in same entity); Sector hedge (inverse ETF or futures); Portfolio hedge (index puts, VIX exposure) |
| **Producers** | Risk management system; risk committee; triggered by elevated VIX, event risk, or portfolio concentration |
| **Consumers** | Execution system; portfolio risk system; capital management |
| **Hedge Effectiveness** | Measured as the reduction in portfolio VaR or maximum drawdown per unit of hedge cost |
| **Cost-Benefit** | Expected hedge cost must be justified by the risk reduction provided; pure insurance has a cost |
| **Failure Modes** | Imperfect hedge (correlation breaks down); hedge too expensive (reduces returns disproportionately); hedge too small (insufficient protection); hedge too large (net short bias) |
| **Lifecycle** | Risk identified → Hedge instrument selected → Hedge ratio calculated → Cost assessed → Committee review → Approved → Executed → Monitored → Removed when risk condition passes |
| **Capital Impact** | Consumes capital for the hedge position; reduces available capital |
| **Risk Impact** | Reduces the specific risk being hedged; may introduce new risks (basis risk, theta decay) |
| **Portfolio Impact** | Reduces net exposure and beta; protects against the specific hedged scenario |
| **Examples** | "Portfolio banking exposure at 28% approaching limit — buy NIFTY Bank puts (ATM, 30-day expiry) sized to cap banking sector drawdown at 5% of portfolio" |
| **Anti-Examples** | "I hedged by just selling some positions" (that is reduction, not hedging); hedging without assessing hedge cost impact on expected portfolio return |


---

### DPRIM-013 — WATCHLIST PROMOTION DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-013 |
| **Name** | Watchlist Promotion Decision |
| **Definition** | The decision to elevate an entity from passive monitoring to active hypothesis evaluation — committing research resources and analytical attention without yet committing capital |
| **Why It Exists** | Not every entity in the investment universe warrants active analysis. The watchlist promotion decision allocates scarce analytical resources to entities with sufficient initial evidence to justify deeper investigation. |
| **Classification** | Resource-Allocating | Pre-Capital | Attention-Committing |
| **Inputs Required** | Initial signal or observation; materiality threshold met; entity within mandate; capacity in active hypothesis pool |
| **Promotion Criteria** | At least 1 material signal; entity in the investable universe; no conflicting current position |
| **Producers** | Opportunity scanner; news monitoring; anomaly detection |
| **Consumers** | Research pipeline; evidence accumulation system; hypothesis tracking |
| **Lifecycle** | Material signal detected → Entity checked against mandate → Active hypothesis pool has capacity → Promoted to watchlist → Evidence accumulation begins → Reaches conviction threshold (→ Recommendation) or conviction fails to develop (→ Removed) |
| **Demotion Triggers** | Evidence fails to develop within 30 days; contradicting evidence overwhelms initial signal; regime change makes thesis implausible |
| **Capital Impact** | None — the watchlist promotion commits analytical attention, not capital |
| **Examples** | "BHEL unusual volume detected — promoted to active watchlist for infrastructure spending thesis evaluation" |
| **Anti-Examples** | Adding every stock that moves to the watchlist (no signal threshold); keeping exhausted watchlist items beyond their validity period |

---

### DPRIM-014 — HOLD DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-014 |
| **Name** | Hold Decision |
| **Definition** | An explicit, active decision to maintain an existing open position without modification, made after reconfirming that the original thesis remains intact and conviction is above the maintenance threshold |
| **Why It Exists** | Holding is not the absence of a decision — it is a positive commitment to continue. Without explicit hold decisions, positions linger through inertia rather than active management, creating the risk of holding beyond a valid thesis. |
| **Classification** | Maintenance | Reconfirming | Active-Passive |
| **Inputs Required** | Open position; current conviction score; thesis validity check; regime compatibility check; evidence status review |
| **Outputs Produced** | Reconfirmed hold authorization; updated conviction record; next review date |
| **Hold Threshold** | Conviction must be >= 4.0 to justify continued holding; below 4.0, exit is triggered |
| **Review Frequency** | Daily for positions in volatile conditions; weekly for stable thesis positions |
| **Failure Modes** | Holding without re-evaluation (inertia holding); holding below the maintenance threshold; holding after thesis invalidation |
| **Lifecycle** | Review triggered → Current evidence set evaluated → Conviction recalculated → If >= 4.0 and thesis intact → Hold confirmed → Next review scheduled; If < 4.0 or thesis invalidated → Exit decision triggered |
| **Capital Impact** | Maintains existing capital deployment |
| **Risk Impact** | Maintains existing risk exposure |
| **Examples** | "HDFC Bank position: 21st day. Thesis: NIM expansion intact, rate cut expectation unchanged, conviction 7.1/10 → HOLD confirmed, next review in 5 days" |
| **Anti-Examples** | "I am just holding and not reviewing" (inertia, not a hold decision); holding at conviction 3.2 (below exit threshold) |

---

### DPRIM-015 — SCALING DECISION (ADD TO WINNER)

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-015 |
| **Name** | Scaling Decision |
| **Definition** | A decision to increase the size of an existing open position that is performing well and showing improving conviction — adding to a winner as the thesis confirms, not as the price rises indiscriminately |
| **Why It Exists** | When a thesis is proving correct and conviction is increasing, the position size should reflect the higher-quality evidence. Scaling is the mechanism for calibrating position size to conviction dynamically throughout the holding period. |
| **Classification** | Position-Increasing | Conviction-Responsive | Capital-Deploying |
| **Inputs Required** | Open profitable position; conviction score above scaling threshold (typically 7.5+); confirming evidence since entry; available capital; portfolio constraints |
| **Scaling Rules** | Only to a position showing unrealized gains; conviction must have increased since entry; total position must remain within mandate limits; add at logical continuation levels |
| **Scaling Prohibition** | Absolutely prohibited to add to a losing position to average down on an invalidated thesis |
| **Producers** | Position monitoring system when scaling criteria met; triggered by confirming evidence arrival |
| **Consumers** | Execution system; capital management; risk system (updated exposure) |
| **Failure Modes** | Adding to losers (opposite of intended use); scaling beyond mandate limits; scaling on conviction that has not actually improved; scaling at overextended technical levels |
| **Lifecycle** | Confirming evidence arrives → Conviction recalculated (must improve) → Position in profit → Portfolio limits checked → Scaling size calculated → Approval → Execution → Updated cost basis recorded |
| **Capital Impact** | Increases capital deployed; must be within available capital |
| **Portfolio Impact** | Increases sector and correlation exposure; may approach concentration limits |
| **Examples** | "HDFC Bank position: day 15, +4.8%, conviction improved to 8.1 on RBI rate cut signal — scale by 50 additional shares to 250 total; within banking 30% limit" |
| **Anti-Examples** | "I will add to TATAMOTORS even though it is down 5% because I believe in the thesis" (averaging down, constitutional violation) |

---

### DPRIM-016 — PARTIAL EXIT DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-016 |
| **Name** | Partial Exit Decision |
| **Definition** | A decision to close a defined fraction of an existing open position, realizing partial P&L while retaining residual exposure to the remaining thesis |
| **Why It Exists** | Full binary entry and exit creates all-or-nothing outcomes. Partial exits allow the system to secure realized gains while allowing the thesis to continue developing, balancing capital preservation with continued upside participation. |
| **Classification** | Position-Reducing | Profit-Securing | Thesis-Continuing |
| **Inputs Required** | Open profitable position; partial profit target reached; remaining thesis justification; partial exit percentage |
| **Common Triggers** | First target reached (exit 50%); second target (exit remaining 50%); portfolio concentration limit approached; partial thesis confirmation |
| **Minimum Residual** | The retained portion must still meet the hold threshold conviction |
| **Producers** | Position monitoring system; target level system |
| **Consumers** | Execution system; portfolio system; P&L attribution system |
| **Lifecycle** | Partial target reached → Conviction of remaining thesis assessed → Partial exit size calculated → Execution → P&L for exited tranche recorded → Residual position continues monitoring |
| **Capital Impact** | Releases partial capital; reduces deployed amount |
| **Risk Impact** | Reduces risk exposure proportionate to exited tranche |
| **P&L Handling** | Realized P&L for the exited tranche is recorded immediately; residual continues on the original cost basis |
| **Examples** | "HDFC Bank at target 1 (1880): Exit 100 of 200 shares, realize +3.3% on first tranche. Stop on remaining 100 shares moved to 1820 (breakeven). Continue to Target 2 at 1940." |
| **Anti-Examples** | "I am selling half just to feel better" (no analytical basis for the partial exit fraction) |

---

### DPRIM-017 — SECTOR ALLOCATION DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-017 |
| **Name** | Sector Allocation Decision |
| **Definition** | A portfolio-level decision determining the target exposure to each market sector, governed by regime assessment, opportunity quality, and concentration limits |
| **Why It Exists** | Sector allocation determines the portfolio-level context within which all individual decisions operate. Without explicit sector allocation decisions, individual decisions can inadvertently create dangerous sector concentration. |
| **Classification** | Portfolio-Level | Strategic | Constraint-Setting |
| **Inputs Required** | Regime assessment; sector performance; economic cycle stage; upcoming sector catalysts; mandate sector limits |
| **Outputs Produced** | Target sector allocations by percentage; maximum single-sector limit; current vs target delta |
| **Review Cadence** | Monthly standard review; immediate review on regime change |
| **Producers** | Investment committee; portfolio governance layer |
| **Consumers** | All entry decisions (sector limit check); capital allocation system; rebalancing decision system |
| **Failure Modes** | Static allocation in changing regime; ignoring correlation between sectors; setting limits without mechanism to enforce them |
| **Examples** | "July 2026 sector allocation: Banking 25%, IT 20%, Consumer 20%, Energy 15%, Healthcare 10%, Infrastructure 10%. Maximum single sector: 30%" |

---

### DPRIM-018 — OVERRIDE DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-018 |
| **Name** | Override Decision |
| **Definition** | A deliberate supersession of a system-generated decision by a human agent, substituting human judgment for AI recommendation, with full documentation and accountability |
| **Why It Exists** | The AI system cannot anticipate all circumstances. Human override provides the escape valve for truly novel situations, relationship-driven information (management body language, for example), or extreme conditions where human judgment is constitutionally required. |
| **Classification** | Human-Authority | Documented | Accountable | Exceptional |
| **Authorization** | Only designated human agents may override; override authority is specific to position size tier |
| **Documentation Requirements** | Override reason must be documented; what system recommended; what human decided instead; expected outcome |
| **Post-Override Review** | Every override is reviewed in the next governance cycle; aggregate override patterns are analyzed quarterly |
| **Override Types** | Entry override (enter when system rejects); exit override (hold when system recommends exit); size override (change recommended size) |
| **Prohibited Overrides** | Kill switch override is constitutionally prohibited; stop loss override is constitutionally prohibited |
| **Failure Modes** | Undocumented override; override beyond authority tier; using override to bypass risk governance |
| **Learning Value** | Overrides that outperform the system reveal areas where human judgment adds value; those that underperform identify behavioral biases |
| **Examples** | "System recommended Reject on RELIANCE (conviction 6.4). Human override: management channel check confirmed major contract win not yet public. Override applied, position opened. Outcome: +12.8%" |
| **Anti-Examples** | Undocumented override; override of kill switch |

---

### DPRIM-019 — COMMITTEE APPROVAL DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-019 |
| **Name** | Committee Approval Decision |
| **Definition** | A governance decision made collectively by a multi-agent committee, requiring quorum, structured debate, and formal vote, applied to decisions above the individual agent authority threshold |
| **Why It Exists** | Individual agents have authority limits. For decisions above those limits — large positions, novel strategies, concentrated sectors — collective committee judgment provides higher quality governance than individual approval. |
| **Classification** | Governance | Collective | Quorum-Required | Formal |
| **Quorum** | Minimum 3 agents; majority vote required; tie goes to Chief Intelligence Agent |
| **Triggers** | Position size above 3% of portfolio; novel strategy type; sector concentration above 20%; emergency non-kill-switch situation |
| **Debate Requirements** | Each member presents position; devil's advocate presents opposing case; dissent is recorded |
| **Vote Recording** | Every member's vote and rationale is permanently recorded |
| **Decision Speed** | Target completion within 15 minutes for time-sensitive decisions; 60 minutes for standard |
| **Failure Modes** | Groupthink; quorum not achieved; debate shortcuts; vote not recorded; decision made by authority rather than by evidence |
| **Examples** | "Committee convened for NIFTY Index fund 4% position: Technical (Bull 7.1), Fundamental (Bull 6.8), Macro (Neutral 6.2), Risk (Concern 5.8). Vote: 3-1 Bull. Devil's advocate: liquidity risk in stressed markets. Final conviction: 7.0 with risk note. APPROVED." |

---

### DPRIM-020 — DECISION RECORD

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-020 |
| **Name** | Decision Record |
| **Definition** | The permanent, immutable document capturing every material aspect of a decision from recommendation creation through governance, execution, monitoring, outcome, and learning |
| **Why It Exists** | Without a comprehensive decision record, learning is impossible, accountability is absent, and governance cannot be verified. The decision record is the audit artifact that makes the entire decision system trustworthy. |
| **Classification** | Audit | Permanent | Immutable | Learning-Input |
| **Required Fields** | Decision ID; creation timestamp; entity; direction; quantity; entry price; stop price; target price; conviction score; evidence citations (minimum 3); governance gate results; approval timestamp; execution confirmation; holding log; exit details; P&L; learning notes |
| **Immutability** | Once approved, the decision record cannot be altered; only appended |
| **Retention** | Permanent — the decision record is never deleted |
| **Producers** | Decision pipeline at each stage; monitoring system; execution system; learning system |
| **Consumers** | Learning system; audit system; attribution analysis; calibration system; governance review |
| **Failure Modes** | Incomplete record; missing governance gate documentation; outcome not recorded; learning notes absent |
| **Examples** | "Record ID: 2026-07-01-HDFC-001. Entry: 1820, Stop: 1755, Target: 1940. Conviction: 7.2. Evidence: [1] NIM expansion Q3, [2] Rate cut signal, [3] Volume breakout. Gates: PASS all 6. Approved: 09:47. Executed: 10:02. Exit: 21 days at 1937.50. P&L: +6.5%. Learning: NIM expansion signal weight increased to 0.82." |

---

### DPRIM-021 — RE-ENTRY DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-021 |
| **Name** | Re-Entry Decision |
| **Definition** | A new entry into a previously held and closed position, requiring a completely new reasoning cycle and full governance process — not a resumption of the old thesis |
| **Why It Exists** | After a position is closed (whether at stop loss, profit target, or thesis invalidation), the market conditions have changed. A re-entry is not a continuation — it is a new investment decision that happens to involve the same entity. |
| **Classification** | New Decision | Entity-Repeated | Full-Process |
| **Key Requirement** | The re-entry must be based on new evidence, not the recycled original thesis |
| **Minimum Gap** | After a stop loss exit, a minimum re-evaluation period of 24 hours before any re-entry consideration |
| **Failure Modes** | Re-entering immediately after a stop loss without new evidence; treating re-entry as a continuation rather than a new decision; revenge re-entry |
| **Full Process** | Re-entry requires the complete pipeline from observation through governance — identical to a first entry |
| **Examples** | "TATAMOTORS stopped out at 875. New evidence: Q4 EV volumes beat + management guidance change. New thesis. New governance. Re-entry at 892 with fresh conviction 6.9/10 after 3-day re-evaluation." |

---

### DPRIM-022 — TIME STOP DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-022 |
| **Name** | Time Stop Decision |
| **Definition** | The pre-committed rule to close a position after a specified holding period if the expected catalyst has not materialized, regardless of current P&L |
| **Why It Exists** | Some theses have explicit time horizons — the thesis was correct for a specific time window. If the thesis has not played out within the expected window, the original reasoning may no longer be valid. |
| **Classification** | Rule-Based | Time-Governed | Thesis-Disciplining |
| **Setting** | Defined at entry; typically: catalyst expected within 30 days = 35-day time stop |
| **Override** | Time stop may be extended ONLY if new confirming evidence arrives that justifies an extended horizon — requires governance review |
| **Failure Modes** | Not setting a time stop at entry; extending time stop without new evidence; using time stop extension to avoid accepting a loss |
| **Examples** | "Budget announcement thesis: entry Jan 25, expected catalyst Feb 1. Time stop Feb 10. If no catalyst by Feb 10, exit regardless of price." |

---

### DPRIM-023 — BREAKEVEN STOP DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-023 |
| **Name** | Breakeven Stop Decision |
| **Definition** | The decision to move an existing stop loss to the entry price level once the position has achieved a sufficient gain, transforming a risk position into a risk-free (at worst breakeven) position |
| **Why It Exists** | After a position has moved meaningfully in the expected direction, the system can protect against a full loss while maintaining upside exposure. This is the most important stop migration rule — it converts a risk commitment into a protected commitment. |
| **Classification** | Risk-Reducing | Profit-Protecting | Stop-Migration |
| **Trigger** | Position achieves 50% of the distance to the first profit target (e.g., entry 1820, target 1940, breakeven stop triggered at 1880) |
| **Effect** | Worst-case outcome moves from a loss to breakeven; upside potential unchanged |
| **Rules** | Stop may only be moved to breakeven or better — never moved away from current price direction |
| **Failure Modes** | Moving to breakeven too early (tight stop; shaken out on noise); not moving to breakeven (leaving avoidable risk on table) |
| **Examples** | "HDFC Bank entry 1820, first target 1940. At 1880 (50% of way to target): move stop from 1755 to 1820 (breakeven). Now worst case is breakeven, best case is full target." |

---

### DPRIM-024 — CAPITAL ROTATION DECISION

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-024 |
| **Name** | Capital Rotation Decision |
| **Definition** | A portfolio-level decision to systematically move capital from underperforming or thesis-expired strategies and sectors into outperforming or high-opportunity strategies and sectors |
| **Why It Exists** | Capital should continuously flow toward the highest risk-adjusted expected return opportunities. Capital rotation is the mechanism that ensures the portfolio stays aligned with the current opportunity set rather than reflecting the opportunity set of the past. |
| **Classification** | Portfolio-Level | Strategic | Opportunity-Seeking |
| **Triggers** | Regime change; sector rotation signal; strategy underperformance below threshold; new high-opportunity theme identified |
| **Process** | Identify underperforming capital pools → Evaluate exit costs → Identify high-opportunity destination → Confirm destination thesis → Execute rotation with transaction cost discipline |
| **Failure Modes** | Chasing recent performance (not rotating to opportunity, rotating to momentum); rotating too frequently (excessive costs); rotating without thesis |
| **Examples** | "IT sector earnings disappointing, conviction declining. Rotating 5% from IT to Healthcare on monsoon-driven rural demand thesis." |

---

### DPRIM-025 — LEARNING-TRIGGERED DECISION UPDATE

| Attribute | Value |
|---|---|
| **Primitive Code** | DPRIM-025 |
| **Name** | Learning-Triggered Decision Update |
| **Definition** | A modification to the decision architecture, thresholds, or parameters triggered by accumulated evidence from the learning system — the feedback loop that allows decisions to improve over time |
| **Why It Exists** | The decision architecture is not static. Evidence accumulates about what works and what does not. The learning-triggered update is the mechanism by which the system improves its decision-making based on what it has learned from outcomes. |
| **Classification** | Meta-Decision | Learning-Driven | Architecture-Updating |
| **Update Types** | Conviction threshold recalibration; evidence weight update; strategy parameter adjustment; new governance gate addition; failure mode mitigation update |
| **Evidence Requirement** | Changes require statistical evidence from >= 30 recent decisions; not triggered by single outcomes |
| **Governance** | Learning updates require committee review for anything above parameter adjustment; architectural changes require full committee and documentation |
| **Failure Modes** | Over-fitting to recent results; updating on insufficient evidence; updating the wrong parameter in response to a failure |
| **Examples** | "Analysis of 45 recent event-driven decisions: entries made within 48 hours of event announcement have 15% higher win rate than those made earlier. Update: tighten pre-event entry timing window from 5 days to 2 days." |
| **Anti-Examples** | "We lost on 3 momentum trades so we are stopping momentum strategy" (3 trades is not sufficient statistical evidence) |

---

## PART IV — DECISION TYPES

*The complete taxonomy of investment decision paradigms. Each type has specific strengths, weaknesses, appropriate uses, and failure modes.*

---

### Decision Type Overview

| Code | Type | Core Mechanism | Time Horizon | Capital Impact |
|---|---|---|---|---|
| DT-01 | Investment Decision | Long-term thesis-driven commitment | Months to years | Large; high conviction |
| DT-02 | Trading Decision | Shorter-term price movement capture | Days to weeks | Moderate; tactical |
| DT-03 | Portfolio Decision | Aggregate portfolio optimization | Ongoing | Variable; cross-portfolio |
| DT-04 | Risk Decision | Risk management and capital preservation | Immediate | Defensive |
| DT-05 | Capital Allocation Decision | Resource distribution across opportunities | Monthly/strategic | Portfolio-wide |
| DT-06 | Rebalancing Decision | Restoring target allocations after drift | Triggered by drift | Neutral across portfolio |
| DT-07 | Entry Decision | Opening a new position | Point-in-time | Capital commitment |
| DT-08 | Exit Decision | Closing an existing position | Point-in-time | Capital release |
| DT-09 | Scaling Decision | Increasing a profitable position | Conviction-triggered | Additional capital |
| DT-10 | Hedging Decision | Offsetting existing risk | Regime-driven | Defensive capital |
| DT-11 | Diversification Decision | Adding uncorrelated exposure | Portfolio-driven | Spread capital |
| DT-12 | Emergency Decision | Rapid de-risking under extreme conditions | Immediate | Full or partial exit |
| DT-13 | Strategic Decision | Multi-year portfolio direction | Quarterly/annual | Architecture-wide |
| DT-14 | Tactical Decision | Near-term opportunity exploitation | Days to weeks | Targeted allocation |
| DT-15 | Operational Decision | Portfolio maintenance and process | Ongoing | Administrative |
| DT-16 | Long-Horizon Decision | Multi-year compounding thesis | Years | High capital; patient |
| DT-17 | Short-Horizon Decision | Days to weeks timeframe | Days | Moderate; active |
| DT-18 | Intraday Decision | Within-session positioning | Hours | Small; precision-required |
| DT-19 | Event-Driven Decision | Specific upcoming catalyst | Event-bounded | Time-limited capital |
| DT-20 | Systematic Decision | Rules-based automatic execution | Defined by rules | Algorithm-sized |
| DT-21 | Discretionary Decision | Judgment-based manual approval | Case-by-case | Judgment-sized |
| DT-22 | AI Decision | Fully autonomous AI recommendation | AI cycle-based | Mandate-bounded |
| DT-23 | Human Decision | Human-initiated and approved | Human review pace | Human-determined |
| DT-24 | Hybrid Decision | AI recommendation, human approval | Deliberated pace | Governance-calibrated |
| DT-25 | Hierarchical Decision | Multi-level portfolio cascade | Aggregate → specific | Top-down allocation |
| DT-26 | Conditional Decision | Action contingent on future condition | Trigger-dependent | Conditional commitment |
| DT-27 | Probabilistic Decision | Multiple-scenario weighted approach | Uncertainty-explicit | Scenario-weighted |
| DT-28 | Adaptive Decision | Self-modifying based on feedback | Learning-triggered | Dynamic adjustment |
| DT-29 | Momentum Decision | Trend continuation exploitation | Regime-conditional | Trend-following |
| DT-30 | Value Decision | Intrinsic value gap exploitation | Patient; long-horizon | Deep value; patient |

---

### DT-01 — INVESTMENT DECISION

| Attribute | Value |
|---|---|
| **Definition** | A commitment to build a long-term position based on a fundamental thesis about the intrinsic value, competitive position, or structural growth of an entity |
| **Core Mechanism** | Fundamental Analysis → Intrinsic Value → Price Gap → Long-Term Position |
| **Strengths** | High-quality thesis; less sensitive to short-term noise; compound returns over time; lower transaction costs from lower turnover |
| **Weaknesses** | Requires patience; mark-to-market volatility tests conviction; illiquidity during adverse periods |
| **Appropriate Use** | When fundamental thesis is strong; when time horizon is 6+ months; when entity has identifiable competitive advantages |
| **Failure Modes** | Holding through fundamental deterioration out of attachment; failing to exit when thesis is genuinely invalidated; confusing temporary price weakness with thesis failure |
| **Time Horizon** | 6 months to 3+ years |
| **Conviction Requirement** | Minimum 7.0/10 — higher bar due to longer commitment |
| **Example** | "HDFC Bank: ROIC consistently above cost of capital; NIM expansion cycle; retail loan book growth; management track record. 18-month investment decision, 4% portfolio allocation." |

---

### DT-02 — TRADING DECISION

| Attribute | Value |
|---|---|
| **Definition** | A shorter-term commitment to capture a price movement driven by a near-term catalyst, technical pattern, or temporary mispricing |
| **Core Mechanism** | Near-Term Catalyst or Pattern → Expected Move → Timed Position |
| **Strengths** | Faster capital recycling; lower commitment duration; faster feedback for learning |
| **Weaknesses** | Higher transaction costs from turnover; requires more precise timing; higher operational intensity |
| **Appropriate Use** | When a specific catalyst has a defined timeline; when technical setup has clear entry and exit; when the thesis is time-limited |
| **Failure Modes** | Overtrading; turning a trading decision into an investment decision when stop is hit; imprecise timing on entry |
| **Time Horizon** | 2-30 days |
| **Conviction Requirement** | Minimum 6.5/10 |
| **Example** | "TATAMOTORS Q4 results next week: volume beat expected + EV reclassification. Trading entry 905, stop 875, target 960, 10-day horizon." |

---

### DT-03 — PORTFOLIO DECISION

| Attribute | Value |
|---|---|
| **Definition** | A decision about the aggregate composition, risk, and character of the portfolio — affecting multiple positions simultaneously rather than a single entity |
| **Core Mechanism** | Portfolio State Assessment → Target State Definition → Rebalancing Actions |
| **Strengths** | Manages aggregate risk; optimizes capital allocation; prevents individual decision drift from portfolio strategy |
| **Weaknesses** | Requires visibility across all positions; complex interdependencies; may force exits of individually strong positions |
| **Appropriate Use** | Monthly rebalancing; regime change adaptation; risk budget reallocation; sector rotation |
| **Failure Modes** | Ignoring aggregate effects of individual decisions; optimizing individual positions while ignoring portfolio-level risk |
| **Time Horizon** | Ongoing; reviewed monthly |
| **Example** | "Portfolio review: banking at 32% vs 30% limit — trim 2%; IT at 17% vs 20% target — add 3%; cash at 12% vs 10% minimum — deploy 2% into best current opportunity" |

---

### DT-04 — RISK DECISION

| Attribute | Value |
|---|---|
| **Definition** | A decision made primarily to reduce, bound, or manage risk rather than to generate return — capital preservation as the primary objective |
| **Core Mechanism** | Risk Signal → Acceptable Risk Level → Defensive Action |
| **Strengths** | Preserves capital; prevents catastrophic loss; maintains ability to re-enter when conditions improve |
| **Weaknesses** | Sacrifice of return; potential for over-hedging; defensive action too early gives up gains |
| **Appropriate Use** | When VIX is elevated; when portfolio drawdown is approaching limits; when regime is uncertain; when black swan risk is elevated |
| **Failure Modes** | Over-reacting to temporary volatility; not taking defensive action when genuinely warranted |
| **Example** | "VIX at 38, approaching historical stress level: reduce portfolio exposure from 82% to 60%, add NIFTY put hedge, increase cash buffer." |

---

### DT-05 — CAPITAL ALLOCATION DECISION

| Attribute | Value |
|---|---|
| **Definition** | The strategic decision determining how total capital is distributed across strategies, sectors, and risk levels — the highest-level resource decision |
| **Core Mechanism** | Opportunity Set Assessment → Return per Risk Ranking → Capital Budget Setting |
| **Strengths** | Ensures capital works toward the highest expected return; prevents unintended concentration; drives portfolio strategy |
| **Weaknesses** | Forecasts used in allocation may be wrong; rigidity can prevent opportunistic deployment |
| **Appropriate Use** | Monthly strategic review; regime change; new strategy activation |
| **Time Horizon** | 1-3 months between major reviews |
| **Example** | "Q3 2026 allocation: Momentum strategies 35%, Fundamental 35%, Event-driven 20%, Cash 10%. Max banking 30%, max IT 25%." |

---

### DT-06 — REBALANCING DECISION

| Attribute | Value |
|---|---|
| **Definition** | A decision to restore target portfolio allocations after market movements have caused drift beyond defined tolerance bands |
| **Core Mechanism** | Current Allocation vs Target → Drift Calculation → Rebalancing Trades |
| **Strengths** | Systematic; not thesis-dependent; maintains risk profile; constitutes implied buy-low-sell-high discipline |
| **Weaknesses** | Transaction costs; may trim strong performers prematurely |
| **Appropriate Use** | When allocation drifts beyond 5% from target; monthly systematic review |
| **Failure Modes** | Rebalancing too frequently (excessive costs); not rebalancing when drift is significant |
| **Example** | "RELIANCE grew from 8% to 11% of portfolio — trim by 3%; Healthcare shrank to 7% from 10% target — add 3%" |

---

### DT-07 — ENTRY DECISION (See DPRIM-003 for full specification)

| Attribute | Value |
|---|---|
| **Definition** | The commitment to open a new position at a specific time and price, initiating capital deployment and risk exposure |
| **Strengths** | Converts conviction into capital deployment; initiates learning cycle |
| **Weaknesses** | Timing risk; immediate capital commitment; creates obligation to monitor and exit |
| **Appropriate Use** | When conviction >= 6.5, regime validated, all governance gates cleared |
| **Key Rule** | Stop loss must be defined before entry is executed |

---

### DT-08 — EXIT DECISION (See DPRIM-004 for full specification)

| Attribute | Value |
|---|---|
| **Definition** | The commitment to close all or part of an existing position, realizing P&L and triggering the learning cycle |
| **Strengths** | Enforces discipline; releases capital; triggers learning |
| **Weaknesses** | Timing uncertainty; exit too early or too late affects returns |
| **Appropriate Use** | Stop loss hit; target reached; thesis invalidated; time stop; conviction below 4.0 |
| **Key Rule** | Every exit must be followed by a learning record regardless of P&L |

---

### DT-09 — SCALING DECISION (See DPRIM-015 for full specification)

| Attribute | Value |
|---|---|
| **Definition** | Adding to a winning position as conviction increases and the thesis confirms |
| **Strengths** | Aligns capital to highest-conviction positions dynamically |
| **Weaknesses** | Increases concentration; chasing if done on price momentum rather than evidence |
| **Appropriate Use** | Position in profit; conviction has increased; portfolio limits permit |
| **Key Rule** | Never scale into a losing position |

---

### DT-10 — HEDGING DECISION (See DPRIM-012 for full specification)

| Attribute | Value |
|---|---|
| **Definition** | Entering an offsetting position to reduce risk on an existing position |
| **Strengths** | Reduces tail risk; protects capital; allows holding thesis through adverse conditions |
| **Weaknesses** | Costs money; reduces upside; may be a sign of insufficient confidence in the original thesis |
| **Appropriate Use** | When event risk is elevated; when sector concentration approaches limits; when regime is uncertain |

---

### DT-11 — DIVERSIFICATION DECISION

| Attribute | Value |
|---|---|
| **Definition** | A decision specifically motivated by the need to add uncorrelated exposure to reduce aggregate portfolio risk |
| **Core Mechanism** | Portfolio Correlation Analysis → Low-Correlation Opportunity → Diversifying Position |
| **Strengths** | Reduces portfolio risk without proportionate reduction in expected return |
| **Weaknesses** | Forced diversification into low-conviction opportunities reduces decision quality |
| **Appropriate Use** | When portfolio correlation is high; when regime creates cluster risk |
| **Key Rule** | Diversification decisions still require minimum conviction threshold; diversification does not justify low-quality decisions |

---

### DT-12 — EMERGENCY DECISION (See DPRIM-010 for full specification)

| Attribute | Value |
|---|---|
| **Definition** | An immediate decision to exit positions triggered by kill switch conditions |
| **Strengths** | Preserves capital in extreme conditions; removes emotion from crisis response |
| **Weaknesses** | May exit at worst prices; may exit good positions along with problematic ones |
| **Appropriate Use** | Kill switch conditions only; VIX > 45, daily loss > 2%, extreme event |
| **Key Rule** | Kill switch override is constitutionally prohibited |

---

### DT-19 — EVENT-DRIVEN DECISION

| Attribute | Value |
|---|---|
| **Definition** | A decision thesis built around a specific upcoming corporate, macroeconomic, or regulatory event that is expected to be a price catalyst |
| **Core Mechanism** | Expected Event → Price Gap Assessment → Pre-Event Positioning → Event Resolution |
| **Strengths** | Defined catalyst with clear timeline; thesis has natural expiry (the event date); easier to assess thesis invalidation |
| **Weaknesses** | Binary risk if event is the opposite of expected; gap risk if event occurs overnight |
| **Appropriate Use** | Earnings announcements; policy decisions; regulatory rulings; merger completions |
| **Failure Modes** | Event does not occur; event occurs but market already priced in; event matches but market response is counter-intuitive |
| **Time Horizon** | Event-bounded; typically 5-30 days before the event |
| **Example** | "RBI Policy decision in 21 days — rate cut expected (probability 72%). Pre-policy position in rate-sensitive banking names. Time stop 2 days after policy announcement." |

---

### DT-22 — AI DECISION

| Attribute | Value |
|---|---|
| **Definition** | A decision generated and approved autonomously by the AI decision system within its delegated mandate, without requiring human deliberation |
| **Core Mechanism** | AI Reasoning Pipeline → Autonomous Decision within Mandate |
| **Strengths** | Speed; consistency; no emotional bias; always follows the defined process |
| **Weaknesses** | Cannot handle truly novel situations; dependent on quality of training; black swan susceptibility |
| **Appropriate Use** | All routine decisions within the mandate and below the human review threshold |
| **Governance** | Bounded by mandate; subject to kill switch; escalated to human for exceptions |
| **Example** | "AI Decision: Buy 2,300 HDFC Bank at market open, stop 1755, target 1940, Conviction 7.2, all gates cleared, within mandate" |

---

### DT-24 — HYBRID DECISION

| Attribute | Value |
|---|---|
| **Definition** | A decision where AI generates the recommendation and human governance provides final approval — combining the analytical depth of AI with the judgment and accountability of human oversight |
| **Core Mechanism** | AI Analysis → AI Recommendation → Human Review → Human Approval or Override |
| **Strengths** | Best of both: AI analytical depth and human judgment; clear accountability |
| **Weaknesses** | Slower than pure AI; human may introduce bias; human approval may become rubber stamp |
| **Appropriate Use** | Decisions above the autonomous approval threshold; novel situations; large positions |
| **Key Rule** | Human review must be genuine, not a rubber stamp; human must specifically confirm they reviewed the evidence |
| **Example** | "AI recommends: Buy NIFTY ETF, 4% portfolio, Conviction 7.8. Human review: confirmed macro context; adjusted size to 3.5% given correlation with existing banking positions. Approved at 3.5%." |

---

### DT-28 — ADAPTIVE DECISION

| Attribute | Value |
|---|---|
| **Definition** | A decision type that modifies its own parameters and structure based on accumulated outcome feedback — the decision learns from itself |
| **Core Mechanism** | Decision Outcome → Performance Measurement → Parameter Update → Improved Future Decision |
| **Strengths** | Continuous self-improvement; responds to changing market conditions; calibrates to actual accuracy |
| **Weaknesses** | Risk of over-fitting to recent history; may adapt too quickly or too slowly |
| **Appropriate Use** | All decision types incorporate adaptive elements; the adaptive decision makes the adaptation itself explicit and governed |
| **Governance** | Adaptation changes require evidence from >= 30 decisions; committee review for threshold changes |
| **Example** | "Adaptive update: earnings-beat threshold lowered from +5% to +4% for banking sector after analysis of 47 outcomes showing significant excess returns begin at 4% beat" |


---

## PART V — THE COMPLETE DECISION PIPELINE

*The full investment decision pipeline — from raw information arriving at the system boundary to portfolio update, outcome realization, and knowledge update. Every stage is documented, sequenced, and governed. No stage may be bypassed.*

---

### Pipeline Overview

```
════════════════════════════════════════════════════════════════════════
                    THE COMPLETE DECISION PIPELINE
════════════════════════════════════════════════════════════════════════

STAGE 0 ─── INFORMATION ARRIVAL
              │
              │  Market data, news, filings, macro data, alternative data
              │  arrive at the system boundary via data feeds
              │  Information is timestamped and classified by type
              │
              ▼
STAGE 1 ─── OBSERVATION REGISTRATION
              │
              │  Relevant observations extracted from information stream
              │  Anomaly detection: unusual price, volume, news, filing
              │  Observations timestamped and entered in evidence queue
              │
              ▼
STAGE 2 ─── EVIDENCE CLASSIFICATION
              │
              │  Observations assessed for materiality and relevance
              │  Evidence classified: supporting, contradicting, neutral
              │  Evidence weighted: source reliability × relevance × recency
              │  Each item assigned to active hypotheses if relevant
              │
              ▼
STAGE 3 ─── HYPOTHESIS UPDATE
              │
              ├── EXISTING HYPOTHESIS: evidence added to hypothesis pool
              │     Prior conviction → Bayesian update → New conviction
              │
              └── NEW SIGNAL: if no active hypothesis for this entity
                    New hypothesis created at base rate conviction
                    Added to active hypothesis pool
              │
              ▼
STAGE 4 ─── CONVICTION CALCULATION
              │
              │  Conviction = (Supporting evidence weights − Contradicting weights)
              │               × Independence multiplier
              │               × Source diversity multiplier
              │               [Scaled to 0-10]
              │
              │  Conviction < 4.0: hypothesis archived or held at prior
              │  Conviction 4.0 – 6.4: hypothesis monitored; evidence accumulates
              │  Conviction >= 6.5: advance to recommendation creation
              │
              ▼
STAGE 5 ─── ALTERNATIVE HYPOTHESIS CHECK
              │
              │  For every conviction >= 6.5 hypothesis:
              │  Must hold at least one alternative hypothesis simultaneously
              │  Evidence evaluated against both primary and alternative
              │  Alternative reduces conviction by 0.2-0.5 based on its strength
              │
              ▼
STAGE 6 ─── RECOMMENDATION CREATION
              │
              │  Full recommendation document assembled:
              │    Entity | Direction | Entry zone | Stop level | Target |
              │    Position size (from sizing framework) | Conviction score |
              │    Evidence citations (minimum 3, all independent) |
              │    Alternative hypothesis acknowledged |
              │    Rationale narrative |
              │    Expected holding period | Risk-reward ratio |
              │
              │  Recommendation enters governance queue
              │
              ▼
STAGE 7 ─── GOVERNANCE GATE EVALUATION
              │
              ├── Gate 1: Evidence quality (>= 3 independent types, all cited)
              │     FAIL → Rejected: "Insufficient evidence"
              │
              ├── Gate 2: Conviction (>= 6.5/10)
              │     FAIL → Rejected: "Below conviction threshold"
              │
              ├── Gate 3: Risk budget (capital at risk within per-position limit)
              │     FAIL → Rejected or resized: "Exceeds risk budget"
              │
              ├── Gate 4: Portfolio constraints (sector and correlation within limits)
              │     FAIL → Rejected or resized: "Portfolio limit exceeded"
              │
              ├── Gate 5: Regime validation (strategy type appropriate for regime)
              │     FAIL → Rejected: "Strategy not validated for current regime"
              │
              └── Gate 6: Mandate compliance (entity and strategy within policy)
                    FAIL → Rejected: "Outside investment mandate"
              │
              ALL 6 PASS → Advance to approval
              ANY FAIL → Recommendation archived with rejection reason
              │
              ▼
STAGE 8 ─── MULTI-AGENT DEBATE
              │
              │  Convened for all decisions above materiality threshold
              │  (All decisions within mandate; committee for > 3% portfolio)
              │
              │  Technical Agent: price, volume, and pattern evidence
              │  Fundamental Agent: company economics and valuation
              │  Macro Agent: regime, sector, and macro context
              │  Risk Agent: downside scenarios, failure modes, risk assessment
              │  Sentiment Agent: flows, positioning, and behavioral signals
              │
              │  Devil's Advocate: mandatory opposing case
              │  Each agent: independent analysis before sharing
              │  Vote: Bull / Bear / Neutral + confidence score
              │
              ▼
STAGE 9 ─── CONVICTION AGGREGATION
              │
              │  Agent votes aggregated with accuracy-calibrated weights
              │  Agreement bonus applied if agents agree
              │  Contradiction penalty applied if agents disagree
              │  Devil's advocate reduction applied (mandatory)
              │
              │  Final conviction score calculated
              │  If final conviction >= 6.5: advance to approval
              │  If final conviction < 6.5: return to monitoring
              │
              ▼
STAGE 10 ── APPROVAL DECISION
              │
              │  Approval authority determined (individual AI vs committee)
              │  For decisions within delegated authority: auto-approved
              │  For decisions above threshold: committee convened
              │  Committee debate, vote, record
              │  Decision: APPROVED or REJECTED (with reason)
              │
              ▼
STAGE 11 ── DECISION RECORD CREATION
              │
              │  Decision ID assigned
              │  All parameters locked: entity, direction, quantity,
              │    entry zone, stop price, target price, conviction score
              │  All governance results recorded
              │  Approval documented
              │  Decision record created (DPRIM-020)
              │
              ▼
STAGE 12 ── CAPITAL RESERVATION
              │
              │  Capital system notified: reserve [amount] for Decision ID
              │  Available capital reduced by reserved amount
              │  Risk budget updated to reflect pending commitment
              │  Portfolio constraint monitors updated
              │
              ▼
STAGE 13 ── EXECUTION REQUEST
              │
              │  Execution engine receives: entity, direction, quantity,
              │    order type, price parameters, time constraints
              │  Entry trigger verified before order submission
              │  Order formatted and submitted to broker
              │  Order routing: limit vs market vs SL-order
              │
              ▼
STAGE 14 ── ORDER EXECUTION
              │
              │  Order sent to exchange
              │  Fill monitoring begins
              │  Full fill: proceed
              │  Partial fill: reassess (fill at different price than approved?)
              │  No fill: re-evaluate (decision window still valid?)
              │
              ▼
STAGE 15 ── POSITION CONFIRMATION
              │
              │  Fill confirmed: quantity, price, timestamp
              │  Capital moves from Reserved to Deployed
              │  Position record created with:
              │    Entry price (actual) | Entry time | Quantity |
              │    Stop price placed | Target price set |
              │    Conviction at entry | Thesis statement |
              │    Decision ID reference
              │
              ▼
STAGE 16 ── STOP LOSS PLACEMENT
              │
              │  Stop loss order placed immediately upon position confirmation
              │  Stop type: hard stop, trailing stop, or both
              │  Stop placement confirmed
              │  If stop cannot be placed → EMERGENCY EXIT of position
              │  (Never hold a position without a defined stop)
              │
              ▼
STAGE 17 ── ACTIVE MONITORING
              │
              │  Continuous real-time monitoring while position is open:
              │
              │  Price monitoring: Is price approaching stop or target?
              │  Thesis monitoring: Is the original thesis still intact?
              │  Evidence monitoring: Has new contradicting evidence arrived?
              │  Conviction monitoring: Is conviction score still above 4.0?
              │  Regime monitoring: Has regime changed against the thesis?
              │  Time monitoring: Is the holding period approaching expiry?
              │
              ├── Stop hit → Trigger STAGE 18 (forced exit)
              ├── Target hit → Trigger STAGE 18 (planned exit)
              ├── Thesis invalidated → Trigger STAGE 18 (conviction exit)
              ├── Time stop → Trigger STAGE 18 (time exit)
              ├── Kill switch → Trigger STAGE 18 (emergency exit)
              └── Still within parameters → Continue monitoring
              │
              ▼
STAGE 18 ── EXIT TRIGGER AND DECISION
              │
              │  Exit type recorded: Stop / Target / Thesis / Time / Emergency
              │  For forced exits (stop, kill switch): immediate market order
              │  For planned exits (target, conviction): limit order or market
              │  Exit order created and submitted
              │
              ▼
STAGE 19 ── EXIT EXECUTION
              │
              │  Exit order sent to exchange
              │  Fill confirmed: quantity, price, timestamp
              │  Capital released from Deployed to Available
              │  Risk budget released
              │  Position record closed
              │
              ▼
STAGE 20 ── OUTCOME CALCULATION
              │
              │  P&L calculated: Exit price − Entry price × Quantity
              │  Transaction costs deducted
              │  Net realized return calculated
              │  Portfolio impact updated
              │  Attribution recorded: which strategy, sector, decision type
              │
              ▼
STAGE 21 ── LEARNING RECORD CREATION
              │
              │  Learning record (DPRIM-018) created with:
              │    Entry conviction vs actual outcome
              │    Evidence item accuracy (each item credited or discounted)
              │    Exit timing quality assessment
              │    Position sizing quality assessment
              │    Thesis accuracy assessment
              │    Process adherence score
              │    Key lessons identified
              │
              ▼
STAGE 22 ── KNOWLEDGE UPDATE
              │
              │  Evidence item weights updated (accurate items +; inaccurate −)
              │  Strategy performance metrics updated (win rate, avg return)
              │  Agent accuracy records updated
              │  Conviction calibration checked and updated
              │  New knowledge item created if threshold of confirming instances met
              │  Contradicting knowledge item reassessed
              │
              ▼
CYCLE COMPLETE — SYSTEM READY FOR NEXT OPPORTUNITY

════════════════════════════════════════════════════════════════════════
```

---

### Pipeline Stage Timing Guidelines

| Stage | Target Duration | Notes |
|---|---|---|
| Information Arrival | Continuous | Real-time feed; latency < 100ms from market event |
| Observation Registration | < 200ms | Threshold-based trigger; anomaly detection parallel |
| Evidence Classification | < 500ms per item | Relevance scoring against active hypotheses |
| Hypothesis Update | < 300ms | Bayesian update computation |
| Conviction Calculation | < 500ms | Evidence aggregation; weight application |
| Alternative Hypothesis Check | < 1 second | Against pre-maintained alternative set |
| Recommendation Creation | 2-10 minutes | Parameter calculation; document assembly |
| Gate 1 (Evidence) | < 30 seconds | Automated citation check |
| Gate 2 (Conviction) | < 5 seconds | Threshold comparison |
| Gate 3 (Risk Budget) | < 15 seconds | Capital and risk budget query |
| Gate 4 (Portfolio) | < 15 seconds | Concentration and correlation check |
| Gate 5 (Regime) | < 10 seconds | Regime registry lookup |
| Gate 6 (Mandate) | < 10 seconds | Policy compliance check |
| Multi-Agent Debate | 3-15 minutes | Depends on decision complexity |
| Conviction Aggregation | < 1 minute | Vote weighting and calculation |
| Approval Decision | < 5 minutes auto; 30 min committee | Depends on authority tier |
| Decision Record Creation | < 1 minute | Automated document assembly |
| Capital Reservation | < 10 seconds | Capital system API call |
| Order Execution | Market-dependent | Target < 1 second for market orders |
| Position Confirmation | < 5 seconds post-fill | Automated on fill event |
| Stop Loss Placement | < 30 seconds post-fill | Immediate; cannot be delayed |
| Monitoring (continuous) | Real-time throughout | 24x7 while market open and positions open |
| Exit Execution | Immediate for forced; market for planned | Target < 30 seconds for forced exit |
| Outcome Calculation | < 5 minutes post-exit | Automated calculation |
| Learning Record Creation | < 15 minutes post-exit | Structured but requires some analysis |
| Knowledge Update | < 30 minutes post-learning | Batch update after learning record |

---

### Pipeline State Diagram

```
                    ┌──────────────────────────────┐
                    │      INFORMATION ARRIVES      │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     MATERIALITY FILTER        │
                    └──────────────┬───────────────┘
                                   │
              ┌────────────────────┼──────────────────────┐
              │ Not material       │ Material              │ High Anomaly
              │                    │                       │
              ▼                    ▼                       ▼
        ┌──────────┐       ┌──────────────┐        ┌────────────────┐
        │ DISCARD  │       │  HYPOTHESIS  │        │  NEW HYPOTHESIS│
        │          │       │  UPDATE      │        │  CREATED       │
        └──────────┘       └──────┬───────┘        └──────┬─────────┘
                                  │                       │
                                  └──────────┬────────────┘
                                             │
                               ┌─────────────▼──────────────┐
                               │    CONVICTION CALCULATION   │
                               └─────────────┬──────────────┘
                                             │
                    ┌────────────────────────┼──────────────────────────┐
                    │ < 4.0                  │ 4.0 – 6.4                │ >= 6.5
                    │                        │                          │
                    ▼                        ▼                          ▼
             ┌────────────┐          ┌────────────────┐         ┌────────────────┐
             │  ARCHIVED  │          │ MONITORING     │         │ RECOMMENDATION │
             │            │          │ (accumulate    │         │ CREATED        │
             └────────────┘          │ more evidence) │         └────────┬───────┘
                                     └────────────────┘                  │
                                                                          │
                                                              ┌───────────▼──────────┐
                                                              │  GOVERNANCE GATES    │
                                                              │  (All 6 must pass)   │
                                                              └───────────┬──────────┘
                                                                          │
                                                         ┌────────────────┼──────────────────┐
                                                         │ Any gate fails │ All gates pass    │
                                                         │                │                   │
                                                         ▼                ▼                   │
                                                  ┌────────────┐  ┌─────────────────┐        │
                                                  │  REJECTED  │  │  MULTI-AGENT    │        │
                                                  │  (reason   │  │  DEBATE         │        │
                                                  │   recorded)│  └────────┬────────┘        │
                                                  └────────────┘           │                 │
                                                                            │                 │
                                                              ┌─────────────▼──────────┐      │
                                                              │   CONVICTION >= 6.5?   │      │
                                                              └─────────────┬──────────┘      │
                                                                            │                 │
                                                       ┌────────────────────┤                 │
                                                       │ No                 │ Yes             │
                                                       ▼                    ▼                 │
                                                ┌────────────┐     ┌────────────────┐        │
                                                │  RETURN TO │     │  APPROVAL      │        │
                                                │  MONITORING│     │  DECISION      │        │
                                                └────────────┘     └────────┬───────┘        │
                                                                            │                 │
                                                              ┌─────────────▼──────────┐      │
                                                              │  APPROVED?             │      │
                                                              └─────────────┬──────────┘      │
                                                                            │                 │
                                                         ┌──────────────────┤                 │
                                                         │ Rejected         │ Approved        │
                                                         ▼                  ▼                 │
                                                  ┌────────────┐  ┌──────────────────┐       │
                                                  │ ARCHIVED   │  │  CAPITAL         │       │
                                                  │            │  │  RESERVATION +   │       │
                                                  └────────────┘  │  EXECUTION       │       │
                                                                   └────────┬─────────┘       │
                                                                            │                 │
                                                              ┌─────────────▼──────────┐      │
                                                              │  POSITION MONITORING   │      │
                                                              └─────────────┬──────────┘      │
                                                                            │                 │
                                                              ┌─────────────▼──────────┐      │
                                                              │  EXIT TRIGGERED        │      │
                                                              └─────────────┬──────────┘      │
                                                                            │                 │
                                                              ┌─────────────▼──────────┐      │
                                                              │  OUTCOME + LEARNING    ├──────┘
                                                              │  (feeds back to        │
                                                              │   evidence weights)    │
                                                              └────────────────────────┘
```

---

### Special Pipeline: The Kill Switch Protocol

When kill switch conditions are triggered:

```
KILL SWITCH CONDITION DETECTED
(VIX > 45 OR Daily Portfolio Loss > 2%)
          │
          ▼
STEP 1: ALL PENDING DECISIONS — CANCELLED IMMEDIATELY
          │
          ▼
STEP 2: ALL OPEN POSITIONS — EXIT AT MARKET PRICE
          Priority order: Largest position first
          Method: Market orders for speed
          All orders submitted within 60 seconds of trigger
          │
          ▼
STEP 3: ALL RESERVED CAPITAL — RELEASED
          Portfolio moves to maximum cash position
          │
          ▼
STEP 4: ALL NEW RECOMMENDATIONS — BLOCKED
          Conviction gate temporarily raised to 9.5/10
          Only absolute emergency entries permitted
          │
          ▼
STEP 5: INCIDENT RECORD CREATED
          Kill switch type recorded
          All exited positions documented with P&L
          Market conditions at trigger recorded
          │
          ▼
STEP 6: POST-EMERGENCY REVIEW (within 24 hours)
          Was trigger appropriate?
          Could earlier action have prevented the trigger?
          What can be learned for future risk management?
          │
          ▼
STEP 7: GRADUAL RE-ENTRY PROTOCOL
          Conditions required to return to normal operations:
          VIX below 30 for 2 consecutive days
          Portfolio drawdown recovery to -1.5% or better
          Fresh conviction assessment on all previous positions
          Staged re-deployment: 25% of normal sizing initially
```

---

## PART VI — PORTFOLIO DECISION GOVERNANCE

*The complete governance architecture — the structure of authority, responsibility, and control that ensures all decisions are made at the appropriate level, with the appropriate oversight, and with full accountability.*

---

### The Governance Architecture

```
═══════════════════════════════════════════════════════════════════════
                 PORTFOLIO DECISION GOVERNANCE ARCHITECTURE
═══════════════════════════════════════════════════════════════════════

TIER 1 — HUMAN OVERSIGHT (Ultimate Authority)
┌─────────────────────────────────────────────────────────────────────┐
│  HUMAN PRINCIPAL                                                     │
│  Authority: All decisions; can override any AI decision              │
│  Mandatory for: Kill switch override (prohibited); mandate changes   │
│  Review cadence: Weekly portfolio review; ad-hoc for exceptions     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
TIER 2 — INVESTMENT COMMITTEE (Strategic Decisions)
┌─────────────────────────────────────────────────────────────────────┐
│  INVESTMENT COMMITTEE                                                │
│  Composition: Chief AI Agent + 5 Specialist Agents                  │
│  Authority: Decisions > 3% of portfolio; strategy activation        │
│  Quorum: Minimum 4 agents; majority vote                            │
│  Review cadence: Convened on trigger (large decision, novel event)  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
TIER 3 — RISK COMMITTEE (Risk Governance)
┌─────────────────────────────────────────────────────────────────────┐
│  RISK COMMITTEE                                                      │
│  Composition: Risk Agent + Macro Agent + Chief Agent                 │
│  Authority: Risk gate evaluations; kill switch activation;           │
│             position limit changes; regime assessment                │
│  Veto power: Can block any decision on risk grounds                  │
│  Review cadence: Daily risk summary; real-time on kill switch event │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
TIER 4 — AI AUTONOMOUS (Routine Decisions)
┌─────────────────────────────────────────────────────────────────────┐
│  AI DECISION SYSTEM (Delegated Authority)                            │
│  Authority: Decisions within mandate; position <= 3% of portfolio   │
│  Autonomous approval: All 6 gates cleared; within delegated limits  │
│  Escalation triggers: Any gate failure; position > 3%; novel type   │
│  Monitoring: All autonomous decisions reviewed in weekly summary    │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Decision Authority Matrix

| Decision Type | Size Tier | Required Authority | Escalation Trigger |
|---|---|---|---|
| Entry: Standard | <= 1% portfolio | Autonomous AI | Gate failure |
| Entry: Medium | 1-3% portfolio | Autonomous AI + Risk Gate | Any flag |
| Entry: Large | 3-5% portfolio | Investment Committee | Always |
| Entry: Very Large | > 5% portfolio | Investment Committee + Human | Always |
| Exit: Stop Loss | Any | Automatic (rule-based) | None needed |
| Exit: Target | Any | Automatic (rule-based) | None needed |
| Exit: Conviction | Any | Autonomous AI | None |
| Exit: Thesis | Any | Autonomous AI + Record | None |
| Emergency Exit | Any | Kill Switch (automatic) or Human | None |
| Strategy Activation | Any | Investment Committee | Always |
| Capital Allocation | Any | Investment Committee | Always |
| Mandate Change | Any | Human Principal | Always |
| Override | Any | Human Principal | Always |
| Kill Switch | N/A | Automatic | N/A |

---

### Portfolio Constraint Framework

```
═══════════════════════════════════════════════════════════════════
                     PORTFOLIO CONSTRAINTS
═══════════════════════════════════════════════════════════════════

POSITION LIMITS (per individual position)
──────────────────────────────────────────────────────────────────
Maximum position size:         5% of total portfolio
Standard position range:       0.5% – 3% of total portfolio
Minimum position size:         0.5% (below is not worth the governance)
Capital at risk per position:  Maximum 2% of total portfolio

SECTOR LIMITS (per SEBI sector classification)
──────────────────────────────────────────────────────────────────
Maximum single sector:         30% of total portfolio
Target single sector:          10-20% for high-conviction
Minimum diversification:       At least 4 sectors represented at all times

CORRELATION LIMITS
──────────────────────────────────────────────────────────────────
Maximum pairwise correlation:  0.75 between any two active positions
Maximum portfolio beta:        1.3 in trending regime; 0.8 in uncertain
Correlation cluster limit:     No more than 40% in highly correlated group

DRAWDOWN LIMITS
──────────────────────────────────────────────────────────────────
Daily portfolio loss limit:    2% — triggers kill switch review
Weekly portfolio loss limit:   5% — triggers Investment Committee review
Monthly portfolio loss limit:  8% — triggers strategy overhaul
Annual maximum drawdown:       15% — triggers full portfolio reconstruction

DEPLOYMENT LIMITS
──────────────────────────────────────────────────────────────────
Minimum cash buffer:           10% at all times (non-deployable)
Minimum liquidity reserve:     5% for opportunistic deployment
Maximum deployment:            85% of total portfolio (leaves 15% buffer)
Standard target deployment:    65-75% of total portfolio

POSITION COUNT LIMITS
──────────────────────────────────────────────────────────────────
Minimum concurrent positions:  5 (prevents over-concentration)
Maximum concurrent positions:  20 (prevents over-diversification)
Standard optimal range:        8-15 concurrent positions

LEVERAGE LIMITS (if applicable)
──────────────────────────────────────────────────────────────────
Maximum gross leverage:        1.5x (50% borrowed capital)
Maximum net directional:       1.2x long or 0.5x short
Derivatives (options) max:     20% of portfolio in premium
═══════════════════════════════════════════════════════════════════
```

---

### Governance Review Calendar

| Review Type | Frequency | Scope | Authority |
|---|---|---|---|
| Real-Time Monitoring | Continuous | All active positions | Automated + Risk System |
| Daily Risk Summary | Every trading day close | Portfolio risk metrics; kill switch check | Risk Committee |
| Weekly Portfolio Review | Every Friday | All positions; thesis validation; conviction refreshes | Investment Committee |
| Monthly Strategy Review | First Monday of month | Strategy performance; capital allocation; sector allocation | Investment Committee |
| Quarterly Calibration | End of each quarter | Agent accuracy; conviction calibration; evidence weight update | Full Committee |
| Regime Review | As needed (minimum monthly) | Market regime assessment; strategy activation changes | Risk Committee |
| Annual Architecture Review | January each year | Decision architecture; mandate review; long-term strategy | Human Principal |
| Emergency Review | Immediately on trigger | Kill switch event; major loss; governance failure | Human Principal |

---

### Conflict Resolution Protocol

```
CONFLICT DETECTED (two decisions competing for same capital or risk budget)
          │
          ▼
STEP 1: IDENTIFY CONFLICT TYPE
          │
          ├── Same capital: two approved decisions exceed available capital
          │
          ├── Same sector: two decisions would push sector over limit
          │
          └── Correlation conflict: two decisions are highly correlated
          │
          ▼
STEP 2: COMPARE CONVICTION SCORES
          Higher conviction decision takes priority
          If equal conviction: compare reward-to-risk ratios
          If equal R:R: compare evidence freshness
          │
          ▼
STEP 3: CHECK PORTFOLIO IMPACT
          Which decision adds more diversification value?
          Which decision better aligns with portfolio strategy?
          │
          ▼
STEP 4: ARBITRATION
          If still unresolved: Chief Intelligence Agent decides
          Human override available at any stage
          Decision and reason recorded permanently
          │
          ▼
STEP 5: LOWER-PRIORITY DECISION HANDLING
          Option A: Defer to next available capital slot
          Option B: Resize to fit within remaining capacity
          Option C: Reject with option to re-evaluate
```

---

### Decision Escalation Framework

| Trigger Condition | From | To | Required Action |
|---|---|---|---|
| Position size > 3% | AI Autonomous | Investment Committee | Full debate + vote |
| Novel strategy type | AI Autonomous | Investment Committee | Strategy review + pilot |
| Any governance gate failure | AI Autonomous | Rejection + Review | Reason recorded |
| Agent deadlock (tied vote) | AI Committee | Chief AI Agent | Arbitration |
| Chief AI uncertainty | Chief AI Agent | Human Principal | Human deliberation |
| Kill switch trigger | Automatic | Risk Committee + Human | Emergency protocol |
| Mandate boundary question | Any tier | Human Principal | Policy clarification |
| Post-mortem reveals systemic issue | Learning System | Investment Committee | Architecture review |
| Quarterly calibration deviation > 15% | Calibration System | Investment Committee | Recalibration + review |


---

## PART VII — RISK–REWARD FRAMEWORK

*The conceptual architecture of how risk, return, probability, and conviction interact to produce decision quality — the intellectual foundation of every investment decision made by the system.*

---

### The Three Pillars of Decision Quality

Every investment decision is evaluated on three pillars. A decision that fails any pillar is not a high-quality decision regardless of how well it scores on the other two.

```
═══════════════════════════════════════════════════════════════
              THE THREE PILLARS OF DECISION QUALITY
═══════════════════════════════════════════════════════════════

PILLAR 1                PILLAR 2                PILLAR 3
EVIDENCE QUALITY   ×   RISK MANAGEMENT   ×   PORTFOLIO FIT
                                                               
"Is the thesis      "Is the downside      "Does this decision
 well-supported?"   bounded and within     fit the portfolio
                    the budget?"           strategy?"
                                                               
Evidence count      Stop loss defined      Sector within limits
Evidence weight     Capital at risk        Correlation managed
Conviction score    Risk budget check      Deployment rate
Independence        Max loss bounded       Diversity value
Freshness           VaR impact             Strategy alignment
                                                               
MINIMUM STANDARD:   MINIMUM STANDARD:     MINIMUM STANDARD:
Conviction >= 6.5   Capital at risk        All portfolio
3 independent       < 2% of portfolio      constraints met
evidence types      Stop defined before    All gates passed
                    entry (unconditional)
═══════════════════════════════════════════════════════════════
```

---

### The Risk-Reward Relationship

The fundamental investment equation is not simply "maximize return" — it is "maximize risk-adjusted return." Every decision involves a trade-off between the potential reward and the risk of loss. The architecture governs this trade-off through the following principles:

**Principle: Reward Must Justify Risk**
The minimum reward-to-risk ratio for any approved decision is 2:1 — for every 1 unit of capital at risk (the stop loss distance), the expected reward must be at least 2 units. This ensures that even with a 50% win rate, the system is profitable on expectation.

**Principle: Probability Matters**
A 2:1 reward-to-risk ratio with 60% probability of success is mathematically superior to a 3:1 ratio with 40% probability. The system evaluates both dimensions simultaneously — not just the ratio of potential returns.

**Principle: Expected Value Is the Foundation**
Expected Value = (Win Rate × Average Win) − (Loss Rate × Average Loss)

A positive expected value, after transaction costs, is the minimum threshold for any approved decision. The system is not in the business of hoping — it is in the business of making decisions with positive expected value.

**Principle: Risk Budget Is Non-Negotiable**
No matter how attractive the expected return, if a decision would exceed the risk budget, it is either resized or rejected. The risk budget is the total drawdown capacity available at the portfolio level. Individual decisions draw from this budget — when it is consumed, no new decisions may be made.

**Principle: Conviction Is the Multiplier**
Conviction does not change the expected value of a decision — it changes the appropriate position size. Higher conviction earns a larger position (up to the mandate limit). Lower conviction earns a smaller position. The conviction score is the multiplier that translates edge into appropriate capital commitment.

---

### Conceptual Position Sizing Framework

Position sizing is not about how much the decision-maker wants to own. It is about how much capital the evidence quality justifies, subject to risk constraints. The conceptual hierarchy is:

```
STEP 1 — START WITH MAXIMUM PERMITTED SIZE
          (portfolio mandate sets the ceiling)
                    │
                    ▼
STEP 2 — APPLY CONVICTION SCALING
          Conviction 6.5 → 50% of maximum
          Conviction 7.0 → 65% of maximum
          Conviction 7.5 → 80% of maximum
          Conviction 8.0 → 100% of maximum
                    │
                    ▼
STEP 3 — APPLY VOLATILITY ADJUSTMENT
          High VIX environment → Scale down by 0-50%
          Normal volatility → No adjustment
          Low volatility → No adjustment (VIX is asymmetric)
                    │
                    ▼
STEP 4 — APPLY PORTFOLIO CONSTRAINT CHECK
          If sector would exceed limit → Reduce to fit
          If correlation would exceed limit → Reduce
          If deployment would exceed 85% → Reduce
                    │
                    ▼
STEP 5 — VERIFY CAPITAL AT RISK
          (Entry price − Stop price) / Entry price × Position size
          Must be <= 2% of total portfolio
          If > 2%: Reduce position size OR widen stop (widen with care)
                    │
                    ▼
FINAL — APPROVED POSITION SIZE
```

---

### The Risk Budget Conceptual Model

```
TOTAL RISK BUDGET = Maximum Acceptable Portfolio Drawdown
                   (Example: 15% of portfolio value)

RISK BUDGET IS CONSUMED BY:
──────────────────────────────────────────────────────
Position 1 (2.0% capital at risk) → Uses 13% of budget
Position 2 (1.5% capital at risk) → Uses 10% of budget
Position 3 (1.8% capital at risk) → Uses 12% of budget
Position 4 (2.0% capital at risk) → Uses 13% of budget
...continuing...

RISK BUDGET CONSUMPTION:
   Used: Sum of all capital at risk across positions
   Available: Total budget minus consumed
   Ceiling: When available budget < minimum position size,
            no new decisions may be approved

ADDITIONAL RISK DIMENSIONS:
   Correlation amplifier: Correlated positions consume
      more of the effective risk budget than uncorrelated
   Volatility amplifier: High-VIX periods consume
      more risk budget per unit of nominal exposure
   Regime amplifier: Trending-to-sideways transition
      increases effective risk of momentum positions
```

---

### Tail Risk Architecture

Tail risk — extreme losses beyond the normal distribution's prediction — requires specific architectural provisions beyond standard risk management:

**Black Swan Protocol:**
The system does not assume that because a black swan has not occurred recently, one cannot occur. The kill switch is calibrated to protect against tail events. Position sizes are deliberately conservative (Half-Kelly) to ensure that even the worst-case scenario of multiple simultaneous stop-loss hits does not exhaust the capital floor.

**Scenario-Based Tail Assessment:**
Before any decision above 2% portfolio size is approved, a tail scenario is required: "What happens to this position and the portfolio if the 5th-percentile outcome occurs?" If the 5th-percentile outcome would trigger the kill switch, the decision is either resized or requires human review.

**Correlation Breakdown Awareness:**
In stress scenarios, correlations between asset classes typically increase toward 1.0 — assets that appeared diversified become correlated. The portfolio architecture accounts for this by maintaining a diversification reserve: even in the worst-case correlation scenario, no single catalyst should be able to simultaneously impair more than 30% of portfolio value.

---

### Decision Quality Dimensions

| Dimension | What Is Measured | Quality Indicator |
|---|---|---|
| Evidence Quality | Number and independence of evidence items | >= 3 independent; high source reliability |
| Conviction Quality | How well conviction reflects actual accuracy | Calibration curve alignment |
| Timing Quality | Entry and exit timing relative to optimal | Percentage of theoretical maximum captured |
| Sizing Quality | Position size relative to the evidence-justified size | Neither over nor under the conviction-calibrated amount |
| Exit Discipline | Adherence to pre-defined exit rules | Stop honored unconditionally; target respected |
| Governance Quality | Completeness of governance process | All 6 gates completed; debate conducted; record created |
| Thesis Accuracy | Was the original thesis directionally correct? | The process metric — separate from P&L |
| Learning Quality | Quality of the learning record created | Specific lessons; evidence item updates; calibration inputs |

---

### Opportunity Cost Architecture

Every deployed position has an implicit opportunity cost — the return that could have been earned on an alternative use of the same capital. The decision architecture addresses opportunity cost through:

**Capital Rotation Reviews:** Weekly assessment of whether deployed capital is still in its best use compared to new high-conviction opportunities. If a new opportunity has significantly higher expected value than an existing position, the portfolio may rotate.

**Minimum Return Threshold:** Every open position must justify its continued holding on a going-forward basis. The question is not "did this decision make sense when we entered?" but "does holding make sense from now?" The sunk cost of entry is irrelevant to the hold-or-exit decision.

**Idle Capital Penalty:** Capital sitting in cash beyond the minimum buffer is not neutral — it has an opportunity cost. The system tracks the deployment rate and generates decision opportunities proactively to ensure capital is working.

---

## PART VIII — DECISION FAILURE MODES

*A comprehensive taxonomy of how investment decisions fail — and the system's detection, mitigation, and recovery protocols for each mode.*

---

### Decision Failure Mode Taxonomy

| Code | Failure Mode | Category | Severity | Detectability | Primary Mitigation |
|---|---|---|---|---|---|
| DFM-01 | Overtrading | Behavioral | High | Moderate | Decision frequency monitoring; transaction cost tracking |
| DFM-02 | Undertrading | Behavioral | High | Moderate | Opportunity pipeline audit; conviction deployment tracking |
| DFM-03 | Late Entry | Timing | High | Moderate | Entry conviction freshness check; decision window enforcement |
| DFM-04 | Early Exit | Exit Discipline | High | Moderate | Pre-committed targets; exit rule enforcement |
| DFM-05 | Late Exit — Holding Losers | Exit Discipline | Critical | Moderate | Unconditional stop loss; thesis validity monitoring |
| DFM-06 | Premature Profit Taking | Exit Discipline | High | Low | Trailing stop discipline; target enforcement |
| DFM-07 | Overconfidence | Calibration | Critical | Low | Calibration monitoring; conviction threshold discipline |
| DFM-08 | Decision Paralysis | Behavioral | High | Moderate | Decision window with expiry; conviction threshold |
| DFM-09 | Analysis Paralysis | Behavioral | High | Moderate | Decision window enforcement; imperfect information acceptance |
| DFM-10 | Confirmation Bias in Decisions | Cognitive | Critical | Low | Devil's advocate; mandatory contradiction seeking |
| DFM-11 | Sunk Cost Violation | Cognitive | Critical | Moderate | Thesis-based exit rule; P&L-independent exit criteria |
| DFM-12 | Ignoring Stop Loss | Risk | Critical | Low | Unconditional stop rule; automatic stop orders |
| DFM-13 | Regime Blindness | Systemic | Critical | Low | Mandatory regime check at every decision |
| DFM-14 | Ignoring Liquidity | Risk | High | Moderate | Pre-entry liquidity check; position size vs daily volume |
| DFM-15 | Position Oversizing | Risk | Critical | Moderate | Conviction-calibrated sizing; capital at risk limit |
| DFM-16 | Portfolio Concentration | Systemic | Critical | Moderate | Sector and correlation limits; portfolio constraint gates |
| DFM-17 | Capital Exhaustion | Systemic | Critical | Moderate | Cash buffer requirement; deployment rate monitoring |
| DFM-18 | Revenge Decision | Behavioral | Critical | Moderate | Post-loss cooling period; emotion detection |
| DFM-19 | Decision Drift | Systemic | High | Low | Architecture audit; process adherence monitoring |
| DFM-20 | Governance Bypass | Governance | Critical | Moderate | Unconditional gate enforcement; audit trail |
| DFM-21 | Committee Deadlock | Process | High | Moderate | Quorum rules; deadlock resolution protocol |
| DFM-22 | AI Hallucination in Decisions | AI | Critical | Moderate | Mandatory evidence citation; citation verification |
| DFM-23 | Wrong Objective | Strategic | Critical | Low | Clear mandate definition; decision quality score |
| DFM-24 | False Conviction | Evidence | Critical | Low | Independence check; correlation-adjusted conviction |
| DFM-25 | Stale Decision | Temporal | High | Moderate | Decision window expiry; freshness check at execution |
| DFM-26 | Recency Chasing | Behavioral | High | Low | Evidence quality weight vs recency bias check |
| DFM-27 | Averaging Down | Risk | Critical | Moderate | No-averaging rule; thesis invalidation exit |
| DFM-28 | Stop Dilation | Risk | Critical | Low | Stop migration rules; stop move audit |

---

### Detailed Failure Mode Analysis

#### DFM-05 — HOLDING LOSERS (Violation of Stop Loss Discipline)

**Description:** A losing position is maintained beyond the pre-defined stop loss level, allowing losses to accumulate beyond the mandated maximum. Often accompanied by rationalization: "I still believe in the thesis" or "it will come back."

**Why It Occurs:**
- Loss aversion: the pain of realizing a loss is greater than the pain of the same unrealized loss
- Sunk cost fallacy: "I have already lost so much, I cannot exit now"
- Hope: the belief that the position will recover without new evidence
- Ego protection: exiting at a loss feels like admitting a mistake

**Detection Methods:**
- Price-based: monitoring system flags when position price crosses stop level
- Conviction-based: conviction score below 4.0 triggers exit recommendation
- Time-based: review cadence ensures positions are evaluated, not just held
- Pattern detection: if same entity has been held through multiple consecutive losses, flag for behavioral audit

**Mitigation:**
- Unconditional stop loss rule: the stop loss cannot be overridden by any reasoning argument once triggered
- Automatic stop orders: stop orders are pre-placed at the exchange level — the system executes without deliberation
- Exit rule: "Thesis invalidation" is a separate and independent exit trigger — the market price of the stop loss and the thesis validity are both independent exit conditions

**Recovery:**
- When detected: immediate exit regardless of current P&L
- Post-mortem: mandatory behavioral audit
- Pattern: if the same agent or decision source repeatedly produces this failure, weight reduction applied

---

#### DFM-07 — OVERCONFIDENCE IN DECISIONS

**Description:** The system approves decisions at conviction levels that are not supported by the actual quality of evidence, leading to positions that are larger than the evidence justifies.

**Why It Occurs:**
- Small sample of recent successes inflates confidence
- Narrative coherence of the thesis creates an illusion of certainty
- Evidence items from the same causal source are counted as independent
- The system has not been calibrated against enough outcomes in the current regime

**Detection Methods:**
- Calibration monitoring: compare stated conviction level against actual win rate for that conviction tier
- Correlation audit: verify that evidence items cited as independent are causally independent
- Sample size check: conviction above 7.5 requires >= 5 independent evidence items, not 3
- Post-mortem clustering: multiple similar failures in the same period signal systematic overconfidence

**Mitigation:**
- Calibration requirement: conviction scores are discounted if calibration error exceeds 10% in the current regime
- Independence check: evidence items from the same sector, same news source, or same cause are counted as 1, not multiple
- Devil's advocate reduction: mandatory 0.3-0.7 reduction from devil's advocate argument, regardless of conviction level

**Recovery:**
- When detected: apply overconfidence correction factor for the affected decision type
- Scale down all positions in affected category by 25% until recalibration
- Trigger full calibration audit across all conviction tiers

---

#### DFM-11 — SUNK COST VIOLATION

**Description:** A decision to hold a position is made based on the capital already committed (sunk cost) rather than on the current quality of the thesis. The investor refuses to exit because "I cannot afford to take this loss."

**Why It Occurs:**
- Mental accounting: capital that has been "spent" on a losing position feels like it would be wasted if exited
- Ego: exiting at a loss is experienced as admitting the decision was wrong
- Hope: the belief that the position will recover to entry price even without supporting evidence
- Framing: the loss feels permanent only when it is realized — while unrealized, it still feels like a chance to recover

**Detection Methods:**
- Exit rule monitoring: has the thesis been invalidated? Was the stop hit? If yes and position is still open → sunk cost violation in progress
- Conviction tracking: is the hold decision based on current conviction (>= 4.0) or on the original entry conviction that may no longer be valid?
- Behavioral audit: when exit decisions are consistently delayed for losing positions relative to winning positions, the disposition effect is active

**Mitigation:**
- Constitutional principle: every hold decision requires reconfirmed current conviction — not a reference to entry conviction
- The thesis validity is evaluated against current evidence, not the thesis as it was at entry
- Mandatory question in every hold review: "If this position did not exist and I had this cash free today, would I open this position at this price with this evidence?" If no → exit

**Recovery:**
- When detected: immediate exit review
- The position is evaluated entirely on forward-looking thesis and current conviction
- Any reference to "I need it to get back to my entry price" is flagged as behavioral contamination

---

#### DFM-15 — POSITION OVERSIZING

**Description:** A position is opened or maintained at a size larger than the conviction level and risk budget justify, creating exposure that exceeds the maximum loss the portfolio can absorb from this single decision.

**Why It Occurs:**
- Overconfidence causes the conviction-calibrated size to feel too small
- High-conviction moments feel like certainties that justify maximum commitment
- The magnitude of the expected return makes the risk feel small relative to the opportunity
- Kelly's formula is applied without appropriate conservatism

**Detection Methods:**
- Pre-entry: capital at risk calculation > 2% of portfolio triggers automatic rejection
- Pre-entry: conviction < 8.0 with full position size triggers automatic review
- Post-entry: periodic audit of all positions for sizing appropriateness relative to current conviction

**Mitigation:**
- Hard mandate limit: maximum position size is 5% of portfolio, unconditional
- Conviction-calibrated ceiling: conviction 6.5 → 50% of maximum, not 100%
- Half-Kelly rule: never commit more than Half-Kelly to any single decision
- Automatic block: position sizing calculation is built into the recommendation document; oversized recommendations are rejected at the source

**Recovery:**
- When detected: immediate review and potential position reduction to mandate-compliant level
- The reduction does not change the thesis — just the size
- Learning record: oversizing failure recorded; contributes to behavioral bias profile

---

#### DFM-18 — REVENGE DECISION

**Description:** After a significant loss, an immediate new decision is made to "win back" the lost capital — not because evidence supports the decision, but because of the emotional need to recover quickly.

**Why It Occurs:**
- Loss aversion creates pressure to restore the previous capital level immediately
- Emotional state following a loss reduces rational decision-making capacity
- The "hot hand" fallacy in reverse: "I need to win now to prove the loss was bad luck"
- Activity bias: doing something feels better than accepting the loss and waiting

**Detection Methods:**
- Temporal pattern: any new entry within 4 hours of a stop-loss exit on the same entity triggers review
- Entity pattern: re-entry into the just-stopped-out position without the required 24-hour minimum gap
- Sequence pattern: if 3+ stop-loss exits occur in one day, any new entries that day are flagged for behavioral review

**Mitigation:**
- Mandatory cooling period: 24 hours minimum after any stop-loss exit before a new entry into the same entity
- Heightened threshold: conviction requirement increased to 7.5 for any decision made within 2 hours of a stop-loss exit
- Process check: the recommendation document must certify it is not motivated by loss recovery

**Recovery:**
- When detected: the pending decision is held for 24-hour review before any execution
- Mandatory question: "Would this decision have the same conviction score if I had not just taken a loss?"
- Learning record documents the behavioral pattern

---

#### DFM-27 — AVERAGING DOWN

**Description:** Adding to a losing position by purchasing additional shares at a lower price, in order to reduce the average entry cost — when the original thesis has been weakened or invalidated by the price move itself.

**Why It Occurs:**
- The lower price feels like a better value than the original entry
- Sunk cost fallacy intensified: the new purchase feels like it will help recover the original loss
- Conviction in the original thesis is maintained despite price action contradicting it
- "The market is wrong" belief justifies additional commitment

**Why It Is Constitutionally Prohibited:**
If the price has moved significantly against the position, that price movement is evidence that at least some participants have information that contradicts the thesis. Adding capital to a contradicted thesis is adding to a position where the evidence quality has declined, not improved.

**Detection Methods:**
- Rule-based: any order to increase a position that is currently at a loss below entry triggers an automatic block
- Pattern-based: if a position has consecutive lower entries over time, this pattern is flagged

**Mitigation:**
- Absolute rule: no adding to a losing position — constitutional prohibition
- The only exception: if the position has been partially exited and the price has since improved above the first exit price (this is not averaging down, it is re-entry at a higher level)
- Scale-in is permitted only at the entry decision stage, before the position is in loss

**Recovery:**
- When averaging down is detected: the added-to position must be reviewed immediately
- The full position (original + added tranche) is evaluated as a new decision based on current conviction
- If consolidated conviction is below entry threshold, the full position is exited

---

## PART IX — DECISION CONSTITUTION

*Thirty constitutional principles governing all investment decisions in the Investment Intelligence Operating System. These principles are not guidelines — they are invariant requirements. Any decision that violates them is unconstitutional and must be reviewed.*

---

**Principle 1 — Every Decision Must Be Explainable**
Every investment decision must be fully traceable from the evidence through the reasoning to the conclusion. "The model says so" is never acceptable. Every approved decision must be explainable to a reasonable expert who had access only to the same evidence. If a decision cannot be explained, it was not properly reasoned and should not have been approved.

---

**Principle 2 — Every Decision Must Be Auditable**
Every step in the decision process — from the first observation through governance approval to final outcome — must be permanently recorded. There are no private decisions. Every decision must be examinable, explainable, and reconstructable from the audit trail. Any decision without a complete audit trail is constitutionally invalid.

---

**Principle 3 — Capital Is Finite and Sacred**
Capital is the fundamental resource of the investment system. It took time and decisions to accumulate. Its preservation is the first obligation of the system. No return opportunity, however compelling, justifies placing total capital at existential risk. Capital preservation supersedes return maximization when the two conflict.

---

**Principle 4 — Risk Precedes Reward**
Before considering the expected return of any decision, the system must first ask: "What is the worst-case outcome, and can the portfolio survive it?" No decision may be approved without a defined stop loss, a calculated capital at risk, and a confirmed risk budget check. The reward is only considered after the risk is bounded.

---

**Principle 5 — No Decision Without Evidence**
A decision recommendation without a minimum of 3 independent, cited evidence items is not a recommendation — it is a guess. The governance system will reject any recommendation lacking sufficient evidence citations. Evidence is the starting point; without it, there is nothing to decide.

---

**Principle 6 — No Decision Without Reasoning**
Collecting evidence is not sufficient — the evidence must be systematically processed through the reasoning pipeline. A decision that skips from observation directly to action, without the intermediate steps of hypothesis formation, conviction calculation, and multi-agent debate, is a governance violation.

---

**Principle 7 — No Decision Without Uncertainty Estimation**
Every approved decision must include an explicit assessment of uncertainty: what is the confidence level, what could make the thesis wrong, and what is the probability of the alternative hypothesis? A decision presented as certain when it is uncertain is a form of evidence fabrication.

---

**Principle 8 — Every Decision Has an Expiry**
Decision recommendations expire after their defined decision window. Approved decisions expire if the triggering conditions change materially before execution. Open positions expire when the thesis life is exceeded without new confirming evidence. Nothing in the decision system is indefinitely valid — time conditions everything.

---

**Principle 9 — Every Decision Affects Portfolio State**
No decision is made in isolation. Every entry changes sector exposure, correlation, deployment rate, and portfolio beta. Every exit releases capital and changes diversification. Every decision must be evaluated against the portfolio context it is entering — not as if the portfolio did not exist.

---

**Principle 10 — Every Decision Produces Learning**
Every closed position — whether profitable, unprofitable, stopped out, or target-reached — generates a mandatory learning record. The system cannot selectively learn from successes. Learning from losses is more valuable than learning from successes because failures reveal where the architecture needs improvement.

---

**Principle 11 — Every Decision Must Be Reproducible**
Given the same evidence set and the same market conditions, the reasoning process must produce consistent decisions. If identical inputs produce wildly different outputs, the decision process has unacceptable variance that must be diagnosed. Reproducibility is the test of a principled process.

---

**Principle 12 — The Stop Loss Is Inviolable**
Once a stop loss is defined and placed for an open position, no reasoning argument — however compelling, however high-conviction — may override it when it is triggered. The stop loss exists precisely for the moments when the conviction is highest that it should be overridden. Those moments are when it is most important to honor it.

---

**Principle 13 — The Kill Switch Is Inviolable**
When kill switch conditions are met, the kill switch activates. No governance authority, no human override, no "but this is a special situation" argument may suspend the kill switch. The kill switch is not a guideline — it is a hard circuit breaker protecting against catastrophic loss in extreme conditions.

---

**Principle 14 — The Sunk Cost Has No Standing**
Capital already deployed in a losing position is sunk. It is gone. The decision to hold, exit, or add must be made on the basis of the current thesis and current evidence, not the history of capital deployed. "I cannot exit because I am down 8%" is a constitutional violation — the relevant question is "does the forward-looking thesis justify continuing?"

---

**Principle 15 — Position Size Reflects Conviction, Not Desire**
The quantity of shares purchased must be determined by the conviction-calibrated sizing framework, not by how large the decision-maker wants the position to be. Wanting a larger position is not evidence of higher conviction. Conviction is determined by evidence quality, not by desire.

---

**Principle 16 — The Minority Opinion Has Standing**
In multi-agent debate, the dissenting opinion must be formally recorded and monitored for subsequent vindication. A minority position that is outvoted is not wrong — it is outvoted. History is full of cases where the minority was correct. The system treats minority opinions as intellectual assets.

---

**Principle 17 — No Averaging Down**
Adding to a losing position to reduce average cost is constitutionally prohibited. If the position is losing, either the thesis is still valid (hold without adding) or the thesis is invalidating (exit). There is no third case where adding more capital to a losing thesis is appropriate.

---

**Principle 18 — Regime Context Is Non-Negotiable**
Before any decision is approved, the system must confirm that the strategy type and thesis are appropriate for the current market regime. A momentum decision in a sideways market is constitutionally invalid. Regime context supersedes all other contextual factors.

---

**Principle 19 — The Decision Window Must Be Respected**
A decision recommendation has a defined validity window. A recommendation that was fresh and well-supported at creation may be stale and potentially wrong 3 days later. No recommendation may be executed after its decision window has closed — it must be re-evaluated from the current evidence position.

---

**Principle 20 — Portfolio Constraints Are Hard Limits**
Sector concentration limits, correlation limits, deployment limits, and drawdown limits are constitutional constraints, not guidelines. No decision that violates any portfolio constraint may be approved, regardless of how high the conviction or how attractive the expected return. Constraints exist to prevent the portfolio from being bet on a single outcome.

---

**Principle 21 — Process Quality Is More Important Than Outcome**
A decision made with an excellent process that produces a loss is a high-quality decision. A decision made with a poor process that produces a gain is a low-quality decision. The learning system evaluates process quality — not just outcomes. This prevents the system from learning to reason poorly in ways that have historically been profitable by chance.

---

**Principle 22 — All Governance Gates Are Mandatory**
The six governance gates are not a menu from which the most convenient may be selected. All six must be passed for every decision above the minimum threshold. Gate 3 (risk budget) cannot be waived because Gate 2 (conviction) is high. Gate 5 (regime) cannot be waived because Gate 4 (portfolio) was easy. Every gate evaluates an independent dimension; all are required.

---

**Principle 23 — Conviction Must Be Calibrated**
Conviction scores must reflect demonstrated accuracy, not stated confidence. A conviction level of 7.0 must correspond to a historical win rate of approximately 70% for that conviction tier and strategy type. If calibration error exceeds 10%, conviction scores are automatically adjusted by the calibration correction factor until the discrepancy is corrected.

---

**Principle 24 — Time Is a First-Class Dimension**
Every decision has a temporal dimension: the evidence has a timestamp, the thesis has a horizon, the holding period has an expectation, and the stop has a time dimension. Timeless investment positions — held indefinitely without review — are not permitted. Everything in the system is time-conditioned.

---

**Principle 25 — The Human Override Is an Option of Last Resort**
Human override of AI decisions is available but is not a routine governance tool. It is the final authority when the AI system operates outside its mandate, misses a qualitative dimension, or encounters a genuinely novel situation. Human override is subject to the same documentation requirements as all other decisions. Override patterns are audited for behavioral bias.

---

**Principle 26 — Independence Must Be Genuine**
Multi-agent analysis is only valuable when agents genuinely analyze independently. If agents are sharing conclusions before completing analysis, the independence is fake and groupthink risk is active. Independence means: each agent's analysis is completed and sealed before any agent's output is shared.

---

**Principle 27 — The Alternative Hypothesis Must Be Maintained**
For every active investment thesis, at least one alternative hypothesis that could also explain the available evidence must be explicitly held. The system evaluates evidence against both simultaneously. A thesis that has no conceivable alternative is not a thesis — it is a certainty, and certainties do not exist in investment.

---

**Principle 28 — Leverage Amplifies Both Errors and Successes**
The use of leverage is not prohibited but is strictly controlled. Leverage does not change the quality of a decision — it amplifies its consequences. A good decision with leverage produces better returns; a bad decision with leverage produces catastrophic losses. The use of leverage requires committee approval and heightened conviction thresholds.

---

**Principle 29 — Decision Failures Are Learning Events**
No decision failure is wasted if it produces a high-quality learning record. The worst outcome is a failure from which no lessons are extracted. Every decision failure must trigger a post-mortem, a root cause analysis, a lesson formulation, and an architecture check. The system improves through failure more than through success.

---

**Principle 30 — The System Must Know the Boundary of Its Competence**
The AI decision system operates best within its validated domain of experience. When confronted with genuinely novel conditions — a market structure change, a new regulatory regime, a type of event with no historical precedent — the system must escalate to human judgment rather than extrapolate from potentially inapplicable prior experience. Knowing the limit of competence is the foundation of all other principles.

---

## PART X — FUTURE EVOLUTION

*How the Decision Architecture grows, improves, and evolves from its current state toward increasingly autonomous, collaborative, and institutionally-scaled investment intelligence.*

---

### Evolution Dimensions

The Decision Architecture will evolve along five strategic dimensions:

**Dimension 1 — Decision Speed:** Reducing the pipeline from observation to approved decision without sacrificing quality. The target: same-day for tactical decisions; same-hour for time-critical events.

**Dimension 2 — Decision Coverage:** Expanding the universe of decision types, entity types, and market structures the system can confidently evaluate and decide on.

**Dimension 3 — Decision Quality:** Improving calibration, reducing behavioral bias, increasing evidence independence, and improving the learning feedback loop.

**Dimension 4 — Decision Autonomy:** Expanding the scope of decisions the system can make autonomously within its mandate, reducing the need for human deliberation for routine decisions.

**Dimension 5 — Decision Collaboration:** Enhancing the multi-agent architecture, enabling richer debate, more sophisticated consensus mechanisms, and higher-quality collective decisions.

---

### Near-Term Evolution (1-2 Years)

| Evolution | Description | Architectural Impact |
|---|---|---|
| Calibration Automation | Automatic conviction score adjustment based on rolling accuracy measurement | Eliminates manual recalibration; maintains accuracy in real time |
| Evidence Independence Scoring | Automatic detection and penalization of correlated evidence streams | Reduces false conviction from dependent evidence |
| Decision Latency Reduction | Pipeline optimization to reduce average time from signal to execution | Time-critical opportunities captured more reliably |
| Enhanced Exit Analytics | Real-time quality scoring of exit timing relative to optimal | Identifies exit timing improvements systematically |
| Post-Mortem Automation | Structured automatic post-mortem generation for all closed positions | Ensures consistent quality learning across all decisions |

---

### Medium-Term Evolution (2-4 Years)

| Evolution | Description | Architectural Impact |
|---|---|---|
| Cross-Asset Decision Extension | Expanding to fixed income, currencies, and commodity decisions | Full multi-asset portfolio architecture |
| Natural Language Evidence Processing | Processing unstructured analyst reports and filings as evidence | Expands evidence universe; reduces information latency |
| Regime-Adaptive Thresholds | Conviction thresholds and position sizes that automatically adjust to regime | More appropriate sizing in extreme conditions |
| Institutional-Scale Governance | Multi-fund, multi-strategy governance layers | Enables institutional portfolio management |
| Collaborative Human-AI Committee | Structured framework for human and AI agents to debate simultaneously | Maximizes benefit of both human and AI perspectives |

---

### Long-Term Evolution (5-10 Years)

| Evolution | Description |
|---|---|
| **Recursive Decision Self-Improvement** | The system modifies its own decision architecture based on accumulated evidence — not just strategy parameters but the structure of governance itself |
| **Cross-Portfolio Decision Intelligence** | Decisions that consider multiple portfolios simultaneously — identifying opportunities that are optimal across a portfolio family rather than a single fund |
| **Multi-Agent Distributed Decisions** | Multiple independent decision-making instances collaborating across geographies and time zones |
| **Autonomous Full-Cycle Decision System** | An AI investment management system that handles the full decision lifecycle from research to execution to learning without routine human intervention |
| **AGI-Level Investment Decision Intelligence** | The ability to reason about and decide on investment opportunities that have no historical precedent, using first-principles economic reasoning |
| **Institutional-Scale Autonomous Portfolio** | Managing a diversified institutional portfolio with multiple asset classes, complex derivatives, and cross-market exposure fully autonomously within a human-set mandate |

---

### Protocol for Adding New Decision Types

When a new decision paradigm is identified and proposed for incorporation into this architecture:

1. **Define** — Name, definition, core mechanism, inputs, outputs, and governance requirements
2. **Differentiate** — Demonstrate it is genuinely distinct from all existing types (DT-01 to DT-30)
3. **Use Cases** — Identify at least 3 specific investment situations where it adds value
4. **Failure Modes** — Identify at least 3 failure modes specific to this decision type
5. **Governance** — Define what governance gates, authority tier, and approval requirements apply
6. **Test** — Run the decision type in paper trading for minimum 60 days before live deployment
7. **Validate** — Confirm win rate, Sharpe, and maximum drawdown pass the promotion gates
8. **Assign Code** — DT-31, DT-32, continuing the sequence
9. **Document** — Full specification in the format of Part IV
10. **Committee Review** — Full Investment Committee review and approval before live activation

---

### Backward Compatibility Commitments

1. **Primitive codes are permanent** — DPRIM-001 through DPRIM-025 always refer to the primitives defined here; they may be extended but not redefined
2. **Decision type codes are permanent** — DT-01 through DT-30 always refer to the types defined here
3. **Constitutional principles are inviolable** — Principles 1-30 cannot be weakened; new principles may be added but existing ones cannot be removed or softened
4. **Governance gates are permanent** — The 6 governance gates are constitutionally fixed; additional gates may be added, but no existing gate may be removed
5. **Kill switch conditions are permanent** — The kill switch thresholds (VIX > 45, daily loss > 2%) may only be tightened, never loosened, without human principal approval

---

### Versioning

The Decision Architecture follows semantic versioning:

- **Major version (X.0):** Constitutional principle changes, primitive redefinitions, governance architecture restructuring
- **Minor version (X.Y):** New decision types, new primitives, new governance tiers, significant new constraints
- **Patch version (X.Y.Z):** Threshold recalibrations, additional examples, clarifications, documentation improvements

Current version: **1.0** — as of July 1, 2026

---

## DECISION CONCEPT COUNT SUMMARY

| Group | Name | Concepts Defined |
|---|---|---|
| A | Core Decision Concepts | 45 |
| B | Capital and Resource Concepts | 37 |
| C | Risk Concepts | 36 |
| D | Return and Reward Concepts | 36 |
| E | Entry Decision Concepts | 40 |
| F | Exit Decision Concepts | 40 |
| G | Portfolio Governance Concepts | 36 |
| H | Approval and Process Concepts | 32 |
| I | Behavioral Decision Concepts | 35 |
| J | Temporal Decision Concepts | 30 |
| K | Multi-Agent Decision Concepts | 29 |
| L | Market-Specific Decision Concepts | 35 |
| M | Decision Failure Mode Concepts | 31 |
| N | Meta-Decision and Learning Concepts | 27 |
| **Total** | | **509 concepts** |

**Decision Primitives (Part III):** 25 fully specified (DPRIM-001 to DPRIM-025) — 28 attributes each

**Decision Types (Part IV):** 30 paradigms (DT-01 to DT-30) — strengths, weaknesses, use cases, failure modes

**Constitutional Principles (Part IX):** 30 inviolable principles

**Decision Pipeline Stages:** 22 stages from information arrival to knowledge update

**Governance Tiers:** 4 (Human Principal, Investment Committee, Risk Committee, AI Autonomous)

**Governance Gates:** 6 mandatory gates for every decision recommendation

**Decision Failure Modes:** 28 classified and documented (DFM-01 to DFM-28)

---

## DOCUMENT HISTORY

| Version | Date | Description |
|---|---|---|
| 1.0 | 2026-07-01 | Initial authoritative decision architecture — 509 decision concepts, 25 fully defined primitives (28 attributes each), 30 decision types, 22-stage pipeline, 4-tier governance, 30 constitutional principles, 28 failure modes |

---

*This document answers the question: "How does intelligence decide?"*
*Every entry decision traces to a decision type and primitive defined here.*
*Every exit discipline traces to the constitution defined here.*
*Every governance gate traces to the authority matrix defined here.*
*Every capital commitment traces to the risk-reward framework defined here.*
*Every decision failure traces to a failure mode defined here.*
*Before making any investment decision, confirm it is architecturally grounded in this document.*
*Extend this document before implementing any decision pattern not already defined here.*
