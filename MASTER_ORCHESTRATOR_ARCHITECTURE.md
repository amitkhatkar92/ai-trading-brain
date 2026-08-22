# MASTER ORCHESTRATOR ARCHITECTURE

**Document Code:** IIOS-MO-ARCH-001
**Version:** 1.0.0
**Classification:** Authoritative Architecture
**Status:** RELEASED
**Date:** 2026-07-04
**Author:** Investment Intelligence Operating System — Architecture Council
**Series:** IIOS Engine Architecture Series
**Preceding Documents:**
- IIOS-DB-ARCH-001 — Database Persistence Architecture
- IIOS-KE-ARCH-001 — Knowledge Engine Architecture
- IIOS-ENT-ARCH-001 — Entity Engine Architecture
- IIOS-REL-ARCH-001 — Relationship Engine Architecture
- IIOS-EVT-ARCH-001 — Event Engine Architecture
- IIOS-INF-ARCH-001 — Information Engine Architecture
- IIOS-OBS-ARCH-001 — Observation Engine Architecture
- IIOS-EVI-ARCH-001 — Evidence Engine Architecture
- IIOS-HYP-ARCH-001 — Hypothesis Engine Architecture
- IIOS-RSN-ARCH-001 — Reasoning Engine Architecture
- IIOS-DEC-ARCH-001 — Decision Engine Architecture
- IIOS-EXE-ARCH-001 — Execution Engine Architecture
- IIOS-LRN-ARCH-001 — Learning Engine Architecture
- IIOS-PRD-ARCH-001 — Prediction Engine Architecture
- IIOS-RSK-ARCH-001 — Risk Engine Architecture
- IIOS-PRT-ARCH-001 — Portfolio Engine Architecture
- IIOS-STR-ARCH-001 — Strategy Engine Architecture
- IIOS-SIM-ENG-ARCH-001 — Simulation Engine Architecture
- IIOS-GOV-ENG-ARCH-001 — Governance Engine Architecture

---

## POSITION IN IIOS

`
+=========================================================================+
|                    MASTER ORCHESTRATOR (IIOS-MO-ARCH-001)               |
|    Supreme coordination engine — coordinates ALL engines, ALL agents    |
+=========================================================================+
     |          |          |          |          |          |
+--------+ +--------+ +--------+ +--------+ +--------+ +--------+
|Knowl.  | |Inform. | |Observ. | |Entity  | |Relation| |Event   |
|Engine  | |Engine  | |Engine  | |Engine  | |Engine  | |Engine  |
+--------+ +--------+ +--------+ +--------+ +--------+ +--------+
     |          |          |          |          |          |
+--------+ +--------+ +--------+ +--------+ +--------+ +--------+
|Predict | |Decision| |Risk    | |Portfolio| |Learning| |Strategy|
|Engine  | |Engine  | |Engine  | |Engine  | |Engine  | |Engine  |
+--------+ +--------+ +--------+ +--------+ +--------+ +--------+
     |          |          |          |
+--------+ +--------+ +--------+ +----------------+
|Simul.  | |Govern. | |Future  | |All IIOS        |
|Engine  | |Engine  | |Engines | |Infrastructure  |
+--------+ +--------+ +--------+ +----------------+
`

**Core Mandate:**
The Master Orchestrator does NOT perform investment analysis.
The Master Orchestrator does NOT replace any engine.
The Master Orchestrator COORDINATES every engine.
The Master Orchestrator SCHEDULES every workflow.
The Master Orchestrator GOVERNS engine communication.
The Master Orchestrator ensures IIOS behaves as one intelligent organism.

---

## INTERNAL ARCHITECTURE

`
+=========================================================================+
|                        MASTER ORCHESTRATOR                              |
|                                                                         |
|  TIER 1 — CORE COORDINATION                                             |
|  +------------------+ +------------------+ +------------------+        |
|  | OC-01 Master     | | OC-02 Workflow   | | OC-03 Dependency |        |
|  | Scheduler        | | Manager          | | Manager          |        |
|  +------------------+ +------------------+ +------------------+        |
|  +------------------+ +------------------+ +------------------+        |
|  | OC-04 Execution  | | OC-05 Priority   | | OC-06 Resource   |        |
|  | Coordinator      | | Manager          | | Manager          |        |
|  +------------------+ +------------------+ +------------------+        |
|                                                                         |
|  TIER 2 — ENGINE INTEGRATION                                            |
|  +------------------+ +------------------+ +------------------+        |
|  | OC-07 Agent      | | OC-08 Engine     | | OC-09 Engine     |        |
|  | Coordinator      | | Registry         | | Discovery Mgr    |        |
|  +------------------+ +------------------+ +------------------+        |
|  +------------------+ +------------------+ +------------------+        |
|  | OC-10 Commun.    | | OC-11 Message    | | OC-12 Conflict   |        |
|  | Manager          | | Router           | | Resolver         |        |
|  +------------------+ +------------------+ +------------------+        |
|                                                                         |
|  TIER 3 — STATE AND HEALTH                                              |
|  +------------------+ +------------------+ +------------------+        |
|  | OC-13 Synchroniz.| | OC-14 State      | | OC-15 Health     |        |
|  | Manager          | | Manager          | | Manager          |        |
|  +------------------+ +------------------+ +------------------+        |
|  +------------------+ +------------------+                             |
|  | OC-16 Monitoring | | OC-17 Incident   |                             |
|  | Manager          | | Manager          |                             |
|  +------------------+ +------------------+                             |
|                                                                         |
|  TIER 4 — INTELLIGENCE AND OPERATIONS                                   |
|  +------------------+ +------------------+ +------------------+        |
|  | OC-18 Recovery   | | OC-19 Analytics  | | OC-20 Reporting  |        |
|  | Manager          | | Manager          | | Manager          |        |
|  +------------------+ +------------------+ +------------------+        |
|  +------------------+ +------------------+                             |
|  | OC-21 Version    | | OC-22 Config.    |                             |
|  | Manager          | | Manager          |                             |
|  +------------------+ +------------------+                             |
+=========================================================================+
`

---

## TABLE OF CONTENTS

`
PART I    — MASTER ORCHESTRATOR PHILOSOPHY ............... Section 1
  1.1      The Nature of Orchestration
  1.2      Nineteen Coordination Concepts Defined
  1.3      Why Orchestration Must Remain Independent
  1.4      The Orchestrator as Meta-Intelligence

PART II   — ORCHESTRATOR TAXONOMY ........................ Section 2
  2.1      Taxonomy Reference Table
  2.2      OT-01 Workflow Orchestration
  2.3      OT-02 Knowledge Orchestration
  2.4      OT-03 Observation Orchestration
  2.5      OT-04 Prediction Orchestration
  2.6      OT-05 Decision Orchestration
  2.7      OT-06 Risk Orchestration
  2.8      OT-07 Portfolio Orchestration
  2.9      OT-08 Learning Orchestration
  2.10     OT-09 Strategy Orchestration
  2.11     OT-10 Simulation Orchestration
  2.12     OT-11 Governance Orchestration
  2.13     OT-12 AI Agent Orchestration
  2.14     OT-13 Resource Orchestration
  2.15     OT-14 Infrastructure Orchestration
  2.16     OT-15 Incident Orchestration
  2.17     OT-16 Recovery Orchestration

PART III  — CORE COMPONENTS .............................. Section 3
  3.1      OC-01 Master Scheduler
  3.2      OC-02 Workflow Manager
  3.3      OC-03 Dependency Manager
  3.4      OC-04 Execution Coordinator
  3.5      OC-05 Priority Manager
  3.6      OC-06 Resource Manager
  3.7      OC-07 Agent Coordinator
  3.8      OC-08 Engine Registry
  3.9      OC-09 Engine Discovery Manager
  3.10     OC-10 Communication Manager
  3.11     OC-11 Message Router
  3.12     OC-12 Conflict Resolver
  3.13     OC-13 Synchronization Manager
  3.14     OC-14 State Manager
  3.15     OC-15 Health Manager
  3.16     OC-16 Monitoring Manager
  3.17     OC-17 Incident Manager
  3.18     OC-18 Recovery Manager
  3.19     OC-19 Analytics Manager
  3.20     OC-20 Reporting Manager
  3.21     OC-21 Version Manager
  3.22     OC-22 Configuration Manager

PART IV   — ORCHESTRATION LIFECYCLE ...................... Section 4
  4.1      Lifecycle Stage Reference
  4.2      Stage Diagrams and State Transitions
  4.3      Timing Reference

PART V    — ORCHESTRATION SERVICES ....................... Section 5
  OS-01 through OS-15

PART VI   — WORKFLOW PIPELINES ........................... Section 6
  OP-01 System Startup Pipeline
  OP-02 Daily Market Pipeline
  OP-03 Observation Pipeline
  OP-04 Knowledge Pipeline
  OP-05 Prediction Pipeline
  OP-06 Decision Pipeline
  OP-07 Risk Pipeline
  OP-08 Portfolio Pipeline
  OP-09 Learning Pipeline
  OP-10 Strategy Pipeline
  OP-11 Simulation Pipeline
  OP-12 Governance Pipeline
  OP-13 System Shutdown Pipeline
  OP-14 Failure Recovery Pipeline

PART VII  — QUALITY FRAMEWORK ............................ Section 7
  OQD-01 through OQD-13

PART VIII — ORCHESTRATION GOVERNANCE ..................... Section 8
  8.1 through 8.11

PART IX   — MASTER ORCHESTRATOR CONSTITUTION ............. Section 9
  OCC-A Engine Registration (10 rules)
  OCC-B Engine Independence (10 rules)
  OCC-C Scheduling (10 rules)
  OCC-D Coordination (8 rules)
  OCC-E Communication (8 rules)
  OCC-F Synchronization (8 rules)
  OCC-G Workflow Integrity (8 rules)
  OCC-H Conflict Resolution (8 rules)
  OCC-I Recovery (8 rules)
  OCC-J Monitoring (8 rules)
  OCC-K Health (8 rules)
  OCC-L Resource Allocation (8 rules)
  OCC-M Priority (8 rules)
  OCC-N Security (8 rules)
  OCC-O Governance (8 rules)
  OCC-P Human Override (6 rules)
  OCC-Q Future Engine Integration (8 rules)
  OCC-R Constitutional Completeness (4 rules)

PART X    — READINESS CHECKLIST .......................... Section 10
  P1 Engine Registry Ready
  P2 Workflow Ready
  P3 Scheduling Ready
  P4 Communication Ready
  P5 Synchronization Ready
  P6 Monitoring Ready
  P7 Recovery Ready
  P8 Governance Approved
  P9 Security Verified
  P10 Documentation Complete
  P11 Operationally Ready
  P12 Archived Correctly

SUPPLEMENTS
  A — Engine Interaction Matrix
  B — Workflow Catalog
  C — Scheduling Reference
  D — Dependency Matrix
  E — Governance Decision Records
  F — Anti-Patterns
  G — Operational Runbook
  H — Comprehensive Glossary
`

---

## PART I — MASTER ORCHESTRATOR PHILOSOPHY

### 1.1 The Nature of Orchestration

Orchestration is the supreme act of coordination. In a multi-engine intelligence
system such as IIOS, no single engine possesses complete knowledge, complete
authority, or complete capability. Each engine is a specialist. The Knowledge
Engine knows what is known. The Decision Engine decides. The Risk Engine measures
risk. The Governance Engine enforces rules. Every engine is extraordinarily capable
within its domain — and entirely dependent on coordination with other engines to
produce any coherent system-level outcome.

Orchestration is the discipline that enables a collection of specialized engines
to behave as a unified, coherent, intelligent operating system. Without
orchestration, IIOS is a set of disconnected tools. With orchestration, IIOS is
one intelligent organism.

The Master Orchestrator is the nervous system of IIOS. It does not think about
investments. It does not know about RSI or Sharpe ratios or VIX levels. It knows
about engines, workflows, dependencies, priorities, schedules, messages, states,
health, conflicts, and resources. It is the meta-intelligence that enables every
other intelligence.

The Master Orchestrator achieves this through five fundamental capabilities:

First, **temporal coordination** — ensuring that engines execute in the correct
sequence, at the correct time, with the correct inputs available. A prediction
cannot precede an observation. A decision cannot precede a prediction. An execution
cannot precede a risk-approved decision. Temporal coordination imposes the correct
order of operations on the investment process.

Second, **dependency management** — maintaining and enforcing the full dependency
graph of all engine interactions. Before invoking any engine, the Master Orchestrator
verifies that all upstream dependencies have completed successfully. No engine
receives stale inputs. No engine executes before its prerequisites are satisfied.

Third, **resource governance** — ensuring that computational resources, data access
bandwidth, communication channels, and storage are allocated across engines in
proportion to their current criticality and within configured limits. No engine
monopolizes resources at the expense of the system.

Fourth, **health assurance** — continuously monitoring the health of every engine,
every workflow, and the system as a whole. When an engine becomes unhealthy, the
Master Orchestrator knows, responds, and either recovers or gracefully degrades
the system to protect capital.

Fifth, **conflict resolution** — detecting and resolving conflicts that arise between
engines — when two engines produce contradictory outputs, when two workflows compete
for the same resource, when a scheduling decision conflicts with a governance
requirement. The Master Orchestrator applies defined resolution policies rather
than allowing conflicts to propagate unresolved.

---

### 1.2 Nineteen Coordination Concepts Defined

**Orchestration:** The highest-level coordination discipline. Orchestration combines
scheduling, workflow management, dependency enforcement, communication governance,
health assurance, and conflict resolution into a unified coordination system.
Orchestration produces coherent system-level behavior from a collection of
specialized, independent components. The Master Orchestrator IS the orchestration
layer of IIOS.

**Scheduling:** The temporal discipline of determining WHEN each workflow,
pipeline, or engine invocation should execute. Scheduling assigns time slots,
manages recurring cycles, handles trigger-based execution, and enforces temporal
ordering constraints. Scheduling answers the question: "When should this run?"
The Master Scheduler (OC-01) is the dedicated scheduling component.

**Workflow:** A defined, named sequence of steps with explicit dependencies,
inputs, outputs, and success criteria. A workflow is the specification of how
a multi-step process should proceed. The Master Orchestrator manages 14 named
workflows (OP-01 through OP-14). Workflows are declarative — they define WHAT
should happen, not HOW each engine achieves its step.

**Automation:** The elimination of manual intervention from routine execution.
Automation transforms scheduled and event-driven workflows into self-executing
processes. Automation is a property of individual steps within workflows — the
Master Orchestrator provides the automation infrastructure that enables workflows
to execute without manual initiation for every step.

**Coordination:** The alignment of independent actors toward a shared goal without
those actors having direct authority over each other. The Master Orchestrator
coordinates engines — it does not command engines. Each engine is autonomous within
its domain; the Orchestrator aligns them toward system-level outcomes.

**Execution:** The act of invoking an engine and processing its output. Execution
is one operational step within coordination. The Execution Coordinator (OC-04)
manages execution events, but execution itself happens inside each specialized
engine. The Orchestrator coordinates execution; it does not execute investment
analysis.

**Management:** The ongoing activity of maintaining system state, tracking progress,
allocating resources, and resolving problems. Management is broader than execution —
it encompasses everything that happens before, during, and after execution.
The Master Orchestrator performs system-level management through its 22 components.

**Governance:** The authority framework that constrains what the Master Orchestrator
may do and how it must do it. Governance is imposed ON the Orchestrator by the
Governance Engine — the Orchestrator implements governance policies, does not define
them. The Orchestrator is governed; it is not the governor. This distinction is
non-negotiable. (The Governance Engine, IIOS-GOV-ENG-ARCH-001, defines all
governance rules; the Master Orchestrator enforces them operationally.)

**Communication:** The structured exchange of information between engines through
defined interfaces. Communication is not ad hoc message passing — it is
governed, typed, logged, and auditable. The Communication Manager (OC-10) and
Message Router (OC-11) govern all engine-to-engine communication through the
Master Orchestrator.

**Synchronization:** The coordination of multiple concurrent execution threads to
ensure consistency. When multiple engines execute in parallel, their outputs may
need to be synchronized before a downstream engine can proceed. The Synchronization
Manager (OC-13) manages synchronization barriers and ensures no race conditions
exist in the IIOS workflow graph.

**Control:** The ability to start, stop, pause, resume, and redirect any engine or
workflow. Control is the operational authority that the Master Orchestrator holds
over workflow execution (not over engine intelligence). An engine's internal
reasoning is not subject to Orchestrator control — its participation in workflows is.

**Delegation:** The act of assigning a workflow step, a resource allocation
decision, or a scheduling slot to a specific engine or component. The Master
Orchestrator delegates execution responsibility to engines while retaining
coordination authority. Delegation is explicit, logged, and bounded.

**Supervision:** Continuous observation of delegated execution with the authority
to intervene when execution deviates from expected parameters. Supervision differs
from monitoring in that supervision implies the authority and willingness to act.
The Master Orchestrator supervises every engine it has delegated work to.

**Resource Allocation:** The governance of computational resources (CPU, memory),
data access (bandwidth, rate limits), communication channels (queue capacity),
and storage (I/O quota) across all engines. The Resource Manager (OC-06) performs
resource allocation according to policies that prioritize critical workflows.

**Distributed Intelligence:** The architectural property of IIOS whereby intelligence
is distributed across specialized engines rather than concentrated in a single
monolithic system. The Master Orchestrator enables distributed intelligence by
providing the coordination infrastructure that prevents distribution from becoming
fragmentation.

**Event-Driven Execution:** A scheduling paradigm in which execution is triggered
by events rather than fixed time slots. The Master Orchestrator supports both
time-driven scheduling (market open at 09:00 IST) and event-driven execution
(execute Risk Pipeline when Decision Engine emits a Decision Record).

**Priority Management:** The discipline of ranking workflows and engine invocations
by importance and urgency, and ensuring that higher-priority work receives resources
and scheduling preference over lower-priority work. The Priority Manager (OC-05)
maintains dynamic priority queues and re-ranks work as system conditions change.

**Dependency Resolution:** The computational process of evaluating the dependency
graph of all workflows and determining a valid execution order. Dependency
resolution detects circular dependencies (which are architectural errors), identifies
the critical path through complex workflows, and ensures that all inputs to every
step are available before that step is invoked.

**Meta-Intelligence:** The intelligence of the Orchestrator is meta-intelligence —
intelligence about intelligence. The Orchestrator does not know about financial
markets. It knows about engines that know about financial markets. It reasons about
which engine should run next, when, with what resources, in what context — not
about what that engine should produce.

---

### 1.3 Why Orchestration Must Remain Independent

The Master Orchestrator must remain strictly independent from the specialized
intelligence it coordinates. This independence is not a preference — it is a
structural necessity for four reasons.

**Reason 1 — Separation of Concerns Prevents Corruption:**
If the Master Orchestrator developed opinions about investment outcomes, it would
begin scheduling workflows to produce desired results rather than to serve the
investment process correctly. A biased orchestrator is more dangerous than an
absent orchestrator — because it introduces hidden bias into every engine's
execution context. The Orchestrator must be indifferent to investment outcomes.

**Reason 2 — Independence Enables Trustworthy Governance:**
The Governance Engine (IIOS-GOV-ENG-ARCH-001) governs the Master Orchestrator.
If the Orchestrator embedded investment opinions, it could use its scheduling
authority to circumvent governance by ensuring certain engines ran before
governance checks. An independent Orchestrator has no incentive to circumvent
governance.

**Reason 3 — Independence Makes the Orchestrator Replaceable:**
Because the Master Orchestrator contains no investment intelligence, it can in
principle be replaced with a different orchestration implementation without
affecting the investment intelligence of any engine. This property is essential
for long-term system evolution.

**Reason 4 — Independence Makes the Orchestrator Auditable:**
An Orchestrator with no investment intelligence makes fully auditable decisions.
Every scheduling decision, every delegation, every conflict resolution follows a
policy. There are no "judgment calls" about market conditions. This makes the
audit record of the Orchestrator a complete and trustworthy operational log.

---

### 1.4 The Orchestrator as Meta-Intelligence

The Master Orchestrator is the intelligence of the intelligence system. It does
not possess investment domain knowledge. It possesses coordination domain knowledge:
topology of the engine network, dependency graph, performance profiles, failure
modes, resource consumption patterns, priority hierarchies, and operational
health indicators.

The Orchestrator's intelligence improves over time through the OC-19 Analytics
Manager, which tracks workflow performance, engine reliability, scheduling
effectiveness, and conflict frequency. This intelligence is used to improve
scheduling policies, refine priority assignments, and predict engine health
degradation before it causes workflow failures.

This constitutes genuine meta-intelligence: reasoning about the system that does
the reasoning. The Master Orchestrator optimizes the investment intelligence system
without optimizing for any particular investment outcome.

---

## PART II — ORCHESTRATOR TAXONOMY

### 2.1 Taxonomy Reference Table

The Orchestrator Taxonomy defines 16 orchestration domains. Each domain captures
a distinct category of coordination responsibility.

| ID    | Domain                    | Primary Component  | Workflows     | Priority |
|-------|---------------------------|--------------------|---------------|----------|
| OT-01 | Workflow Orchestration    | OC-02, OC-03       | OP-01 to OP-14| CRITICAL |
| OT-02 | Knowledge Orchestration   | OC-04, OC-10       | OP-04         | HIGH     |
| OT-03 | Observation Orchestration | OC-04, OC-13       | OP-03         | HIGH     |
| OT-04 | Prediction Orchestration  | OC-04, OC-05       | OP-05         | HIGH     |
| OT-05 | Decision Orchestration    | OC-04, OC-12       | OP-06         | CRITICAL |
| OT-06 | Risk Orchestration        | OC-04, OC-05       | OP-07         | CRITICAL |
| OT-07 | Portfolio Orchestration   | OC-04, OC-13       | OP-08         | HIGH     |
| OT-08 | Learning Orchestration    | OC-04, OC-06       | OP-09         | NORMAL   |
| OT-09 | Strategy Orchestration    | OC-04, OC-12       | OP-10         | HIGH     |
| OT-10 | Simulation Orchestration  | OC-04, OC-06       | OP-11         | NORMAL   |
| OT-11 | Governance Orchestration  | OC-04, OC-08       | OP-12         | CRITICAL |
| OT-12 | AI Agent Orchestration    | OC-07, OC-05       | Multiple      | HIGH     |
| OT-13 | Resource Orchestration    | OC-06, OC-14       | All           | HIGH     |
| OT-14 | Infrastructure Orchestration | OC-15, OC-16    | OP-01, OP-13  | CRITICAL |
| OT-15 | Incident Orchestration    | OC-17, OC-11       | OP-14         | CRITICAL |
| OT-16 | Recovery Orchestration    | OC-18, OC-13       | OP-14         | CRITICAL |

---

### 2.2 OT-01 — Workflow Orchestration

Workflow Orchestration is the foundational orchestration domain. It governs the
creation, scheduling, execution, monitoring, and completion of all named workflows
in IIOS. Every engine invocation in IIOS occurs within the context of a workflow;
no engine may be invoked outside a registered workflow.

Workflow Orchestration enforces workflow integrity: every workflow has a defined
start condition, a defined dependency graph, defined success and failure criteria,
and a defined cleanup procedure. The Workflow Manager (OC-02) and Dependency
Manager (OC-03) are the primary components for this domain.

**Key responsibilities:**
- Maintaining the master workflow registry.
- Evaluating workflow start conditions.
- Building and validating dependency graphs before execution.
- Tracking workflow state from PENDING through COMPLETED or FAILED.
- Invoking cleanup and archiving procedures on workflow completion.

**Critical constraint:** No workflow may be deleted from history. Completed
workflows are archived permanently.

---

### 2.3 OT-02 — Knowledge Orchestration

Knowledge Orchestration governs all interactions with the Knowledge Engine
(IIOS-KE-ARCH-001). The Knowledge Engine maintains the institutional knowledge
base of IIOS — market patterns, strategy facts, historical precedents, entity
knowledge, relationship knowledge, and event knowledge.

Knowledge must be current for every other engine to function correctly. The
Orchestrator ensures that the Knowledge Engine refresh pipeline (OP-04) executes
on schedule and that all downstream engines — Prediction, Decision, Risk —
receive notification that knowledge has been refreshed before their pipelines
execute.

**Key responsibilities:**
- Scheduling Knowledge Engine refresh cycles (daily, event-triggered).
- Coordinating knowledge validation before downstream engines consume it.
- Routing knowledge update notifications to all dependent engines.
- Enforcing knowledge freshness SLAs (no engine consumes knowledge older than its configured TTL).

---

### 2.4 OT-03 — Observation Orchestration

Observation Orchestration governs the Observation Engine (IIOS-OBS-ARCH-001),
which transforms raw market data into structured, typed Observation records. The
Observation Pipeline (OP-03) is the highest-frequency pipeline in IIOS — during
market hours it executes continuously.

The Orchestrator ensures that observation results are available to all downstream
engines within the required latency. It coordinates between the market data feeds,
the Observation Engine, and the Entity Engine so that price, volume, and signal
observations are consistently timestamped and routed.

**Key responsibilities:**
- Scheduling continuous and periodic Observation Engine cycles.
- Enforcing observation latency SLAs (observations must be available within defined windows).
- Coordinating with the Event Engine on observation-triggered events.
- Managing Observation Engine health during high-volatility sessions.

---

### 2.5 OT-04 — Prediction Orchestration

Prediction Orchestration governs the Prediction Engine (IIOS-PRD-ARCH-001).
The Prediction Engine generates probabilistic forecasts about market behavior,
strategy performance, and portfolio dynamics. Predictions are the primary input
to the Decision Engine.

The Orchestrator coordinates the Prediction Pipeline (OP-05), ensuring that the
Prediction Engine executes after observations are complete and before the Decision
Engine is invoked. It manages the handoff of prediction artifacts — probability
distributions, confidence intervals, forecast horizons — to the Decision Engine.

**Key responsibilities:**
- Sequencing the Prediction Pipeline after OP-03 Observation Pipeline.
- Routing prediction artifacts to the Decision Engine and Risk Engine.
- Enforcing prediction freshness SLAs.
- Escalating if prediction confidence falls below operational thresholds.

---

### 2.6 OT-05 — Decision Orchestration

Decision Orchestration is among the highest-priority orchestration domains. It
governs the Decision Engine (IIOS-DEC-ARCH-001), which produces all investment
decisions in IIOS. A Decision Engine output is the trigger for execution. Every
decision must be preceded by validated observations, validated predictions, and
a passed risk check.

The Orchestrator enforces the pre-decision checklist: observation freshness,
prediction availability, risk approval, governance authorization. No decision
reaches execution unless all prerequisites are satisfied.

**Key responsibilities:**
- Enforcing the complete pre-decision prerequisite chain.
- Routing decision records to the Risk Engine for risk approval.
- Coordinating the 5-agent debate process (managed by the Decision Engine internally).
- Enforcing the decision threshold (6.5 score) at the coordination level.
- Routing approved decisions to the Execution workflow.

---

### 2.7 OT-06 — Risk Orchestration

Risk Orchestration is a CRITICAL-priority domain. It governs the Risk Engine
(IIOS-RSK-ARCH-001), which measures, monitors, and enforces all risk limits. No
trading activity proceeds without risk approval.

The Orchestrator ensures that the Risk Pipeline (OP-07) executes after every
decision and before any execution. It also ensures that continuous risk monitoring
is active throughout the trading session, running independently of the decision
cycle.

**Key responsibilities:**
- Enforcing risk approval as a mandatory gate before execution.
- Scheduling continuous risk monitoring (30-second cycle during market hours).
- Coordinating kill switch evaluation with the Governance Engine.
- Escalating immediately on risk limit breach (P1 priority).

---

### 2.8 OT-07 — Portfolio Orchestration

Portfolio Orchestration governs the Portfolio Engine (IIOS-PRT-ARCH-001), which
manages the aggregate portfolio: position sizing, concentration limits, correlation
monitoring, rebalancing, and performance attribution.

The Orchestrator coordinates the Portfolio Pipeline (OP-08) to ensure portfolio
state is updated after every execution event and available to the Risk Engine and
Decision Engine in real time.

**Key responsibilities:**
- Scheduling Portfolio Engine updates after each execution.
- Routing portfolio state to Risk Engine and Decision Engine.
- Coordinating end-of-day portfolio reconciliation.
- Enforcing portfolio concentration limits as a pre-execution gate.

---

### 2.9 OT-08 — Learning Orchestration

Learning Orchestration governs the Learning Engine (IIOS-LRN-ARCH-001), which
continuously improves IIOS's investment intelligence by analyzing outcomes and
updating strategy models, prediction models, and entity profiles.

Learning is a lower-priority operation that runs post-session and does not block
any trading workflow. The Orchestrator schedules the Learning Pipeline (OP-09)
in post-session hours and ensures that learning outputs are available for the next
session's Knowledge refresh.

**Key responsibilities:**
- Scheduling Learning Pipeline in post-session hours.
- Coordinating learning output delivery to the Knowledge Engine.
- Enforcing learning isolation (learning processes must not affect live strategy weights).
- Scheduling paper trading evaluation cycles.

---

### 2.10 OT-09 — Strategy Orchestration

Strategy Orchestration governs the Strategy Engine (IIOS-STR-ARCH-001), which
manages the lifecycle of investment strategies: generation, evaluation, promotion,
deployment, and retirement.

No strategy enters live trading without completing the Strategy Governance Gate
(GIP-02, defined in IIOS-GOV-ENG-ARCH-001). The Orchestrator enforces this gate
and sequences the Strategy Pipeline (OP-10) to coordinate with Simulation and
Governance Engines.

**Key responsibilities:**
- Enforcing the strategy governance gate before live deployment.
- Coordinating Strategy Engine with Simulation Engine for validation runs.
- Routing strategy promotion decisions to the Governance Engine.
- Scheduling strategy performance review cycles.

---

### 2.11 OT-10 — Simulation Orchestration

Simulation Orchestration governs the Simulation Engine (IIOS-SIM-ENG-ARCH-001),
which provides the simulation infrastructure for strategy validation, risk scenario
testing, and Monte Carlo analysis.

Simulation runs are computationally intensive and scheduled outside trading hours
(or in low-priority slots during trading hours for non-blocking analysis). The
Orchestrator coordinates resource allocation for simulation runs and routes
simulation results to the Governance Engine as evidence artifacts.

**Key responsibilities:**
- Scheduling simulation runs in appropriate resource windows.
- Coordinating resource allocation for computationally intensive simulation jobs.
- Routing simulation artifacts to the Governance Engine's evidence dossier process.
- Enforcing simulation result validity requirements (SimQS thresholds).

---

### 2.12 OT-11 — Governance Orchestration

Governance Orchestration is a CRITICAL-priority domain. It governs all interactions
with the Governance Engine (IIOS-GOV-ENG-ARCH-001). The Governance Engine is the
constitutional authority of IIOS; the Master Orchestrator implements governance
decisions without overriding them.

**Key responsibilities:**
- Scheduling pre-session governance certification (GIP-01).
- Routing all strategy deployment requests through the Strategy Governance Gate (GIP-02).
- Coordinating continuous governance monitoring (GIP-03).
- Routing post-session governance reconciliation (GIP-04).
- Submitting exception requests to the Governance Engine (GIP-05).

**Critical invariant:** The Master Orchestrator NEVER bypasses the Governance
Engine. If the Governance Engine is unavailable, the system enters SAFE mode.

---

### 2.13 OT-12 — AI Agent Orchestration

AI Agent Orchestration governs the coordination of individual AI agents within
IIOS. Each engine contains AI agents (analysis agents, debate agents, evaluation
agents). The Orchestrator coordinates agent activation sequencing, resource
allocation per agent, and ensures that no agent operates outside its authorized
behavioral envelope.

**Key responsibilities:**
- Maintaining the agent registry (a subset of the Engine Registry OC-08).
- Enforcing agent invocation sequencing rules.
- Allocating per-agent resource budgets.
- Detecting runaway agent behavior and escalating to OC-17 Incident Manager.
- Coordinating multi-agent debate processes (Decision Engine, Strategy Engine).

---

### 2.14 OT-13 — Resource Orchestration

Resource Orchestration governs the allocation of all shared system resources:
CPU, memory, I/O bandwidth, data feed rate limits, queue capacity, and storage
I/O quota. Resources are shared across all engines; unmanaged resource competition
degrades system performance and can cause critical workflow failures.

**Key responsibilities:**
- Maintaining the real-time resource utilization map.
- Enforcing per-engine and per-workflow resource budgets.
- Preempting low-priority resource consumers when critical workflows need resources.
- Detecting resource exhaustion and triggering graceful degradation.

---

### 2.15 OT-14 — Infrastructure Orchestration

Infrastructure Orchestration governs the coordination of the underlying technical
infrastructure: containers, process management, network connectivity, data feed
connections, storage health, and VPS availability.

**Key responsibilities:**
- Monitoring infrastructure health continuously.
- Coordinating container restart sequences on failure.
- Managing data feed reconnection protocols.
- Ensuring storage health before session start.
- Coordinating VPS failover procedures.

---

### 2.16 OT-15 — Incident Orchestration

Incident Orchestration governs the detection, classification, escalation, and
management of operational incidents. An incident is any event that deviates from
expected system behavior and requires coordinated response.

**Key responsibilities:**
- Receiving incident signals from all monitoring components.
- Classifying incidents by severity (P1: 1 hour, P2: 4 hours, P3: 1 business day, P4: 5 business days).
- Coordinating the incident response workflow.
- Ensuring post-incident review is scheduled.

---

### 2.17 OT-16 — Recovery Orchestration

Recovery Orchestration governs the detection of system failures and the execution
of recovery procedures. Recovery must be rapid (within 30 seconds for session-
critical components), reliable (same outcome every time), and safe (no action
that risks unhedged exposure).

**Key responsibilities:**
- Maintaining the recovery procedure library.
- Executing recovery procedures in the correct sequence.
- Verifying that recovered components pass health checks before re-entering workflows.
- Coordinating with the Governance Engine to report recovery events.

---

## PART III — CORE COMPONENTS

### Component Reference Table

| ID    | Component Name             | Tier | Primary Domain | Dependencies         |
|-------|----------------------------|------|----------------|----------------------|
| OC-01 | Master Scheduler           | 1    | OT-01          | OC-02, OC-05, OC-14  |
| OC-02 | Workflow Manager           | 1    | OT-01          | OC-03, OC-04, OC-14  |
| OC-03 | Dependency Manager         | 1    | OT-01          | OC-08, OC-14         |
| OC-04 | Execution Coordinator      | 1    | OT-01 to OT-11 | OC-05, OC-06, OC-11  |
| OC-05 | Priority Manager           | 1    | OT-13          | OC-14                |
| OC-06 | Resource Manager           | 1    | OT-13          | OC-14, OC-15         |
| OC-07 | Agent Coordinator          | 2    | OT-12          | OC-08, OC-10         |
| OC-08 | Engine Registry            | 2    | OT-01          | OC-21, OC-22         |
| OC-09 | Engine Discovery Manager   | 2    | OT-01          | OC-08                |
| OC-10 | Communication Manager      | 2    | OT-01          | OC-11, OC-13         |
| OC-11 | Message Router             | 2    | OT-01          | OC-10, OC-14         |
| OC-12 | Conflict Resolver          | 2    | OT-01          | OC-05, OC-14         |
| OC-13 | Synchronization Manager    | 3    | OT-01          | OC-14, OC-10         |
| OC-14 | State Manager              | 3    | All            | OC-19                |
| OC-15 | Health Manager             | 3    | OT-14          | OC-16, OC-17         |
| OC-16 | Monitoring Manager         | 3    | OT-14, OT-15   | OC-17, OC-19         |
| OC-17 | Incident Manager           | 3    | OT-15          | OC-11, OC-18         |
| OC-18 | Recovery Manager           | 4    | OT-16          | OC-14, OC-15         |
| OC-19 | Analytics Manager          | 4    | All            | OC-20                |
| OC-20 | Reporting Manager          | 4    | All            | OC-19                |
| OC-21 | Version Manager            | 4    | OT-01          | OC-08, OC-22         |
| OC-22 | Configuration Manager      | 4    | All            | OC-21                |

---

### 3.1 OC-01 — Master Scheduler

**Purpose:**
The Master Scheduler is the temporal authority of IIOS. It determines WHEN every
workflow, pipeline, and engine invocation executes. It manages recurring schedules,
one-time schedules, event-triggered schedules, and external-event-reactive schedules.
Every time-based execution decision flows through OC-01.

**Responsibilities:**
- Maintaining the master schedule: a complete, authoritative list of all scheduled
  events with their next execution time, frequency, timezone, and priority.
- Computing next execution times for all recurring schedules using the IIOS trading
  calendar (NSE trading days, IST timezone, market hours 09:00–15:30).
- Triggering workflow creation events to OC-02 Workflow Manager at the correct time.
- Managing schedule conflicts: when two high-priority workflows are scheduled for
  the same time slot, applying priority policies to sequence or offset them.
- Maintaining holiday calendar and automatically skipping schedules on non-trading
  days (NSE calendar, including Diwali, Republic Day, and other Indian market holidays).
- Logging every schedule trigger with timestamp, schedule ID, workflow ID, and priority.

**Inputs:**
- Schedule definitions (from OC-22 Configuration Manager on startup).
- Event signals (from OC-16 Monitoring Manager for event-triggered schedules).
- Trading calendar (loaded from Governance Engine's calendar authority).
- Priority directives (from OC-05 Priority Manager for dynamic priority adjustment).

**Outputs:**
- Workflow creation events to OC-02 Workflow Manager.
- Schedule execution log entries to OC-14 State Manager.
- Schedule health metrics to OC-16 Monitoring Manager.

**Dependencies:** OC-02 (workflow creation), OC-05 (priority), OC-14 (state), OC-22 (config).

**Interactions:**
OC-01 interacts directly with OC-02 to create workflow instances. It receives
dynamic priority updates from OC-05 when market conditions change. It consults
OC-22 on startup to load the full schedule configuration.

**Failure Modes:**
- Schedule miss: a scheduled event is not triggered. Detected by OC-16 monitoring
  schedule execution latency. Recovery: OC-01 catches up missed schedules if within
  catchup window (5 minutes); otherwise escalates to OC-17.
- Clock drift: system clock drifts from IST. Mitigated by NTP synchronization.
  OC-16 monitors clock skew; alert if skew exceeds 1 second.
- Calendar corruption: holiday calendar becomes corrupted. Mitigated by readonly
  calendar file with hash verification at startup.

**Recovery Strategy:**
On restart, OC-01 loads the schedule state from OC-14. It evaluates which scheduled
events were missed during the downtime and applies the catchup policy: CRITICAL
schedules that were missed within the last 10 minutes are executed immediately;
others are deferred to the next scheduled time.

**Monitoring:**
- Schedule execution latency per workflow type.
- Schedule miss count per session.
- Clock skew (NTP offset).
- Schedule queue depth.

**Scalability:**
OC-01 supports up to 1,000 distinct schedule entries. For IIOS's 14 named
workflows and their sub-schedules, this capacity is vastly sufficient.

**Extensibility:**
New schedules are added via OC-22 Configuration Manager without modifying OC-01.
New schedule types (cron-style, interval-based, event-triggered) are registered
through the schedule definition format.

**Engineering Notes:**
OC-01 must be deterministic: given the same schedule configuration and clock,
it must produce the same trigger sequence. This enables replay-based testing.
OC-01 must never block: it schedules but does not execute. All execution is
delegated to OC-02 and OC-04.

---

### 3.2 OC-02 — Workflow Manager

**Purpose:**
The Workflow Manager is the owner of all workflow instances. It creates workflow
instances on trigger from OC-01, tracks their state throughout execution, enforces
workflow-level policies, and ensures proper completion (success, failure, or timeout).

**Responsibilities:**
- Creating workflow instances: allocating a unique Workflow Instance ID
  (WF-{PIPELINE_CODE}-{YYYYMMDD}-{SEQ:08d}), recording the trigger event, and
  initializing the workflow state machine to PENDING.
- Loading the workflow definition from the workflow catalog (Supplement B).
- Invoking OC-03 Dependency Manager to validate and build the execution graph.
- Advancing the workflow state machine: PENDING → READY → RUNNING → COMPLETED
  or FAILED or TIMED_OUT.
- Enforcing workflow timeout policies: each workflow has a maximum duration.
  On timeout, OC-02 escalates to OC-17 Incident Manager.
- Recording workflow completion to OC-14 State Manager.
- Triggering downstream workflows on successful completion (chained workflows).

**Inputs:**
- Workflow creation events from OC-01 (scheduled) or OC-04 (event-triggered).
- Workflow definitions from OC-22 Configuration Manager.
- Dependency validation results from OC-03.
- Execution completion events from OC-04 Execution Coordinator.

**Outputs:**
- Workflow state transitions to OC-14 State Manager.
- Execution requests to OC-04 Execution Coordinator (per workflow step).
- Downstream workflow triggers to OC-01 (chained workflows).
- Workflow completion records to OC-20 Reporting Manager.

**Dependencies:** OC-01, OC-03, OC-04, OC-14, OC-20.

**Interactions:**
OC-02 is the central hub of the workflow execution process. Every workflow step
flows through OC-02: dependency check (via OC-03), execution (via OC-04), state
update (via OC-14), completion notification (via OC-20). OC-02 interacts with
every component in the Orchestrator.

**Failure Modes:**
- Workflow state corruption: the workflow state machine enters an invalid state.
  Detected by OC-14 state validation. Recovery: rollback to last valid checkpoint.
- Duplicate workflow creation: two instances of the same workflow run simultaneously.
  Prevented by OC-02's duplicate detection check at creation time.
- Workflow timeout: a workflow step does not complete within its SLA.
  Response: escalate to OC-17; apply timeout recovery procedure.

**Recovery Strategy:**
On restart, OC-02 loads all in-progress workflow states from OC-14. Workflows
in RUNNING state are evaluated: steps that can be safely retried are resubmitted
to OC-04; steps that cannot be safely retried (non-idempotent) are failed and
the workflow transitions to FAILED for manual review.

**Monitoring:**
- Workflow completion rate per pipeline type.
- Workflow duration per pipeline type.
- Workflow failure rate.
- Active workflow count.
- Timeout event count per session.

**Scalability:** Supports up to 100 concurrent workflow instances.
**Extensibility:** New workflow types are registered in the workflow catalog.

---

### 3.3 OC-03 — Dependency Manager

**Purpose:**
The Dependency Manager maintains the complete dependency graph of all IIOS
engines, workflows, and workflow steps. Before any workflow executes, OC-03
validates that all dependencies are satisfied, detects circular dependencies
(architectural errors), and provides the topologically sorted execution order.

**Responsibilities:**
- Maintaining the dependency registry: a directed acyclic graph of all engine-
  to-engine dependencies, workflow-to-workflow dependencies, and step-to-step
  dependencies.
- Performing dependency validation on workflow creation: every new workflow
  instance receives a validated execution plan before it enters RUNNING state.
- Detecting circular dependencies (a fatal architectural error) and escalating
  immediately to OC-17.
- Computing the critical path through complex workflow graphs to inform scheduling
  and resource allocation.
- Monitoring dependency satisfaction in real time: as upstream steps complete,
  OC-03 notifies OC-02 that downstream steps are ready.

**Inputs:**
- Dependency definitions (from OC-22 Configuration Manager).
- Step completion notifications (from OC-04 Execution Coordinator).
- Engine availability updates (from OC-08 Engine Registry).

**Outputs:**
- Execution plans (topologically sorted step sequences) to OC-02.
- Critical path estimates to OC-01 (for scheduling optimization).
- Dependency satisfaction notifications to OC-02 (step ready events).

**Dependencies:** OC-02, OC-04, OC-08, OC-22.

**Failure Modes:**
- Circular dependency: fatal architectural error. Response: halt the affected
  workflow; escalate to Architecture Council.
- Stale dependency data: dependency registry is not updated when an engine is
  deregistered. Mitigated by OC-08 notifying OC-03 on all registry changes.
- Missing dependency: a workflow step has an undeclared dependency. Detected
  by monitoring step execution failures caused by missing inputs.

**Engineering Notes:**
OC-03 stores the dependency graph as an immutable structure for each workflow
type. The graph is validated at startup (OLS-01) and on any engine registry
change (OC-08 → OC-03 notification). Runtime dependency checks are read-only
lookups against this pre-validated graph.

---

### 3.4 OC-04 — Execution Coordinator

**Purpose:**
The Execution Coordinator is the bridge between the Master Orchestrator and
the specialized engines. It translates workflow step execution requests from
OC-02 into engine invocations, receives engine outputs, validates them, and
returns results to OC-02.

**Responsibilities:**
- Receiving step execution requests from OC-02 Workflow Manager.
- Looking up the target engine in OC-08 Engine Registry.
- Checking engine health with OC-15 Health Manager before invoking.
- Allocating execution resources through OC-06 Resource Manager.
- Invoking the target engine according to the defined execution protocol.
- Receiving the engine output and validating it against the expected output schema.
- Recording execution timing, status, and output metadata to OC-14 State Manager.
- Returning execution results to OC-02 for workflow state advancement.

**Critical constraint:** OC-04 NEVER interprets engine outputs for investment
meaning. It validates schema and completeness, not investment correctness. Deciding
whether a prediction is good is the Decision Engine's responsibility.

**Failure Modes:**
- Engine unavailable: target engine is not registered or is unhealthy. Response:
  apply engine substitution policy (if a substitute is registered) or fail the step.
- Engine timeout: engine does not complete within its SLA. Response: increment
  retry counter; on max retries, fail the step and escalate.
- Output validation failure: engine returns malformed output. Response: fail the
  step; escalate to OC-17.
- Resource allocation failure: OC-06 cannot allocate required resources. Response:
  queue the step and retry when resources are available.

---

### 3.5 OC-05 — Priority Manager

**Purpose:**
The Priority Manager maintains the dynamic priority ranking of all active workflows,
pending steps, and resource allocation requests. In a system where multiple workflows
execute concurrently, priority management is essential to ensure that critical
workflows (risk monitoring, governance checks) preempt routine workflows
(learning, simulation) when resources are constrained.

**Responsibilities:**
- Maintaining the priority table: a ranked list of all active workflows and pending
  steps with their current priority level.
- Responding to dynamic priority change requests (e.g., P1 incident triggers
  priority elevation for the Incident Recovery workflow).
- Providing priority comparisons to OC-06 Resource Manager for resource allocation
  decisions.
- Providing priority ordering to OC-01 Master Scheduler for schedule conflict resolution.
- Monitoring for priority inversion: a low-priority task holding a resource needed
  by a high-priority task.

**Priority Levels:**
`
CRITICAL  — Risk monitoring, governance check, kill switch evaluation
HIGH      — Decision workflow, execution workflow, observation workflow
NORMAL    — Prediction workflow, knowledge refresh, portfolio update
LOW       — Learning workflow, simulation run, reporting
DEFERRED  — Non-urgent analytics, historical backtesting
`

**Failure Modes:**
- Priority starvation: DEFERRED tasks never execute because CRITICAL/HIGH tasks
  always preempt. Mitigated by aging: a task's priority increases 1 level after
  waiting 10 minutes beyond its scheduled start.
- Priority inversion: managed by priority inheritance protocol.

---

### 3.6 OC-06 — Resource Manager

**Purpose:**
The Resource Manager governs the allocation of all computational and operational
resources across all engines and workflows. It enforces resource budgets, detects
resource exhaustion, and enables graceful degradation when resources are constrained.

**Responsibilities:**
- Maintaining the real-time resource utilization map: CPU, memory, I/O bandwidth,
  data feed rate limit consumption, queue capacity, and storage I/O.
- Enforcing per-engine resource budgets (configured in OC-22).
- Implementing resource allocation policies: priority-based preemption, fair-share
  allocation for equal-priority workflows.
- Detecting resource exhaustion and triggering the graceful degradation protocol.
- Tracking resource utilization trends for capacity planning (via OC-19 Analytics).

**Resource Categories:**
| Category          | Unit          | Total Budget  | CRITICAL Reserve |
|-------------------|---------------|---------------|------------------|
| CPU               | cores         | Configured    | 20%              |
| Memory            | GB            | Configured    | 10%              |
| Data Feed Rate    | req/min       | Broker limit  | 10%              |
| Queue Capacity    | messages      | 10,000        | 10%              |
| Storage I/O       | IOPS          | Configured    | 5%               |

**Graceful Degradation Protocol:**
When resources reach 90% utilization, OC-06 notifies OC-05 Priority Manager,
which suspends all DEFERRED workflows. At 95%, LOW workflows are suspended.
At 99%, only CRITICAL workflows are permitted.

---

### 3.7 OC-07 — Agent Coordinator

**Purpose:**
The Agent Coordinator manages the coordination of individual AI agents within
IIOS. Each specialized engine contains AI agents; the Agent Coordinator ensures
that agents execute within their authorized parameters, that multi-agent processes
are correctly sequenced, and that runaway agents are detected and contained.

**Responsibilities:**
- Maintaining the agent registry: all registered AI agents with their engine,
  authorized behavioral envelope, and current state.
- Coordinating multi-agent processes: the 5-agent debate in the Decision Engine,
  the evaluation panel in the Strategy Engine, the ensemble prediction in the
  Prediction Engine.
- Enforcing agent behavioral boundaries (defined by the Governance Engine).
- Detecting anomalous agent behavior: an agent that runs significantly longer than
  expected, consumes more resources than its budget, or produces output that is
  structurally invalid.
- Escalating detected anomalies to OC-17 Incident Manager.

**Agent Categories:**
| Category           | Example Agents                    | Invocation Pattern  |
|--------------------|-----------------------------------|---------------------|
| Analysis Agents    | MarketIntelligenceAgent           | Single, sequential  |
| Debate Agents      | BullAgent, BearAgent, NeutralAgent| Multi-agent panel   |
| Evaluation Agents  | ValidationAgent, ScoringAgent     | Single, sequential  |
| Prediction Agents  | EnsembleForecaster, RegimeDetector| Multi-agent ensemble|
| Monitoring Agents  | RiskMonitorAgent, HealthAgent     | Continuous          |

---

### 3.8 OC-08 — Engine Registry

**Purpose:**
The Engine Registry is the authoritative catalog of all registered engines,
components, and AI agents in IIOS. No engine may participate in any workflow
without being registered. The Engine Registry is the first component initialized
at system startup and the last component shut down.

**Responsibilities:**
- Maintaining the engine catalog: Engine ID, Engine Name, Version, Capabilities,
  Dependencies, Resource Budget, Health Status, and Registration Date.
- Processing engine registration requests (OLS-03 Registration Stage).
- Issuing Engine Registration Certificates (ERC-{ENGINE_CODE}-{YYYYMMDD}-{SEQ:04d}).
- Validating engine versions against the authorized version list (from OC-21).
- Broadcasting engine availability/unavailability events to all subscribed components.
- Maintaining the engine capability index: a searchable index of which engine
  provides which capability.

**Engine Registration Record Format:**
`
Engine ID:       OER-{ENGINE_CODE}-{YYYYMMDD}-{SEQ:04d}
Engine Name:     [Full engine name]
Engine Code:     [Short code, e.g. KE, IE, OE]
Version:         [MAJOR.MINOR.PATCH]
Capabilities:    [List of declared capabilities]
Dependencies:    [List of required engine IDs]
Resource Budget: [CPU, Memory, I/O limits]
Health Status:   [HEALTHY / DEGRADED / UNHEALTHY / OFFLINE]
Registered:      [ISO-8601 timestamp]
Certificate:     [ERC ID]
`

**Failure Modes:**
- Unregistered engine invocation: OC-04 attempts to invoke an unregistered engine.
  Prevented by OC-04 always checking OC-08 before invocation. If detected, the
  step fails and escalates.
- Duplicate registration: an engine attempts to register twice. OC-08 rejects the
  second registration and returns the existing record.

**Monitoring:**
- Registered engine count.
- Engine health distribution (HEALTHY/DEGRADED/UNHEALTHY/OFFLINE count).
- Registration events per session.
- Engine availability uptime per session.

---

### 3.9 OC-09 — Engine Discovery Manager

**Purpose:**
The Engine Discovery Manager is responsible for detecting newly available engines
(engines that come online after initial startup), de-registering engines that
become permanently offline, and maintaining the accuracy of the Engine Registry
over time.

**Responsibilities:**
- Executing engine discovery scans on schedule (every 5 minutes during startup,
  every 30 minutes during normal operation).
- Probing candidate engines with a capability handshake protocol.
- Submitting valid discovered engines to OC-08 Engine Registry for registration.
- Detecting engine disappearance (engine that was registered but no longer responds).
- Coordinating with OC-03 Dependency Manager to update dependency graphs when
  engines are added or removed.
- Notifying OC-02 Workflow Manager when an engine whose capability is required
  by an active workflow becomes available.

**Discovery Protocol:**
`
STEP 1: OC-09 sends capability probe to candidate endpoint.
STEP 2: Candidate engine responds with capability manifest.
STEP 3: OC-09 validates manifest completeness and schema.
STEP 4: OC-09 checks engine version against authorized list (OC-21).
STEP 5: OC-09 submits registration request to OC-08.
STEP 6: OC-08 issues Engine Registration Certificate.
STEP 7: OC-09 notifies OC-03 and OC-02 of new registration.
`

---

### 3.10 OC-10 — Communication Manager

**Purpose:**
The Communication Manager governs all communication between the Master Orchestrator
and the specialized engines, and between engines (when routed through the Orchestrator).
All inter-engine communication in IIOS flows through OC-10; no engine communicates
directly with another engine outside this governance layer.

**Responsibilities:**
- Maintaining communication channels between the Orchestrator and all registered engines.
- Enforcing communication protocols: message format, versioning, acknowledgment, timeout.
- Managing communication queues: inbound messages to the Orchestrator, outbound
  messages to engines.
- Enforcing communication security: message authentication, integrity checks.
- Providing message delivery guarantees: at-least-once delivery for CRITICAL messages,
  best-effort for LOW priority messages.
- Recording all communication events in the communication log (to OC-14).

**Communication Modes:**
| Mode               | Description                            | Use Cases               |
|--------------------|----------------------------------------|-------------------------|
| Request-Response   | Synchronous invocation with response   | Engine step execution   |
| Publish-Subscribe  | Asynchronous event broadcast           | State change events     |
| Command            | One-way directive                      | Engine configuration    |
| Query              | Synchronous data request               | Registry lookups        |

**Failure Modes:**
- Communication channel failure: the channel to an engine is broken. Response:
  OC-10 notifies OC-15 Health Manager; marks engine as UNREACHABLE in OC-08;
  triggers OC-17 incident.
- Message queue overflow: inbound queue fills beyond capacity. Response:
  apply back-pressure; suspend non-CRITICAL message senders; escalate.

---

### 3.11 OC-11 — Message Router

**Purpose:**
The Message Router is the routing intelligence within the Communication Manager.
It determines which component should receive each message, applies routing rules,
manages message priorities in the communication queue, and ensures messages are
delivered to the correct destination.

**Responsibilities:**
- Maintaining the routing table: for each message type, the set of authorized
  recipient components.
- Applying routing rules: message type, source engine, destination engine, priority.
- Managing the priority message queue: CRITICAL messages are routed ahead of NORMAL
  messages.
- Implementing dead letter queue: messages that cannot be delivered within their
  TTL (time-to-live) are moved to the dead letter queue and an alert is raised.
- Recording routing decisions to OC-14 State Manager.

**Routing Rule Format:**
`
Message Type:    [Engine output type, e.g. DecisionRecord]
Source:          [Authorized source engine ID]
Destinations:    [List of destination engine IDs or component IDs]
Priority:        [CRITICAL / HIGH / NORMAL / LOW]
TTL:             [Maximum delivery time in seconds]
Acknowledgment:  [REQUIRED / OPTIONAL]
`

**Failure Modes:**
- Unknown message type: a message arrives with a type not in the routing table.
  Response: route to dead letter queue; raise LOW priority alert.
- Delivery failure: message cannot be delivered within TTL. Response: dead letter
  queue; raise alert proportional to message priority.

---

### 3.12 OC-12 — Conflict Resolver

**Purpose:**
The Conflict Resolver detects and resolves conflicts that arise in the orchestration
process. Conflicts occur when two workflows compete for the same resource, when two
engines produce contradictory coordination-level outputs, when a scheduling decision
conflicts with a governance requirement, or when a priority ordering produces
deadlock conditions.

**Responsibilities:**
- Detecting resource conflicts: two workflows requesting the same exclusive resource.
- Detecting scheduling conflicts: two CRITICAL workflows scheduled at the same time.
- Detecting state conflicts: two workflow steps both attempting to modify the same
  state element.
- Detecting governance conflicts: a workflow attempting an action that is prohibited
  by the current governance state (e.g., attempting to execute a trade during a
  kill-switch condition).
- Applying conflict resolution policies to produce a deterministic resolution.
- Recording all conflicts and resolutions to OC-14 and OC-20.

**Conflict Resolution Policies:**
| Conflict Type         | Resolution Policy                                    |
|-----------------------|------------------------------------------------------|
| Resource conflict     | Priority-based: higher priority workflow gets resource|
| Scheduling conflict   | Defer lower-priority workflow by 30 seconds          |
| State conflict        | First-writer wins; second request queued             |
| Governance conflict   | Governance wins; workflow step blocked, escalated    |
| Deadlock              | Identify the lowest-priority participant; abort it   |

**Invariant:** OCC-H-001 — Governance conflicts always resolve in favor of the
Governance Engine. No conflict resolution policy may override a governance rule.

**Failure Modes:**
- Deadlock detection failure: OC-12 fails to detect a deadlock in the resource
  graph. Mitigated by a 30-second deadlock detection watchdog.
- Resolution loop: applying a resolution policy creates a new conflict. Detected
  by counting resolution iterations; escalate after 3 iterations.

---

### 3.13 OC-13 — Synchronization Manager

**Purpose:**
The Synchronization Manager manages synchronization barriers in the workflow
execution graph. When a workflow has a step that requires outputs from multiple
parallel steps, OC-13 maintains the synchronization barrier and releases the
downstream step only when all prerequisites have been satisfied.

**Responsibilities:**
- Maintaining synchronization barriers for all active workflow instances.
- Tracking which parallel steps have completed for each barrier.
- Releasing downstream steps when their barrier conditions are met.
- Enforcing barrier timeout policies: if any parallel step does not complete
  within the barrier timeout, the downstream step is either run with partial
  inputs (if configured as non-strict) or failed (if strict barrier).
- Detecting synchronization deadlocks (barrier waiting on a step that has failed).

**Synchronization Barrier Types:**
| Type                | Description                                     | Behavior on Partial Completion |
|---------------------|-------------------------------------------------|-------------------------------|
| AND barrier         | All steps must complete                         | STRICT: fail if any step fails |
| OR barrier          | At least N of M steps must complete             | Proceed when N completed      |
| QUORUM barrier      | Majority of steps must complete                 | Proceed when > 50% complete   |
| TIMEOUT barrier     | Wait until timeout, then proceed with available | Proceed with what is available|

**Failure Modes:**
- Barrier deadlock: all remaining steps in a barrier have failed or timed out.
  Response: fail the barrier; escalate to OC-17.
- Orphaned barrier: a barrier's workflow was cancelled but the barrier was not
  cleaned up. Detected by OC-14 state reconciliation. Cleaned up on detection.

---

### 3.14 OC-14 — State Manager

**Purpose:**
The State Manager is the single source of truth for all Orchestrator state.
Every component reads state from OC-14 and writes state to OC-14. The State
Manager ensures state consistency, supports rollback to checkpoints, and
maintains the complete operational history of the Orchestrator.

**Responsibilities:**
- Maintaining the complete state of all active and historical workflows,
  engine registrations, schedules, resource allocations, and incidents.
- Providing atomic state update operations: no partial state updates are visible.
- Creating state checkpoints at defined intervals (every 30 seconds during active
  sessions) to support recovery.
- Providing state queries to all other components.
- Maintaining state history: all state changes are recorded with timestamp and
  initiating component ID. State is never overwritten — it is versioned.
- Enforcing state access controls: each component may only read/write its
  authorized state domains.

**State Categories:**
| Category             | Owner Components         | Retention        |
|----------------------|--------------------------|------------------|
| Workflow state       | OC-02                    | Permanent        |
| Schedule state       | OC-01                    | 90 days          |
| Engine registry      | OC-08                    | Permanent        |
| Resource state       | OC-06                    | 7 days           |
| Communication state  | OC-10                    | 7 days           |
| Incident state       | OC-17                    | Permanent        |
| Recovery state       | OC-18                    | 1 year           |
| Analytics state      | OC-19                    | 3 years          |

**Invariant:** OC-14 never deletes any state in its permanent categories.
Historical state is archived, not deleted.

**Failure Modes:**
- State storage failure: the underlying storage becomes unavailable. This is a
  P1 incident. Recovery requires restoring from the latest checkpoint.
- State corruption: state data is corrupted. Detected by hash verification on
  every state read. Response: rollback to last valid checkpoint.

---

### 3.15 OC-15 — Health Manager

**Purpose:**
The Health Manager continuously monitors the health of all registered engines,
all Orchestrator components, and the IIOS system as a whole. It computes the
Orchestrator Health Score (OHS) and triggers health-state transitions and
escalations.

**Responsibilities:**
- Executing health probes against all registered engines at configurable intervals.
- Computing health scores for individual engines and system-wide.
- Maintaining health state machines for each engine (HEALTHY / DEGRADED / UNHEALTHY / OFFLINE).
- Triggering health state transitions based on probe results.
- Escalating health degradations to OC-17 Incident Manager.
- Providing health status to OC-04 Execution Coordinator before every engine invocation.

**Orchestrator Health Score (OHS) Formula:**

OHS = SUM(component_health_score * component_weight)

Where component weights reflect operational importance.

**OHS Tiers:**
| Tier      | OHS Range  | Operational Mode                                    |
|-----------|------------|-----------------------------------------------------|
| OPTIMAL   | 0.95 – 1.00| Full operation; all workflows active                |
| NOMINAL   | 0.80 – 0.94| Full operation; minor degradation tolerated         |
| DEGRADED  | 0.60 – 0.79| Reduced operation; non-critical workflows suspended |
| CRITICAL  | 0.35 – 0.59| Minimal operation; only CRITICAL workflows active   |
| FAILED    | 0.00 – 0.34| System halt; human intervention required            |

**Health Probe Interval by Engine Priority:**
| Priority  | Probe Interval  | Consecutive Failures Before Alert |
|-----------|-----------------|-----------------------------------|
| CRITICAL  | 10 seconds      | 2                                 |
| HIGH      | 30 seconds      | 3                                 |
| NORMAL    | 60 seconds      | 3                                 |
| LOW       | 5 minutes       | 5                                 |

---

### 3.16 OC-16 — Monitoring Manager

**Purpose:**
The Monitoring Manager provides comprehensive operational visibility into all
aspects of the Master Orchestrator. It collects metrics from all components,
evaluates metrics against thresholds, and provides the data that drives the
Orchestrator monitoring dashboard.

**Responsibilities:**
- Collecting operational metrics from all 22 components (latency, throughput,
  error rates, queue depths, state counts).
- Evaluating metrics against configured WARN and CRIT thresholds.
- Publishing metric events to the Orchestrator monitoring dashboard (L17 ControlTower).
- Detecting anomalous patterns: sudden latency spikes, error rate increases,
  throughput drops.
- Providing metric history to OC-19 Analytics Manager for trend analysis.

**Key Metrics:**
`
Workflow execution latency (per pipeline type)
Engine invocation latency (per engine)
Schedule execution lag (per scheduled workflow)
Resource utilization (CPU, memory, I/O, queues)
Message queue depth and processing rate
Health probe success rate (per engine)
Incident count and resolution time (per severity)
Conflict count and resolution time (per type)
Synchronization barrier completion time
Recovery procedure success rate
`

**Monitoring Dashboard Summary Panel:**
`
+-----------------------------------------------------------------+
|  MASTER ORCHESTRATOR OPERATIONAL STATUS                         |
|  OHS: 0.98 [OPTIMAL]        Active Workflows: 3                |
|  Scheduled Events Today: 47  Completed: 44  Pending: 3         |
|  Engine Registry: 15 HEALTHY, 0 DEGRADED, 0 OFFLINE            |
|  Incidents Today: 0          Open Incidents: 0                  |
|  Resource Utilization: CPU 45%  Memory 38%  Queue 12%           |
+-----------------------------------------------------------------+
`

---

### 3.17 OC-17 — Incident Manager

**Purpose:**
The Incident Manager receives, classifies, escalates, and coordinates the
resolution of all operational incidents in the Master Orchestrator. An incident
is any event that deviates from expected behavior and requires coordinated response.

**Responsibilities:**
- Receiving incident signals from all Orchestrator components.
- Classifying incidents by severity: P1 (1 hour), P2 (4 hours), P3 (1 business
  day), P4 (5 business days).
- Creating incident records with a unique Incident ID.
- Routing incident notifications to the appropriate responders.
- Coordinating incident response: triggers OC-18 Recovery Manager for automated
  recovery, notifies Operations Lead for human-required incidents.
- Tracking incident resolution and recording post-incident review outcomes.

**Incident Classification:**
| Severity | Criteria                                       | Response Time | Human Required? |
|----------|------------------------------------------------|---------------|-----------------|
| P1       | System halt, live trading affected             | 1 hour        | Always          |
| P2       | Degraded operation, active workflow impacted   | 4 hours       | Usually         |
| P3       | Non-critical component failure                 | 1 business day| Sometimes       |
| P4       | Warning threshold crossed, no active impact    | 5 business days| Rarely         |

**Incident Record Format:**
`
Incident ID:     OINC-{SEVERITY}-{YYYYMMDD}-{SEQ:04d}
Title:           [Brief description]
Severity:        [P1 / P2 / P3 / P4]
Detected:        [ISO-8601 timestamp]
Source:          [Component or engine that generated the signal]
Affected:        [Workflows, engines, or system areas affected]
Root Cause:      [Initial assessment; updated during investigation]
Status:          [OPEN / INVESTIGATING / RESOLVING / RESOLVED / CLOSED]
Resolution:      [Actions taken; if automated recovery, procedure name]
Resolved:        [ISO-8601 timestamp]
`

---

### 3.18 OC-18 — Recovery Manager

**Purpose:**
The Recovery Manager maintains the library of automated recovery procedures and
executes them when OC-17 Incident Manager triggers a recovery action. Recovery
must be rapid, reliable, and safe.

**Responsibilities:**
- Maintaining the recovery procedure library.
- Executing recovery procedures in the correct sequence.
- Verifying that recovered components pass health checks after recovery.
- Recording recovery execution results to OC-14 State Manager.
- Escalating to human operator when automated recovery fails or is not applicable.

**Recovery Procedures:**
| Procedure ID | Name                        | Trigger                          | SLA   |
|--------------|-----------------------------|----------------------------------|-------|
| ORP-01       | Engine Restart              | Engine UNHEALTHY                 | 30s   |
| ORP-02       | Workflow Restart            | Workflow TIMED_OUT (retryable)   | 60s   |
| ORP-03       | Communication Reconnect     | Channel BROKEN                   | 15s   |
| ORP-04       | State Checkpoint Restore    | State corruption detected        | 120s  |
| ORP-05       | Scheduler Resync            | Schedule miss > 5 minutes        | 30s   |
| ORP-06       | Resource Limit Reset        | Resource deadlock detected       | 30s   |
| ORP-07       | Conflict Resolver Reset     | Resolution loop detected         | 15s   |
| ORP-08       | Session Emergency Stop      | OHS FAILED                       | 10s   |

**Recovery Safety Rule:** No recovery procedure may open a new position, close
an existing position, or modify any risk limit. Recovery is operational only.

---

### 3.19 OC-19 — Analytics Manager

**Purpose:**
The Analytics Manager collects operational performance data from all components
and produces trend analysis, performance insights, and improvement recommendations
for the Master Orchestrator.

**Responsibilities:**
- Collecting historical performance data from OC-16 Monitoring Manager.
- Computing trend metrics: workflow duration trends, engine invocation latency
  trends, resource utilization trends, incident frequency trends.
- Detecting performance degradation patterns before they become incidents.
- Computing the Orchestrator Performance Score (OPS) for each session.
- Producing analytics reports for OC-20 Reporting Manager.
- Providing insights to human operators about scheduling optimization opportunities.

**Key Analytics Products:**
| Product                  | Frequency  | Audience        |
|--------------------------|------------|-----------------|
| Session Performance Report| Daily     | Operations Lead |
| Weekly Trend Analysis    | Weekly     | Architecture Council|
| Engine Reliability Report| Weekly     | All teams       |
| Capacity Utilization Report| Monthly  | Infrastructure  |
| Incident Trend Report    | Monthly    | Operations Lead |

---

### 3.20 OC-20 — Reporting Manager

**Purpose:**
The Reporting Manager produces all operational reports from the Master Orchestrator
and distributes them to the appropriate audiences. Reports provide systematic
visibility into Orchestrator operations.

**Report Schedule:**
| Report                          | Frequency   | Trigger          |
|---------------------------------|-------------|------------------|
| Session Operational Summary     | Daily       | Market close     |
| Workflow Execution Report       | Daily       | Market close     |
| Engine Health Report            | Daily       | Market close     |
| Incident Report                 | On incident | P1/P2 immediately|
| Weekly Operations Review        | Weekly      | Friday post-close|
| Monthly Performance Report      | Monthly     | Month end        |

---

### 3.21 OC-21 — Version Manager

**Purpose:**
The Version Manager maintains the authoritative list of authorized engine versions
for IIOS. Every engine version must be authorized before it can be registered.
The Version Manager works with OC-08 Engine Registry to enforce version governance.

**Responsibilities:**
- Maintaining the authorized version registry: engine code, authorized versions,
  release dates, and deprecation dates.
- Rejecting engine registrations that reference unauthorized versions.
- Notifying OC-09 Engine Discovery Manager when a new version is authorized.
- Tracking version usage statistics.
- Enforcing version retirement: when a version's deprecation date passes, engines
  using that version are flagged for upgrade.

**Version Authorization Format:**
`
Engine Code:        [Short code, e.g. KE, IE, OE]
Version:            [MAJOR.MINOR.PATCH]
Authorized Date:    [ISO-8601]
Authorized By:      [Architecture Council reference]
Deprecation Date:   [ISO-8601 or NONE]
Status:             [AUTHORIZED / DEPRECATED / RETIRED]
SHA-256 Hash:       [Hash of the authorized engine package]
`

---

### 3.22 OC-22 — Configuration Manager

**Purpose:**
The Configuration Manager is the source of all runtime configuration for the
Master Orchestrator. It loads configuration at startup, validates it against
the configuration schema, and provides configuration values to all components
on request.

**Responsibilities:**
- Loading the master configuration from the configuration store at startup.
- Validating configuration completeness and correctness (all required fields
  present; values within allowed ranges).
- Providing configuration values to all components through a typed configuration
  query interface.
- Detecting configuration changes and notifying affected components.
- Maintaining configuration version history.
- Providing configuration audit records to OC-14 State Manager.

**Configuration Categories:**
| Category              | Examples                                      |
|-----------------------|-----------------------------------------------|
| Schedule config       | Workflow schedules, trading calendar          |
| Engine config         | Engine endpoints, resource budgets, timeouts  |
| Priority config       | Priority levels per workflow type             |
| Resource config       | Total resource budgets, reserve percentages   |
| Health config         | Probe intervals, failure thresholds           |
| Monitoring config     | Metric thresholds (WARN/CRIT)                 |
| Recovery config       | Recovery procedure parameters                 |
| Governance config     | Governance Engine connection, certificate TTL |

---

## PART IV — ORCHESTRATION LIFECYCLE

### 4.1 Lifecycle Stage Reference

The Master Orchestrator lifecycle defines 12 stages from initial boot through
orderly shutdown. These stages apply to the Orchestrator itself (system-level
lifecycle) and to each individual workflow instance (workflow-level lifecycle).

#### System-Level Lifecycle Stages

| ID     | Stage Name           | Description                                          | Duration Limit  |
|--------|----------------------|------------------------------------------------------|-----------------|
| OLS-01 | Initialization       | Boot, configuration load, component startup          | 60 seconds      |
| OLS-02 | Engine Discovery     | Probe and catalog all available engines              | 120 seconds     |
| OLS-03 | Registration         | Register all engines and issue certificates          | 60 seconds      |
| OLS-04 | Dependency Validation| Validate complete dependency graph; detect cycles    | 30 seconds      |
| OLS-05 | Health Assessment    | Initial health probe of all registered engines       | 30 seconds      |
| OLS-06 | Governance Cert.     | Obtain Governance Readiness Certificate from Gov.Eng.| 300 seconds     |
| OLS-07 | Ready                | System operational; workflows may be scheduled       | Indefinite      |
| OLS-08 | Active Session       | Market hours operation; full workflow execution      | Market hours    |
| OLS-09 | Post-Session         | End-of-day processing; learning; archiving           | 120 minutes     |
| OLS-10 | Maintenance          | Optional: upgrades, configuration changes            | Scheduled       |
| OLS-11 | Pre-Shutdown         | Drain active workflows; final state commit           | 60 seconds      |
| OLS-12 | Shutdown             | Orderly component shutdown; final archiving          | 60 seconds      |

#### Workflow-Level Lifecycle Stages

| ID     | Stage Name           | Trigger                            | Exit Conditions               |
|--------|----------------------|------------------------------------|-------------------------------|
| WLS-01 | Pending              | Workflow creation event            | Dependencies satisfied        |
| WLS-02 | Ready                | All dependencies satisfied         | Execution request submitted   |
| WLS-03 | Running              | First step execution begins        | All steps complete or fail    |
| WLS-04 | Synchronizing        | Parallel step synchronization wait | All barrier conditions met    |
| WLS-05 | Completed            | All steps succeeded                | Archive triggered             |
| WLS-06 | Failed               | Unrecoverable step failure         | Incident triggered            |
| WLS-07 | Timed Out            | Workflow max duration exceeded     | Incident triggered            |
| WLS-08 | Recovering           | OC-18 Recovery procedure active    | Recovery succeeded or failed  |
| WLS-09 | Cancelled            | Manual cancellation received       | Cleanup triggered             |
| WLS-10 | Archived             | Completion archived                | Terminal state                |

---

### 4.2 System Lifecycle State Diagram

`
  +--[POWER ON]--+
  |              |
  v              |
OLS-01           |
INIT             |
  |              |
  v              |
OLS-02           |
ENGINE DISCOVERY |
  |              |
  v              |
OLS-03           |
REGISTRATION     |
  |              |
  v              |
OLS-04           |
DEP VALIDATION   |
  |              |
  v              |
OLS-05           |
HEALTH ASSESS    |
  |              |
  v              |
OLS-06           |
GOV CERT         |
  |  CERT DENIED ---> SAFE MODE ---> Human Intervention
  v
OLS-07
READY
  |
  +--> [09:00 IST] --> OLS-08 ACTIVE SESSION
  |                         |
  |                    [15:30 IST]
  |                         v
  |                    OLS-09 POST-SESSION
  |                         |
  |                    [Complete]
  |                         v
  |                    OLS-07 READY
  |
  +--> [SHUTDOWN SIGNAL]
            |
            v
       OLS-11 PRE-SHUTDOWN
            |
            v
       OLS-12 SHUTDOWN
`

---

### 4.3 Workflow Lifecycle State Diagram

`
         [Trigger]
             |
             v
       +----------+
       | WLS-01   |
       | PENDING  |
       +----------+
             |
       [Deps. OK]
             |
             v
       +----------+
       | WLS-02   |
       |  READY   |
       +----------+
             |
       [Submit to
        OC-04]
             v
       +----------+
       | WLS-03   |
       | RUNNING  |
       +----------+
        |         |
  [Parallel]  [Sequential]
        |         |
        v         |
  +----------+    |
  | WLS-04   |    |
  |  SYNC    |----+
  +----------+
        |
  [Barrier OK]   [Barrier FAIL]
        |               |
        v               v
  +----------+    +----------+
  | WLS-05   |    | WLS-06   |
  |COMPLETED |    |  FAILED  |
  +----------+    +----------+
        |               |
   [Archive]      [OC-17 Incident]
        v               |
  +----------+    [OC-18 Recover?]
  | WLS-10   |          |
  | ARCHIVED |    [WLS-08 RECOVERING]
  +----------+          |
                  [Success] [Fail]
                     |         |
                  WLS-03    WLS-06
`

---

### 4.4 Lifecycle Timing Reference

**System startup timing (T-60 to T-00 before market open):**

| Time     | Stage     | Activity                                              |
|----------|-----------|-------------------------------------------------------|
| T-60     | OLS-01    | Orchestrator boot; configuration load; component init |
| T-55     | OLS-02    | Engine discovery scans begin                          |
| T-45     | OLS-03    | Engine registrations processed; certificates issued   |
| T-40     | OLS-04    | Full dependency graph validation                      |
| T-35     | OLS-05    | Health probes; initial OHS computed                   |
| T-30     | OLS-06    | Governance certification request submitted            |
| T-20     | OLS-06    | Governance Engine returns Readiness Certificate       |
| T-15     | OLS-07    | System enters READY state; pre-session pipelines begin|
| T-10     | OLS-07    | Knowledge refresh pipeline (OP-04) executed           |
| T-05     | OLS-07    | Observation pipeline (OP-03) first cycle executed     |
| T-00     | OLS-08    | Market open; full active session mode                 |

---

## PART V — ORCHESTRATION SERVICES

### Service Reference Table

| ID    | Service Name            | Tier | SLA    | Primary Components     |
|-------|-------------------------|------|--------|------------------------|
| OS-01 | Scheduling Service      | 1    | 99.99% | OC-01, OC-05           |
| OS-02 | Workflow Service        | 1    | 99.99% | OC-02, OC-03, OC-04    |
| OS-03 | Dependency Service      | 1    | 99.99% | OC-03, OC-08           |
| OS-04 | Coordination Service    | 1    | 99.99% | OC-04, OC-07           |
| OS-05 | Communication Service   | 2    | 99.95% | OC-10, OC-11           |
| OS-06 | Synchronization Service | 2    | 99.95% | OC-13, OC-14           |
| OS-07 | Resource Service        | 2    | 99.90% | OC-06, OC-05           |
| OS-08 | Priority Service        | 2    | 99.99% | OC-05, OC-12           |
| OS-09 | Health Service          | 3    | 99.99% | OC-15, OC-16           |
| OS-10 | Monitoring Service      | 3    | 99.95% | OC-16, OC-19           |
| OS-11 | Recovery Service        | 3    | 99.90% | OC-18, OC-17           |
| OS-12 | Incident Service        | 3    | 99.99% | OC-17, OC-11           |
| OS-13 | Analytics Service       | 4    | 99.80% | OC-19, OC-20           |
| OS-14 | Reporting Service       | 4    | 99.80% | OC-20, OC-19           |
| OS-15 | Configuration Service   | 4    | 99.99% | OC-22, OC-21           |

---

### OS-01 — Scheduling Service

**Purpose:** The Scheduling Service provides time-based and event-based workflow
execution triggering. Every scheduled event in IIOS flows through OS-01.

**Operations:**
- SCHEDULE_WORKFLOW: register a new schedule entry.
- TRIGGER_WORKFLOW: immediately trigger a workflow.
- SUSPEND_SCHEDULE: temporarily suspend a schedule entry.
- RESUME_SCHEDULE: resume a suspended schedule entry.
- QUERY_SCHEDULE: retrieve schedule state and next execution time.

**Authorization:** Schedule modification requires OT-11 (Governance Orchestration)
approval for schedules affecting CRITICAL workflows. Routine schedule queries
require NORMAL authorization.

**SLA:** Schedule trigger must occur within 1 second of the scheduled time.

---

### OS-02 — Workflow Service

**Purpose:** The Workflow Service manages the full lifecycle of workflow instances,
from creation through archiving.

**Operations:**
- CREATE_WORKFLOW: create a new workflow instance.
- ADVANCE_WORKFLOW: advance a workflow to the next step.
- CANCEL_WORKFLOW: cancel a running workflow.
- QUERY_WORKFLOW: retrieve workflow state and history.
- LIST_WORKFLOWS: list all active and recent workflows.

**SLA:** Workflow step transition must complete within 500ms.

---

### OS-03 — Dependency Service

**Purpose:** The Dependency Service maintains and validates the complete dependency
graph of all IIOS engines and workflow steps.

**Operations:**
- VALIDATE_DEPENDENCIES: validate that all dependencies for a workflow are satisfied.
- COMPUTE_EXECUTION_ORDER: return the topologically sorted execution order.
- COMPUTE_CRITICAL_PATH: return the critical path through a workflow.
- REGISTER_DEPENDENCY: add a new dependency to the registry.
- QUERY_DEPENDENCY: retrieve dependency information.

**SLA:** Dependency validation must complete within 200ms.

---

### OS-04 — Coordination Service

**Purpose:** The Coordination Service bridges the Orchestrator to individual engines.
It handles all engine invocations and output routing.

**Operations:**
- INVOKE_ENGINE: invoke a registered engine for a workflow step.
- QUERY_ENGINE_STATUS: retrieve the current status of an engine invocation.
- ABORT_ENGINE_INVOCATION: abort an in-progress engine invocation.
- ROUTE_OUTPUT: route an engine's output to the appropriate downstream step.

**SLA:** Engine invocation setup latency must be < 50ms. Total invocation latency
depends on the engine; the Coordination Service adds no more than 100ms overhead.

---

### OS-05 — Communication Service

**Purpose:** The Communication Service governs all inter-component messaging.

**Operations:**
- SEND_MESSAGE: send a message to a registered destination.
- BROADCAST_EVENT: broadcast an event to all subscribers.
- SUBSCRIBE: subscribe a component to an event type.
- QUERY_DELIVERY_STATUS: check the delivery status of a sent message.
- DEAD_LETTER_REPORT: report messages in the dead letter queue.

**SLA:** Message delivery latency < 10ms for CRITICAL; < 100ms for NORMAL.

---

### OS-06 — Synchronization Service

**Purpose:** The Synchronization Service manages all synchronization barriers
in the workflow execution graph.

**Operations:**
- CREATE_BARRIER: create a synchronization barrier for a workflow step.
- MARK_COMPLETE: mark a participant step as complete.
- WAIT_FOR_BARRIER: block downstream step until barrier releases.
- QUERY_BARRIER_STATUS: retrieve current barrier state.
- FORCE_RELEASE_BARRIER: emergency barrier release (human override only).

**SLA:** Barrier state update latency < 10ms.

---

### OS-07 — Resource Service

**Purpose:** The Resource Service allocates and monitors computational resources
across all active workflows.

**Operations:**
- ALLOCATE_RESOURCES: allocate resources for a workflow step.
- RELEASE_RESOURCES: release resources after a step completes.
- QUERY_UTILIZATION: retrieve current resource utilization.
- SET_BUDGET: configure a resource budget for an engine or workflow.
- ENFORCE_PREEMPTION: preempt a low-priority resource consumer.

---

### OS-08 — Priority Service

**Purpose:** The Priority Service provides priority management for workflows,
steps, and resource allocation requests.

**Operations:**
- GET_PRIORITY: get the current priority of a workflow or step.
- SET_PRIORITY: set the priority (authorized contexts only).
- COMPARE_PRIORITY: compare two items for scheduling decisions.
- ELEVATE_PRIORITY: temporarily elevate priority (incident response).
- RESTORE_PRIORITY: restore priority after elevation expires.

---

### OS-09 — Health Service

**Purpose:** The Health Service provides real-time health status for all registered
engines and the Orchestrator system as a whole.

**Operations:**
- PROBE_ENGINE: execute a health probe against an engine.
- GET_ENGINE_HEALTH: retrieve the current health state of an engine.
- GET_OHS: retrieve the current Orchestrator Health Score.
- GET_HEALTH_HISTORY: retrieve health history for trend analysis.
- REGISTER_HEALTH_ALERT: register a health threshold alert.

---

### OS-10 — Monitoring Service

**Purpose:** The Monitoring Service provides access to all operational metrics.

**Operations:**
- RECORD_METRIC: record a metric value.
- QUERY_METRIC: retrieve metric values and history.
- SET_THRESHOLD: configure a metric threshold.
- GET_ALERTS: retrieve active threshold alerts.

---

### OS-11 — Recovery Service

**Purpose:** The Recovery Service executes automated recovery procedures.

**Operations:**
- EXECUTE_RECOVERY: execute a named recovery procedure.
- QUERY_RECOVERY_STATUS: retrieve the status of an in-progress recovery.
- REGISTER_PROCEDURE: register a new recovery procedure.
- QUERY_PROCEDURE: retrieve a recovery procedure definition.

---

### OS-12 — Incident Service

**Purpose:** The Incident Service manages the full lifecycle of operational incidents.

**Operations:**
- RAISE_INCIDENT: create a new incident record.
- UPDATE_INCIDENT: update incident status or information.
- RESOLVE_INCIDENT: mark an incident as resolved.
- QUERY_INCIDENT: retrieve incident information.
- LIST_INCIDENTS: list active or historical incidents.

---

### OS-13 — Analytics Service

**Purpose:** The Analytics Service provides performance trend analysis.

**Operations:**
- COMPUTE_TREND: compute a trend for a given metric over a period.
- GET_SESSION_PERFORMANCE: retrieve session performance summary.
- GET_ENGINE_RELIABILITY: retrieve engine reliability statistics.
- GENERATE_CAPACITY_REPORT: generate a capacity utilization report.

---

### OS-14 — Reporting Service

**Purpose:** The Reporting Service generates and distributes operational reports.

**Operations:**
- GENERATE_REPORT: generate a named report.
- DISTRIBUTE_REPORT: distribute a report to configured recipients.
- QUERY_REPORT: retrieve a historical report.
- SCHEDULE_REPORT: schedule recurring report generation.

---

### OS-15 — Configuration Service

**Purpose:** The Configuration Service provides access to all runtime configuration.

**Operations:**
- GET_CONFIG: retrieve a configuration value.
- SET_CONFIG: update a configuration value (authorized contexts only).
- VALIDATE_CONFIG: validate a configuration set.
- GET_CONFIG_HISTORY: retrieve configuration change history.
- RELOAD_CONFIG: reload configuration from the configuration store.

---

## PART VI — WORKFLOW PIPELINES

### Pipeline Reference Table

| ID    | Pipeline Name              | Priority  | Trigger               | Max Duration  |
|-------|----------------------------|-----------|-----------------------|---------------|
| OP-01 | System Startup Pipeline    | CRITICAL  | System boot           | 10 minutes    |
| OP-02 | Daily Market Pipeline      | CRITICAL  | 09:00 IST             | 15 minutes    |
| OP-03 | Observation Pipeline       | HIGH      | Continuous / 30s      | 25 seconds    |
| OP-04 | Knowledge Pipeline         | HIGH      | Daily / event         | 20 minutes    |
| OP-05 | Prediction Pipeline        | HIGH      | Post-observation      | 60 seconds    |
| OP-06 | Decision Pipeline          | CRITICAL  | Post-prediction       | 30 seconds    |
| OP-07 | Risk Pipeline              | CRITICAL  | Post-decision         | 15 seconds    |
| OP-08 | Portfolio Pipeline         | HIGH      | Post-execution        | 30 seconds    |
| OP-09 | Learning Pipeline          | LOW       | Post-session          | 120 minutes   |
| OP-10 | Strategy Pipeline          | HIGH      | Weekly / on-demand    | 60 minutes    |
| OP-11 | Simulation Pipeline        | NORMAL    | Scheduled / on-demand | 4 hours       |
| OP-12 | Governance Pipeline        | CRITICAL  | Continuous / session  | 60 minutes    |
| OP-13 | System Shutdown Pipeline   | CRITICAL  | Shutdown signal       | 5 minutes     |
| OP-14 | Failure Recovery Pipeline  | CRITICAL  | Incident P1/P2        | 30 minutes    |

---

### OP-01 — System Startup Pipeline

**Purpose:** Initializes the complete IIOS system in a defined, validated sequence
before market operations begin.

**Trigger:** System boot signal (automated via OS Task Scheduler or manual).

**Architecture Diagram:**
`
[SYSTEM BOOT]
     |
     v
[OLS-01: Orchestrator Initialization]
     |
     v
[OC-22 Load Configuration]
  |
  v
[OC-08 Initialize Engine Registry]
  |
  v
[OLS-02: Engine Discovery]
  OC-09 discovers all available engines
  |
  v
[OLS-03: Registration]
  OC-08 registers all discovered engines
  OC-21 validates all versions
  |
  v
[OLS-04: Dependency Validation]
  OC-03 validates complete dependency graph
  Detects circular dependencies (FATAL if found)
  |
  v
[OLS-05: Health Assessment]
  OC-15 probes all engines
  OC-06 initializes resource allocations
  |
  v
[OLS-06: Governance Certification]
  Request Governance Readiness Certificate
  from Governance Engine (IIOS-GOV-ENG-ARCH-001)
  BLOCKED until certificate received
  |
  v
[Infrastructure Checks: Network, Storage, Data Feeds]
  |
  v
[Knowledge Engine warm-up]
  Execute OP-04 Knowledge Pipeline (pre-session)
  |
  v
[OLS-07: READY STATE]
  |
  v
[PIPELINE COMPLETE — System ready for market operation]
`

**Success Criteria:**
- OHS >= 0.80 (NOMINAL or better).
- Governance Readiness Certificate obtained.
- All CRITICAL engines registered and HEALTHY.
- Dependency graph validated with zero circular dependencies.
- Configuration loaded and validated.

**Failure Handling:** If any CRITICAL step fails, the system halts in SAFE mode.
Human intervention is required. Partial startup (some engines unavailable) is
permitted if the available engines can support minimal safe operation.

---

### OP-02 — Daily Market Pipeline

**Purpose:** Performs the complete pre-market session initialization immediately
before market open. Runs after OP-01 on the first session of the day, or on
subsequent days when the system has been running overnight.

**Trigger:** 09:00 IST (with pre-execution starting at T-15).

**Architecture Diagram:**
`
[T-15: PRE-MARKET PREPARATION]
     |
     v
[Daily Governance Check]
  Governance Engine validates session authorization
  Kill switch configuration verified
  |
  v
[Market Data Feed Validation]
  All configured feeds verified responsive
  Instrument reference data refreshed
  |
  v
[Risk Limit Validation]
  Daily loss counter reset to zero
  All risk limits loaded and validated
  Constitutional limits confirmed active
  |
  v
[Strategy Activation Check]
  All live strategies confirmed registered
  Strategy weights normalized
  Governance certificates current
  |
  v
[Portfolio State Load]
  Previous session positions loaded and reconciled
  Portfolio Engine initialized with current state
  |
  v
[T-00: MARKET OPEN]
  OLS-08 Active Session mode engaged
  OP-03 Observation Pipeline begins continuous execution
  OP-12 Governance Pipeline begins continuous monitoring
  |
  v
[PIPELINE COMPLETE — Session active]
`

---

### OP-03 — Observation Pipeline

**Purpose:** Transforms raw market data into structured Observation records.
This is the highest-frequency pipeline in IIOS, executing every 30 seconds
during market hours.

**Trigger:** Continuous during market hours (09:15 IST to 15:30 IST). Also
triggered by significant market events (circuit breakers, large price moves).

**Architecture Diagram:**
`
[TRIGGER: 30-second timer OR market event]
     |
     v
[Data Feed Collection]
  Fetch price, volume, order book data
  from active data feeds
  |
  v
[Observation Engine Invocation]
  (IIOS-OBS-ARCH-001)
  Transform raw data to typed Observations
  Classify: price, volume, breadth, sentiment
  |
  v
[Entity Engine Update]
  (IIOS-ENT-ARCH-001)
  Update entity observation state
  |
  v
[Event Engine Evaluation]
  (IIOS-EVT-ARCH-001)
  Evaluate whether observations trigger events
  |
  v
[Observation Freshness Record]
  Update observation timestamp in OC-14 State Manager
  Notify downstream pipelines that fresh observations available
  |
  v
[PIPELINE COMPLETE — Observations available]
  Triggers OP-05 Prediction Pipeline if due
`

**Latency SLA:** Full pipeline completion within 25 seconds.

---

### OP-04 — Knowledge Pipeline

**Purpose:** Refreshes the IIOS institutional knowledge base by integrating new
observations, outcomes, and learnings into the Knowledge Engine.

**Trigger:** Daily pre-session (T-10 before market open). Also triggered post-
session after OP-09 Learning Pipeline completes.

**Architecture Diagram:**
`
[TRIGGER: Daily pre-session OR post-learning signal]
     |
     v
[Knowledge Engine Refresh Request]
  (IIOS-KE-ARCH-001)
  Process new market observations since last refresh
  |
  v
[Entity Knowledge Update]
  Update entity profiles with new observations
  |
  v
[Relationship Knowledge Update]
  (IIOS-REL-ARCH-001)
  Update relationship network with new data
  |
  v
[Event Knowledge Update]
  (IIOS-EVT-ARCH-001)
  Archive recent events; update event patterns
  |
  v
[Knowledge Validation]
  Knowledge Engine validates internal consistency
  Knowledge quality score computed
  |
  v
[Knowledge Freshness Record]
  Update knowledge timestamp in OC-14
  Notify all consumers: Prediction, Decision, Risk Engines
  |
  v
[PIPELINE COMPLETE — Knowledge current]
`

---

### OP-05 — Prediction Pipeline

**Purpose:** Generates probabilistic market forecasts and strategy performance
predictions for the current session context.

**Trigger:** After each OP-03 Observation Pipeline cycle (when observations
are fresh enough to warrant a new prediction cycle, per configured interval).
Typically every 5–15 minutes during market hours.

**Architecture Diagram:**
`
[TRIGGER: Fresh observations available + prediction interval elapsed]
     |
     v
[Prerequisite Check]
  Observations fresh (within 30 seconds)?
  Knowledge current (within 24 hours)?
  Prediction Engine HEALTHY?
  All checks PASS: proceed
  Any check FAIL: defer prediction
  |
  v
[Market Regime Assessment]
  Feed current observations to regime classifier
  Update regime probability distribution
  |
  v
[Prediction Engine Invocation]
  (IIOS-PRD-ARCH-001)
  Generate forecasts for configured horizons
  Compute confidence intervals
  Produce risk scenario predictions
  |
  v
[Prediction Quality Assessment]
  Prediction confidence meets minimum threshold?
  Calibration score acceptable?
  |
  v
[Prediction Artifact Publication]
  Route prediction artifacts to Decision Engine
  Route prediction artifacts to Risk Engine
  Update prediction timestamp in OC-14
  |
  v
[PIPELINE COMPLETE — Predictions available]
  Triggers OP-06 Decision Pipeline if decision cycle due
`

---

### OP-06 — Decision Pipeline

**Purpose:** Produces investment decisions from current predictions, knowledge,
and risk context. The Decision Pipeline is the most consequential pipeline in
IIOS — its output triggers actual trade execution.

**Trigger:** Post-prediction, when all prerequisites are satisfied.

**Architecture Diagram:**
`
[TRIGGER: Fresh predictions available + decision cycle due]
     |
     v
[Complete Pre-Decision Gate]
  Observations current?         REQUIRED
  Predictions current?          REQUIRED
  Risk limits not breached?     REQUIRED
  Governance session active?    REQUIRED
  Kill switch NOT triggered?    REQUIRED
  Daily loss < 2% limit?        REQUIRED
  ALL GATES PASS: proceed
  ANY GATE FAIL: block, log, alert
  |
  v
[Decision Engine Invocation]
  (IIOS-DEC-ARCH-001)
  5-agent debate process
  BullAgent / BearAgent / NeutralAgent / RiskAgent / RegimeAgent
  Debate produces composite score (0-10)
  |
  v
[Decision Threshold Evaluation]
  Score >= 6.5? -> APPROVED for risk review
  Score < 6.5? -> REJECTED, record reason
  Score >= 9.0 and extreme conditions? -> ESCALATE to human
  |
  v
[Approved Decision Routing]
  Route Decision Record to OP-07 Risk Pipeline
  Log decision to OC-14 State Manager
  Notify OC-07 Agent Coordinator of debate completion
  |
  v
[PIPELINE COMPLETE — Decision record produced]
`

**Decision Record Format:**
`
Decision ID:       ODEC-{YYYYMMDD}-{SEQ:08d}
Decision Type:     [ENTER_LONG / ENTER_SHORT / EXIT / HOLD]
Instrument:        [Instrument identifier]
Score:             [0.00 – 10.00]
Agents Voted:      [BullAgent: N, BearAgent: N, NeutralAgent: N, ...]
Confidence:        [0.00 – 1.00]
Reasoning:         [Summary of debate outcome]
Timestamp:         [ISO-8601]
Prediction Ref:    [Prediction artifact ID]
Status:            [PENDING_RISK / RISK_APPROVED / RISK_REJECTED / EXECUTED]
`

---

### OP-07 — Risk Pipeline

**Purpose:** Evaluates every approved decision against all risk limits and
governance constraints before execution is permitted. The Risk Pipeline is
the final safety gate before any capital is committed.

**Trigger:** Post-decision approval (every approved Decision Record).

**Architecture Diagram:**
`
[TRIGGER: Approved Decision Record received]
     |
     v
[Risk Engine Invocation]
  (IIOS-RSK-ARCH-001)
  Position size calculation
  Drawdown impact assessment
  Portfolio impact assessment
  |
  v
[Constitutional Risk Gate — Layer 1]
  Daily loss < 2% (constitutional limit)?
  VIX <= 45 (constitutional kill switch)?
  Single strategy drawdown < 15% (auto-suspension)?
  ALL PASS: continue
  ANY FAIL: REJECT, P1 alert, system halt if kill switch
  |
  v
[Portfolio Risk Gate — Layer 2]
  Position within strategy weight limit (40% of capital)?
  Sector concentration <= 30%?
  Correlation to existing positions acceptable?
  ALL PASS: continue
  ANY FAIL: REJECT, log reason
  |
  v
[Position Size Calculation]
  Compute final position size within approved limits
  Apply portfolio-level constraints
  |
  v
[Governance Risk Confirmation]
  Confirm Governance Engine has current active session
  Confirm no kill switch conditions pending
  |
  v
[Risk Approval Record]
  Issue Risk Approval Record
  Route to Execution workflow
  |
  v
[PIPELINE COMPLETE — Risk approved, execution authorized]
`

---

### OP-08 — Portfolio Pipeline

**Purpose:** Updates portfolio state after every execution event and performs
ongoing portfolio monitoring for concentration, correlation, and performance.

**Trigger:** Post-execution confirmation. Also: end-of-session for reconciliation.

**Architecture Diagram:**
`
[TRIGGER: Execution confirmation received]
     |
     v
[Portfolio Engine Update]
  (IIOS-PRT-ARCH-001)
  Record executed position
  Recalculate portfolio weights
  Update portfolio P&L
  |
  v
[Portfolio Concentration Check]
  Strategy weight within 40% limit?
  Sector concentration within 30% limit?
  Any limits breached? -> Risk alert
  |
  v
[Correlation Update]
  Compute updated correlation matrix
  Flag new high-correlation pairs
  |
  v
[Portfolio State Publication]
  Publish updated portfolio state to:
  - Risk Engine (for continuous monitoring)
  - Decision Engine (for next decision context)
  Update OC-14 State Manager
  |
  v
[END-OF-SESSION VARIANT]
  Full portfolio reconciliation
  Performance attribution calculation
  Daily P&L lock
  Drawdown calculation
  |
  v
[PIPELINE COMPLETE — Portfolio state current]
`

---

### OP-09 — Learning Pipeline

**Purpose:** Processes the session's trade outcomes and system performance to
update strategy models, improve predictions, and accumulate institutional learning.

**Trigger:** Post-session (15:45 IST), after OP-08 end-of-session reconciliation.

**Architecture Diagram:**
`
[TRIGGER: Post-session, portfolio reconciliation complete]
     |
     v
[Trade Outcome Extraction]
  Collect all closed trades from the session
  Pair each trade with its originating decision and prediction
  |
  v
[Learning Engine Invocation]
  (IIOS-LRN-ARCH-001)
  Strategy performance analysis
  Prediction accuracy assessment
  Regime detection accuracy review
  |
  v
[Strategy Performance Update]
  Update strategy win rates, Sharpe, max drawdown
  Auto-disable strategies below thresholds
  Flag strategies for promotion or demotion
  |
  v
[Prediction Model Update]
  Update prediction model calibration scores
  Compute prediction improvement recommendations
  |
  v
[Knowledge Engine Update Signal]
  Signal OP-04 Knowledge Pipeline to run
  Incorporate learning outputs into knowledge base
  |
  v
[Learning Archive]
  Commit learning records to persistent store
  Archive session learning artifacts
  |
  v
[PIPELINE COMPLETE — Learning integrated]
`

---

### OP-10 — Strategy Pipeline

**Purpose:** Manages the lifecycle of investment strategies: evaluation of
candidate strategies, promotion decisions, and retirement of underperforming strategies.

**Trigger:** Weekly (weekend, post-session). Also: on-demand for new strategy candidates.

**Architecture Diagram:**
`
[TRIGGER: Weekly schedule OR new strategy candidate]
     |
     v
[Strategy Performance Review]
  (IIOS-STR-ARCH-001)
  Review all live strategies against performance gates:
  Win Rate >= 50%, Sharpe > 0.8, MaxDD < 15%
  |
  v
[Promotion Candidates Evaluation]
  Paper trading candidates reviewed
  Apply promotion gates: sufficient sample, performance thresholds
  |
  v
[Simulation Validation]
  Request OP-11 Simulation Pipeline for each candidate
  Wait for simulation evidence dossier
  |
  v
[Governance Gate Submission]
  Submit promotion candidates with evidence dossier
  to Governance Engine (GIP-02)
  |
  v
[Retirement Evaluation]
  Live strategies below survival thresholds
  Retirement recommendation to System Owner
  |
  v
[Strategy Registry Update]
  Update strategy registry with new statuses
  Notify Risk Engine and Portfolio Engine of changes
  |
  v
[PIPELINE COMPLETE — Strategy registry current]
`

---

### OP-11 — Simulation Pipeline

**Purpose:** Provides simulation evidence for strategy validation, risk scenario
analysis, and portfolio stress testing using the Simulation Engine.

**Trigger:** Requested by OP-10 Strategy Pipeline for promotions. Scheduled
weekly for portfolio stress testing. On-demand for governance requirements.

**Architecture Diagram:**
`
[TRIGGER: OP-10 request OR weekly schedule OR on-demand]
     |
     v
[Resource Allocation Check]
  Simulation is computationally intensive
  OC-06 Resource Manager allocates simulation budget
  Must not exceed 60% of available resources
  (Reserve 40% for CRITICAL workflows)
  |
  v
[Simulation Engine Invocation]
  (IIOS-SIM-ENG-ARCH-001)
  Configure simulation parameters
  Run historical backtest
  Run walk-forward test
  Run Monte Carlo scenarios
  Run stress tests
  |
  v
[Simulation Quality Evaluation]
  SimQS (Simulation Quality Score) computed
  Minimum SimQS thresholds evaluated
  Look-ahead bias check (automated)
  |
  v
[Evidence Dossier Assembly]
  Package simulation results as evidence dossier
  Format according to Governance Engine requirements
  Include: SimQS score, stress results, scenario results
  |
  v
[Evidence Dossier Publication]
  Route to requesting pipeline (OP-10)
  Route to Governance Engine (IIOS-GOV-ENG-ARCH-001)
  Archive in simulation results store
  |
  v
[PIPELINE COMPLETE — Evidence dossier available]
`

---

### OP-12 — Governance Pipeline

**Purpose:** Coordinates all governance activities — continuous monitoring,
certification, compliance checking, and audit record management — with the
Governance Engine throughout the session.

**Trigger:** Multiple: pre-session certification, continuous 30-second monitoring,
post-session reconciliation, and event-triggered governance checks.

**Architecture Diagram:**
`
[CONTINUOUS GOVERNANCE MONITORING — Every 30 seconds]
     |
     v
[Governance Engine Health Check]
  Governance Engine HEALTHY?
  If NOT: P1 incident; system enters SAFE mode
  |
  v
[Session Authorization Confirmation]
  Active Governance Readiness Certificate valid?
  Constitutional kill switches inactive?
  Daily loss within constitutional limit?
  |
  v
[Compliance Snapshot]
  Route current system state to Governance Engine
  Governance Engine returns compliance status
  |
  v
[Governance Dashboard Update]
  Update ControlTower governance panel
  |
  v
[END-OF-SESSION VARIANT]
  Full post-session compliance suite
  Audit hash chain verification
  Session governance archive
  |
  v
[PIPELINE COMPLETE — Governance status current]

[PRE-SESSION VARIANT — T-30]
     |
     v
[Governance Readiness Certificate Request]
  Submit pre-session checklist to Governance Engine
  (Per GIP-01 protocol in IIOS-GOV-ENG-ARCH-001)
  |
  v
[Certificate Receipt]
  Store certificate; notify OLS-06 complete
  |
  v
[PIPELINE COMPLETE — Session authorized by Governance]
`

---

### OP-13 — System Shutdown Pipeline

**Purpose:** Performs orderly shutdown of the complete IIOS system, ensuring
no data loss, proper archiving, and safe financial state preservation.

**Trigger:** Shutdown signal (scheduled or manual). Must run at end of each
trading day and can be triggered by ORP-08 Emergency Stop.

**Architecture Diagram:**
`
[TRIGGER: Shutdown signal received]
     |
     v
[Drain Active Workflows]
  OC-02 stops creating new workflow instances
  Wait for all RUNNING workflows to complete or timeout
  Maximum wait: 60 seconds
  |
  v
[Final Portfolio Reconciliation]
  Confirm no open positions that should be closed
  Lock portfolio state
  |
  v
[Final Governance Archiving]
  Post-session governance reconciliation (OP-12 end-of-session)
  Governance Engine archives session records
  |
  v
[Final Learning Trigger]
  Trigger OP-09 Learning Pipeline (begins async, does not block shutdown)
  |
  v
[State Commit]
  OC-14 commits all pending state changes
  Final state checkpoint created
  |
  v
[Component Shutdown Sequence]
  Orderly shutdown in reverse-registration order:
  1. OC-01 Master Scheduler (stop new triggers)
  2. OC-04 Execution Coordinator (stop new engine invocations)
  3. Specialized engines (deregistered from OC-08)
  4. OC-08 Engine Registry (archive registration records)
  5. OC-14 State Manager (final archive)
  |
  v
[Shutdown Verification]
  Confirm all components shut down cleanly
  Final health record committed
  |
  v
[OLS-12 SHUTDOWN COMPLETE]
`

---

### OP-14 — Failure Recovery Pipeline

**Purpose:** Manages the coordinated response to P1 and P2 incidents including
automated recovery attempts and, if automated recovery fails, safe system
halt to protect capital.

**Trigger:** P1 or P2 incident raised by OC-17 Incident Manager.

**Architecture Diagram:**
`
[TRIGGER: P1 or P2 incident]
     |
     v
[Incident Assessment]
  OC-17: Classify and characterize incident
  Identify affected engines and workflows
  |
  v
[Automated Recovery Attempt]
  OC-18: Select applicable recovery procedure (ORP-01 to ORP-08)
  Execute recovery procedure
  |
  v
  [Recovery Success?]
       YES                    NO
        |                      |
        v                      v
[Verify Recovered        [Escalate to Human]
 Component]               Notify Operations Lead
        |                 Telegram alert
  [Health Check]          Log incident
        |                      |
  HEALTHY?                [Safe Position Check]
    YES -> NORMAL          Are any positions at risk?
    NO  -> Retry once      If YES: notify immediately
           then Escalate   |
                           [SAFE MODE]
                           Suspend all trading workflows
                           Keep monitoring active
                           Wait for human resolution
        |
        v
[Incident Resolution Record]
  Record timeline, cause, resolution
  Schedule post-incident review
  |
  v
[PIPELINE COMPLETE — System recovered or safely halted]
`

**Safety Invariant:** OP-14 never closes positions automatically (except
where explicitly authorized in the risk kill switch protocol). Recovery is
operational, not financial.

---

## PART VII — QUALITY FRAMEWORK

### Quality Dimension Reference

| ID     | Dimension             | Weight | Measurement                                |
|--------|-----------------------|--------|--------------------------------------------|
| OQD-01 | Reliability           | 0.18   | Workflow success rate                      |
| OQD-02 | Availability          | 0.15   | System uptime during market hours          |
| OQD-03 | Scalability           | 0.05   | Throughput under load                      |
| OQD-04 | Determinism           | 0.10   | Outcome consistency for identical inputs   |
| OQD-05 | Fault Tolerance       | 0.12   | Degraded operation on component failure    |
| OQD-06 | Synchronization       | 0.08   | Barrier completion time accuracy           |
| OQD-07 | Observability         | 0.08   | Metric coverage; dashboard completeness    |
| OQD-08 | Performance           | 0.07   | Pipeline latency vs. SLA compliance        |
| OQD-09 | Maintainability       | 0.05   | Configuration change impact; update ease   |
| OQD-10 | Auditability          | 0.06   | Event log completeness; trace coverage     |
| OQD-11 | Security              | 0.06   | Authentication coverage; authorization audit|
| OQD-12 | Extensibility         | 0.05   | Engine onboarding time; new workflow cost  |
| OQD-13 | Operational Stability | 0.05   | Session-to-session variance in OHS         |

**Sum of weights: 1.00**

**Orchestrator Quality Score (OQS) Formula:**
OQS = SUM(OQD-{N}_score * OQD-{N}_weight) for N = 01 to 13

**OQS Tiers:**
| Tier        | Range      | Interpretation                                   |
|-------------|------------|--------------------------------------------------|
| EXCELLENT   | 0.88 – 1.00| Orchestration operating at reference standard    |
| GOOD        | 0.72 – 0.87| Operating well; minor improvements available     |
| ACCEPTABLE  | 0.56 – 0.71| Adequate; improvements needed in specific areas  |
| MARGINAL    | 0.36 – 0.55| Concerning; multiple dimensions underperforming  |
| FAILED      | 0.00 – 0.35| Critical; immediate intervention required        |

---

### OQD-01 — Reliability

**Definition:** The probability that any given workflow execution completes
successfully without unrecoverable error.

**Measurement:** Workflow success rate = Completed workflows / (Completed + Failed)
across a rolling 7-day window.

**Scoring Anchors:**
| Score | Condition                                     |
|-------|-----------------------------------------------|
| 1.00  | Workflow success rate >= 99.9%                |
| 0.80  | Workflow success rate >= 99.0%                |
| 0.60  | Workflow success rate >= 97.0%                |
| 0.40  | Workflow success rate >= 94.0%                |
| 0.20  | Workflow success rate >= 90.0%                |
| 0.00  | Workflow success rate < 90.0%                 |

**Target:** >= 0.80 (Score 99.0% success rate).

---

### OQD-02 — Availability

**Definition:** The fraction of scheduled market hours during which the Master
Orchestrator is operational at NOMINAL or better health.

**Measurement:** Uptime ratio = minutes at NOMINAL+ / total market-hour minutes,
rolling 30-day window.

**Scoring Anchors:**
| Score | Condition                        |
|-------|----------------------------------|
| 1.00  | Availability >= 99.9%            |
| 0.80  | Availability >= 99.5%            |
| 0.60  | Availability >= 99.0%            |
| 0.40  | Availability >= 98.0%            |
| 0.20  | Availability >= 95.0%            |
| 0.00  | Availability < 95.0%             |

**Target:** >= 0.80 (99.5% availability).

---

### OQD-03 — Scalability

**Definition:** The degree to which the Orchestrator maintains performance
under increasing workflow load.

**Measurement:** Workflow completion latency at peak load vs. nominal load.
Throughput: workflows completed per minute at peak vs. nominal.

**Target:** Performance degradation < 20% at 2x normal load.

---

### OQD-04 — Determinism

**Definition:** The property that identical orchestration inputs produce identical
orchestration outputs. Determinism is essential for auditability and testing.

**Measurement:** Percentage of scheduling decisions that match the expected
deterministic outcome in replay tests.

**Target:** 100% determinism. Any non-determinism is an architectural defect.

**Note:** Determinism applies to scheduling and coordination decisions, not to
the outputs of specialized engines (which may be intentionally non-deterministic).

---

### OQD-05 — Fault Tolerance

**Definition:** The ability of the Orchestrator to maintain reduced but functional
operation when individual components or engines fail.

**Measurement:** System availability after single component failure vs. baseline.
Test: remove each CRITICAL component in succession; measure degradation.

**Scoring Anchors:**
| Score | Condition                                             |
|-------|-------------------------------------------------------|
| 1.00  | Any single NORMAL/LOW component failure: no impact    |
| 0.80  | Any single HIGH component failure: DEGRADED operation |
| 0.60  | Single CRITICAL non-core component: DEGRADED          |
| 0.40  | Single CRITICAL core component: CRITICAL operation    |
| 0.00  | Single component failure causes system halt           |

---

### OQD-06 — Synchronization

**Definition:** The accuracy and timeliness of barrier-based synchronization
across parallel workflow execution.

**Measurement:** Percentage of synchronization barriers that complete within
their configured timeout; percentage of false barrier failures.

**Target:** Barrier completion within timeout: >= 99.5%.
False barrier failure rate (barrier fails when all steps are actually complete): 0%.

---

### OQD-07 — Observability

**Definition:** The degree to which the internal state and behavior of the
Orchestrator is externally observable through metrics, logs, traces, and dashboards.

**Measurement:** Metric coverage (percentage of components with active metrics);
trace coverage (percentage of workflow steps producing trace records);
dashboard completeness (all OHS dimensions visible).

**Target:** 100% metric coverage; 100% trace coverage; complete dashboard.

---

### OQD-08 — Performance

**Definition:** The ability of the Orchestrator to complete its coordination
activities within defined latency SLAs.

**Key SLA Targets:**
| Activity                         | SLA       | Measurement         |
|----------------------------------|-----------|---------------------|
| Schedule trigger latency         | < 1s      | Per scheduled event |
| Workflow step transition         | < 500ms   | Per step            |
| Engine invocation overhead       | < 100ms   | Per invocation      |
| Message delivery (CRITICAL)      | < 10ms    | Per message         |
| Health probe response            | < 5s      | Per engine          |
| Barrier state update             | < 10ms    | Per completion      |

**Measurement:** Percentage of activities meeting their SLA, rolling 24-hour window.
**Target:** >= 99% SLA compliance.

---

### OQD-09 — Maintainability

**Definition:** The ease with which the Orchestrator can be configured, updated,
and extended without disrupting operations.

**Measurement:** Average time to apply a configuration change; number of components
that require restart for a configuration change; change error rate.

**Target:** Configuration changes that do not require restart: 80% or more.
Changes requiring restart: apply during maintenance window.

---

### OQD-10 — Auditability

**Definition:** The completeness of the audit trail for all orchestration activities.

**Measurement:** Percentage of orchestration events with complete audit records;
audit record retrieval coverage; audit chain integrity.

**Target:** 100% event coverage; 100% audit record retrieval; complete chain integrity.

---

### OQD-11 — Security

**Definition:** The strength of authentication, authorization, and integrity
controls across all orchestration activities.

**Measurement:** Authentication coverage (percentage of engine communications
authenticated); authorization audit (unauthorized access attempts detected and
blocked); integrity check coverage.

**Target:** 100% authentication coverage; 0 unauthorized access incidents.

---

### OQD-12 — Extensibility

**Definition:** The ease with which new engines, workflows, and services can
be added to the Orchestrator without modifying existing components.

**Measurement:** Time to onboard a new engine (from registration to first workflow
participation); lines of existing code modified per new workflow; documentation
completeness for extension points.

**Target:** New engine onboarding time < 1 hour; zero modification of existing
components for new engine registration.

---

### OQD-13 — Operational Stability

**Definition:** The consistency of Orchestrator performance from session to session.

**Measurement:** Standard deviation of OHS across sessions; variance in workflow
completion times; variance in incident rates.

**Target:** OHS standard deviation across sessions < 0.05.

---

## PART VIII — ORCHESTRATION GOVERNANCE

### 8.1 Ownership

The Master Orchestrator is owned by the Architecture Council of IIOS, with
day-to-day operational responsibility assigned to the Operations Lead.

| Role                  | Responsibility                                               |
|-----------------------|--------------------------------------------------------------|
| Architecture Council  | Constitution; component architecture; version authorization  |
| Operations Lead       | Daily operation; incident response; schedule management      |
| System Owner          | Override authority; final escalation path                    |
| Governance Engine     | Constitutional compliance; session authorization             |

---

### 8.2 Scheduling Policy

All workflow schedules are defined in OC-22 Configuration Manager. Changes to
CRITICAL workflow schedules require Architecture Council approval. Changes to
NORMAL and LOW workflow schedules require Operations Lead approval.

No workflow schedule may be eliminated without confirming that its downstream
dependencies are also updated or eliminated. The Dependency Manager (OC-03)
must re-validate the full dependency graph after every schedule change.

---

### 8.3 Priority Policy

Priority levels are defined in OC-05 Priority Manager. The default priority
for each pipeline type is defined in the Pipeline Reference Table (Section 6).

Dynamic priority elevation (incident response) is permitted for OC-17 Incident
Manager. Elevated priorities expire automatically after the incident resolves.
No human may manually set a workflow's priority above CRITICAL.

Priority starvation is prevented by the aging policy: any workflow waiting
more than 10 minutes beyond its scheduled start time is elevated by 1 level.

---

### 8.4 Conflict Resolution

The Conflict Resolver (OC-12) applies documented policies (Section 3.12).
Conflict resolution decisions are logged to OC-14 and available for review.
Monthly conflict analysis (OC-19 Analytics Manager) reviews conflict frequency
and patterns to identify scheduling improvements.

---

### 8.5 Resource Allocation Policy

Resource budgets are configured per engine and per workflow type in OC-22.
Total resource budget must leave a minimum 20% reserve for CRITICAL operations.
Resource budgets are reviewed monthly by the Operations Lead.

When total resource utilization exceeds 90%, OC-06 triggers the graceful
degradation protocol automatically.

---

### 8.6 Health Monitoring Policy

OC-15 Health Manager probes all engines continuously. The OHS threshold for
active trading is NOMINAL (0.80) or better. If OHS drops below 0.60 (DEGRADED),
only CRITICAL workflows continue. If OHS drops below 0.35 (FAILED), the system
halts and requires human intervention.

OHS is computed every 30 seconds during market hours.

---

### 8.7 Security Policy

All communication between the Orchestrator and engines uses authenticated,
integrity-checked messaging. Engine credentials are managed in the secrets
management system — never stored in configuration files.

Access to the Orchestrator's management interface (start/stop/configure) is
restricted to Operations Lead and System Owner roles.

---

### 8.8 Compliance with Governance Engine

The Master Orchestrator operates under the constitutional authority of the
Governance Engine (IIOS-GOV-ENG-ARCH-001). The following governance interactions
are mandatory and cannot be bypassed:

1. Pre-session certification (GIP-01) before every trading session.
2. Strategy governance gate (GIP-02) for every strategy promotion.
3. Continuous governance monitoring (GIP-03) throughout the session.
4. Post-session reconciliation (GIP-04) after market close.
5. Exception submission (GIP-05) for any governance deviation request.

No trading workflow proceeds without an active Governance Readiness Certificate.

---

### 8.9 Versioning Policy

The Orchestrator version is managed by OC-21 Version Manager. Each Orchestrator
release is tagged with a MAJOR.MINOR.PATCH version number. Version upgrades
require Architecture Council approval for MAJOR and MINOR changes; Operations
Lead approval for PATCH changes.

At startup, OC-21 verifies the hash of all registered engine versions against
the authorized version registry. Unauthorized engine versions cannot be registered.

---

### 8.10 Recovery Policy

Recovery procedures are maintained in OC-18 Recovery Manager. Automated recovery
is attempted for all P2 and below incidents. P1 incidents trigger automated
recovery AND immediate human notification simultaneously.

Recovery success rate is tracked by OC-19 Analytics Manager. A recovery success
rate below 80% for any procedure triggers an Architecture Council review.

---

### 8.11 Continuous Improvement

The Master Orchestrator undergoes continuous improvement through:
- Monthly operational reviews (OC-20 Reporting Manager produces Monthly Operations Report).
- Quarterly architecture reviews (Architecture Council evaluates OQS trends).
- Annual constitution review (all constitutional rules reviewed for relevance).
- Post-incident reviews (mandatory for all P1 incidents; recommended for P2).

Improvement proposals are evaluated against the architectural impact criteria
in the IIOS Copilot Instructions: correctness, performance, architecture, and
smallest-change principle.

---

## PART IX — MASTER ORCHESTRATOR CONSTITUTION

### Preamble

The Master Orchestrator Constitution defines the inviolable rules that govern
the design, operation, modification, and evolution of the Master Orchestrator.
These rules exist to ensure that the Orchestrator remains trustworthy, predictable,
auditable, and safe across its operational lifetime.

The Constitution is organized into 18 rule categories (OCC-A through OCC-R).
Rules are classified as:
- **NON-NEGOTIABLE HARD:** No exception, no override, no circumstance.
- **HARD:** No runtime exception; change requires Architecture Council approval.
- **SOFT:** Best practice; deviation requires Operations Lead approval and documentation.

**Total rules: 140. NON-NEGOTIABLE HARD: 15. HARD: 98. SOFT: 27.**

---

### OCC-A — Engine Registration (10 rules)

**OCC-A-001** [NON-NEGOTIABLE HARD] No engine may participate in any IIOS workflow
without being registered in OC-08 Engine Registry. Unregistered engine invocations
are a fatal error and must not occur under any circumstances.

**OCC-A-002** [HARD] Every engine registration must include: engine ID, engine name,
version, capabilities, dependencies, resource budget, and contact endpoint.
Incomplete registrations must be rejected by OC-08.

**OCC-A-003** [HARD] Every registered engine version must appear in the authorized
version registry maintained by OC-21 Version Manager. Engines with unauthorized
versions must not be registered.

**OCC-A-004** [HARD] The Engine Registry must issue an Engine Registration Certificate
for every successful registration. No registration is complete without a certificate.

**OCC-A-005** [HARD] Duplicate engine registrations must be rejected. The Engine
Registry must detect and reject any registration attempt for an engine that is
already registered with a HEALTHY or DEGRADED status.

**OCC-A-006** [HARD] Engine deregistration must be coordinated with OC-03 Dependency
Manager to update the dependency graph before the deregistration is confirmed.
An engine with active workflow dependencies must not be deregistered while those
workflows are running.

**OCC-A-007** [HARD] The Engine Registry must be the first Orchestrator component
initialized at startup (OLS-01) and the last shut down (OLS-12). The Engine
Registry must be available throughout the entire system lifecycle.

**OCC-A-008** [SOFT] Engine registration records are permanent. Even after an engine
is deregistered, its registration history must remain in the Engine Registry archive.

**OCC-A-009** [HARD] Engine capability declarations must be validated on registration.
An engine that declares capabilities it cannot demonstrate in a capability handshake
must not be registered.

**OCC-A-010** [SOFT] Engines should provide a semantic version that follows
MAJOR.MINOR.PATCH conventions. The minor and patch versions are informational;
the major version must be consistent with the authorized major version for that
engine type.

---

### OCC-B — Engine Independence (10 rules)

**OCC-B-001** [NON-NEGOTIABLE HARD] The Master Orchestrator must not contain
investment domain logic. No code, configuration, or architectural element within
the Orchestrator may implement, replicate, or substitute for any specialized
engine's functionality.

**OCC-B-002** [NON-NEGOTIABLE HARD] The Master Orchestrator must not interpret
the investment meaning of any engine's output. It validates schema and delivery;
it does not evaluate correctness, quality, or investment implications.

**OCC-B-003** [HARD] Each specialized engine must remain internally autonomous.
The Orchestrator coordinates WHEN an engine runs and WHAT inputs it receives;
it does not coordinate HOW the engine processes those inputs.

**OCC-B-004** [HARD] Engine business logic must be isolated from orchestration
concerns. An engine must be able to run standalone (with appropriate inputs)
without the Orchestrator being present.

**OCC-B-005** [HARD] The Orchestrator must not retain or process engine outputs
beyond what is necessary for routing, workflow state management, and audit
logging. Engine outputs are data in transit; the Orchestrator is not their consumer.

**OCC-B-006** [HARD] Engine failures must be handled by the Orchestrator at the
coordination level (retry, substitute, fail the workflow step) without attempting
to remediate the engine's internal error through orchestration-level workarounds.

**OCC-B-007** [SOFT] Engine interfaces (input schemas, output schemas) should be
defined in the engine's own architecture document, not in the Orchestrator. The
Orchestrator references these schemas but does not define them.

**OCC-B-008** [HARD] The Master Orchestrator must not modify, supplement, or
interpret engine outputs before routing them to downstream engines. Outputs
must be passed unmodified.

**OCC-B-009** [SOFT] Engines should be designed so that they can be replaced
with a newer version without changing the Orchestrator. The contract between
Orchestrator and engine is the registered capability set and the message schema.

**OCC-B-010** [HARD] Adding a new engine to IIOS must not require modifying any
existing Orchestrator component. New engines are added through registration and
configuration, not through code changes to the Orchestrator.

---

### OCC-C — Scheduling (10 rules)

**OCC-C-001** [NON-NEGOTIABLE HARD] Every scheduled workflow must have a defined
and registered schedule entry. Ad hoc workflow execution (without a registered
trigger) is not permitted in a production system.

**OCC-C-002** [HARD] The Master Scheduler must use the IIOS trading calendar
(NSE calendar, IST timezone) as the authoritative source for all market-hour
scheduling decisions. No hardcoded dates or manually maintained lists are permitted.

**OCC-C-003** [HARD] Schedule modifications require approval proportional to the
affected workflow's priority: CRITICAL and HIGH schedules require Architecture
Council approval; NORMAL and LOW schedules require Operations Lead approval.

**OCC-C-004** [HARD] The Master Scheduler must produce a deterministic trigger
sequence: for any given schedule configuration and clock time, the sequence of
workflow triggers must be the same every time. Non-deterministic scheduling is
an architectural defect.

**OCC-C-005** [HARD] Schedule conflicts (two CRITICAL workflows scheduled simultaneously)
must be detected and resolved by OC-01 and OC-12 before they cause resource
competition at runtime. Schedule conflicts must not be silently ignored.

**OCC-C-006** [SOFT] The Master Scheduler should schedule resource-intensive
workflows (Simulation, Learning) during off-peak hours to minimize resource
competition with CRITICAL market-hours workflows.

**OCC-C-007** [HARD] On Orchestrator restart, OC-01 must evaluate all missed
scheduled events during downtime. CRITICAL events missed within the last 10 minutes
must be executed immediately. Events missed longer ago are deferred.

**OCC-C-008** [SOFT] Schedule entries should include a maximum catchup window
beyond which a missed execution is simply skipped rather than caught up. This
prevents runaway catchup cascades after extended downtime.

**OCC-C-009** [HARD] The trading calendar must be validated at system startup.
If the calendar cannot be loaded or is corrupted, the system must halt. Operating
without a valid trading calendar is not permitted.

**OCC-C-010** [SOFT] Scheduled events should be logged with sufficient metadata
(schedule ID, intended trigger time, actual trigger time, delta) to support
schedule performance analysis.

---

### OCC-D — Coordination (8 rules)

**OCC-D-001** [HARD] All engine invocations must be coordinated through OC-04
Execution Coordinator. No engine may be invoked directly from any component
other than OC-04.

**OCC-D-002** [HARD] The Execution Coordinator must check engine health (via
OC-15) before every invocation. Invoking an UNHEALTHY or OFFLINE engine is
a coordination error.

**OCC-D-003** [HARD] Engine invocation must include a timeout. No engine invocation
may run indefinitely. Timeout values must be configured per engine type in OC-22.

**OCC-D-004** [HARD] When an engine invocation times out, OC-04 must increment
the failure counter, log the timeout event, and apply the configured retry
policy before failing the workflow step.

**OCC-D-005** [SOFT] Retry policies should be exponential backoff for transient
failures and immediate abort for deterministic failures. The distinction between
transient and deterministic failure types must be documented per engine.

**OCC-D-006** [HARD] Multi-engine coordination sequences must be driven by the
workflow definition in OC-02, not by any engine's internal logic. Engines must
not trigger other engines directly.

**OCC-D-007** [HARD] The Agent Coordinator (OC-07) must be notified of all
multi-agent process starts and completions. The Orchestrator must maintain
visibility into multi-agent processes at all times.

**OCC-D-008** [SOFT] Coordination events (engine invocation start, completion,
failure, timeout) should be logged with enough detail to reconstruct the full
execution sequence during incident investigation.

---

### OCC-E — Communication (8 rules)

**OCC-E-001** [NON-NEGOTIABLE HARD] All inter-engine communication in IIOS must
flow through OC-10 Communication Manager. Engines must not establish direct
communication channels outside the Orchestrator.

**OCC-E-002** [HARD] All communication must use authenticated, integrity-checked
messages. Unauthenticated messages must be rejected by OC-10.

**OCC-E-003** [HARD] Every message must include: message ID, source, destination,
message type, timestamp, content version, and payload. Messages missing required
fields must be rejected.

**OCC-E-004** [HARD] CRITICAL messages must have acknowledged delivery semantics.
The sender must receive a delivery acknowledgment within the configured TTL.
If acknowledgment is not received, the message is retried.

**OCC-E-005** [HARD] The dead letter queue must be monitored continuously by
OC-16 Monitoring Manager. Dead letters must generate alerts proportional to the
message priority.

**OCC-E-006** [SOFT] Communication channels should be encrypted in transit,
particularly for channels traversing untrusted network segments.

**OCC-E-007** [HARD] Message schema versions must be validated on receipt.
Messages with unknown or incompatible schema versions must be rejected and
sent to the dead letter queue.

**OCC-E-008** [SOFT] Communication performance metrics (message throughput,
delivery latency, queue depth) should be available in the monitoring dashboard
with sufficient granularity to diagnose bottlenecks.

---

### OCC-F — Synchronization (8 rules)

**OCC-F-001** [HARD] Every synchronization barrier in a workflow must have a
configured timeout. Indefinite barrier waits are not permitted.

**OCC-F-002** [HARD] Barrier types (AND, OR, QUORUM, TIMEOUT) must be explicitly
specified in the workflow definition. Ambiguous barrier semantics are not permitted.

**OCC-F-003** [HARD] A barrier that detects all participants have failed must
fail the barrier immediately rather than waiting for the timeout. Waiting for
a timeout when all participants are known to have failed wastes time.

**OCC-F-004** [SOFT] Barriers with more than 5 participants should be monitored
with additional granularity to detect slow participants before they cause a
barrier timeout.

**OCC-F-005** [HARD] Force-releasing a barrier (bypassing the completion condition)
requires human authorization and must be logged as a governance event.

**OCC-F-006** [HARD] The Synchronization Manager must detect orphaned barriers
(barriers whose parent workflows have been cancelled or failed) and clean them
up promptly. Orphaned barriers accumulate resource consumption.

**OCC-F-007** [SOFT] Synchronization barrier completion times should be tracked
per barrier type and per workflow type for performance trend analysis.

**OCC-F-008** [HARD] Race conditions in barrier management must be architecturally
prevented. Two participants must not be able to simultaneously mark the same
barrier as complete in a way that corrupts the barrier's participant count.

---

### OCC-G — Workflow Integrity (8 rules)

**OCC-G-001** [NON-NEGOTIABLE HARD] Every workflow instance must have a unique
Workflow Instance ID. Duplicate workflow IDs are a fatal architectural error.

**OCC-G-002** [HARD] Every workflow step must produce an audit record in OC-14
State Manager. Workflows with unrecorded steps are not fully auditable.

**OCC-G-003** [HARD] Workflow definitions are immutable at runtime. A running
workflow may not have its definition modified mid-execution.

**OCC-G-004** [HARD] Completed workflows (COMPLETED, FAILED, TIMED_OUT,
CANCELLED) must be archived permanently. Completed workflow records must not
be deleted.

**OCC-G-005** [HARD] Workflow state transitions must be atomic. A partial
transition that leaves the workflow in an inconsistent state is a critical error.

**OCC-G-006** [SOFT] Workflow definitions should be versioned. When a workflow
definition changes, existing instances continue with the version they started on.

**OCC-G-007** [HARD] Workflow step retries must be idempotent. Steps that are
non-idempotent (produce side effects that cannot be reversed) must be marked as
NON_RETRYABLE in the workflow definition and must not be retried automatically.

**OCC-G-008** [SOFT] Workflows with more than 20 steps should be decomposed into
sub-workflows to maintain cognitive manageability and testability.

---

### OCC-H — Conflict Resolution (8 rules)

**OCC-H-001** [NON-NEGOTIABLE HARD] Governance conflicts always resolve in favor
of the Governance Engine. No conflict resolution policy may override a governance
rule, constitutional limit, or kill switch condition.

**OCC-H-002** [HARD] All conflict resolutions must be logged with: conflict type,
competing parties, resolution policy applied, outcome, and timestamp. Conflict
resolution must not be silent.

**OCC-H-003** [HARD] Resource conflicts must be resolved by priority order.
When two workflows compete for the same resource, the higher-priority workflow
receives the resource. The lower-priority workflow is queued.

**OCC-H-004** [HARD] Deadlock detection must run continuously. A deadlock that
persists undetected for more than 30 seconds is a monitoring failure.

**OCC-H-005** [HARD] When a deadlock is detected, the lowest-priority participant
must be aborted. The abort must be logged as an incident.

**OCC-H-006** [SOFT] Repeated conflicts (the same conflict type occurring more
than 5 times in a session) should trigger a scheduling review. Repeated conflicts
indicate a structural scheduling problem, not a transient event.

**OCC-H-007** [HARD] Conflict resolution must be deterministic. Given the same
conflict state, the resolver must produce the same resolution every time.

**OCC-H-008** [SOFT] Conflict resolution decisions should be available in the
monitoring dashboard for real-time operational visibility.

---

### OCC-I — Recovery (8 rules)

**OCC-I-001** [NON-NEGOTIABLE HARD] Recovery procedures must never open, close,
or modify any investment position. Recovery is purely operational. Financial
position management remains exclusively with the specialized engines through
their normal governance-approved workflows.

**OCC-I-002** [HARD] Every automated recovery attempt must be logged with:
procedure name, trigger incident ID, start time, completion time, outcome,
and any error messages encountered.

**OCC-I-003** [HARD] If automated recovery fails after the configured maximum
retry count, a P1 incident must be raised and a human operator must be notified
immediately. Automated recovery must not loop indefinitely.

**OCC-I-004** [HARD] Recovery procedures must be tested regularly (minimum
monthly) in non-production to verify they function as designed. Recovery
procedures that have not been tested within the last 90 days must be flagged.

**OCC-I-005** [HARD] The system must enter SAFE mode (all trading workflows
suspended) when OHS drops below 0.35 (FAILED tier). SAFE mode disables new
workflow creation but keeps monitoring, governance, and health systems active.

**OCC-I-006** [HARD] Recovery from SAFE mode requires explicit human authorization.
The system must not exit SAFE mode automatically without human confirmation.

**OCC-I-007** [SOFT] Recovery procedures should be designed for idempotency:
running a recovery procedure twice should produce the same result as running it
once. This enables safe retry without side effects.

**OCC-I-008** [SOFT] Post-incident recovery reviews should include a root cause
analysis that identifies whether the recovery procedure was adequate or whether
it needs to be updated to handle similar incidents faster or more safely.

---

### OCC-J — Monitoring (8 rules)

**OCC-J-001** [NON-NEGOTIABLE HARD] The Monitoring Manager (OC-16) must be
operational at all times when the Orchestrator is running. A monitoring outage
is itself a P1 incident. The system cannot operate safely without monitoring.

**OCC-J-002** [HARD] Every Orchestrator component must emit metrics to OC-16.
Components that produce no metrics are operationally invisible and architecturally
non-compliant.

**OCC-J-003** [HARD] Metric retention must be sufficient for trend analysis:
real-time metrics retained for 7 days; aggregated metrics retained for 3 years.

**OCC-J-004** [HARD] CRITICAL metric threshold breaches must generate alerts
within 10 seconds of the threshold being crossed. Delayed alerts for CRITICAL
conditions are a monitoring system failure.

**OCC-J-005** [SOFT] Metrics should be dimensioned: every metric should carry
context dimensions (workflow type, engine name, session date) to enable
drill-down analysis.

**OCC-J-006** [HARD] The monitoring dashboard must be available to the Operations
Lead and System Owner during all market hours. Dashboard unavailability is a P2 incident.

**OCC-J-007** [SOFT] Anomaly detection (detecting unusual patterns in metrics
before they cross thresholds) should supplement threshold-based alerting.
Predictive alerts give operators time to act before a threshold is crossed.

**OCC-J-008** [HARD] Monitoring must be self-monitoring: OC-16 must emit metrics
about its own health (collection success rate, processing latency, dashboard
availability). Monitoring that cannot monitor itself is unreliable.

---

### OCC-K — Health (8 rules)

**OCC-K-001** [HARD] The OHS calculation must include all 22 Orchestrator
components and all registered engines. Omitting any component from the OHS
calculation understates system health risk.

**OCC-K-002** [HARD] OHS must be recomputed every 30 seconds during market
hours and every 5 minutes outside market hours.

**OCC-K-003** [HARD] OHS computation must be deterministic: given the same
component health states and weights, OHS must produce the same value every time.

**OCC-K-004** [HARD] Component weights in the OHS calculation must sum to 1.00.
Weight configurations that do not sum to 1.00 must be rejected by OC-22.

**OCC-K-005** [HARD] A CRITICAL engine (Risk Engine, Governance Engine, Decision
Engine) transitioning to OFFLINE must trigger an immediate P1 incident regardless
of the overall OHS value.

**OCC-K-006** [SOFT] Individual component health scores should be available in
the dashboard alongside the aggregate OHS. Aggregate scores that hide critical
component failures are operationally dangerous.

**OCC-K-007** [HARD] Health probe failures must be distinguished from component
unavailability. A probe failure could indicate a network issue, not necessarily
component failure. Multiple consecutive probe failures are required before
marking a component UNHEALTHY.

**OCC-K-008** [SOFT] Health probe responses should include component-reported
self-assessment metrics (not just connectivity). An engine that responds to the
probe but is internally stressed should report DEGRADED health.

---

### OCC-L — Resource Allocation (8 rules)

**OCC-L-001** [HARD] The CRITICAL resource reserve (20% of total resources) must
never be allocated to non-CRITICAL workflows. This reserve exists solely to ensure
CRITICAL workflows can execute during resource pressure events.

**OCC-L-002** [HARD] Resource allocation decisions must be logged. Resource
allocation is a governance-relevant activity; unexplained resource allocation
patterns are a security risk.

**OCC-L-003** [HARD] When a resource limit is exceeded, the Orchestrator must
apply the graceful degradation protocol rather than allowing uncontrolled
resource competition. Uncontrolled competition causes unpredictable behavior.

**OCC-L-004** [SOFT] Resource budgets should be reviewed monthly using actual
utilization data from OC-19 Analytics Manager. Static budgets that do not reflect
actual usage patterns are inefficient.

**OCC-L-005** [HARD] Resource preemption must be logged as an operational event.
A workflow that has its resources preempted must be notified through OC-11
Message Router.

**OCC-L-006** [SOFT] Resource utilization forecasts (based on the current workflow
schedule and historical resource profiles) should be computed at session start
to identify potential resource conflicts before they occur.

**OCC-L-007** [HARD] No single workflow may consume more than 60% of any resource
category. Workflows requiring more than 60% of a resource must be decomposed
or rescheduled to avoid monopolizing shared resources.

**OCC-L-008** [SOFT] Resource recovery after workflow completion should be prompt.
Resource leaks (resources not released after workflow completion) accumulate over
sessions and eventually cause resource exhaustion.

---

### OCC-M — Priority (8 rules)

**OCC-M-001** [HARD] The five priority levels (CRITICAL, HIGH, NORMAL, LOW,
DEFERRED) must be the only priority levels used. Custom priority levels are
not permitted; they undermine the priority management framework.

**OCC-M-002** [HARD] Priority assignments for each pipeline type are defined in
the Pipeline Reference Table and must not be changed without Architecture Council
approval for CRITICAL/HIGH, and Operations Lead approval for NORMAL/LOW/DEFERRED.

**OCC-M-003** [HARD] Priority inversion must be detected and corrected. The
priority inheritance protocol in OC-05 Priority Manager is the authoritative
mechanism for handling priority inversions.

**OCC-M-004** [HARD] The aging policy (priority elevation after 10 minutes of
waiting) is mandatory and must not be disabled. Priority starvation is not
acceptable in a production financial system.

**OCC-M-005** [SOFT] Dynamic priority elevation (by incident response) should
expire automatically when the triggering incident is resolved. Permanently
elevated priorities circumvent the intended priority structure.

**OCC-M-006** [HARD] Priority comparisons (used by resource allocation and
scheduling) must be deterministic. Given the same priority table, comparisons
must produce the same ordering every time.

**OCC-M-007** [SOFT] Priority assignments should be reviewed in the monthly
operations report. If low-priority workflows frequently starve even with aging,
the priority structure may need rebalancing.

**OCC-M-008** [HARD] No human-initiated action may set a workflow priority above
CRITICAL. CRITICAL is the maximum priority level.

---

### OCC-N — Security (8 rules)

**OCC-N-001** [NON-NEGOTIABLE HARD] All engine credentials (authentication tokens,
API keys, certificates) must be stored in the secrets management system, never
in configuration files, environment variables visible to unprivileged processes,
or source code.

**OCC-N-002** [HARD] Access to the Orchestrator's management interface (start,
stop, configure, override) must be restricted to Operations Lead and System Owner
roles using multi-factor authentication.

**OCC-N-003** [HARD] All communication channels between the Orchestrator and
engines must use authenticated, integrity-checked protocols. The use of
unauthenticated communication is not permitted.

**OCC-N-004** [HARD] Security events (unauthorized access attempts, authentication
failures, integrity check failures) must generate P1 or P2 incidents depending
on severity and must be logged to the permanent audit record.

**OCC-N-005** [HARD] The Orchestrator must not log sensitive data (authentication
tokens, position details, strategy parameters) in operational logs. Sensitive
data appearing in operational logs is a security violation.

**OCC-N-006** [SOFT] Security configurations (authentication methods, key rotation
schedules) should be reviewed at least annually by the System Owner.

**OCC-N-007** [HARD] Engine capability handshakes during discovery must be
authenticated. An unauthenticated capability response must be rejected.

**OCC-N-008** [SOFT] Communication channels should implement certificate pinning
where technically feasible to prevent man-in-the-middle attacks.

---

### OCC-O — Governance (8 rules)

**OCC-O-001** [NON-NEGOTIABLE HARD] The Master Orchestrator must not begin any
trading session workflow (OP-02 Daily Market Pipeline) without a valid Governance
Readiness Certificate from the Governance Engine (IIOS-GOV-ENG-ARCH-001).

**OCC-O-002** [HARD] If the Governance Engine becomes unavailable during an active
session, the Orchestrator must suspend all new trading workflow creation immediately.
Active in-flight workflows complete; new ones do not start.

**OCC-O-003** [HARD] All five governance integration patterns (GIP-01 through
GIP-05, defined in IIOS-GOV-ENG-ARCH-001) must be implemented by the Orchestrator.
Partial governance integration is not permitted.

**OCC-O-004** [HARD] The Orchestrator must submit exception requests to the
Governance Engine (GIP-05) when it encounters governance rule conflicts, rather
than resolving them independently. The Orchestrator is governed; it does not govern.

**OCC-O-005** [SOFT] Governance integration interactions should be logged at the
Orchestrator level in addition to being recorded by the Governance Engine, to
provide a complete bilateral audit trail.

**OCC-O-006** [HARD] The Orchestrator must not cache governance decisions beyond
their defined validity period. A governance decision expires with its certificate
or when a new governance event supersedes it.

**OCC-O-007** [HARD] Strategy promotion workflows (OP-10 Strategy Pipeline) must
route through the Governance Strategy Gate (GIP-02) before any strategy is marked
as authorized for live trading.

**OCC-O-008** [SOFT] Governance communication latency (time from Orchestrator
governance request to Governance Engine response) should be tracked and included
in the session performance report.

---

### OCC-P — Human Override (6 rules)

**OCC-P-001** [NON-NEGOTIABLE HARD] Human override of a constitutional rule is
not possible. The constitution is not subject to runtime override. Only an
Architecture Council-approved constitutional amendment (minimum 30-day review)
can change a constitutional rule.

**OCC-P-002** [HARD] Human override of a HARD rule requires written justification
from Operations Lead and is logged as a governance event. The override expires
at the end of the current session.

**OCC-P-003** [HARD] All human overrides must be logged with: actor identity,
timestamp, rule overridden, justification, and expiration time. Anonymous overrides
are not permitted.

**OCC-P-004** [HARD] The System Owner has override authority for HARD rules.
The Operations Lead has override authority for SOFT rules. Neither has override
authority for NON-NEGOTIABLE HARD or constitutional rules.

**OCC-P-005** [SOFT] A human override that is applied more than 3 times for the
same rule within a 30-day period should trigger an Architecture Council review
of whether the rule is calibrated correctly.

**OCC-P-006** [HARD] Human override actions must be visible in the monitoring
dashboard in real time. An override that is not visible is unaccountable.

---

### OCC-Q — Future Engine Integration (8 rules)

**OCC-Q-001** [HARD] Every future engine added to IIOS must register with OC-08
Engine Registry using the same registration protocol as existing engines. No
special-case integration paths are permitted.

**OCC-Q-002** [HARD] New engines must declare their dependencies in their
registration record. OC-03 must validate the updated dependency graph for
circular dependencies before the new engine participates in any workflow.

**OCC-Q-003** [HARD] New engine additions must not require modification of any
existing Orchestrator component. The Orchestrator is designed for extension without
modification.

**OCC-Q-004** [SOFT] New engines should be onboarded first in PAPER mode
(simulated execution, no live trading) before being authorized for live workflows.
This protects the production system from new engine integration errors.

**OCC-Q-005** [HARD] New workflows for new engines must be added to the workflow
catalog (Supplement B) and validated by OC-03 before being scheduled.

**OCC-Q-006** [SOFT] Engine onboarding documentation (capabilities, dependencies,
resource profile, failure modes) should be completed before registration rather
than after. Late documentation creates operational knowledge gaps.

**OCC-Q-007** [HARD] Retiring an engine requires coordinating with OC-03
Dependency Manager to ensure no remaining workflows depend on the retiring
engine's capabilities. Orphaned workflow dependencies are an architectural error.

**OCC-Q-008** [SOFT] The Engine Registry should maintain a roadmap list of
planned future engines, even before they are available for registration. This
allows dependency graph pre-validation of planned architectures.

---

### OCC-R — Constitutional Completeness (4 rules)

**OCC-R-001** [HARD] The Master Orchestrator Constitution is the supreme governing
document for all orchestration operations. Any operational practice, configuration,
or architectural decision that conflicts with the Constitution is invalid.

**OCC-R-002** [HARD] The Constitution must be reviewed annually by the Architecture
Council. Amendments require a minimum 30-day review period and System Owner approval.

**OCC-R-003** [HARD] Every constitutional rule must be traceable to at least one
Orchestrator component, service, or process. Rules without a traceable operational
implementation are incomplete and must be implemented before the system operates.

**OCC-R-004** [SOFT] Constitutional rules should be self-enforcing where possible:
built into Orchestrator component logic rather than relying solely on human compliance.
Self-enforcing rules are more reliable than human-compliance rules.

---

### Constitutional Summary

| Category   | Rules | NON-NEG HARD | HARD | SOFT |
|------------|-------|--------------|------|------|
| OCC-A      | 10    | 1            | 7    | 2    |
| OCC-B      | 10    | 2            | 7    | 1    |
| OCC-C      | 10    | 1            | 6    | 3    |
| OCC-D      | 8     | 0            | 6    | 2    |
| OCC-E      | 8     | 1            | 6    | 1    |
| OCC-F      | 8     | 0            | 6    | 2    |
| OCC-G      | 8     | 1            | 6    | 1    |
| OCC-H      | 8     | 1            | 5    | 2    |
| OCC-I      | 8     | 1            | 5    | 2    |
| OCC-J      | 8     | 1            | 5    | 2    |
| OCC-K      | 8     | 0            | 6    | 2    |
| OCC-L      | 8     | 0            | 5    | 3    |
| OCC-M      | 8     | 0            | 6    | 2    |
| OCC-N      | 8     | 1            | 6    | 1    |
| OCC-O      | 8     | 1            | 6    | 1    |
| OCC-P      | 6     | 1            | 4    | 1    |
| OCC-Q      | 8     | 0            | 4    | 4    |
| OCC-R      | 4     | 0            | 3    | 1    |
| **TOTAL**  | **140**| **12**      | **99**| **29**|

---

## PART X — MASTER ORCHESTRATOR READINESS CHECKLIST

### Readiness Overview

The Master Orchestrator Readiness Checklist defines 12 readiness phases, each
containing multiple gate items. The system may not enter active trading operation
until all HARD gates in all 12 phases are verified PASS.

**Gate Classification:**
- **HARD gate:** Must pass. System cannot operate in trading mode if any HARD
  gate fails.
- **SOFT gate:** Should pass. SOFT gate failures require Operations Lead acknowledgment
  but do not block operation.

**Readiness Certificate Format:** OCERT-{YYYYMMDD}-{SESSION}-{SEQ:04d}

---

### P1 — Engine Registry Ready

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P1-01   | HARD | OC-08 Engine Registry initialized and responding       | Health probe to OC-08            |
| P1-02   | HARD | All CRITICAL engines registered                        | Registry query: status HEALTHY   |
| P1-03   | HARD | All engine versions authorized by OC-21                | Version check report             |
| P1-04   | HARD | Zero unauthorized engine versions in registry          | Version audit report             |
| P1-05   | HARD | Engine Registration Certificates issued for all entries| Certificate count matches registr|
| P1-06   | SOFT | Engine capability index fully populated                | Capability index query           |
| P1-07   | SOFT | No stale engine entries from previous sessions         | Stale entry scan report          |

---

### P2 — Workflow Ready

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P2-01   | HARD | OC-02 Workflow Manager initialized and responding      | Health probe                     |
| P2-02   | HARD | All 14 workflow definitions loaded from OC-22          | Workflow catalog query           |
| P2-03   | HARD | All workflow definitions pass schema validation        | Validation report                |
| P2-04   | HARD | Workflow state from previous session loaded (if any)   | State manager query              |
| P2-05   | HARD | No workflows in RUNNING state from previous session    | Active workflow count = 0        |
| P2-06   | SOFT | Workflow archive from last session archived cleanly    | Archive completion report        |

---

### P3 — Scheduling Ready

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P3-01   | HARD | OC-01 Master Scheduler initialized and responding      | Health probe                     |
| P3-02   | HARD | Trading calendar loaded and validated for current date | Calendar validation report       |
| P3-03   | HARD | All scheduled events for today loaded                  | Schedule query for today's date  |
| P3-04   | HARD | No schedule conflicts detected for today               | Conflict detection report        |
| P3-05   | HARD | Clock synchronized with NTP (skew < 1 second)          | NTP sync status report           |
| P3-06   | SOFT | Schedule history from yesterday archived               | Archive report                   |
| P3-07   | SOFT | Market holiday check confirmed for today               | Calendar confirmation            |

---

### P4 — Communication Ready

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P4-01   | HARD | OC-10 Communication Manager initialized               | Health probe                     |
| P4-02   | HARD | OC-11 Message Router initialized and routing table loaded| Routing table query             |
| P4-03   | HARD | All engine communication channels verified responsive  | Channel connectivity test        |
| P4-04   | HARD | Message queue depths at zero (clean start)             | Queue depth query                |
| P4-05   | HARD | Dead letter queue empty or reviewed                    | Dead letter queue query          |
| P4-06   | SOFT | Communication latency within SLA for all channels      | Latency measurement report       |
| P4-07   | SOFT | Message authentication configured for all channels    | Auth configuration audit         |

---

### P5 — Synchronization Ready

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P5-01   | HARD | OC-13 Synchronization Manager initialized             | Health probe                     |
| P5-02   | HARD | No orphaned barriers from previous session             | Barrier audit report             |
| P5-03   | HARD | All barrier timeout configurations loaded              | Configuration query              |
| P5-04   | SOFT | Barrier performance from previous session reviewed     | Analytics report query           |

---

### P6 — Monitoring Ready

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P6-01   | HARD | OC-16 Monitoring Manager initialized                  | Health probe                     |
| P6-02   | HARD | All 22 components emitting metrics to OC-16            | Metric coverage report           |
| P6-03   | HARD | All metric thresholds loaded from OC-22                | Threshold configuration audit    |
| P6-04   | HARD | Monitoring dashboard accessible to Operations Lead     | Dashboard availability check     |
| P6-05   | HARD | OC-16 self-monitoring active                           | Self-metric report               |
| P6-06   | SOFT | Previous session metric archive confirmed complete     | Archive completion report        |
| P6-07   | SOFT | Anomaly detection baseline updated with recent data   | Analytics baseline report        |

---

### P7 — Recovery Ready

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P7-01   | HARD | OC-18 Recovery Manager initialized                    | Health probe                     |
| P7-02   | HARD | All 8 recovery procedures (ORP-01 to ORP-08) loaded   | Procedure library query          |
| P7-03   | HARD | Each recovery procedure tested within last 90 days    | Test history report              |
| P7-04   | HARD | P1 notification contacts verified (Telegram, email)   | Contact test notification        |
| P7-05   | SOFT | Recovery procedure documentation current               | Documentation review date check  |

---

### P8 — Governance Approved

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P8-01   | HARD | Governance Engine (IIOS-GOV-ENG-ARCH-001) HEALTHY      | Governance health probe          |
| P8-02   | HARD | Governance Readiness Certificate received and valid    | Certificate validation           |
| P8-03   | HARD | All live strategy Validation Certificates current      | Certificate expiry query         |
| P8-04   | HARD | Constitutional kill switches confirmed inactive        | Kill switch status query         |
| P8-05   | HARD | Daily loss counter reset for new session               | Loss counter query = 0           |
| P8-06   | HARD | VIX level within constitutional limit (<= 45)          | VIX level from market data       |
| P8-07   | SOFT | Governance Engine OHS at NOMINAL or better             | GEHS query                       |
| P8-08   | SOFT | Previous session governance archive confirmed complete | Archive report                   |

---

### P9 — Security Verified

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P9-01   | HARD | All engine credentials loaded from secrets manager     | Secrets manager health check     |
| P9-02   | HARD | No credentials in configuration files                  | Configuration security scan      |
| P9-03   | HARD | All communication channels authenticated               | Authentication audit report      |
| P9-04   | HARD | Management interface access restricted to authorized users| Access control audit           |
| P9-05   | SOFT | Certificate rotation schedule current                  | Certificate expiry check         |
| P9-06   | SOFT | Security event log from previous session reviewed      | Security event query             |

---

### P10 — Documentation Complete

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P10-01  | HARD | MASTER_ORCHESTRATOR_ARCHITECTURE.md current and accessible| Document version check        |
| P10-02  | HARD | All 14 workflow definitions documented in Supplement B | Workflow catalog completeness    |
| P10-03  | HARD | All 8 recovery procedures documented with test history | Procedure documentation check   |
| P10-04  | SOFT | Session operational log initialized for today          | Log initialization check        |

---

### P11 — Operationally Ready

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P11-01  | HARD | OHS >= 0.80 (NOMINAL tier or better)                   | OHS computation                  |
| P11-02  | HARD | All CRITICAL components at HEALTHY status              | Component health report          |
| P11-03  | HARD | Dependency graph validated (zero circular dependencies)| Dependency validation report     |
| P11-04  | HARD | Data feeds verified responsive                         | Feed health check                |
| P11-05  | HARD | Portfolio state loaded and reconciled                  | Portfolio reconciliation report  |
| P11-06  | HARD | Risk limits configured and validated                   | Risk configuration audit         |
| P11-07  | SOFT | All HIGH components at HEALTHY or DEGRADED status      | Component health report          |

---

### P12 — Archived Correctly

| Gate    | Type | Requirement                                            | Verification Method              |
|---------|------|--------------------------------------------------------|----------------------------------|
| P12-01  | HARD | Previous session workflow archive complete             | Archive completeness check       |
| P12-02  | HARD | Previous session audit records committed to OC-14     | Audit record count verification  |
| P12-03  | HARD | Previous session incident records closed or actioned  | Open incident count check        |
| P12-04  | SOFT | Previous session performance report generated         | Report existence check           |
| P12-05  | SOFT | Previous session learning outcomes archived           | Learning archive check           |

---

### Readiness Gate Summary

| Phase | HARD Gates | SOFT Gates | Total |
|-------|------------|------------|-------|
| P1    | 5          | 2          | 7     |
| P2    | 5          | 1          | 6     |
| P3    | 5          | 2          | 7     |
| P4    | 5          | 2          | 7     |
| P5    | 3          | 1          | 4     |
| P6    | 5          | 2          | 7     |
| P7    | 4          | 1          | 5     |
| P8    | 6          | 2          | 8     |
| P9    | 4          | 2          | 6     |
| P10   | 3          | 1          | 4     |
| P11   | 6          | 1          | 7     |
| P12   | 3          | 2          | 5     |
|**TOTAL**|**54**   | **19**     | **73**|

**54 HARD gates must all PASS before session authorization.**

---

### Readiness State Machine

`
  [STARTUP]
      |
      v
[P1 REGISTRY READY] --> FAIL -> BLOCKED
      |
      v
[P2 WORKFLOW READY] --> FAIL -> BLOCKED
      |
      v
[P3 SCHEDULING READY] --> FAIL -> BLOCKED
      |
      v
[P4 COMMUNICATION READY] --> FAIL -> BLOCKED
      |
      v
[P5 SYNC READY] --> FAIL -> BLOCKED
      |
      v
[P6 MONITORING READY] --> FAIL -> BLOCKED
      |
      v
[P7 RECOVERY READY] --> FAIL -> BLOCKED
      |
      v
[P8 GOVERNANCE APPROVED] --> FAIL -> BLOCKED (no cert)
      |
      v
[P9 SECURITY VERIFIED] --> FAIL -> BLOCKED
      |
      v
[P10 DOCUMENTATION COMPLETE] --> FAIL -> BLOCKED
      |
      v
[P11 OPERATIONALLY READY] --> FAIL -> BLOCKED
      |
      v
[P12 ARCHIVED CORRECTLY] --> FAIL -> WARNING (non-blocking)
      |
      v
[ALL 54 HARD GATES: PASS]
      |
      v
[ISSUE READINESS CERTIFICATE]
OCERT-{YYYYMMDD}-{SESSION}-{SEQ:04d}
      |
      v
[ACTIVE SESSION — TRADING AUTHORIZED]
`

---

## SUPPLEMENTS

### SUPPLEMENT A — ENGINE INTERACTION MATRIX

The Engine Interaction Matrix defines every directed interaction between the
Master Orchestrator and each engine, and between engines (as coordinated by
the Orchestrator). Each row defines a source; each column defines a destination.
The cell content defines the interaction type and pipeline context.

---

#### A.1 Orchestrator-to-Engine Interactions

| Engine                | Invocation Context    | Interaction Type    | Priority  | SLA     |
|-----------------------|-----------------------|---------------------|-----------|---------|
| Knowledge Engine      | OP-04                 | Workflow step exec  | HIGH      | 20 min  |
| Information Engine    | OP-03, OP-04          | Workflow step exec  | HIGH      | 5 min   |
| Observation Engine    | OP-03                 | Workflow step exec  | HIGH      | 25 sec  |
| Entity Engine         | OP-03, OP-04          | Workflow step exec  | HIGH      | 30 sec  |
| Relationship Engine   | OP-04                 | Workflow step exec  | HIGH      | 10 min  |
| Event Engine          | OP-03, OP-05          | Workflow step exec  | HIGH      | 30 sec  |
| Prediction Engine     | OP-05                 | Workflow step exec  | HIGH      | 60 sec  |
| Decision Engine       | OP-06                 | Workflow step exec  | CRITICAL  | 30 sec  |
| Risk Engine           | OP-07, continuous     | Workflow step exec  | CRITICAL  | 15 sec  |
| Portfolio Engine      | OP-08                 | Workflow step exec  | HIGH      | 30 sec  |
| Learning Engine       | OP-09                 | Workflow step exec  | LOW       | 120 min |
| Strategy Engine       | OP-10                 | Workflow step exec  | HIGH      | 60 min  |
| Simulation Engine     | OP-11                 | Workflow step exec  | NORMAL    | 4 hrs   |
| Governance Engine     | OP-12, all pipelines  | Certificate + check | CRITICAL  | 5 min   |

---

#### A.2 Engine-to-Engine Routing Matrix (via Orchestrator)

The following interactions are routed by the Master Orchestrator (OC-11 Message Router).
No engine communicates directly with another.

| From                  | To                    | Data Artifact               | Pipeline Context |
|-----------------------|-----------------------|-----------------------------|------------------|
| Observation Engine    | Event Engine          | ObservationRecord           | OP-03            |
| Observation Engine    | Entity Engine         | PriceObservation            | OP-03            |
| Event Engine          | Knowledge Engine      | EventRecord                 | OP-04            |
| Event Engine          | Prediction Engine     | MarketEvent                 | OP-05            |
| Knowledge Engine      | Prediction Engine     | KnowledgeSnapshot           | OP-05            |
| Knowledge Engine      | Decision Engine       | KnowledgeContext            | OP-06            |
| Knowledge Engine      | Risk Engine           | RiskKnowledge               | OP-07            |
| Entity Engine         | Relationship Engine   | EntityProfile               | OP-04            |
| Relationship Engine   | Knowledge Engine      | RelationshipGraph           | OP-04            |
| Prediction Engine     | Decision Engine       | PredictionArtifact          | OP-06            |
| Prediction Engine     | Risk Engine           | RiskPrediction              | OP-07            |
| Decision Engine       | Risk Engine           | DecisionRecord              | OP-07            |
| Risk Engine           | Portfolio Engine      | RiskApproval                | OP-07, OP-08     |
| Risk Engine           | Decision Engine       | RiskContext                 | OP-06 (feedback) |
| Portfolio Engine      | Risk Engine           | PortfolioState              | OP-07 (input)    |
| Portfolio Engine      | Decision Engine       | PortfolioContext            | OP-06 (input)    |
| Learning Engine       | Knowledge Engine      | LearningOutput              | OP-04 (post)     |
| Learning Engine       | Strategy Engine       | StrategyPerformance         | OP-10            |
| Strategy Engine       | Simulation Engine     | StrategyCandidate           | OP-11            |
| Simulation Engine     | Governance Engine     | EvidenceDossier             | OP-12            |
| Governance Engine     | All engines           | GovernanceCertificate       | OP-12            |
| Governance Engine     | Decision Engine       | GovernanceConstraints       | OP-06            |
| Governance Engine     | Risk Engine           | ConstitutionalLimits        | OP-07            |

---

#### A.3 Engine Dependency Resolution Order

The following is the topologically valid execution order for the IIOS full-cycle
pipeline (each engine may begin when all its upstream dependencies are complete):

`
LAYER 1 (parallel, no dependencies):
  - Information Engine
  - Entity Engine (initial)

LAYER 2 (depends on Layer 1):
  - Observation Engine (uses Information Engine output)
  - Event Engine (uses Observation output)

LAYER 3 (depends on Layer 2):
  - Knowledge Engine (uses Event, Entity, Relationship inputs)
  - Relationship Engine (uses Entity output)

LAYER 4 (depends on Layer 3):
  - Prediction Engine (uses Knowledge, Event)

LAYER 5 (depends on Layer 4):
  - Risk Engine (initial context: uses Portfolio, Prediction)
  - Decision Engine (uses Prediction, Knowledge, Risk context)

LAYER 6 (depends on Layer 5):
  - Risk Engine (final approval: uses Decision Record)
  - Portfolio Engine (post-execution update)

LAYER 7 (parallel, post-session):
  - Learning Engine
  - Governance Engine (post-session reconciliation)
  - Simulation Engine (scheduled runs)

LAYER 8 (depends on Layer 7):
  - Strategy Engine (uses Learning output)
  - Knowledge Engine refresh (uses Learning output)
`

---

#### A.4 Critical Path Analysis

The critical path through the IIOS full decision cycle is:

`
Data Feeds
  --> Observation Engine (25s)
      --> Event Engine (10s)
          --> Knowledge Engine (180s, when full refresh)
              --> Prediction Engine (60s)
                  --> Decision Engine (30s)
                      --> Risk Engine (15s)
                          --> Portfolio Engine (30s)

Critical path total (including Knowledge refresh): ~350 seconds (~6 minutes)
Critical path total (Knowledge cached): ~170 seconds (~3 minutes)
`

The Knowledge Engine is the primary critical path bottleneck. The 5-minute
knowledge cache (loaded at session start) eliminates the Knowledge Engine from
the intra-session critical path.

---

#### A.5 Engine Availability Requirements

For the system to operate in full production mode, the following engines must
be available at HEALTHY or DEGRADED status:

| Engine              | Required Availability | Degraded Mode Impact           |
|---------------------|-----------------------|--------------------------------|
| Observation Engine  | REQUIRED              | No observations = no signals   |
| Decision Engine     | REQUIRED              | No decisions = no trading      |
| Risk Engine         | REQUIRED              | No risk check = no execution   |
| Governance Engine   | REQUIRED              | No cert = no session auth      |
| Knowledge Engine    | HIGH (cache backup)   | Cached knowledge may be used   |
| Prediction Engine   | HIGH                  | Reduced decision quality       |
| Portfolio Engine    | HIGH                  | Manual portfolio monitoring    |
| Learning Engine     | NORMAL                | Post-session, non-blocking     |
| Strategy Engine     | NORMAL                | Weekly, non-blocking           |
| Simulation Engine   | LOW                   | Validation deferred            |

**Minimum viable operation:** Observation + Decision + Risk + Governance engines
all HEALTHY. All other engines DEGRADED is acceptable for limited operation.

---

### SUPPLEMENT B — WORKFLOW CATALOG

The Workflow Catalog is the authoritative list of all named workflows in the
Master Orchestrator. Each entry defines the workflow's trigger, steps, dependencies,
SLA, and failure policy.

---

#### B.1 Workflow Catalog — Summary

| Workflow ID | Name                    | Trigger Type  | Frequency          | Steps |
|-------------|-------------------------|---------------|--------------------|-------|
| WF-STARTUP  | System Startup          | Manual/Auto   | Per boot           | 10    |
| WF-DAILY    | Daily Market Init       | Scheduled     | Daily 09:00 IST    | 8     |
| WF-OBS      | Observation Cycle       | Interval      | Every 30s          | 5     |
| WF-KNOW     | Knowledge Refresh       | Scheduled     | Daily + post-learn | 7     |
| WF-PRED     | Prediction Cycle        | Event-driven  | Per observation    | 5     |
| WF-DEC      | Decision Cycle          | Event-driven  | Per prediction     | 6     |
| WF-RISK     | Risk Approval           | Event-driven  | Per decision       | 5     |
| WF-PORT     | Portfolio Update        | Event-driven  | Per execution      | 4     |
| WF-LEARN    | Post-Session Learning   | Scheduled     | Daily 15:45 IST    | 6     |
| WF-STRAT    | Strategy Review         | Scheduled     | Weekly             | 7     |
| WF-SIM      | Simulation Run          | On-demand     | Per request        | 6     |
| WF-GOV      | Governance Check        | Interval      | Every 30s          | 4     |
| WF-STOP     | System Shutdown         | Signal        | Per shutdown req   | 8     |
| WF-RECOV    | Failure Recovery        | Incident      | Per P1/P2 incident | 6     |

---

#### B.2 WF-STARTUP — System Startup Workflow

**Definition:**
`
WF-STARTUP
  Version: 1.0
  Priority: CRITICAL
  Trigger: System boot or manual start
  Timeout: 600 seconds (10 minutes)
  Steps:
    STEP-01: Load configuration (OC-22) [Required]
    STEP-02: Initialize Engine Registry (OC-08) [Required]
    STEP-03: Run Engine Discovery (OC-09) [Required]
    STEP-04: Register all discovered engines (OC-08) [Required]
    STEP-05: Validate dependency graph (OC-03) [Required]
    STEP-06: Initial health assessment (OC-15) [Required]
    STEP-07: Request Governance Certificate (Governance Engine) [Required]
    STEP-08: Infrastructure checks [Required]
    STEP-09: Pre-session knowledge refresh (WF-KNOW) [Required]
    STEP-10: Set system state READY (OC-14) [Required]
  Failure Policy: HALT on any Required step failure
  Success Criteria: All 10 steps COMPLETED; OHS >= 0.80; Gov Cert obtained
`

---

#### B.3 WF-OBS — Observation Cycle Workflow

**Definition:**
`
WF-OBS
  Version: 1.0
  Priority: HIGH
  Trigger: 30-second interval timer during market hours
  Timeout: 25 seconds
  Steps:
    STEP-01: Fetch market data from active feeds [Required]
    STEP-02: Invoke Observation Engine (OC-04) [Required]
    STEP-03: Update Entity Engine with new observations [Required]
    STEP-04: Evaluate observations in Event Engine [Required]
    STEP-05: Publish observation freshness record (OC-14) [Required]
  Failure Policy: Log and skip cycle; do not block next cycle
  Success Criteria: All steps complete within 25s; freshness record updated
  Chained Workflow: Triggers WF-PRED if prediction interval elapsed
`

---

#### B.4 WF-DEC — Decision Cycle Workflow

**Definition:**
`
WF-DEC
  Version: 1.0
  Priority: CRITICAL
  Trigger: Event — fresh predictions available + decision interval elapsed
  Timeout: 30 seconds
  Pre-conditions (all must be true):
    Observations fresh (< 30s)
    Predictions available (< prediction TTL)
    Kill switch NOT triggered
    Daily loss < 2% (constitutional limit)
    Governance session active
    Active Readiness Certificate valid
  Steps:
    STEP-01: Evaluate pre-decision gate (all conditions) [Required]
    STEP-02: Invoke Decision Engine 5-agent debate (OC-04) [Required]
    STEP-03: Evaluate decision score against threshold (6.5) [Required]
    STEP-04: Route approved decision to WF-RISK [If score >= 6.5]
    STEP-05: Log decision record (OC-14) [Required]
    STEP-06: Notify Agent Coordinator of completion (OC-07) [Required]
  Failure Policy: Fail step; log reason; do not cascade to WF-RISK
  Success Criteria: Decision record created; routing to WF-RISK if approved
`

---

#### B.5 WF-RISK — Risk Approval Workflow

**Definition:**
`
WF-RISK
  Version: 1.0
  Priority: CRITICAL
  Trigger: Event — Decision Record received (score >= 6.5)
  Timeout: 15 seconds
  Steps:
    STEP-01: Invoke Risk Engine for position sizing (OC-04) [Required]
    STEP-02: Constitutional risk gate check [Required]
      - Daily loss < 2%
      - VIX <= 45
      - Strategy drawdown < 15%
    STEP-03: Portfolio risk gate check [Required]
      - Strategy weight <= 40%
      - Sector concentration <= 30%
      - Correlation acceptable
    STEP-04: Compute final position size [Required]
    STEP-05: Issue Risk Approval Record [Required if approved]
  Failure Policy: REJECT decision; log reason; no execution
  Success Criteria: Risk Approval Record issued; Execution workflow triggered
`

---

#### B.6 WF-LEARN — Post-Session Learning Workflow

**Definition:**
`
WF-LEARN
  Version: 1.0
  Priority: LOW
  Trigger: Scheduled — 15:45 IST, after portfolio end-of-session reconciliation
  Timeout: 7200 seconds (120 minutes)
  Steps:
    STEP-01: Extract session trade outcomes (OC-04 → Portfolio Engine) [Required]
    STEP-02: Invoke Learning Engine analysis (OC-04) [Required]
    STEP-03: Update strategy performance tracker [Required]
    STEP-04: Update prediction model calibration [Required]
    STEP-05: Signal Knowledge Refresh (trigger WF-KNOW) [Required]
    STEP-06: Archive learning outputs (OC-14) [Required]
  Failure Policy: Log and continue; non-blocking for next session
  Success Criteria: Learning artifacts archived; WF-KNOW triggered
`

---

### SUPPLEMENT C — SCHEDULING REFERENCE

#### C.1 Master Schedule — Full Reference Table

The Master Schedule defines all scheduled events for a standard trading day.
All times are in IST (Indian Standard Time, UTC+5:30).

| Schedule ID | Description                          | Time          | Frequency   | Workflow    | Priority  |
|-------------|--------------------------------------|---------------|-------------|-------------|-----------|
| SCH-001     | System startup (if not running)      | 08:00 IST     | Weekdays    | WF-STARTUP  | CRITICAL  |
| SCH-002     | Pre-session knowledge refresh        | 08:50 IST     | Weekdays    | WF-KNOW     | HIGH      |
| SCH-003     | Governance pre-session cert request  | 08:30 IST     | Weekdays    | WF-GOV      | CRITICAL  |
| SCH-004     | Daily market pipeline                | 09:00 IST     | Weekdays    | WF-DAILY    | CRITICAL  |
| SCH-005     | Observation cycle (continuous)       | 09:15–15:30   | Every 30s   | WF-OBS      | HIGH      |
| SCH-006     | Governance monitoring (continuous)   | 09:00–15:30   | Every 30s   | WF-GOV      | CRITICAL  |
| SCH-007     | Portfolio mid-session review         | 12:00 IST     | Weekdays    | WF-PORT     | HIGH      |
| SCH-008     | End-of-session processing            | 15:35 IST     | Weekdays    | WF-PORT     | CRITICAL  |
| SCH-009     | Post-session learning                | 15:45 IST     | Weekdays    | WF-LEARN    | LOW       |
| SCH-010     | Governance post-session              | 15:40 IST     | Weekdays    | WF-GOV      | CRITICAL  |
| SCH-011     | Knowledge refresh (post-learning)    | 17:30 IST     | Weekdays    | WF-KNOW     | HIGH      |
| SCH-012     | Daily performance report             | 16:00 IST     | Weekdays    | OC-20 report| LOW       |
| SCH-013     | Strategy review                      | Saturdays     | Weekly      | WF-STRAT    | HIGH      |
| SCH-014     | Simulation run (strategy candidates) | Weekends      | Weekly      | WF-SIM      | NORMAL    |
| SCH-015     | Weekly operations report             | Friday 17:00  | Weekly      | OC-20 report| LOW       |
| SCH-016     | Monthly performance report           | Month end     | Monthly     | OC-20 report| LOW       |
| SCH-017     | Recovery procedure test              | Saturday      | Monthly     | OC-18 test  | NORMAL    |
| SCH-018     | System shutdown (end of trading day) | 18:00 IST     | Weekdays    | WF-STOP     | CRITICAL  |

---

#### C.2 Trading Calendar Integration

The Master Scheduler integrates with the NSE trading calendar to:
- Skip all scheduled events on NSE holidays.
- Adjust session times for Muhurat trading (special Diwali session).
- Handle partial trading days (when NSE announces early closure).

**Calendar source:** Loaded from the Governance Engine's calendar authority
at startup (OLS-01) and refreshed monthly.

**NSE Holiday Types:**
| Holiday Type      | Example                       | Action                          |
|-------------------|-------------------------------|---------------------------------|
| National holiday  | Republic Day, Independence Day| Skip all market schedules       |
| Diwali Muhurat    | Evening session, 1 day/year   | Special evening session schedule|
| Market closure    | NSE announced                 | Skip market schedules           |
| Scheduled holiday | Holi, Good Friday, etc.       | Skip all market schedules       |

---

#### C.3 Schedule Conflict Resolution Reference

When two or more scheduled workflows conflict at the same time slot:

| Scenario                               | Resolution Policy                         |
|----------------------------------------|-------------------------------------------|
| Two CRITICAL workflows same slot       | Highest-priority runs; other deferred 30s |
| CRITICAL + HIGH same slot              | CRITICAL first; HIGH deferred             |
| CRITICAL + NORMAL same slot            | CRITICAL first; NORMAL deferred by 60s    |
| HIGH + HIGH same slot                  | First-registered runs; second deferred 30s|
| Any + DEFERRED same slot               | DEFERRED deferred until no conflict       |
| All CRITICAL, resource constrained     | OC-06 Resource Manager arbitrates         |

---

#### C.4 Schedule Miss Recovery Policy

| Missed Schedule Urgency | Recovery Policy                                     |
|-------------------------|-----------------------------------------------------|
| CRITICAL, < 10 min late | Execute immediately on detection                    |
| CRITICAL, 10-30 min late| Execute immediately; raise P2 incident              |
| CRITICAL, > 30 min late | Escalate to P1 incident; do not auto-execute        |
| HIGH, < 15 min late     | Execute immediately on detection                    |
| HIGH, 15-60 min late    | Execute if still in session; raise P3 incident      |
| HIGH, > 60 min late     | Defer to next scheduled time; raise P3 incident     |
| NORMAL/LOW, any         | Defer to next scheduled time; log only              |

---

#### C.5 Event-Driven Schedule Triggers

In addition to time-based schedules, the following events trigger workflow execution:

| Event                                  | Triggered Workflow | Priority  |
|----------------------------------------|--------------------|-----------|
| Observation pipeline completes         | WF-PRED (if interval elapsed) | HIGH|
| Prediction pipeline completes          | WF-DEC (if decision time)     | CRITICAL|
| Decision score >= 6.5                  | WF-RISK                       | CRITICAL|
| Risk approval granted                  | Execution (external)          | CRITICAL|
| Execution confirmed                    | WF-PORT                       | HIGH   |
| Learning pipeline completes            | WF-KNOW (refresh)             | HIGH   |
| Strategy candidate ready               | WF-SIM                        | NORMAL |
| P1 or P2 incident raised               | WF-RECOV                      | CRITICAL|
| Governance Engine UNHEALTHY            | System SAFE mode              | CRITICAL|
| OHS drops below 0.35                   | WF-STOP (Emergency)           | CRITICAL|
| Kill switch triggered                  | WF-STOP (Emergency)           | CRITICAL|
| VIX > 45                               | WF-GOV + halt trading         | CRITICAL|

---

### SUPPLEMENT D — DEPENDENCY MATRIX

#### D.1 Workflow Step Dependency Matrix

This matrix defines, for each workflow step, the prerequisite conditions that
must be satisfied before the step can execute. The Dependency Manager (OC-03)
enforces these dependencies.

**Notation:** "Engine X: Complete" means the named workflow step for Engine X
must have completed successfully. "State: value" means OC-14 must show that state.

| Workflow  | Step | Engine             | Prerequisites                                  |
|-----------|------|--------------------|------------------------------------------------|
| WF-OBS    | 1    | Data Feeds         | Market hours active; feeds HEALTHY             |
| WF-OBS    | 2    | Observation Engine | Step 1 complete; Observation Engine HEALTHY    |
| WF-OBS    | 3    | Entity Engine      | Step 2 complete; Entity Engine HEALTHY         |
| WF-OBS    | 4    | Event Engine       | Step 2 complete; Event Engine HEALTHY          |
| WF-OBS    | 5    | State Manager      | Steps 3 & 4 complete (OR barrier)             |
| WF-PRED   | 1    | —                  | WF-OBS: complete; freshness < 30s             |
| WF-PRED   | 2    | Prediction Engine  | Step 1 complete; Knowledge fresh               |
| WF-PRED   | 3    | State Manager      | Step 2 complete                                |
| WF-DEC    | 1    | —                  | WF-PRED: complete; Gov cert valid; KS inactive |
| WF-DEC    | 2    | Decision Engine    | Step 1: all gates PASS                         |
| WF-DEC    | 3    | —                  | Step 2: score computed                         |
| WF-DEC    | 4    | Message Router     | Step 3: score >= 6.5                           |
| WF-RISK   | 1    | Risk Engine        | WF-DEC complete; Decision Record received      |
| WF-RISK   | 2    | —                  | Step 1 complete: constitutional gate          |
| WF-RISK   | 3    | —                  | Step 2 PASS: portfolio gate                   |
| WF-RISK   | 4    | Risk Engine        | Step 3 PASS                                   |
| WF-RISK   | 5    | —                  | Step 4 complete                                |
| WF-PORT   | 1    | Portfolio Engine   | Execution confirmed                            |
| WF-PORT   | 2    | —                  | Step 1 complete                                |
| WF-KNOW   | 1    | Knowledge Engine   | No active trading workflows; feeds available   |
| WF-KNOW   | 2    | Entity Engine      | Step 1 complete                                |
| WF-KNOW   | 3    | Relationship Engine| Step 2 complete                                |
| WF-KNOW   | 4    | Event Engine       | Step 1 complete                                |
| WF-KNOW   | 5    | Knowledge Engine   | Steps 2, 3, 4 complete (AND barrier)          |
| WF-LEARN  | 1    | Portfolio Engine   | WF-PORT end-of-session complete               |
| WF-LEARN  | 2    | Learning Engine    | Step 1 complete                                |
| WF-LEARN  | 3–6  | various            | Step 2 complete                                |

---

#### D.2 Inter-Workflow Dependency Table

| Workflow    | Depends On        | Dependency Type | Notes                              |
|-------------|-------------------|-----------------|------------------------------------|
| WF-PRED     | WF-OBS            | Sequential      | Must complete each cycle           |
| WF-DEC      | WF-PRED           | Sequential      | Must have fresh predictions        |
| WF-RISK     | WF-DEC            | Sequential      | Decision Record required           |
| WF-PORT     | Execution confirm | Event-driven    | After each executed trade          |
| WF-LEARN    | WF-PORT (EoD)     | Sequential      | After end-of-session reconciliation|
| WF-KNOW(post)| WF-LEARN         | Sequential      | Incorporate learning outputs       |
| WF-STRAT    | WF-LEARN (recent) | Soft dep.       | Benefits from recent learning      |
| WF-SIM      | WF-STRAT          | Event-driven    | For each strategy candidate        |
| WF-DAILY    | WF-STARTUP        | Sequential      | Session init requires system ready |
| WF-STOP     | WF-DAILY          | Sequential      | Shutdown after session init        |
| WF-GOV(pre) | WF-STARTUP        | Sequential      | After system ready                 |
| WF-RECOV    | Incident raised   | Event-driven    | Per P1/P2 incident                 |

---

#### D.3 Resource Dependency Matrix

This matrix shows which resource categories are required by each workflow type.

| Workflow | CPU     | Memory  | Data Feed | Queue   | Storage I/O |
|----------|---------|---------|-----------|---------|-------------|
| WF-OBS   | MEDIUM  | MEDIUM  | HIGH      | LOW     | LOW         |
| WF-PRED  | HIGH    | HIGH    | LOW       | LOW     | MEDIUM      |
| WF-DEC   | HIGH    | HIGH    | NONE      | LOW     | MEDIUM      |
| WF-RISK  | MEDIUM  | MEDIUM  | NONE      | LOW     | LOW         |
| WF-PORT  | LOW     | LOW     | NONE      | LOW     | LOW         |
| WF-KNOW  | MEDIUM  | HIGH    | MEDIUM    | LOW     | HIGH        |
| WF-LEARN | HIGH    | HIGH    | NONE      | LOW     | HIGH        |
| WF-STRAT | HIGH    | MEDIUM  | NONE      | LOW     | HIGH        |
| WF-SIM   | VERY HIGH| HIGH   | NONE      | LOW     | HIGH        |
| WF-GOV   | LOW     | LOW     | NONE      | LOW     | LOW         |
| WF-RECOV | MEDIUM  | MEDIUM  | VARIES    | MEDIUM  | MEDIUM      |

**Resource conflict rule:** WF-SIM (VERY HIGH CPU) must not execute concurrently
with WF-PRED or WF-DEC (HIGH CPU) during market hours. OC-01 schedules simulation
runs for off-hours to prevent this conflict.

---

### SUPPLEMENT E — GOVERNANCE DECISION RECORDS

Governance Decision Records (GDRs) for the Master Orchestrator define the
non-negotiable architectural decisions that protect the integrity, safety, and
trustworthiness of the orchestration layer.

---

**GDR-MO-001 — Orchestrator Excluded from Investment Domain**
The Master Orchestrator must never perform, replicate, or approximate investment
domain analysis. If it becomes technically difficult to separate coordination
from analysis (e.g., if adding a "smart routing" feature requires understanding
market conditions), the feature must be rejected.
Rationale: Entangling coordination with investment intelligence creates hidden
bias in scheduling, undermines engine independence, and corrupts governance.

**GDR-MO-002 — All Engine Communication Mediated by Orchestrator**
No engine may communicate with another engine without routing through the
Orchestrator's Communication Manager (OC-10) and Message Router (OC-11).
Direct engine-to-engine communication is architecturally prohibited.
Rationale: Unmediated communication bypasses audit, authorization, and governance
checks. Complete communication mediation is required for auditability.

**GDR-MO-003 — Governance Engine is the Constitutional Authority**
The Governance Engine (IIOS-GOV-ENG-ARCH-001) is the constitutional authority
over IIOS. The Master Orchestrator implements governance decisions but does not
define them, modify them, or bypass them. The Orchestrator is governed; it
does not govern.
Rationale: An Orchestrator that could override governance rules could bypass
any safety mechanism in the system. This separation is non-negotiable.

**GDR-MO-004 — Stateless Execution, Stateful State Manager**
The Execution Coordinator (OC-04) must be stateless: it executes workflow steps
without maintaining its own persistent state. All state belongs to OC-14
State Manager. Stateless execution enables horizontal scaling and simplifies
failure recovery (simply restart OC-04; state is preserved in OC-14).
Rationale: Distributed state is the primary cause of split-brain failures in
distributed systems. Centralizing state in OC-14 eliminates this risk.

**GDR-MO-005 — Deterministic Scheduling**
All scheduling decisions must be deterministic. Given the same configuration,
schedule table, and clock, the sequence of workflow triggers must be reproducible.
Non-deterministic scheduling prevents replay-based testing and debugging.
Rationale: Financial systems require auditability. Auditability requires
reproducibility. Reproducibility requires determinism.

**GDR-MO-006 — Recovery Does Not Touch Positions**
No recovery procedure, failover mechanism, or emergency action within the
Master Orchestrator may open, close, or modify any investment position.
If a failure creates position risk, the response is to notify the Operations
Lead and System Owner, not to automatically modify positions.
Rationale: Automated position modification during a failure state creates
the highest risk of catastrophic loss. Human judgment is required.

**GDR-MO-007 — Single Entry Point for Workflow Creation**
All workflow instances must be created through OC-02 Workflow Manager, and
only in response to a registered trigger (scheduled event, registered event
type, or explicit system command). No component may create workflow instances
outside OC-02.
Rationale: Ad hoc workflow creation bypasses dependency validation, priority
management, and audit logging. Single-point creation ensures every workflow
is tracked and governed.

**GDR-MO-008 — No Engine May Self-Schedule**
Engines must not schedule their own future invocations. Scheduling is
exclusively the responsibility of OC-01 Master Scheduler and OC-02 Workflow
Manager. An engine that schedules its own invocations circumvents priority
management and dependency checking.
Rationale: Self-scheduling creates a coordination hole — the Orchestrator
loses visibility into the engine's future resource needs and execution context.

**GDR-MO-009 — Immutable Orchestrator Operational Log**
The Orchestrator's operational log (maintained by OC-14 and surfaced by OC-08
audit functions) is append-only and immutable. No operational log entry may be
modified or deleted, even to correct errors. Corrections are applied by adding
new entries, not by modifying existing ones.
Rationale: An immutable operational log is the foundation of a trustworthy audit
trail. If log entries can be modified, the audit trail cannot be trusted.

**GDR-MO-010 — Extensibility Without Modification**
Adding a new engine, a new workflow, or a new service to the Orchestrator must
not require modifying any existing Orchestrator component. Extension is through
registration (OC-08), configuration (OC-22), and workflow catalog addition
(Supplement B). The Open/Closed Principle applies to the Master Orchestrator:
open for extension, closed for modification.
Rationale: An Orchestrator that requires code modification to add new engines
creates regression risk with every new engine addition. Extension-without-
modification protects existing functionality.

---

### SUPPLEMENT F — ANTI-PATTERNS

Orchestration anti-patterns are recurring mistakes in orchestration design or
operation that undermine the reliability, safety, or trustworthiness of the
Master Orchestrator. Each anti-pattern is named, described, and accompanied by
the correct alternative.

---

**OMAP-01 — God Orchestrator**

*Description:* The Orchestrator grows to contain investment domain logic, acting
as a strategic decision-maker rather than a coordinator. It begins making decisions
about which strategies to favor, adjusting prediction weights, or modifying risk
parameters based on its own "knowledge."

*Symptoms:*
- Orchestrator configuration files contain investment parameters (thresholds,
  weights, strategy preferences).
- Orchestrator components produce outputs that reference market conditions rather
  than coordination states.
- Specialized engines are consulted less frequently; the Orchestrator answers
  questions that should go to engines.

*Consequences:* Hidden investment bias in scheduling; entangled concerns that make
the system difficult to audit; engines that cannot function without the Orchestrator
present; governance violations.

*Correct Pattern:* The Orchestrator knows nothing about markets. Every investment
question is routed to the appropriate specialized engine. The Orchestrator's
configuration contains only timing, routing, resource, and health parameters.

---

**OMAP-02 — Polling Hell**

*Description:* The Orchestrator (or components within it) poll engine state
repeatedly at short intervals rather than using event-driven notification.
Example: OC-04 polls the Prediction Engine every second to check if it has
produced output, rather than waiting for an event notification.

*Symptoms:*
- High inter-component communication volume with no corresponding workflow progress.
- Engine CPU usage elevated by constant health/status probe responses.
- Message queue depth grows with status queries rather than meaningful data.

*Consequences:* Wasted resources; masked event delays (polling may miss rapid
state changes between poll intervals); inability to distinguish "in progress"
from "stuck."

*Correct Pattern:* Event-driven architecture. Engines notify the Orchestrator
when they produce output. OC-11 Message Router delivers notifications. OC-13
Synchronization Manager waits on barriers, not polls.

---

**OMAP-03 — Silent Failure**

*Description:* A workflow step fails and the failure is swallowed: logged at DEBUG
level, not escalated, not reflected in workflow state. Downstream steps proceed
with missing or stale inputs.

*Symptoms:*
- Workflow success rate appears high but output quality is low.
- Post-session analysis reveals decisions based on hours-old observations.
- OHS remains OPTIMAL while the Decision Engine has been producing decisions
  without fresh predictions for 3 hours.

*Consequences:* Investment decisions made on stale data; undetected operational
risk; loss of trust in system outputs.

*Correct Pattern:* Every workflow step failure is logged at WARN or higher,
reflected in workflow state, and escalated appropriately. The Orchestrator's
health depends on knowing what is actually working.

---

**OMAP-04 — Workflow Sprawl**

*Description:* Ad hoc workflow creation proliferates: components create workflow
instances outside OC-02, temporary workflows are created for one-off tasks and
never cleaned up, and the workflow registry becomes cluttered with thousands of
ambiguously named workflows.

*Symptoms:*
- Workflow count grows continuously even when the same logical pipeline runs.
- Many workflows in TIMED_OUT or PENDING state with no clear owner.
- Dependency graph contains orphaned nodes referring to deleted workflows.

*Consequences:* Resource consumption by dormant workflows; state management
overhead; dependency graph inconsistencies; degraded monitoring clarity.

*Correct Pattern:* All workflow creation through OC-02 Workflow Manager only.
Every workflow has a defined lifecycle with mandatory cleanup. Periodic workflow
archive runs clean up completed/failed instances. The 14 named workflow types
in the catalog cover all legitimate use cases.

---

**OMAP-05 — Brittle Dependency Chains**

*Description:* Workflows are designed with unnecessarily tight sequential
dependencies, preventing any parallel execution. Every step waits for every
previous step even when there is no data dependency.

*Symptoms:*
- Single-threaded workflow execution despite no actual dependencies between steps.
- Workflow duration equals the sum of all step durations.
- Resource utilization peaks and valleys rather than smooth utilization.

*Consequences:* Poor performance; long critical path; unnecessarily slow
decision-to-execution latency.

*Correct Pattern:* OC-03 Dependency Manager enforces only necessary dependencies.
Independent steps run in parallel. OC-13 Synchronization Manager provides barriers
only where data dependencies require them.

---

**OMAP-06 — Priority Inflation**

*Description:* Over time, every workflow is escalated to CRITICAL priority
because teams believe their workflow is the most important. The priority system
becomes meaningless when all workflows are CRITICAL.

*Symptoms:*
- The priority table shows 80% of workflows at CRITICAL or HIGH.
- Scheduling conflicts are frequent because CRITICAL-CRITICAL conflicts resolve
  arbitrarily.
- Low-priority workflows (Learning, Simulation) never execute due to competition.

*Consequences:* Priority system provides no differentiation; resource management
becomes non-functional; DEFERRED and LOW priority workflows starve permanently.

*Correct Pattern:* Priority assignments are controlled by OC-05 Priority Manager
with Architecture Council approval for CRITICAL/HIGH. OCC-M-002 explicitly states
priority assignments require approval. Monthly priority reviews check for creep.

---

**OMAP-07 — Recovery Theater**

*Description:* Recovery procedures exist on paper but are never tested. When an
incident occurs, the recovery procedure fails silently or is discovered to not
apply to the actual failure mode.

*Symptoms:*
- Recovery procedure documentation dated more than 90 days ago without test log.
- Recovery success rate < 80% per OC-19 Analytics.
- Post-incident reviews show "recovery procedure did not apply to this failure."

*Consequences:* False confidence in recovery capabilities; extended downtime
during actual incidents; potential position risk from extended unavailability.

*Correct Pattern:* OCC-I-004 requires recovery procedures tested monthly.
OC-18 Recovery Manager tracks test dates and flags procedures not tested within
90 days. Test results are logged with outcome and any procedure updates required.

---

**OMAP-08 — Configuration Drift**

*Description:* Runtime configuration (in OC-22) diverges from the documented
configuration baseline. Changes are applied directly to the running system
without updating documentation or version-controlling the change.

*Symptoms:*
- Configuration in production does not match the version in the repository.
- Schedule changes applied "temporarily" become permanent without documentation.
- New team members cannot understand the running configuration from documentation.

*Consequences:* Operational unpredictability; failed deployments when configuration
is reset to documented state; governance violations.

*Correct Pattern:* All configuration changes go through OC-22 Configuration
Manager using the defined change process. Configuration is version-controlled.
Changes require appropriate approval level (OCC-C-003 equivalent for config).

---

**OMAP-09 — Monitoring as Afterthought**

*Description:* Monitoring (OC-16) is implemented after the rest of the system,
resulting in incomplete metric coverage, missing threshold definitions, and
a dashboard that does not reflect the actual operational state.

*Symptoms:*
- OQD-07 Observability score consistently below 0.80.
- Incidents are first detected by user reports rather than monitoring alerts.
- The OHS computation omits components because they produce no metrics.

*Consequences:* Unknown failure modes; late incident detection; OHS understates
true system risk.

*Correct Pattern:* Monitoring is designed with each component. Every component
emits metrics. OCC-J-002 requires all components to emit metrics. Monitoring
is tested as a primary system requirement, not an afterthought.

---

**OMAP-10 — Engine Coupling via Orchestrator**

*Description:* The Orchestrator is used as a shared data store or coordination
memory between engines, creating implicit coupling. Engine A writes data to
OC-14 State Manager for Engine B to read directly, bypassing the message
routing architecture.

*Symptoms:*
- Engine B reads data from OC-14 that was written by Engine A, with no explicit
  message routing event.
- Adding or removing Engine A causes Engine B to silently fail.
- The engine dependency declared in registration does not match the actual
  runtime data flows.

*Consequences:* Hidden coupling that violates engine independence (OCC-B-001 through
OCC-B-010); routing changes that have unexpected side effects; governance audit gaps.

*Correct Pattern:* All engine-to-engine data flows use OC-10 Communication Manager
and OC-11 Message Router. OC-14 State Manager stores Orchestrator state only, not
engine-to-engine data. Engine outputs are messages; messages are routed.

---

### SUPPLEMENT G — OPERATIONAL RUNBOOK

The Operational Runbook provides step-by-step procedures for routine and
emergency operational tasks performed by the Operations Lead and System Owner.

---

#### G.1 Daily Startup Procedure (T-60 to T-00)

**Step 1: T-60 — System Boot Verification**
- Confirm the Orchestrator process is running (WF-STARTUP should auto-trigger at 08:00 IST).
- Check system startup log: confirm all OLS-01 through OLS-05 completed without error.
- If system is not running: manually trigger WF-STARTUP. Monitor startup log.
- Confirm: OHS >= 0.80 (NOMINAL or better) before proceeding.

**Step 2: T-45 — Engine Registration Verification**
- Query OC-08 Engine Registry: confirm all CRITICAL engines registered HEALTHY.
- Query OC-21 Version Manager: confirm all versions authorized.
- If any CRITICAL engine is OFFLINE: investigate immediately.
  - OC-09 Engine Discovery: has the engine been discovered?
  - OC-15 Health Manager: what was the last probe result?
  - Check infrastructure: is the engine's container/process running?
- If engine cannot be recovered within 30 minutes: escalate to P1 incident.

**Step 3: T-30 — Governance Certification Verification**
- Confirm Governance Readiness Certificate obtained (P8-02 gate).
- Query Governance Engine health: HEALTHY?
- Confirm constitutional kill switches inactive (VIX <= 45, daily loss = 0).
- Confirm all live strategy Validation Certificates current.
- If Governance Certificate not obtained: do NOT proceed to trading. Investigate.

**Step 4: T-20 — Full Readiness Checklist Review**
- Execute all 12 readiness phases (P1 through P12): confirm 54/54 HARD gates PASS.
- Any HARD gate failure: investigate and resolve before proceeding.
- SOFT gate failures: acknowledge and document; non-blocking.

**Step 5: T-10 — Pre-Session Knowledge Refresh**
- Confirm WF-KNOW completed successfully (SCH-002).
- Knowledge timestamp updated to within last 15 minutes.
- If knowledge refresh failed: check Knowledge Engine health; retry once.
  If retry fails: escalate to P2; operate with yesterday's knowledge (if within 24 hours).

**Step 6: T-05 — First Observation Cycle**
- WF-OBS first cycle should have completed (SCH-005 starts at 09:15 IST).
- Confirm observation freshness < 30 seconds.
- Confirm data feeds responsive.

**Step 7: T-00 — Session Active Confirmation**
- OLS-08 Active Session mode engaged.
- Monitoring dashboard active and accessible.
- Operations Lead confirms readiness in session log.
- Session authorized.

---

#### G.2 Intraday Monitoring Procedure

**Continuous (automated, every 30 seconds):**
- OC-16 Monitoring Manager: collects metrics from all 22 components.
- OC-12 Governance Pipeline: continuous governance checks.
- OC-15 Health Manager: engine health probes.

**Operations Lead: Manual Checks (every 30 minutes):**
- Check monitoring dashboard: OHS current and NOMINAL or better?
- Active workflow count reasonable (not accumulating)?
- Message queue depths within normal range?
- Any WARN threshold alerts? Investigate and document.
- Any open incidents? Check status.

**On WARN Alert:**
- Identify the alerting component and metric.
- Consult the component runbook section for that metric.
- Determine if the WARN is trending toward CRIT.
- If yes: escalate to P3 incident proactively.

**On CRIT Alert:**
- Immediately assess: is trading affected?
- If trading affected: P1 or P2 incident based on severity.
- If trading not yet affected but risk is HIGH: P2 incident.
- Engage OC-18 Recovery Manager for automated recovery if applicable.

---

#### G.3 End-of-Session Procedure (15:30 IST to 18:00 IST)

**15:30 IST — Market Close:**
- WF-OBS continuous cycle stops (SCH-005 end time).
- Final observation cycle completes.
- Monitoring continues.

**15:35 IST — End-of-Session Portfolio Reconciliation:**
- WF-PORT end-of-session variant triggers (SCH-008).
- Confirm all open positions reconciled.
- Daily P&L locked.
- Drawdown computed.

**15:40 IST — Post-Session Governance:**
- WF-GOV post-session variant triggers (SCH-010).
- Governance Engine performs post-session compliance suite.
- Audit hash chain verified.
- Session governance archive committed.

**15:45 IST — Post-Session Learning:**
- WF-LEARN triggers (SCH-009).
- Monitor learning completion (up to 2 hours).
- Do not shut down system before WF-LEARN completes.

**16:00 IST — Daily Performance Report:**
- OC-20 Reporting Manager generates Daily Operational Summary (SCH-012).
- Operations Lead reviews report.
- Any anomalies: document for weekly review.

**17:30 IST — Post-Learning Knowledge Refresh:**
- WF-KNOW triggers with learning outputs (SCH-011).
- Confirms tomorrow's session starts with current knowledge.

**18:00 IST — System Shutdown:**
- WF-STOP triggers (SCH-018).
- Monitor shutdown: all workflows drain within 60 seconds.
- Confirm OLS-12 SHUTDOWN COMPLETE.

---

#### G.4 Incident Response Procedures

**IR-MO-01 — Engine OFFLINE (CRITICAL Engine)**

*Trigger:* OC-15 Health Manager detects CRITICAL engine OFFLINE (2 consecutive probe failures).
*Severity:* P1 immediately.

Step 1: OC-17 Incident Manager raises P1 incident; Telegram notification sent.
Step 2: OC-18 executes ORP-01 (Engine Restart) automatically.
Step 3 (if ORP-01 fails): Operations Lead investigates.
  - Check container/process: is it running?
  - Check logs: what caused the failure?
  - Attempt manual restart.
Step 4: If engine cannot be recovered within 30 minutes:
  - System enters SAFE mode (ORP-08 Emergency Stop).
  - All trading workflows suspended.
  - Operations Lead notifies System Owner.
Step 5: Post-incident: root cause analysis; recovery procedure review.

---

**IR-MO-02 — OHS FAILED (< 0.35)**

*Trigger:* OC-15 computes OHS < 0.35.
*Severity:* P1.

Step 1: OC-17 raises P1; system auto-enters SAFE mode.
Step 2: Operations Lead identifies which components are contributing most to OHS failure.
Step 3: For each failing component: apply appropriate ORP procedure.
Step 4: OHS must recover to DEGRADED (>= 0.60) before any trading workflows resume.
Step 5: OHS must recover to NOMINAL (>= 0.80) before full operations resume.
Step 6: System Owner must authorize exit from SAFE mode.

---

**IR-MO-03 — Kill Switch Triggered (VIX > 45 or Daily Loss > 2%)**

*Trigger:* OC-07 Governance Pipeline detects kill switch condition.
*Severity:* P1.

Step 1: WF-DEC, WF-RISK blocked immediately by OC-12.
Step 2: No new position workflow may start.
Step 3: OC-17 raises P1 incident; Telegram alert sent.
Step 4: In-flight workflow steps complete safely (no new positions opened).
Step 5: Operations Lead reviews the kill switch condition.
Step 6: System Owner must explicitly clear the kill switch condition.
Step 7: Governance Engine must re-certify the session before trading resumes.
Step 8: Post-incident: detailed review; governance record created.

---

**IR-MO-04 — Workflow Timeout (CRITICAL Pipeline)**

*Trigger:* OC-02 detects WF-DEC, WF-RISK, or WF-OBS timeout.
*Severity:* P2 (immediately; P1 if trading activity was blocked > 15 minutes).

Step 1: OC-02 marks workflow TIMED_OUT; step that timed out identified.
Step 2: OC-17 raises P2 (or P1).
Step 3: OC-18 executes ORP-02 (Workflow Restart) if step is retryable.
Step 4: If WF-OBS repeatedly times out: investigate data feed health.
Step 5: If WF-DEC times out: check Decision Engine health.
Step 6: If WF-RISK times out: CRITICAL — investigate Risk Engine immediately.
Step 7: Post-incident: analyze timeout cause; adjust SLA if systematic.

---

**IR-MO-05 — Communication Channel Failure**

*Trigger:* OC-10 detects message delivery failure or channel BROKEN.
*Severity:* P2 (single non-CRITICAL channel); P1 (CRITICAL engine channel).

Step 1: OC-17 raises incident.
Step 2: OC-18 executes ORP-03 (Communication Reconnect).
Step 3: OC-08 marks affected engine UNREACHABLE.
Step 4: If reconnect fails within 3 attempts: investigate network/infrastructure.
Step 5: Post-incident: analyze channel failure cause; add monitoring if needed.

---

**IR-MO-06 — Governance Engine Unavailable**

*Trigger:* OC-15 detects Governance Engine OFFLINE.
*Severity:* P1 immediately.

Step 1: OC-17 raises P1; Telegram alert.
Step 2: All new trading workflow creation suspended (OCC-O-002).
Step 3: In-flight workflows complete.
Step 4: Operations Lead attempts to restore Governance Engine.
Step 5: If restored: request new Governance Readiness Certificate.
Step 6: If not restored within 30 minutes: System Owner decides whether
        to abort the trading session entirely.
Step 7: NEVER resume trading workflows without a valid Governance Certificate.

---

#### G.5 Weekly Operations Procedures

**Every Saturday — Strategy Review:**
- WF-STRAT executes (SCH-013).
- Review strategy performance report from OC-20.
- Identify strategies flagged for promotion or demotion.
- Review simulation runs from WF-SIM.
- Submit promotion candidates to Governance Engine if any.

**Every Friday — Weekly Operations Report:**
- OC-20 generates Weekly Operations Review (SCH-015).
- Review: OHS trends, workflow success rates, incident count and resolution times,
  resource utilization trends, governance check results.
- Any negative trends: document and assign owner.

**Monthly — Capacity Review:**
- OC-19 Analytics generates Capacity Utilization Report.
- Review CPU, memory, data feed, and queue utilization trends.
- Identify any resources approaching 80% sustained utilization.
- Initiate capacity planning if needed.

**Monthly — Recovery Procedure Testing:**
- Execute ORP-01 through ORP-08 in non-production (SCH-017).
- Document test results per procedure.
- Update any procedures that produced unexpected results.
- Confirm all procedures tested; update test log in OC-18.

---

### SUPPLEMENT H — COMPREHENSIVE GLOSSARY

---

#### H.1 Core Orchestration Terms

**Agent Coordinator (OC-07):** The Master Orchestrator component responsible for
managing the coordination of individual AI agents within IIOS. Ensures agent
sequencing, resource allocation, behavioral boundary enforcement, and multi-agent
process visibility.

**AND Barrier:** A synchronization barrier type in which ALL participating parallel
steps must complete before the downstream step is released. The strictest barrier
type; fails if any participant fails (in strict mode).

**Audit Record:** A permanent, immutable record of a governance-significant event
in the Orchestrator. Stored in OC-14 State Manager and contributed to the
Governance Engine's audit ledger.

**Authorization Level:** The approval authority required to perform an action.
The Orchestrator uses four levels: System Owner (highest), Architecture Council,
Operations Lead, and Automated (system itself for routine actions).

**Availability (OQD-02):** The fraction of scheduled market hours during which
the Master Orchestrator operates at NOMINAL or better health. Measured as uptime
ratio over a rolling 30-day window.

**Barrier Timeout:** The maximum time OC-13 Synchronization Manager waits for
all participants in a synchronization barrier to complete. When the timeout
expires, the configured barrier policy is applied.

**Communication Manager (OC-10):** The Master Orchestrator component that governs
all communication between the Orchestrator and engines, and between engines.
Enforces communication protocols, authentication, integrity checks, and delivery
guarantees.

**Component Weight:** The weight assigned to each Orchestrator component in the
OHS (Orchestrator Health Score) computation. All component weights sum to 1.00.

**Configuration Manager (OC-22):** The source of all runtime configuration for
the Master Orchestrator. Loads, validates, and serves configuration to all
components. Maintains configuration version history.

**Constitutional Rule:** An inviolable rule in the Master Orchestrator Constitution.
Rules are classified as NON-NEGOTIABLE HARD (no exception possible), HARD (no
runtime exception; change requires Architecture Council approval), or SOFT (best
practice; deviation requires Operations Lead approval).

**Coordination Service (OS-04):** The Orchestrator service that bridges the
Orchestrator to individual engines. Handles engine invocations and output routing.

**Critical Path:** The longest sequence of dependent steps in a workflow, determining
the minimum possible workflow duration. Computed by OC-03 Dependency Manager.

**Dead Letter Queue:** A holding area for messages that OC-11 Message Router
could not deliver within their TTL. Dead letter queue contents are monitored by
OC-16 and trigger alerts proportional to message priority.

**Delegation:** The act of assigning a workflow step, resource allocation decision,
or scheduling slot to a specific engine or component. The Orchestrator delegates
execution responsibility while retaining coordination authority.

**Dependency Manager (OC-03):** The Master Orchestrator component that maintains
the complete dependency graph of all IIOS engines, workflows, and workflow steps.
Validates dependencies before workflow execution; detects circular dependencies.

**Dependency Validation:** The process of verifying that all upstream dependencies
of a workflow step are satisfied before that step executes. Performed by OC-03
before every step execution.

**Determinism (OQD-04):** The property that identical orchestration inputs produce
identical orchestration outputs. Required for auditability and replay-based testing.

**Engine Code:** A short identifier for an engine type (e.g., KE for Knowledge
Engine, IE for Information Engine). Used in identifiers like Engine Registration
IDs and version entries.

**Engine Discovery Manager (OC-09):** The Master Orchestrator component that
probes for available engines, validates their capability manifests, and submits
them to OC-08 Engine Registry for registration.

**Engine Registration Certificate (ERC):** A certificate issued by OC-08 Engine
Registry upon successful engine registration. Format: ERC-{ENGINE_CODE}-{YYYYMMDD}-{SEQ:04d}.

**Engine Registry (OC-08):** The authoritative catalog of all registered engines,
components, and AI agents in IIOS. The first component initialized at startup
and the last shut down. Issues Engine Registration Certificates.

**Event-Driven Execution:** A scheduling paradigm in which workflow execution is
triggered by events rather than fixed time slots.

**Execution Coordinator (OC-04):** The Master Orchestrator component that bridges
the Orchestrator to specialized engines. Translates workflow step execution requests
into engine invocations, validates outputs, and returns results.

**Extensibility (OQD-12):** The ease with which new engines, workflows, and
services can be added to the Orchestrator without modifying existing components.
Target: new engine onboarding time < 1 hour; zero modification of existing components.

**Fault Tolerance (OQD-05):** The ability of the Orchestrator to maintain reduced
but functional operation when individual components or engines fail.

**Graceful Degradation:** A controlled reduction in system capability in response
to resource exhaustion or component failure. Triggered at 90%, 95%, and 99% resource
utilization, progressively suspending lower-priority workflows.

---

#### H.2 Component Terms

**Health Manager (OC-15):** The Master Orchestrator component that continuously
monitors the health of all registered engines and Orchestrator components. Computes
the OHS. Triggers health state transitions and escalations.

**Incident ID:** A unique identifier for an operational incident. Format:
OINC-{SEVERITY}-{YYYYMMDD}-{SEQ:04d} (e.g., OINC-P1-20260704-0001).

**Incident Manager (OC-17):** The Master Orchestrator component that receives,
classifies, escalates, and coordinates the resolution of all operational incidents.
Classifies incidents as P1 through P4.

**Message Router (OC-11):** The routing intelligence within the Communication
Manager. Determines which component receives each message; applies routing rules;
manages message priorities; operates dead letter queue.

**Monitoring Manager (OC-16):** The Master Orchestrator component that collects
metrics from all components, evaluates against thresholds, and powers the
operational monitoring dashboard.

**OHS (Orchestrator Health Score):** A composite score (0.00–1.00) representing
the overall health of the Master Orchestrator. Computed as a weighted sum of
component health scores. Tiers: OPTIMAL (0.95+), NOMINAL (0.80+), DEGRADED
(0.60+), CRITICAL (0.35+), FAILED (<0.35).

**OPS (Orchestrator Performance Score):** A session-level performance metric
computed by OC-19 Analytics Manager summarizing workflow completion rates,
latency SLA compliance, and resource efficiency.

**OQS (Orchestrator Quality Score):** A composite quality score (0.00–1.00)
computed from 13 OQD dimensions. Reflects the overall quality of orchestration
operations.

**Priority Manager (OC-05):** The Master Orchestrator component that maintains
the dynamic priority ranking of all active workflows and pending steps. Manages
priority elevation for incidents and enforces the aging policy.

**Recovery Manager (OC-18):** The Master Orchestrator component that maintains
the library of automated recovery procedures and executes them on incident trigger.

**Recovery Procedure:** A defined, tested sequence of steps for recovering a
specific failure mode. Maintained by OC-18. Format: ORP-{NN}.

**Reporting Manager (OC-20):** The Master Orchestrator component that generates
and distributes all operational reports.

**Resource Manager (OC-06):** The Master Orchestrator component that governs
allocation of all computational and operational resources across all engines
and workflows.

**State Manager (OC-14):** The single source of truth for all Orchestrator state.
All components read and write through OC-14. Supports atomic updates, checkpoint
creation, and state history.

**Synchronization Manager (OC-13):** The Master Orchestrator component that
manages synchronization barriers in the workflow execution graph.

**Version Manager (OC-21):** The Master Orchestrator component that maintains
the authoritative list of authorized engine versions.

---

#### H.3 Process Terms

**GDR (Governance Decision Record):** An architectural record of a non-negotiable
decision about the Master Orchestrator's design or operation. GDRs for the Master
Orchestrator are numbered GDR-MO-001 through GDR-MO-010.

**GIP (Governance Integration Pattern):** A named, repeatable integration workflow
between the Master Orchestrator and the Governance Engine. Five patterns are defined
(GIP-01 through GIP-05) in IIOS-GOV-ENG-ARCH-001.

**OR Barrier:** A synchronization barrier type in which at least N of M participating
steps must complete (configured as a minimum count). Less strict than AND barrier.

**Orchestration Lifecycle Stage (OLS):** A defined stage in the Master Orchestrator's
system-level lifecycle. 12 stages defined: OLS-01 through OLS-12.

**Orchestrator Health Score:** See OHS.

**Orchestrator Performance Score:** See OPS.

**Orchestrator Quality Score:** See OQS.

**Pre-Decision Gate:** The set of mandatory preconditions that must all be satisfied
before the Decision Engine is invoked. Enforced by OC-12 Conflict Resolver and
OC-02 Workflow Manager in WF-DEC.

**QUORUM Barrier:** A synchronization barrier type in which a majority (> 50%)
of participating steps must complete. Intermediate between OR and AND in strictness.

**Readiness Certificate:** A certificate issued by the Master Orchestrator upon
successful completion of all 54 HARD readiness gates. Format:
OCERT-{YYYYMMDD}-{SESSION}-{SEQ:04d}.

**Recovery Procedure Library:** The collection of all named recovery procedures
(ORP-01 through ORP-08) maintained by OC-18 Recovery Manager.

**SAFE mode:** An operating mode in which all new trading workflow creation is
suspended. OHS monitoring, governance monitoring, and health monitoring remain
active. Entered automatically when OHS drops below 0.35 (FAILED tier). Exit
requires explicit System Owner authorization.

**Step Execution Request:** A request from OC-02 Workflow Manager to OC-04
Execution Coordinator to execute a specific workflow step against a specific engine.

**TIMEOUT Barrier:** A synchronization barrier type in which the downstream step
proceeds after a configured timeout regardless of how many participants have
completed. The downstream step receives whatever outputs are available.

**Workflow Catalog:** The authoritative list of all named workflows in the Master
Orchestrator (Supplement B). 14 workflows defined: WF-STARTUP through WF-RECOV.

**Workflow Instance:** A specific execution of a named workflow, identified by
a unique Workflow Instance ID. Format: WF-{PIPELINE_CODE}-{YYYYMMDD}-{SEQ:08d}.

**Workflow Instance ID:** A unique identifier for a specific workflow execution.
Format: WF-{PIPELINE_CODE}-{YYYYMMDD}-{SEQ:08d}.

**Workflow Lifecycle Stage (WLS):** A defined stage in the workflow-level lifecycle.
10 stages defined: WLS-01 (PENDING) through WLS-10 (ARCHIVED).

**Workflow Step:** An individual unit of execution within a workflow, corresponding
to one engine invocation or one coordination action.

**WF-DEC:** Decision Cycle Workflow. The highest-consequence workflow in IIOS.
Invokes the Decision Engine; routes approved decisions to WF-RISK.

**WF-GOV:** Governance Pipeline Workflow. Coordinates all governance interactions.
Runs every 30 seconds during market hours.

**WF-OBS:** Observation Cycle Workflow. The highest-frequency workflow in IIOS.
Runs every 30 seconds during market hours.

**WF-RECOV:** Failure Recovery Workflow. Triggered on P1/P2 incidents. Executes
automated recovery and escalates to human if recovery fails.

**WF-RISK:** Risk Approval Workflow. The final safety gate before execution. Runs
after every approved decision; enforces constitutional risk limits.

**WF-STARTUP:** System Startup Workflow. Initializes the complete IIOS system.
Runs at system boot.

**WF-STOP:** System Shutdown Workflow. Performs orderly shutdown. Runs at 18:00 IST
or on emergency stop trigger.

---

## EXTENDED REFERENCE — NAMING CONVENTIONS

### Identifier Reference Table

All identifiers in the Master Orchestrator follow strict naming conventions.

| Identifier Type              | Format                                          | Example                                  |
|------------------------------|-------------------------------------------------|------------------------------------------|
| Workflow Instance ID         | WF-{PIPELINE_CODE}-{YYYYMMDD}-{SEQ:08d}         | WF-DEC-20260704-00000001                 |
| Engine Registration ID       | OER-{ENGINE_CODE}-{YYYYMMDD}-{SEQ:04d}          | OER-KE-20260704-0001                     |
| Engine Registration Cert.    | ERC-{ENGINE_CODE}-{YYYYMMDD}-{SEQ:04d}          | ERC-KE-20260704-0001                     |
| Orchestrator Readiness Cert. | OCERT-{YYYYMMDD}-{SESSION}-{SEQ:04d}            | OCERT-20260704-AM-0001                   |
| Orchestrator Incident ID     | OINC-{SEVERITY}-{YYYYMMDD}-{SEQ:04d}            | OINC-P1-20260704-0001                    |
| Recovery Procedure ID        | ORP-{NN}                                        | ORP-03                                   |
| Schedule Entry ID            | SCH-{NNN}                                       | SCH-005                                  |
| Component ID                 | OC-{NN}                                         | OC-07                                    |
| Service ID                   | OS-{NN}                                         | OS-03                                    |
| Pipeline ID                  | OP-{NN}                                         | OP-06                                    |
| Taxonomy Domain ID           | OT-{NN}                                         | OT-12                                    |
| Lifecycle Stage (System)     | OLS-{NN}                                        | OLS-06                                   |
| Lifecycle Stage (Workflow)   | WLS-{NN}                                        | WLS-03                                   |
| Quality Dimension ID         | OQD-{NN}                                        | OQD-08                                   |
| GDR                          | GDR-MO-{NNN}                                    | GDR-MO-007                               |
| Anti-Pattern ID              | OMAP-{NN}                                       | OMAP-04                                  |
| Constitution Category        | OCC-{LETTER}                                    | OCC-G                                    |
| Constitutional Rule          | OCC-{LETTER}-{NNN}                              | OCC-G-003                                |
| Decision Record              | ODEC-{YYYYMMDD}-{SEQ:08d}                       | ODEC-20260704-00000001                   |
| Pipeline Code (for WF IDs)   | STARTUP, DAILY, OBS, KNOW, PRED, DEC,           | WF-DEC-...                               |
|                              | RISK, PORT, LEARN, STRAT, SIM, GOV,             |                                          |
|                              | STOP, RECOV                                     |                                          |

---

## EXTENDED REFERENCE — INTEGRATION WITH PRIOR IIOS ENGINE ARCHITECTURES

The Master Orchestrator coordinates every engine in the IIOS Engine Architecture
Series. The following defines the integration profile for each engine.

---

### Integration with Knowledge Engine (IIOS-KE-ARCH-001)

**Consumed services:** Knowledge refresh invocation; knowledge freshness query.
**Artifacts received:** KnowledgeSnapshot, DomainKnowledge records.
**Orchestration concern:** Knowledge must be fresh before Prediction and Decision
pipelines execute. The Orchestrator enforces knowledge freshness SLA.
**Orchestration workflows:** WF-KNOW (primary), WF-STARTUP (pre-session warm-up).
**Failure impact:** If Knowledge Engine is unavailable: Prediction quality degrades.
Operations may continue with cached knowledge if within 24-hour freshness window.

---

### Integration with Information Engine

**Consumed services:** Market information collection; information classification.
**Artifacts received:** InformationRecord, MarketContext.
**Orchestration concern:** Information collection must precede observation processing.
**Orchestration workflows:** WF-OBS Step 1 (data collection).
**Failure impact:** If unavailable: Observation Engine cannot receive fresh inputs.
WF-OBS times out. P2 incident.

---

### Integration with Observation Engine (IIOS-OBS-ARCH-001)

**Consumed services:** Observation generation; observation classification.
**Artifacts received:** ObservationRecord (price, volume, breadth, sentiment).
**Orchestration concern:** Highest-frequency interaction in IIOS (every 30s).
Latency SLA: 25s total pipeline. Observation freshness is the root dependency
for WF-PRED and WF-DEC.
**Orchestration workflows:** WF-OBS (primary, continuous).
**Failure impact:** If unavailable: no fresh observations. WF-PRED deferred.
WF-DEC blocked after observation TTL expires. P1 if trading-hours failure.

---

### Integration with Entity Engine (IIOS-ENT-ARCH-001)

**Consumed services:** Entity profile updates; entity state queries.
**Artifacts received:** EntityProfile, EntityObservation.
**Orchestration workflows:** WF-OBS Step 3, WF-KNOW Step 2.
**Failure impact:** Entity profiles become stale. Relationship Engine outputs
degrade. Routed to Knowledge Engine for stale-profile handling.

---

### Integration with Relationship Engine (IIOS-REL-ARCH-001)

**Consumed services:** Relationship graph updates; correlation analysis.
**Artifacts received:** RelationshipGraph, CorrelationMatrix.
**Orchestration workflows:** WF-KNOW Step 3.
**Failure impact:** Portfolio correlation monitoring degrades. Risk Engine uses
cached correlation matrix.

---

### Integration with Event Engine (IIOS-EVT-ARCH-001)

**Consumed services:** Event detection; event classification; event routing.
**Artifacts received:** EventRecord, MarketEvent.
**Orchestration concern:** Events may trigger immediate workflow execution outside
the regular 30-second interval (e.g., circuit breaker event triggers immediate WF-OBS).
**Orchestration workflows:** WF-OBS Step 4, WF-KNOW Step 4.
**Failure impact:** Market events not detected. System misses real-time triggers.
P2 incident.

---

### Integration with Prediction Engine (IIOS-PRD-ARCH-001)

**Consumed services:** Forecast generation; confidence assessment.
**Artifacts received:** PredictionArtifact (forecasts, confidence intervals,
regime probabilities).
**Orchestration concern:** Prediction freshness is required for Decision. The
Orchestrator enforces prediction TTL and blocks WF-DEC if predictions are stale.
**Orchestration workflows:** WF-PRED (primary).
**Failure impact:** No fresh predictions. WF-DEC blocked.
If sustained > 1 hour: P2 incident; decision capability suspended.

---

### Integration with Decision Engine (IIOS-DEC-ARCH-001)

**Consumed services:** 5-agent debate; decision scoring; decision record issuance.
**Artifacts received:** DecisionRecord (scored 0-10; APPROVED if >= 6.5).
**Orchestration concern:** The highest-consequence engine interaction. The
pre-decision gate (5 mandatory conditions) is enforced by the Orchestrator
before every Decision Engine invocation.
**Orchestration workflows:** WF-DEC (primary).
**Failure impact:** CRITICAL. No new trade decisions possible. P1 incident.

---

### Integration with Risk Engine (IIOS-RSK-ARCH-001)

**Consumed services:** Position sizing; risk gate evaluation; continuous monitoring.
**Artifacts received:** RiskApproval, PositionSize, RiskContext.
**Orchestration concern:** The final pre-execution safety gate. The Orchestrator
enforces the Risk Engine as a mandatory step before execution. Continuous risk
monitoring is an independent 30-second cycle, not tied to the decision cycle.
**Orchestration workflows:** WF-RISK (primary), continuous risk monitoring.
**Failure impact:** CRITICAL. If Risk Engine unavailable: no new positions may
open. All pending decisions blocked. P1 incident.

---

### Integration with Portfolio Engine (IIOS-PRT-ARCH-001)

**Consumed services:** Portfolio state management; position tracking; rebalancing.
**Artifacts received:** PortfolioState, PositionRecord, PerformanceAttribution.
**Orchestration concern:** Portfolio state must be current for risk and decision
context. The Orchestrator updates portfolio state after every execution event.
**Orchestration workflows:** WF-PORT.
**Failure impact:** Portfolio state stale. Risk Engine may allow positions that
breach concentration limits. P2 incident.

---

### Integration with Learning Engine (IIOS-LRN-ARCH-001)

**Consumed services:** Trade outcome analysis; model calibration updates.
**Artifacts received:** LearningOutput, StrategyPerformanceUpdate.
**Orchestration concern:** Learning runs post-session, non-blocking. The
Orchestrator ensures learning completes before system shutdown and that
learning outputs are delivered to Knowledge Engine for next-session refresh.
**Orchestration workflows:** WF-LEARN.
**Failure impact:** LOW immediate impact. Learning outputs unavailable for
next session. System operates with previous learning state.

---

### Integration with Strategy Engine (IIOS-STR-ARCH-001)

**Consumed services:** Strategy lifecycle management; promotion/demotion decisions.
**Artifacts received:** StrategyPromotion, StrategyPerformanceReport.
**Orchestration concern:** Strategy promotions must route through the Governance
Strategy Gate (GIP-02) before live deployment. The Orchestrator enforces this gate.
**Orchestration workflows:** WF-STRAT.
**Failure impact:** LOW immediate impact. Weekly run; deferrable.

---

### Integration with Simulation Engine (IIOS-SIM-ENG-ARCH-001)

**Consumed services:** Backtesting; Monte Carlo simulation; stress testing.
**Artifacts received:** EvidenceDossier, SimulationReport, SimQS score.
**Orchestration concern:** Simulation is resource-intensive. The Orchestrator
schedules simulation runs in off-peak hours and enforces a 60% CPU ceiling
to preserve CRITICAL workflow capacity.
**Orchestration workflows:** WF-SIM.
**Failure impact:** LOW immediate impact. Simulation deferred. Strategy
promotions blocked if evidence dossier not available.

---

### Integration with Governance Engine (IIOS-GOV-ENG-ARCH-001)

**Consumed services:** Session certification; compliance checking; kill switch
monitoring; exception handling; strategy governance gate.
**Artifacts received:** GovernanceReadinessCertificate, ComplianceStatus,
KillSwitchState, StrategyAuthorizationDecision.
**Orchestration concern:** The most critical engine integration. Governance Engine
availability is a prerequisite for session operation. No Governance Certificate =
no trading session. Kill switch triggers = immediate trading halt.
**Orchestration workflows:** WF-GOV (continuous), WF-STARTUP (cert request),
WF-DAILY (session init), all pipelines (governance checks).
**Failure impact:** CRITICAL. Session cannot begin without certificate. P1 incident
if Governance Engine goes offline during session.

---

## EXTENDED REFERENCE — COMPONENT SLA SUMMARY

| Component     | Availability SLA | Response Latency | Recovery Time |
|---------------|-----------------|------------------|---------------|
| OC-01         | 99.99%           | < 1s trigger     | 30s (ORP-05)  |
| OC-02         | 99.99%           | < 500ms          | 30s (ORP-02)  |
| OC-03         | 99.99%           | < 200ms          | 15s (restart) |
| OC-04         | 99.99%           | < 100ms overhead | 15s (restart) |
| OC-05         | 99.99%           | < 50ms           | 15s (restart) |
| OC-06         | 99.90%           | < 100ms          | 30s (ORP-06)  |
| OC-07         | 99.90%           | < 200ms          | 30s (restart) |
| OC-08         | 99.99%           | < 50ms           | 60s (restore) |
| OC-09         | 99.90%           | < 5s scan        | 30s (restart) |
| OC-10         | 99.95%           | < 10ms (CRIT)    | 15s (ORP-03)  |
| OC-11         | 99.95%           | < 10ms           | 15s (restart) |
| OC-12         | 99.99%           | < 100ms          | 15s (ORP-07)  |
| OC-13         | 99.95%           | < 10ms           | 30s (restart) |
| OC-14         | 99.99%           | < 50ms           | 120s (ORP-04) |
| OC-15         | 99.99%           | < 1s probe       | 30s (restart) |
| OC-16         | 99.95%           | < 30s collect    | 30s (restart) |
| OC-17         | 99.99%           | < 10s classify   | 15s (restart) |
| OC-18         | 99.90%           | < 30s execute    | 60s (restart) |
| OC-19         | 99.80%           | < 5min compute   | 60s (restart) |
| OC-20         | 99.80%           | < 10min report   | 60s (restart) |
| OC-21         | 99.99%           | < 100ms          | 15s (restart) |
| OC-22         | 99.99%           | < 50ms           | 30s (restore) |

---

## EXTENDED REFERENCE — OHS COMPUTATION DETAIL

### Component Weight Table

The Orchestrator Health Score (OHS) is computed as a weighted average of
individual component health scores. Weights reflect operational importance
during market-hours operation.

| Component | Name                    | Weight | Rationale                                     |
|-----------|-------------------------|--------|-----------------------------------------------|
| OC-01     | Master Scheduler        | 0.07   | Temporal backbone of all operations           |
| OC-02     | Workflow Manager        | 0.10   | Owner of all workflow instances               |
| OC-03     | Dependency Manager      | 0.05   | Dependency validation safety net              |
| OC-04     | Execution Coordinator   | 0.12   | Every engine invocation flows through OC-04   |
| OC-05     | Priority Manager        | 0.04   | Resource arbitration; lower weight at runtime |
| OC-06     | Resource Manager        | 0.05   | Resource allocation; important but resilient  |
| OC-07     | Agent Coordinator       | 0.04   | Agent supervision; lower frequency impact     |
| OC-08     | Engine Registry         | 0.08   | Authoritative source for all registrations    |
| OC-09     | Engine Discovery        | 0.02   | Needed at startup; low runtime impact         |
| OC-10     | Communication Manager   | 0.08   | All inter-engine communication                |
| OC-11     | Message Router          | 0.06   | Routing decisions; part of communication      |
| OC-12     | Conflict Resolver       | 0.04   | Conflict detection; important but infrequent  |
| OC-13     | Synchronization Manager | 0.05   | Parallel step coordination                    |
| OC-14     | State Manager           | 0.10   | Single source of truth; high weight           |
| OC-15     | Health Manager          | 0.06   | Health computation driver                     |
| OC-16     | Monitoring Manager      | 0.05   | Operational visibility                        |
| OC-17     | Incident Manager        | 0.04   | Incident response; lower routine weight       |
| OC-18     | Recovery Manager        | 0.03   | Recovery; important on failure; low otherwise |
| OC-19     | Analytics Manager       | 0.02   | Analytics; non-critical runtime impact        |
| OC-20     | Reporting Manager       | 0.01   | Reporting; non-blocking                       |
| OC-21     | Version Manager         | 0.03   | Version governance; startup-critical          |
| OC-22     | Configuration Manager   | 0.06   | Config source; startup-critical               |
| **TOTAL** |                         | **1.00**|                                               |

### OHS Computation Example

**Scenario: Normal operations, one DEGRADED component (OC-09)**

OC-01 through OC-08, OC-10 through OC-22: all HEALTHY = 1.00 score each
OC-09 (Engine Discovery): DEGRADED = 0.50 score

OHS = Sum of (weight * score)
     = (0.07 * 1.00) + (0.10 * 1.00) + (0.05 * 1.00) + (0.12 * 1.00)
       + (0.04 * 1.00) + (0.05 * 1.00) + (0.04 * 1.00) + (0.08 * 1.00)
       + (0.02 * 0.50) + (0.08 * 1.00) + (0.06 * 1.00) + (0.04 * 1.00)
       + (0.05 * 1.00) + (0.10 * 1.00) + (0.06 * 1.00) + (0.05 * 1.00)
       + (0.04 * 1.00) + (0.03 * 1.00) + (0.02 * 1.00) + (0.01 * 1.00)
       + (0.03 * 1.00) + (0.06 * 1.00)
     = 1.00 - (0.02 * 0.50)
     = 1.00 - 0.01
     = 0.99 [OPTIMAL]

Impact: OC-09 DEGRADED reduces OHS by only 0.01 (1%). Engine discovery
is a startup-priority component with low runtime weight. OHS remains OPTIMAL.

**Scenario: OC-04 Execution Coordinator UNHEALTHY (0.20 score)**

OHS = 1.00 - (0.12 * (1.00 - 0.20))
    = 1.00 - (0.12 * 0.80)
    = 1.00 - 0.096
    = 0.904 [NOMINAL, approaching top of NOMINAL range]

Impact: Unhealthy Execution Coordinator is more visible in OHS (weight 0.12)
but NOMINAL tier is maintained. P2 incident; immediate investigation warranted.

**Scenario: OC-04 (0.20) + OC-14 (0.20) + OC-02 (0.20) all UNHEALTHY**

OHS = 1.00 - (0.12 * 0.80) - (0.10 * 0.80) - (0.10 * 0.80)
    = 1.00 - 0.096 - 0.080 - 0.080
    = 0.744 [DEGRADED]

Impact: Three core components UNHEALTHY → DEGRADED tier. Only CRITICAL workflows
continue. P1 incident. Human intervention required.

---

## EXTENDED REFERENCE — ORCHESTRATOR PRINCIPLES

The following 10 principles summarize the design philosophy of the Master Orchestrator.
They are the philosophical foundations from which the 140 constitutional rules
are derived.

**Principle 1 — Coordination Without Intelligence:**
The Master Orchestrator is supremely capable at coordination. It is deliberately
incapable of investment domain analysis. This asymmetry is a design feature, not
a limitation. An orchestrator that knows about markets will eventually act on that
knowledge, corrupting the purity of its coordination role.

**Principle 2 — Independence Enables Trust:**
The Orchestrator's trustworthiness derives from its independence from what it
coordinates. It has no preferences about which strategy wins, which engine is
"better," or what the market should do. This indifference is the foundation of
a fair, auditable orchestration system.

**Principle 3 — Every Action is Traceable:**
Every scheduling decision, every workflow step, every conflict resolution, every
health state change — all of these are recorded with full attribution. There are
no undocumented actions in the Master Orchestrator. Traceability is not overhead;
it is the mechanism of accountability.

**Principle 4 — Governance Is Not Optional:**
The Governance Engine has constitutional authority over the Orchestrator. The
Orchestrator does not evaluate whether governance requirements are convenient.
It implements them without exception. An Orchestrator that chooses when to
comply with governance is not governed.

**Principle 5 — Extensibility Without Modification:**
The Orchestrator grows through registration and configuration, not through code
changes. Every future engine, workflow, and service is accommodated by the same
mechanisms that accommodate the first engine. An architecture that requires
modification to accommodate growth is fragile.

**Principle 6 — Failure Is Expected:**
Component failures are not exceptional events in a distributed system. They are
expected. The Orchestrator is designed to detect failures quickly, respond to
them deterministically, and recover safely. An Orchestrator that is surprised
by failure has not been designed for production.

**Principle 7 — Resource Discipline Prevents Cascade Failures:**
Uncontrolled resource competition is a major cause of cascade failures in
orchestrated systems. The Master Orchestrator enforces resource budgets,
reserves CRITICAL resources, and degrades gracefully rather than allowing
resource competition to produce unpredictable failures.

**Principle 8 — Monitoring Is a Primary Function:**
Operational visibility is not a secondary concern in the Master Orchestrator.
It is a primary function. The Monitoring Manager (OC-16) and Health Manager
(OC-15) are core components with the same architectural standing as the
Workflow Manager and Execution Coordinator. A system that cannot observe
itself cannot be managed.

**Principle 9 — Recovery Must Be Safe:**
No recovery procedure may open, close, or modify investment positions. This
is non-negotiable (OCC-I-001). Recovery restores the orchestration layer;
it does not manage financial risk. The temptation to "help" by automatically
closing a position during a recovery scenario is the path to catastrophic loss.

**Principle 10 — Human Authority Is Preserved:**
The Orchestrator automates coordination for efficiency, not to eliminate human
authority. The System Owner retains override authority for HARD rules. Human
authorization is required to exit SAFE mode. Critical incidents trigger human
notification. Automation serves human judgment; it does not replace it.

---

## EXTENDED REFERENCE — QUICK-START REFERENCE CARD

### Key Identifiers

| Artifact                   | Format                                           |
|----------------------------|--------------------------------------------------|
| Workflow Instance           | WF-DEC-20260704-00000001                         |
| Engine Registration ID     | OER-KE-20260704-0001                             |
| Engine Registration Cert.  | ERC-KE-20260704-0001                             |
| Readiness Certificate       | OCERT-20260704-AM-0001                           |
| Incident Record            | OINC-P1-20260704-0001                            |
| Recovery Procedure         | ORP-01 (Engine Restart)                          |
| Decision Record            | ODEC-20260704-00000001                           |

### Key Thresholds

| Parameter                  | Value                                            |
|----------------------------|--------------------------------------------------|
| OHS NOMINAL minimum        | 0.80                                             |
| OHS DEGRADED threshold     | 0.60 (non-CRITICAL workflows suspended)          |
| OHS FAILED threshold       | 0.35 (SAFE mode, human intervention)             |
| Decision threshold         | 6.5 / 10.0                                       |
| Daily loss limit           | 2% (constitutional)                              |
| VIX kill switch            | > 45 (constitutional)                            |
| Strategy max weight        | 40% of deployed capital                          |
| Sector concentration limit | 30%                                              |
| Strategy drawdown limit    | 15% (auto-suspension)                            |
| Knowledge freshness TTL    | 24 hours                                         |
| Observation freshness TTL  | 30 seconds (intraday)                            |
| CRITICAL reserve           | 20% of all resource categories                   |
| Readiness HARD gates       | 54 (all must pass before session)                |

### Priority Levels

| Level    | Examples                                         |
|----------|--------------------------------------------------|
| CRITICAL | Risk monitoring, governance, kill switch, session|
| HIGH     | Decision, execution, observation, knowledge      |
| NORMAL   | Prediction (when not time-critical), portfolio   |
| LOW      | Learning, reporting                              |
| DEFERRED | Historical analysis, non-urgent simulation       |

### Authority Levels

| Authority               | Scope                                             |
|-------------------------|---------------------------------------------------|
| System Owner            | HARD rule override; SAFE mode exit; P1 escalation |
| Architecture Council    | Constitutional amendments; CRITICAL schedule change|
| Operations Lead         | SOFT rule override; schedule adjustments; P2 mgmt |
| Automated (Orchestrator)| Routine coordination, recovery, health management |

---

## EXTENDED REFERENCE — DOCUMENT METRICS AND SUMMARY

### Document Metrics

| Metric                             | Value                                      |
|------------------------------------|--------------------------------------------|
| Document Code                      | IIOS-MO-ARCH-001                           |
| Version                            | 1.0.0                                      |
| Architecture Parts                 | Parts I through X                          |
| Supplements                        | A through H                                |
| Orchestration Taxonomy Domains     | 16 (OT-01 through OT-16)                  |
| Core Components                    | 22 (OC-01 through OC-22)                  |
| Orchestration Services             | 15 (OS-01 through OS-15)                  |
| Workflow Pipelines                 | 14 (OP-01 through OP-14)                  |
| Named Workflows                    | 14 (WF-STARTUP through WF-RECOV)          |
| System Lifecycle Stages            | 12 (OLS-01 through OLS-12)                |
| Workflow Lifecycle Stages          | 10 (WLS-01 through WLS-10)                |
| Scheduled Events (standard day)    | 18 (SCH-001 through SCH-018)              |
| Quality Dimensions                 | 13 (OQD-01 through OQD-13)               |
| Recovery Procedures                | 8 (ORP-01 through ORP-08)                |
| Constitutional Rule Categories     | 18 (OCC-A through OCC-R)                 |
| Constitutional Rules               | 140 total                                  |
| NON-NEGOTIABLE HARD rules          | 12                                         |
| HARD rules                         | 99                                         |
| SOFT rules                         | 29                                         |
| Readiness Phases                   | 12 (P1 through P12)                       |
| Readiness HARD Gates               | 54                                         |
| Readiness SOFT Gates               | 19                                         |
| Governance Decision Records        | 10 (GDR-MO-001 through GDR-MO-010)       |
| Anti-Patterns                      | 10 (OMAP-01 through OMAP-10)             |
| Incident Response Procedures       | 6 (IR-MO-01 through IR-MO-06)            |
| Component OHS Weights              | Sum = 1.00                                 |
| Quality Dimension Weights (OQD)    | Sum = 1.00                                 |
| Integrated Engine Architectures    | 14 (IIOS-KE through IIOS-GOV)            |

---

### Parts and Supplements Summary

| Part          | Title                              | Key Deliverables                               |
|---------------|------------------------------------|------------------------------------------------|
| Part I        | Master Orchestrator Philosophy     | 19 concepts defined; independence rationale    |
| Part II       | Orchestrator Taxonomy              | 16 domains; all responsibilities defined       |
| Part III      | Core Components                    | 22 components; 12-field profiles each          |
| Part IV       | Orchestration Lifecycle            | 12 system stages; 10 workflow stages; diagrams |
| Part V        | Orchestration Services             | 15 services; all operations and SLAs           |
| Part VI       | Workflow Pipelines                 | 14 pipelines; full architecture diagrams       |
| Part VII      | Quality Framework                  | 13 OQD dimensions; OQS formula and tiers       |
| Part VIII     | Orchestration Governance           | 11 governance policies                         |
| Part IX       | Constitution                       | 140 rules; 18 categories; summary table        |
| Part X        | Readiness Checklist                | 12 phases; 54 HARD gates; state machine        |
| Supplement A  | Engine Interaction Matrix          | 4 interaction views; critical path; availability|
| Supplement B  | Workflow Catalog                   | 14 workflows; full definitions                 |
| Supplement C  | Scheduling Reference               | 18 scheduled events; conflict/miss policies    |
| Supplement D  | Dependency Matrix                  | Step, inter-workflow, resource dependency      |
| Supplement E  | Governance Decision Records        | 10 GDRs; non-negotiable architectural decisions|
| Supplement F  | Anti-Patterns                      | 10 anti-patterns; symptoms; correct patterns   |
| Supplement G  | Operational Runbook                | Daily startup; intraday; end-of-session; 6 IRs |
| Supplement H  | Comprehensive Glossary             | 80+ terms; 3 categories                        |
| Ext. Ref.     | Naming Conventions                 | 20 identifier types with formats               |
| Ext. Ref.     | Engine Integration Profiles        | 14 engines; profile per engine                 |
| Ext. Ref.     | Component SLA Summary              | 22 components; availability, latency, recovery |
| Ext. Ref.     | OHS Computation Detail             | Weight table; 3 worked examples                |
| Ext. Ref.     | Orchestrator Principles            | 10 principles                                  |
| Ext. Ref.     | Quick-Reference Card               | Identifiers, thresholds, priorities, authority |

---

## EXTENDED REFERENCE — NON-NEGOTIABLE HARD RULES SUMMARY

The following 12 rules have NO exception process. No authority, no circumstance,
and no operational need can override them. They represent the inviolable foundation
of the Master Orchestrator's trustworthiness.

1. **OCC-A-001:** No engine participates in any workflow without being registered
   in OC-08 Engine Registry.

2. **OCC-B-001:** The Master Orchestrator must not contain investment domain logic.

3. **OCC-B-002:** The Master Orchestrator must not interpret the investment meaning
   of any engine's output.

4. **OCC-C-001:** Every scheduled workflow must have a defined and registered
   schedule entry. Ad hoc production workflow execution is prohibited.

5. **OCC-E-001:** All inter-engine communication must flow through OC-10
   Communication Manager. No direct engine-to-engine communication.

6. **OCC-G-001:** Every workflow instance must have a unique Workflow Instance ID.

7. **OCC-H-001:** Governance conflicts always resolve in favor of the Governance
   Engine. No conflict resolution policy may override a governance rule.

8. **OCC-I-001:** Recovery procedures must never open, close, or modify any
   investment position.

9. **OCC-J-001:** The Monitoring Manager (OC-16) must be operational at all times
   when the Orchestrator is running.

10. **OCC-N-001:** All engine credentials must be stored in the secrets management
    system, never in configuration files or source code.

11. **OCC-O-001:** The Orchestrator must not begin any trading session workflow
    without a valid Governance Readiness Certificate.

12. **OCC-P-001:** Human override of a constitutional rule is not possible.

---

## EXTENDED REFERENCE — ORCHESTRATOR INTEGRATION EVENTS

Events that the Master Orchestrator generates and routes to interested consumers:

| Event                                    | Source Component  | Consumers              | Priority |
|------------------------------------------|-------------------|------------------------|----------|
| WORKFLOW_CREATED                         | OC-02             | OC-14, OC-16           | NORMAL   |
| WORKFLOW_COMPLETED                       | OC-02             | OC-14, OC-20           | NORMAL   |
| WORKFLOW_FAILED                          | OC-02             | OC-14, OC-17           | HIGH     |
| WORKFLOW_TIMED_OUT                       | OC-02             | OC-14, OC-17           | HIGH     |
| ENGINE_REGISTERED                        | OC-08             | OC-03, OC-09, OC-16    | HIGH     |
| ENGINE_DEREGISTERED                      | OC-08             | OC-03, OC-02, OC-16    | HIGH     |
| ENGINE_HEALTH_CHANGED                    | OC-15             | OC-04, OC-08, OC-16    | HIGH     |
| OHS_TIER_CHANGED                         | OC-15             | OC-16, OC-17, OC-05    | CRITICAL |
| OHS_FAILED                               | OC-15             | OC-17, OC-18           | CRITICAL |
| SCHEDULE_TRIGGERED                       | OC-01             | OC-02, OC-14           | varies   |
| SCHEDULE_MISSED                          | OC-01             | OC-17, OC-14           | HIGH     |
| RESOURCE_LIMIT_APPROACHED                | OC-06             | OC-05, OC-16           | HIGH     |
| RESOURCE_PREEMPTION_APPLIED              | OC-06             | OC-04, OC-14           | HIGH     |
| CONFLICT_DETECTED                        | OC-12             | OC-14, OC-16           | HIGH     |
| CONFLICT_RESOLVED                        | OC-12             | OC-14, OC-16           | NORMAL   |
| BARRIER_RELEASED                         | OC-13             | OC-02                  | NORMAL   |
| BARRIER_TIMED_OUT                        | OC-13             | OC-02, OC-17           | HIGH     |
| INCIDENT_RAISED                          | OC-17             | OC-18, OC-11, OC-14    | CRITICAL |
| INCIDENT_RESOLVED                        | OC-17             | OC-14, OC-20           | NORMAL   |
| RECOVERY_STARTED                         | OC-18             | OC-14, OC-16           | HIGH     |
| RECOVERY_COMPLETED                       | OC-18             | OC-15, OC-14, OC-17    | HIGH     |
| GOVERNANCE_CERT_RECEIVED                 | OC-02 (WF-GOV)    | OC-14, All pipelines   | CRITICAL |
| GOVERNANCE_CERT_EXPIRED                  | OC-02 (WF-GOV)    | OC-17, OC-01           | CRITICAL |
| KILL_SWITCH_ACTIVE                       | OC-12             | OC-01, OC-04, OC-17    | CRITICAL |
| SAFE_MODE_ENTERED                        | OC-15             | All components         | CRITICAL |
| SAFE_MODE_EXITED                         | OC-15             | All components         | CRITICAL |

---

## DOCUMENT SUMMARY

This document, MASTER_ORCHESTRATOR_ARCHITECTURE.md (IIOS-MO-ARCH-001), provides
the complete engineering architecture for the Master Orchestrator of the Investment
Intelligence Operating System (IIOS).

The Master Orchestrator is the supreme coordination engine of IIOS. It does not
replace any specialized engine. It coordinates all of them. Through 22 components
organized into 4 tiers, 15 services, and 14 workflow pipelines, the Master
Orchestrator enables a collection of specialized intelligence engines to function
as a single coherent investment intelligence operating system.

The architecture is defined by three institutional properties:

**Coordination Without Contamination:** The Orchestrator coordinates with complete
independence from investment domain logic. It is incapable of making investment
decisions because it was never designed with investment intelligence. This design
choice — trading capability for purity — makes the Orchestrator permanently
trustworthy as a neutral coordination layer.

**Auditability Through Immutability:** Every scheduling decision, every engine
invocation, every conflict resolution, every health state change is recorded in
OC-14 State Manager with full attribution. The Orchestrator's operational history
is complete, permanent, and trustworthy. Auditors can reconstruct any session
from the log alone.

**Governance Without Exception:** The Orchestrator operates under the constitutional
authority of the Governance Engine (IIOS-GOV-ENG-ARCH-001). The 12 Non-Negotiable
HARD rules in this Constitution are genuinely non-negotiable. The 12 governance
integration patterns are implemented without bypass. The 54 readiness HARD gates
are enforced without shortcuts. This is what it means for governance to be real
rather than theoretical.

These three properties — coordination without contamination, auditability through
immutability, and governance without exception — make the Master Orchestrator
a trustworthy foundation for an institutional-grade investment intelligence system.

---

## REVISION HISTORY

| Version | Date       | Author              | Changes                                        |
|---------|------------|---------------------|------------------------------------------------|
| 1.0.0   | 2026-07-04 | Architecture Council| Initial release — complete document            |

---

*End of MASTER_ORCHESTRATOR_ARCHITECTURE.md (IIOS-MO-ARCH-001)*
*Document Code: IIOS-MO-ARCH-001 | Version 1.0.0 | Status: RELEASED*
*The Master Orchestrator coordinates every engine. It replaces none.*

---

## EXTENDED REFERENCE — ORCHESTRATION PERFORMANCE MODELS

### Scheduling Model

The Master Scheduler (OC-01) uses a **priority-based round-robin** scheduling
model for time-triggered workflows. The model operates as follows:

**Phase 1 — Event Queue Construction (T-30 seconds before trigger time):**
OC-01 scans the schedule table for all events due within the next 30 seconds.
These events are placed in the trigger queue, ordered by: (1) priority level
(CRITICAL first), (2) scheduled trigger time (earliest first), (3) registration
order (oldest first, as tiebreaker).

**Phase 2 — Conflict Detection:**
For each pair of events in the trigger queue, OC-12 checks for resource conflicts
and scheduling conflicts. Conflicts are resolved according to Section 3.12 policies
and Supplement C.4.

**Phase 3 — Workflow Creation:**
At the scheduled time, OC-01 calls OC-02 Workflow Manager for each event in order.
OC-02 creates the workflow instance, verifies dependencies (OC-03), allocates
resources (OC-06), and sets state to RUNNING.

**Phase 4 — Execution:**
OC-04 Execution Coordinator receives step execution requests from OC-02 and
invokes the target engines. Parallel steps are submitted simultaneously to OC-04;
OC-13 Synchronization Manager manages barriers.

---

### Execution Latency Budget

The IIOS intraday decision cycle must complete within 170 seconds (at reference
performance) to maintain fresh signal quality during continuous market operation.

The following budget allocates the 170-second intraday cycle budget:

| Activity                          | Budget (seconds) | Component           |
|-----------------------------------|------------------|---------------------|
| Orchestrator scheduling overhead  | 1s               | OC-01, OC-02        |
| Data feed collection              | 5s               | External             |
| Observation Engine                | 15s              | Observation Engine  |
| Entity Engine update              | 5s               | Entity Engine       |
| Event Engine evaluation           | 5s               | Event Engine        |
| Orchestrator synchronization      | 1s               | OC-13               |
| Prediction Engine                 | 55s              | Prediction Engine   |
| Orchestrator routing overhead     | 1s               | OC-11               |
| Decision Engine (5-agent debate)  | 25s              | Decision Engine     |
| Pre-decision gate evaluation      | 2s               | OC-12, OC-02        |
| Risk Engine evaluation            | 12s              | Risk Engine         |
| Risk gate checks                  | 3s               | OC-12               |
| Portfolio update trigger          | 5s               | Portfolio Engine    |
| Audit record commits              | 5s               | OC-14               |
| Buffer                            | 30s              | All                 |
| **TOTAL BUDGET**                  | **170 seconds**  |                     |

**Note:** The Knowledge Engine is excluded from the intraday budget because
knowledge is refreshed pre-session and cached. The 5-minute knowledge cache
(with background refresh) eliminates the Knowledge Engine from the intraday
critical path.

---

### Resource Utilization Model

Expected resource utilization profiles for a standard trading session:

**CPU Utilization:**
| Period                | Expected CPU | Workflow Context              |
|-----------------------|-------------|-------------------------------|
| Startup (08:00–09:00) | 60–80%      | WF-STARTUP + WF-KNOW          |
| Pre-market (09:00–09:15)| 40–60%    | WF-DAILY + WF-GOV             |
| Active (09:15–15:30)  | 30–50%      | WF-OBS + WF-PRED + WF-DEC + WF-RISK |
| Post-session (15:30–18:00)| 50–70%  | WF-LEARN + WF-KNOW + shutdown |
| After hours            | < 10%      | Monitoring only               |

**Memory Utilization:**
Peak memory usage occurs during WF-LEARN (Learning Engine analysis of full session
data) and WF-SIM (Simulation Engine Monte Carlo runs). Both are scheduled for
off-hours to avoid competition with CRITICAL market-hour workflows.

**Data Feed Rate:**
Data feed rate consumption peaks during WF-OBS (every 30 seconds) and at market
open (09:00 IST) when multiple feeds are hit simultaneously. The Orchestrator
spreads data feed requests across the 30-second observation window to avoid
hitting rate limits.

---

### Fault Tolerance Model

**Single Component Failure Impact Analysis:**

The Orchestrator is designed to tolerate the failure of any single non-CRITICAL
component without halting trading operations.

| Failed Component   | OHS Impact    | Trading Impact       | Recovery Procedure |
|--------------------|---------------|----------------------|--------------------|
| OC-19 (Analytics)  | -0.02         | None                 | ORP-01 (restart)   |
| OC-20 (Reporting)  | -0.01         | None                 | ORP-01 (restart)   |
| OC-09 (Discovery)  | -0.01         | None (new engines)   | ORP-01 (restart)   |
| OC-18 (Recovery)   | -0.03         | None (until needed)  | Manual restart     |
| OC-07 (Agents)     | -0.04         | Reduced agent vis.   | ORP-01 (restart)   |
| OC-12 (Conflict)   | -0.04         | Conflict unresolved  | ORP-07             |
| OC-06 (Resources)  | -0.05         | No resource limits   | ORP-06             |
| OC-13 (Sync)       | -0.05         | Parallel steps serial| ORP-01 (restart)   |
| OC-16 (Monitoring) | -0.05         | Blind ops            | ORP-01 (restart); P1|
| OC-03 (Dependency) | -0.05         | No dep validation    | ORP-01 (restart)   |
| OC-11 (Router)     | -0.06         | Reduced messaging    | ORP-01 (restart)   |
| OC-10 (Commun.)    | -0.08         | Messaging degraded   | ORP-03             |
| OC-01 (Scheduler)  | -0.07         | Schedules missed     | ORP-05             |
| OC-08 (Registry)   | -0.08         | Engine reg degraded  | ORP-04 (restore)   |
| OC-15 (Health)     | -0.06         | No health probe      | ORP-01; P1         |
| OC-05 (Priority)   | -0.04         | Priority unmanaged   | ORP-01 (restart)   |
| OC-02 (Workflow)   | -0.10         | Workflow halted      | ORP-02; P1         |
| OC-14 (State)      | -0.10         | State corrupted      | ORP-04; P1         |
| OC-04 (Execution)  | -0.12         | No engine invocation | ORP-01; P1         |

**Two simultaneous critical component failures** (OC-04 + OC-14) would put OHS
at approximately 0.78 (near bottom of NOMINAL tier). Three would push to DEGRADED
(0.68). The system is designed for single component failure tolerance with
graceful degradation for multiple simultaneous failures.

---

### Continuous Improvement Framework

The Master Orchestrator improves through four mechanisms:

**1. Analytics-Driven Optimization:**
OC-19 Analytics Manager produces weekly trend reports on workflow latency,
resource utilization, and scheduling efficiency. Optimization opportunities
identified by analytics are evaluated against the impact criteria in the IIOS
architectural guidelines (correctness, performance, architecture, smallest change).

**2. Incident-Driven Learning:**
Every P1 incident mandates a post-incident review. The review produces:
(a) Root cause documentation;
(b) Recovery procedure updates if the automated procedure was insufficient;
(c) Monitoring threshold adjustments if the incident was not detected early enough;
(d) Potentially a new or updated constitutional rule if the incident revealed an
architectural gap.

**3. Constitution Review Cycle:**
The Constitution is reviewed annually. Constitutional rules that have never
triggered, rules that trigger false positives, and rules that conflict with
operational experience are candidates for revision. Revisions require Architecture
Council approval and 30-day minimum review.

**4. Extensibility Through New Engine Onboarding:**
Every new engine added to IIOS tests the Orchestrator's extensibility. The time
to onboard a new engine (target: < 1 hour) is tracked as an OQD-12 metric.
Repeated slow onboarding identifies friction in the registration process that can
be reduced without compromising governance.

---

## EXTENDED REFERENCE — IIOS ENGINE ARCHITECTURE SERIES COMPLETION STATUS

The Master Orchestrator Architecture completes the IIOS Engine Architecture Series.
The following is the complete series inventory:

| Architecture Document                   | Document Code        | Status    |
|-----------------------------------------|----------------------|-----------|
| Database Persistence Architecture       | IIOS-DB-ARCH-001     | COMPLETE  |
| Knowledge Engine Architecture           | IIOS-KE-ARCH-001     | COMPLETE  |
| Entity Engine Architecture              | IIOS-ENT-ARCH-001    | COMPLETE  |
| Relationship Engine Architecture        | IIOS-REL-ARCH-001    | COMPLETE  |
| Event Engine Architecture               | IIOS-EVT-ARCH-001    | COMPLETE  |
| Information Engine Architecture         | IIOS-INF-ARCH-001    | COMPLETE  |
| Observation Engine Architecture         | IIOS-OBS-ARCH-001    | COMPLETE  |
| Evidence Engine Architecture            | IIOS-EVI-ARCH-001    | COMPLETE  |
| Hypothesis Engine Architecture          | IIOS-HYP-ARCH-001    | COMPLETE  |
| Reasoning Engine Architecture           | IIOS-RSN-ARCH-001    | COMPLETE  |
| Decision Engine Architecture            | IIOS-DEC-ARCH-001    | COMPLETE  |
| Execution Engine Architecture           | IIOS-EXE-ARCH-001    | COMPLETE  |
| Learning Engine Architecture            | IIOS-LRN-ARCH-001    | COMPLETE  |
| Prediction Engine Architecture          | IIOS-PRD-ARCH-001    | COMPLETE  |
| Risk Engine Architecture                | IIOS-RSK-ARCH-001    | COMPLETE  |
| Portfolio Engine Architecture           | IIOS-PRT-ARCH-001    | COMPLETE  |
| Strategy Engine Architecture            | IIOS-STR-ARCH-001    | COMPLETE  |
| Simulation Engine Architecture          | IIOS-SIM-ENG-ARCH-001| COMPLETE  |
| Governance Engine Architecture          | IIOS-GOV-ENG-ARCH-001| COMPLETE  |
| Master Orchestrator Architecture        | IIOS-MO-ARCH-001     | COMPLETE  |

**Total: 20 authoritative architecture documents. IIOS Engine Architecture Series complete.**

The Master Orchestrator is the capstone of the series. It does not add intelligence
to IIOS. It activates the intelligence that was always there — by ensuring every
engine runs at the right time, with the right inputs, in the right sequence, within
the right resource budget, under proper governance, monitored continuously, with
the capacity to recover safely from failures.

The IIOS is now complete in architecture. Every engine is defined. Every interaction
is governed. Every workflow is specified. Every constitutional rule is written.

*The system is designed. The rest is engineering.*

---

## EXTENDED REFERENCE — ORCHESTRATION QUALITY SCORING EXAMPLES

### Example 1: High-Quality Session

**Session Context:** Normal trading day. All engines HEALTHY. No incidents.
Zero missed schedules. Governance certificate obtained on time.

**OQD Scores:**

| Dimension                | Score  | Basis                                          |
|--------------------------|--------|------------------------------------------------|
| OQD-01 Reliability       | 0.98   | 98.5% workflow success rate (1 non-critical failure)|
| OQD-02 Availability      | 1.00   | 100% availability during market hours          |
| OQD-03 Scalability       | 0.90   | Latency within 5% of nominal at peak load      |
| OQD-04 Determinism       | 1.00   | All scheduling decisions matched replay         |
| OQD-05 Fault Tolerance   | 0.95   | One NORMAL component temporarily DEGRADED      |
| OQD-06 Synchronization   | 0.99   | All barriers completed within timeout; 1 borderline|
| OQD-07 Observability     | 1.00   | 100% metric coverage; dashboard live all day  |
| OQD-08 Performance       | 0.98   | 99.2% of activities within SLA                 |
| OQD-09 Maintainability   | 0.90   | 85% of config changes applied without restart  |
| OQD-10 Auditability      | 1.00   | 100% event coverage; complete chain integrity  |
| OQD-11 Security          | 1.00   | 100% auth coverage; 0 unauthorized access      |
| OQD-12 Extensibility     | 0.90   | No new engines added this session              |
| OQD-13 Op. Stability     | 0.95   | OHS variance across session: 0.03              |

**OQS Computation:**

OQS = (0.98 * 0.18) + (1.00 * 0.15) + (0.90 * 0.05) + (1.00 * 0.10)
      + (0.95 * 0.12) + (0.99 * 0.08) + (1.00 * 0.08) + (0.98 * 0.07)
      + (0.90 * 0.05) + (1.00 * 0.06) + (1.00 * 0.06) + (0.90 * 0.05)
      + (0.95 * 0.05)
    = 0.1764 + 0.1500 + 0.0450 + 0.1000
      + 0.1140 + 0.0792 + 0.0800 + 0.0686
      + 0.0450 + 0.0600 + 0.0600 + 0.0450
      + 0.0475
    = 0.971

**OQS = 0.971 — EXCELLENT tier**

---

### Example 2: Degraded Session with P2 Incident

**Session Context:** P2 incident at 11:15 IST — Prediction Engine UNHEALTHY for 45 minutes.
Decision Engine operated with stale predictions (within TTL). OC-18 Recovery successful at 12:00 IST.
Four WF-PRED workflows failed during the incident window.

**OQD Scores (affected dimensions):**

| Dimension                | Score  | Basis                                          |
|--------------------------|--------|------------------------------------------------|
| OQD-01 Reliability       | 0.82   | 94.2% success rate (4 failed WF-PRED in session)|
| OQD-02 Availability      | 0.95   | 98.5% availability (45-min degraded window)    |
| OQD-04 Determinism       | 1.00   | Scheduling decisions consistent throughout     |
| OQD-05 Fault Tolerance   | 0.75   | NORMAL workflow degraded; trading continued    |
| OQD-06 Synchronization   | 0.92   | 3 barriers timed out during incident window    |
| OQD-08 Performance       | 0.88   | Several SLA misses during incident window      |
| OQD-13 Op. Stability     | 0.72   | OHS variance: 0.08 (high due to incident)      |
| Others                   | 0.90–1.00| Minor impacts                                |

**OQS estimate:** ~0.887 — GOOD tier (close to EXCELLENT boundary)

**Key finding:** The incident degraded reliability, availability, and stability
dimensions. However, the Orchestrator's fault tolerance (OQD-05 = 0.75) showed
the system continued operating throughout — a demonstration of the graceful
degradation architecture working as designed.

**Improvement recommendations from this session:**
1. OQD-01 Reliability: Review whether WF-PRED timeout policy is too aggressive.
2. OQD-05 Fault Tolerance: Prediction Engine UNHEALTHY → Decision should have
   maintained operation (it did) but should have used explicit stale-prediction
   mode rather than implicit TTL tolerance.
3. OQD-13 Stability: 45-minute incident window produced OHS variance of 0.08.
   Target is < 0.05. Recovery time for Prediction Engine should be shortened.

---

## EXTENDED REFERENCE — INTEGRATION VERIFICATION CHECKLIST

Before the Master Orchestrator can be declared production-ready, the following
integration verifications must be completed and documented.

| Test ID  | Verification                                           | Pass Criterion                        |
|----------|--------------------------------------------------------|---------------------------------------|
| IVT-01   | All 14 engines register successfully via OC-09/OC-08   | 14 ERC certificates issued            |
| IVT-02   | Dependency graph validated: zero circular deps         | OC-03 validation report: PASS         |
| IVT-03   | WF-STARTUP completes end-to-end within 10 minutes      | All 10 steps COMPLETED                |
| IVT-04   | WF-GOV obtains Governance Certificate within 5 minutes | OCERT issued before T-00              |
| IVT-05   | WF-OBS completes within 25 seconds (5 runs)            | 5/5 runs within SLA                   |
| IVT-06   | WF-DEC pre-decision gate blocks correctly on fail      | Gate blocks when kill switch active   |
| IVT-07   | WF-RISK blocks on constitutional breach (daily loss)   | Decision rejected when loss = 2%      |
| IVT-08   | OC-15 detects engine OFFLINE within 2 probe intervals  | Engine marked OFFLINE within 20s      |
| IVT-09   | OHS drops to DEGRADED on 3 concurrent UNHEALTHY comps  | OHS <= 0.79 confirmed                 |
| IVT-10   | ORP-08 Emergency Stop executes within 10 seconds       | SAFE mode confirmed within 10s        |
| IVT-11   | WF-STOP completes within 5 minutes                     | All workflows drained; state committed|
| IVT-12   | Conflict detection: resource conflict resolved by prio | Lower-priority workflow deferred      |
| IVT-13   | Recovery ORP-01 Engine Restart completes within 30s    | Engine re-HEALTHY within 30s          |
| IVT-14   | Post-session WF-LEARN completes within 120 minutes     | Learning artifacts archived           |
| IVT-15   | Dead letter queue alert generated within 30s           | Alert confirmed; alert severity correct|
| IVT-16   | Engine communication authentication enforced           | Unauthenticated message rejected      |
| IVT-17   | Priority aging: DEFERRED workflow elevated after 10min | Priority elevated to LOW after 10min  |
| IVT-18   | Schedule miss recovery: CRITICAL missed < 10 min       | Executed immediately on restart       |
| IVT-19   | Governance Engine unavailable: trading suspended       | No new WF-DEC instances created       |
| IVT-20   | OC-14 state checkpoint restore: workflows recovered    | In-progress workflows recovered       |

**All 20 IVTs must pass before production deployment. No exceptions.**

---

*This completes MASTER_ORCHESTRATOR_ARCHITECTURE.md (IIOS-MO-ARCH-001).*

---

## EXTENDED REFERENCE — CONSTITUTIONAL CROSS-REFERENCE

The following maps each Non-Negotiable HARD rule to its operational enforcement
mechanism in the Orchestrator.

| Rule           | Statement (short)                                | Enforced By              | Tested By  |
|----------------|--------------------------------------------------|--------------------------|------------|
| OCC-A-001      | No unregistered engine in workflow               | OC-04 pre-invoke check   | IVT-01     |
| OCC-B-001      | No investment logic in Orchestrator              | Architecture review      | Architecture review|
| OCC-B-002      | No output interpretation by Orchestrator         | OC-04 schema-only check  | Architecture review|
| OCC-C-001      | No ad hoc workflow creation in production        | OC-02 creation gate      | IVT-16     |
| OCC-E-001      | All communication via OC-10                      | OC-10 enforcement        | IVT-16     |
| OCC-G-001      | Unique Workflow Instance IDs                     | OC-02 ID generation      | IVT-03     |
| OCC-H-001      | Governance conflicts resolve for Governance      | OC-12 governance gate    | IVT-06, 07 |
| OCC-I-001      | Recovery never modifies positions                | ORP design constraint    | Architecture review|
| OCC-J-001      | OC-16 always operational                         | P1 auto-raise on OC-16 fail| IVT-08   |
| OCC-N-001      | Credentials in secrets manager only             | OC-22 config validation  | IVT-16     |
| OCC-O-001      | No session without Governance Certificate        | WF-DAILY gate check      | IVT-04     |
| OCC-P-001      | No human override of constitutional rule         | No override UI exists    | Architecture review|

---

## EXTENDED REFERENCE — ORCHESTRATION MATURITY MODEL

The Orchestration Maturity Model defines five maturity levels for the Master
Orchestrator. Each level builds on the previous one.

**Level 1 — Basic Coordination:**
Engines are registered and invokable. Workflows execute sequentially.
Basic health monitoring exists. No dependency management. No priority management.
Characteristic: "The engines run in order."

**Level 2 — Structured Workflows:**
14 named workflows defined with explicit dependency graphs. Parallel execution
supported with synchronization barriers. Priority management active.
Characteristic: "The engines run in the right order with the right inputs."

**Level 3 — Resilient Operations:**
Recovery procedures active and tested. Graceful degradation on resource pressure.
Conflict resolution deterministic. SAFE mode implemented.
Characteristic: "The system recovers from failures predictably."

**Level 4 — Governed Operations:**
Governance Engine fully integrated. Pre-session certification enforced. All
5 GIPs implemented. Constitutional rules enforced at runtime. Human override
process documented.
Characteristic: "The system operates within constitutional constraints at all times."

**Level 5 — Continuously Improving Operations:**
Analytics-driven optimization active. OQS tracked session-over-session.
Incident-driven constitution review. Extensibility proven by successful new engine
onboarding. IVT suite run on every deployment.
Characteristic: "The system becomes better at orchestration over time."

**Target:** IIOS Master Orchestrator at Level 5 by first anniversary of live deployment.

---

## EXTENDED REFERENCE — DEPLOYMENT REQUIREMENTS

**Hardware Requirements:**
The Master Orchestrator components run on the same VPS infrastructure as the
specialized engines. No dedicated hardware is required. The Orchestrator is
lightweight at runtime (coordination overhead is primarily I/O-bound, not compute-bound).

**Network Requirements:**
- All engine endpoints accessible from the Orchestrator over the internal network.
- Governance Engine endpoint accessible (same or separate container/process).
- NTP time synchronization to < 1 second accuracy.
- Telegram Bot API accessible for P1 incident notifications.

**Persistence Requirements:**
- OC-14 State Manager requires persistent storage.
- Audit records require append-only persistent storage.
- Configuration store (OC-22) requires persistent storage with backup.
- All persistent storage must survive container restarts (docker volume mapping).

**Deployment Mode:**
The Master Orchestrator runs as part of the IIOS Docker composition. The
existing docker-compose.yml infrastructure is sufficient. The Orchestrator
components are embedded within the i-trading-brain container and activated
by the enhanced main.py startup sequence.

**Monitoring Infrastructure:**
- Streamlit dashboard (L17 ControlTower) displays the OHS and workflow status.
- Telegram Bot delivers P1/P2 incident notifications.
- Log rotation ensures operational logs are retained for 90 days minimum.

---

*End of Extended References.*
*MASTER_ORCHESTRATOR_ARCHITECTURE.md (IIOS-MO-ARCH-001) Version 1.0.0 — COMPLETE.*

---

## EXTENDED REFERENCE — IIOS MASTER ORCHESTRATOR ARCHITECTURAL STATEMENT

The Master Orchestrator is the final architectural layer of the Investment
Intelligence Operating System. It is built on a single foundational insight:

**Intelligence without coordination is potential. Coordination without intelligence is mechanism. The Master Orchestrator is the mechanism that activates the potential.**

Every engine in IIOS is a specialist. The Knowledge Engine knows. The Prediction
Engine forecasts. The Decision Engine decides. The Risk Engine protects. The
Governance Engine governs. None of these engines, alone, can produce a trade.
Together, coordinated by the Master Orchestrator, they produce an institutional-
grade investment operating system.

The Master Orchestrator contributes:
- **Order** — through the Master Scheduler and Dependency Manager.
- **Safety** — through the Risk Pipeline gate, the Governance integration, and the SAFE mode.
- **Visibility** — through the Monitoring Manager and Health Manager.
- **Resilience** — through the Recovery Manager and fault tolerance architecture.
- **Trust** — through the immutable audit record and constitutional rules.
- **Extensibility** — through the Engine Registry and registration-based architecture.

It asks nothing of the specialized engines except that they register, honor their
declared capabilities, and produce their outputs in the agreed format.
In return, it gives them something no engine can give itself: the coordination
that makes them collectively more than the sum of their parts.

*Document Code: IIOS-MO-ARCH-001 | Released: 2026-07-04 | Series: Complete.*
