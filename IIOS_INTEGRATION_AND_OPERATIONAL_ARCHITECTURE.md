# IIOS INTEGRATION AND OPERATIONAL ARCHITECTURE

**Document Code:** IIOS-INTEG-ARCH-001
**Version:** 1.0.0
**Classification:** Supreme Authoritative Architecture
**Status:** RELEASED
**Date:** 2026-07-04
**Author:** Investment Intelligence Operating System — Architecture Council
**Role:** Final integration document; capstone of the IIOS Architecture Series
**Preceding Series:** IIOS Engine Architecture Series (20 documents, IIOS-DB-ARCH-001 through IIOS-MO-ARCH-001)

---

## CONSTITUTIONAL STATUS

This document is the **capstone and integration layer** of the IIOS Architecture Series.

It does NOT redesign any prior document. Every prior architecture is FINAL and IMMUTABLE.
This document INTEGRATES, COORDINATES, REFERENCES, GOVERNS, VALIDATES, and OPERATIONALIZES them.

**The authoritative inputs to this document:**
- MASTER_KNOWLEDGE_ARCHITECTURE (Foundation)
- INFORMATION_ONTOLOGY, ENTITY_ONTOLOGY, RELATIONSHIP_ONTOLOGY, EVENT_ONTOLOGY
- TEMPORAL_ONTOLOGY, SPATIAL_ONTOLOGY, STATE_ONTOLOGY (Ontologies)
- Knowledge Engine, Information Engine, Entity Engine, Relationship Engine
- Event Engine, Temporal Engine, Spatial Engine, State Engine (Knowledge Layer Engines)
- Prediction Engine, Learning Engine, Decision Engine (Intelligence Layer Engines)
- Risk Engine, Portfolio Engine, Strategy Engine (Financial Layer Engines)
- Simulation Engine, Governance Engine (Validation and Governance Engines)
- Master Orchestrator Architecture (Coordination Layer)
- All prior Foundation Documents and Database Persistence Architecture

---

## IIOS POSITION IN THE INVESTMENT UNIVERSE

`
+=======================================================================+
|            INVESTMENT INTELLIGENCE OPERATING SYSTEM (IIOS)            |
|                   IIOS-INTEG-ARCH-001 v1.0.0                          |
|                                                                       |
|  Supreme Operating Blueprint — All Engines — All Ontologies           |
|  All Workflows — All Governance — All Operations                      |
+=======================================================================+
     |
     v
+------------------------------------------------------------------+
|  LAYER 0 — COORDINATION                                          |
|  Master Orchestrator (IIOS-MO-ARCH-001)                          |
|  Coordinates every engine; schedules every workflow              |
+------------------------------------------------------------------+
     |
     +----------+----------+----------+----------+
     v          v          v          v          v
+--------+ +--------+ +--------+ +--------+ +--------+
|GOVERN. | |SIMULAT.| |STRATEGY| |PORTFOL.| |RISK    |
|ENGINE  | |ENGINE  | |ENGINE  | |ENGINE  | |ENGINE  |
+--------+ +--------+ +--------+ +--------+ +--------+
     |          |          |          |          |
     +----------+----------+----------+----------+
     |
     +----------+----------+----------+
     v          v          v          v
+--------+ +--------+ +--------+ +--------+
|DECISION| |LEARNING| |PREDICT.| |STATE   |
|ENGINE  | |ENGINE  | |ENGINE  | |ENGINE  |
+--------+ +--------+ +--------+ +--------+
     |
     +----------+----------+----------+----------+----------+
     v          v          v          v          v          v
+--------+ +--------+ +--------+ +--------+ +--------+ +--------+
|KNOWL.  | |ENTITY  | |RELAT.  | |EVENT   | |TEMPORAL| |SPATIAL |
|ENGINE  | |ENGINE  | |ENGINE  | |ENGINE  | |ENGINE  | |ENGINE  |
+--------+ +--------+ +--------+ +--------+ +--------+ +--------+
     |
     +----------+----------+----------+----------+----------+----------+
     v          v          v          v          v          v          v
+--------+ +--------+ +--------+ +--------+ +--------+ +--------+ +--------+
|KNOWL.  | |ENTITY  | |RELAT.  | |EVENT   | |TEMPORAL| |SPATIAL | |STATE   |
|ONTOL.  | |ONTOL.  | |ONTOL.  | |ONTOL.  | |ONTOL.  | |ONTOL.  | |ONTOL.  |
+--------+ +--------+ +--------+ +--------+ +--------+ +--------+ +--------+
     |
     +-------------------------+
     v                         v
+------------------+   +------------------+
| DATABASE         |   | INFORMATION      |
| PERSISTENCE      |   | ONTOLOGY         |
| ARCHITECTURE     |   |                  |
+------------------+   +------------------+
`

---

## TABLE OF CONTENTS

`
PART I    — SYSTEM PHILOSOPHY ................................ Section 1
  1.1  What Is IIOS?
  1.2  Why Was IIOS Designed?
  1.3  Core Architectural Principles (15 principles)
  1.4  Architectural Vision
  1.5  Constitutional Hierarchy
  1.6  System Boundaries
  1.7  Operating Philosophy
  1.8  Long-Term Evolution Philosophy

PART II   — COMPLETE SYSTEM MAP .............................. Section 2
  2.1  Layer Architecture Diagram
  2.2  Engine Architecture Map
  2.3  Ontology Architecture Map
  2.4  Engine Dependency Hierarchy
  2.5  Horizontal Integration Map
  2.6  Data Flow Architecture Diagram

PART III  — END-TO-END SYSTEM WORKFLOWS ...................... Section 3
  WF-SYS-01  System Startup
  WF-SYS-02  Market Open
  WF-SYS-03  Observation Flow
  WF-SYS-04  Information Flow
  WF-SYS-05  Knowledge Flow
  WF-SYS-06  Prediction Flow
  WF-SYS-07  Decision Flow
  WF-SYS-08  Risk Flow
  WF-SYS-09  Portfolio Flow
  WF-SYS-10  Strategy Flow
  WF-SYS-11  Learning Flow
  WF-SYS-12  Simulation Flow
  WF-SYS-13  Governance Flow
  WF-SYS-14  System Shutdown
  WF-SYS-15  Recovery
  WF-SYS-16  Maintenance
  WF-SYS-17  Emergency Stop
  WF-SYS-18  Human Override

PART IV   — GLOBAL ENGINE INTERACTION MATRIX ................. Section 4
  4.1  Matrix Reference
  4.2  Producer-Consumer Profiles per Engine
  4.3  Failure Cascade Analysis

PART V    — GLOBAL DATA AND KNOWLEDGE FLOW ................... Section 5
  5.1  Primary Data Flow Architecture
  5.2  Observation-to-Decision Chain
  5.3  Knowledge Accumulation Loop
  5.4  Learning Feedback Loop
  5.5  Governance Integration Points

PART VI   — SYSTEM GOVERNANCE ................................ Section 6
  6.1  through 6.10

PART VII  — SYSTEM OPERATIONAL MODEL ......................... Section 7
  7.1  through 7.11

PART VIII — SYSTEM QUALITY FRAMEWORK ......................... Section 8
  8.1  through 8.13

PART IX   — IIOS CONSTITUTION ................................ Section 9
  SCC-A through SCC-X (180 rules)

PART X    — SYSTEM READINESS CERTIFICATION ................... Section 10
  CP-01 through CP-12

SUPPLEMENTS A through J

FINAL CHAPTER — ROADMAP TO IMPLEMENTATION
`

---

## PART I — SYSTEM PHILOSOPHY

### 1.1 What Is IIOS?

The Investment Intelligence Operating System (IIOS) is an institutional-grade,
multi-layered, AI-governed investment intelligence platform designed to transform
raw market observations into investment decisions through a structured, auditable,
and governed process.

IIOS is not a trading algorithm. It is not a strategy library. It is not a risk
management tool. It is all of these things — and more — organized as an operating
system. Like a computing operating system that coordinates hardware, memory, storage,
and application processes, IIOS coordinates market data, knowledge engines, prediction
models, decision frameworks, risk engines, and governance systems into a single,
coherent, intelligent operating environment.

At its core, IIOS answers one question: **How does an institution with complete
market knowledge, perfect memory, unlimited analytical capacity, and rigorous
governance make better investment decisions than a human acting on intuition?**

The answer has 26 components, 7 ontologies, 14 engines, and one master orchestrator.
The answer is IIOS.

**IIOS in three sentences:**
IIOS observes markets through structured ontologies that define what can be known.
It reasons about what it knows through layered intelligence engines that produce
calibrated predictions and governed decisions.
It governs everything it does through a constitutional framework that protects
capital, preserves audit trails, and enables continuous learning.

---

### 1.2 Why Was IIOS Designed?

Four fundamental problems with investment intelligence motivated the IIOS design:

**Problem 1 — Fragmented Intelligence:**
Most investment systems are collections of disconnected tools: a data feed here,
a strategy model there, a risk system somewhere else. When these tools disagree,
there is no principled way to resolve the disagreement. IIOS was designed to
integrate every intelligence function into one governed system with defined
authority relationships.

**Problem 2 — Absent Institutional Memory:**
Investment organizations accumulate hard-won knowledge in human minds — and lose
it when people leave. Market patterns, historical precedents, strategy outcomes,
and regime knowledge disappear with the analyst. IIOS was designed with a
Knowledge Engine that accumulates institutional memory permanently and makes it
available to every intelligence process.

**Problem 3 — Unaccountable Decisions:**
When a trade loses money, most systems cannot explain why the decision was made,
what information was available, what predictions were generated, or what risk
assessment was performed. IIOS was designed with complete decision traceability:
every decision has a full provenance trail — from raw observation through prediction
through debate through risk approval.

**Problem 4 — Learning Without Memory:**
Investment systems that do not learn from outcomes are doomed to repeat mistakes.
IIOS was designed with a Learning Engine that continuously updates models from
outcomes and a Governance Engine that ensures learning does not corrupt live
strategy parameters without validation.

---

### 1.3 Core Architectural Principles

**Principle 1 — Separation of Concerns:**
Every function belongs to the engine designed for it. The Knowledge Engine knows.
The Prediction Engine predicts. The Decision Engine decides. The Governance Engine
governs. No engine performs another engine's function.

**Principle 2 — Ontology First:**
Before any engine can process information, the information must be defined. The
seven IIOS ontologies (Knowledge, Information, Entity, Relationship, Event,
Temporal, Spatial, State) define every concept that IIOS reasons about. Engines
operate on ontologically typed data, not raw data.

**Principle 3 — Constitutional Governance:**
IIOS operates under a constitution. Constitutional rules are not preferences or
guidelines — they are inviolable constraints. The Governance Engine enforces the
constitution. No component can override a constitutional rule.

**Principle 4 — Traceability Over Convenience:**
Every observation, prediction, decision, execution, and outcome is permanently
recorded and attributed. Traceability is never sacrificed for operational convenience.
If an action cannot be traced, it should not be performed.

**Principle 5 — Layered Independence:**
Higher layers depend on lower layers, not the reverse. Knowledge engines do not
call decision engines. Decision engines do not call governance engines. The
dependency graph is directed and acyclic.

**Principle 6 — Evidence Before Deployment:**
No strategy enters live trading without documented evidence of its behavior.
Evidence is produced by the Simulation Engine, evaluated by the Governance Engine,
and stored permanently in the evidence dossier.

**Principle 7 — Learning Without Contamination:**
The Learning Engine improves models without corrupting live operations. Learning
outputs are validated before they influence live strategies. Learning is isolated
from real-time execution.

**Principle 8 — Fail Safely:**
IIOS fails toward safety, not toward opportunity. When uncertain, IIOS does not
trade. When health is compromised, IIOS reduces activity. When governance is
unavailable, IIOS stops. Safety failure modes are always preferred over unsafe
operation.

**Principle 9 — Human Authority Preserved:**
IIOS augments human judgment; it does not replace it. Human operators retain
override authority. Critical incidents require human authorization to resolve.
IIOS cannot act in ways that circumvent the humans responsible for it.

**Principle 10 — Extensibility Without Modification:**
New capabilities are added to IIOS through new engines, new ontology extensions,
and new workflow registrations. Existing components are not modified to accommodate
new capabilities. The architecture is open for extension, closed for modification.

**Principle 11 — Performance Through Architecture:**
Performance requirements are achieved through architectural decisions, not through
performance tricks. The 5-minute knowledge cache eliminates the Knowledge Engine
from the intraday critical path. The 30-second observation cycle provides fresh
signals without overloading data feeds.

**Principle 12 — Governance Is Not Overhead:**
The Governance Engine is not a compliance checkbox. It is an operational requirement.
A session without a governance certificate does not run. A strategy without an
evidence dossier does not deploy. Governance is woven into the operational fabric.

**Principle 13 — Distributed Intelligence, Unified Behavior:**
Intelligence is distributed across 14 specialized engines. Behavior is unified by
the Master Orchestrator. Neither distribution nor unification is an accident; both
are deliberate architectural choices that serve IIOS's goals simultaneously.

**Principle 14 — Market Indifference at the Orchestration Level:**
The Master Orchestrator knows nothing about markets. It schedules, coordinates,
monitors, and recovers. Market knowledge is the exclusive domain of specialized
engines. This separation ensures that the coordination layer remains permanently
neutral.

**Principle 15 — Constitutional Permanence:**
Constitutional rules do not bend under operational pressure. The daily loss limit,
the VIX kill switch, the pre-session governance certification, and the evidence
dossier requirement are permanent features of IIOS. They are most important during
exactly the conditions that create pressure to relax them.

---

### 1.4 Architectural Vision

IIOS is architected to be:

**A 30-year system.** Not a proof of concept or a minimum viable product. IIOS
is designed to accumulate institutional knowledge for decades, improve continuously,
and remain relevant as markets, regulations, and instruments evolve.

**An institutional platform.** IIOS applies institutional-grade standards to
individual investment: the same rigor in documentation, governance, risk management,
and audit that institutional asset managers apply, made accessible to a single
system operating with disciplined architecture.

**A self-improving intelligence.** Through its Learning Engine and Knowledge
Engine, IIOS accumulates experience and improves prediction accuracy, decision
quality, and strategy performance over time. It does not require manual
re-engineering to adapt to new market regimes.

**A governed machine.** IIOS is not an autonomous agent. It is a governed machine.
Every significant action has a governance trail. The Governance Engine acts as the
institutional conscience of the system, ensuring that the drive for performance
never overrides the requirements of prudence.

---

### 1.5 Constitutional Hierarchy

The IIOS constitutional hierarchy defines the authority order for all architectural
and operational decisions:

`
LEVEL 1 — IIOS CONSTITUTION (IIOS-INTEG-ARCH-001)
   Supreme governing rules of the entire system.
   Cannot be overridden by any engine, operator, or condition.
   Amendment requires Architecture Council + System Owner, 30-day review.
        |
LEVEL 2 — ENGINE CONSTITUTIONS (per-engine architecture documents)
   Governing rules for each engine's internal operations.
   Must not contradict Level 1 rules.
   Amendment requires Architecture Council approval.
        |
LEVEL 3 — GOVERNANCE ENGINE RULES (IIOS-GOV-ENG-ARCH-001)
   Operational governance rules; session authorization; compliance.
   Must not contradict Levels 1 or 2.
   Enforced by the Governance Engine in real time.
        |
LEVEL 4 — MASTER ORCHESTRATOR CONSTITUTION (IIOS-MO-ARCH-001)
   Coordination and operational rules.
   Must not contradict Levels 1, 2, or 3.
        |
LEVEL 5 — OPERATIONAL POLICIES (OC-22 Configuration Manager)
   Runtime configuration within constitutional constraints.
   Can be modified by Operations Lead within authorized bounds.
        |
LEVEL 6 — HUMAN OVERRIDE
   Human operators retain override authority for non-constitutional rules.
   Cannot override constitutional rules (Level 1–2).
   All overrides logged permanently.
`

---

### 1.6 System Boundaries

**IIOS processes:** Market observations, structured knowledge, predictions, decisions,
risk assessments, portfolio state, learning outputs, strategy performance, simulation
results, and governance artifacts.

**IIOS does NOT process:** Raw market orders to brokers (that is the Execution Engine's
interface, which is outside the intelligence system boundary); user portfolio management
instructions (those come in as override events); regulatory filings (those are
informed by IIOS audit records but produced externally).

**IIOS operates within:** The defined financial instruments universe (NSE equities,
options, indices); the defined market hours (09:15–15:30 IST); the defined risk
parameters (2% daily loss limit, VIX<=45 kill switch, strategy-level limits).

**IIOS does not operate on:** Real-time order book microstructure (sub-second data);
cryptocurrency or foreign exchange instruments (current scope); corporate bond markets.

---

### 1.7 Operating Philosophy

IIOS operates with five operating disciplines:

**Discipline 1 — Measure Everything.** Every metric, every latency, every success
rate, every failure is measured. What cannot be measured cannot be improved.

**Discipline 2 — Learn Continuously.** Every session produces learning. Every
outcome is attributed to a decision. Every decision is traced to a prediction.
The Learning Engine never stops improving.

**Discipline 3 — Govern Persistently.** Governance is not a session start-and-end
activity. It runs continuously throughout every session.

**Discipline 4 — Recover Predictably.** Failures are handled by documented procedures
that produce consistent outcomes. The Recovery Manager never improvises.

**Discipline 5 — Improve Intentionally.** Improvement happens through deliberate
architectural choices, not random experimentation. Every improvement is evaluated
for architectural impact before it is implemented.

---

### 1.8 Long-Term Evolution Philosophy

IIOS is designed to evolve through three mechanisms:

**Engine Evolution:** Individual engines improve through internal model updates
(Learning Engine), parameter tuning (Strategy Engine), and capability expansion
(new prediction models in Prediction Engine). Engine evolution is governed: all
changes are validated through the Simulation Engine and approved by the Governance
Engine before affecting live operations.

**Ontology Evolution:** Ontologies may be extended with new concepts as new
instrument types, market structures, or knowledge domains are incorporated. Ontology
extensions add new types and relationships; they never remove existing ones.
Backward compatibility is a constitutional requirement.

**Architecture Evolution:** New engines are added through the Master Orchestrator's
extension mechanism. New engines register, declare capabilities and dependencies,
and integrate through the standard workflow framework. No existing engine is
modified to accommodate a new engine.

---

## PART II — COMPLETE SYSTEM MAP

### 2.1 IIOS Full Layer Architecture

IIOS is organized into seven architectural strata. Each stratum provides services
consumed by strata above it. Strata do not skip levels: a higher-stratum engine
accesses lower-stratum services through the engine immediately below it, not
by reaching down multiple levels.

`
+=========================================================================+
|  STRATUM 7 — COORDINATION STRATUM                                       |
|                                                                         |
|  [ MASTER ORCHESTRATOR ]                                                |
|  IIOS-MO-ARCH-001                                                       |
|  22 components across 4 tiers: Scheduling, Coordination,                |
|  Operational, Infrastructure.                                           |
|  Governs every workflow. Monitors every engine. Recovers every fault.   |
+=========================================================================+
     |               |               |               |
     v               v               v               v
+============+ +============+ +============+ +============+
| STRATUM 6  | | STRATUM 6  | | STRATUM 6  | | STRATUM 6  |
| VALIDATION | | GOVERNANCE | | FINANCIAL  | | INTELLIGENCE|
|            | |            | | LAYER      | | LAYER      |
|            | |            | |            | |            |
| Simulation | | Governance | | Risk Engine| | Decision   |
| Engine     | | Engine     | | Portfolio  | | Engine     |
|            | |            | | Engine     | | Learning   |
|            | |            | | Strategy   | | Engine     |
|            | |            | | Engine     | | Prediction |
|            | |            | |            | | Engine     |
+============+ +============+ +============+ +============+
                                   |
+==========================================================================+
|  STRATUM 5 — STATE STRATUM                                               |
|                                                                          |
|  [ STATE ENGINE ]  (IIOS-STATE-ENG-ARCH-001)                            |
|  Manages system and entity state. Maintains state machines.             |
|  State transitions are the building blocks for event detection.         |
+==========================================================================+
                                   |
+==========================================================================+
|  STRATUM 4 — KNOWLEDGE STRATUM                                           |
|                                                                          |
|  [ KNOWLEDGE ENGINE ]  [ ENTITY ENGINE ]  [ RELATIONSHIP ENGINE ]       |
|  [ EVENT ENGINE ]      [ TEMPORAL ENGINE ] [ SPATIAL ENGINE ]           |
|  [ INFORMATION ENGINE ]                                                  |
|  Seven specialized engines providing structured knowledge services.      |
+==========================================================================+
                                   |
+==========================================================================+
|  STRATUM 3 — ONTOLOGY STRATUM                                            |
|                                                                          |
|  [ KNOWLEDGE ONTOLOGY ] [ INFORMATION ONTOLOGY ] [ ENTITY ONTOLOGY ]    |
|  [ RELATIONSHIP ONTOLOGY ] [ EVENT ONTOLOGY ] [ TEMPORAL ONTOLOGY ]     |
|  [ SPATIAL ONTOLOGY ]  [ STATE ONTOLOGY ]                               |
|  Eight ontologies defining every concept that IIOS reasons about.       |
+==========================================================================+
                                   |
+==========================================================================+
|  STRATUM 2 — PERSISTENCE STRATUM                                         |
|                                                                          |
|  [ DATABASE PERSISTENCE ARCHITECTURE ]  (IIOS-DB-ARCH-001)             |
|  Schema governance. SQLite storage. Audit tables. Backup procedures.    |
+==========================================================================+
                                   |
+==========================================================================+
|  STRATUM 1 — FOUNDATION STRATUM                                          |
|                                                                          |
|  [ MASTER KNOWLEDGE ARCHITECTURE ]  (Foundation Document)              |
|  System identity. Governing philosophy. Architecture Council.           |
+==========================================================================+
`

---

### 2.2 Engine Catalogue with Document Codes

Every IIOS engine has a unique document code and lives in a defined architectural
stratum.

`
+-----+---------------------------+---------------------+--------+----------+
| No. | Engine                    | Document Code       |Stratum | Status   |
+-----+---------------------------+---------------------+--------+----------+
|  01 | Database Persistence      | IIOS-DB-ARCH-001    |  2     | COMPLETE |
|  02 | Information Engine        | IIOS-INFO-ENG-001   |  4     | COMPLETE |
|  03 | Knowledge Engine          | IIOS-KNW-ENG-001    |  4     | COMPLETE |
|  04 | Entity Engine             | IIOS-ENT-ENG-001    |  4     | COMPLETE |
|  05 | Relationship Engine       | IIOS-REL-ENG-001    |  4     | COMPLETE |
|  06 | Event Engine              | IIOS-EVT-ENG-001    |  4     | COMPLETE |
|  07 | Temporal Engine           | IIOS-TMP-ENG-001    |  4     | COMPLETE |
|  08 | Spatial Engine            | IIOS-SPA-ENG-001    |  4     | COMPLETE |
|  09 | State Engine              | IIOS-STE-ENG-001    |  5     | COMPLETE |
|  10 | Prediction Engine         | IIOS-PRD-ENG-001    |  6     | COMPLETE |
|  11 | Learning Engine           | IIOS-LRN-ENG-001    |  6     | COMPLETE |
|  12 | Decision Engine           | IIOS-DEC-ENG-001    |  6     | COMPLETE |
|  13 | Risk Engine               | IIOS-RSK-ENG-001    |  6     | COMPLETE |
|  14 | Portfolio Engine          | IIOS-PFO-ENG-001    |  6     | COMPLETE |
|  15 | Strategy Engine           | IIOS-STG-ENG-001    |  6     | COMPLETE |
|  16 | Simulation Engine         | IIOS-SIM-ENG-001    |  6     | COMPLETE |
|  17 | Governance Engine         | IIOS-GOV-ENG-001    |  6     | COMPLETE |
|  18 | Master Orchestrator       | IIOS-MO-ARCH-001    |  7     | COMPLETE |
+-----+---------------------------+---------------------+--------+----------+
`

---

### 2.3 Ontology Architecture Map

All eight ontologies are instantiated before any engine starts. They are read by
engines but written only by the Ontology Management process (an architectural
function, not a runtime engine).

`
+==========================================================================+
|                        IIOS ONTOLOGY LAYER                               |
+----------------------------------+---------------------------------------+
| FOUNDATIONAL ONTOLOGIES          | DOMAIN ONTOLOGIES                     |
| (define general concepts)        | (define domain-specific concepts)     |
+----------------------------------+---------------------------------------+
|                                  |                                       |
| INFORMATION ONTOLOGY             | ENTITY ONTOLOGY                       |
| Defines: what information is,    | Defines: equity, index, option,       |
| information types, quality,      | sector, market, issuer, instrument    |
| provenance, reliability.         | sub-types, and their properties.      |
|                                  |                                       |
| TEMPORAL ONTOLOGY                | RELATIONSHIP ONTOLOGY                 |
| Defines: time, intervals,        | Defines: correlation, causality,      |
| sessions, horizons, calendars,   | membership, containment, dependency,  |
| market time zones.               | sector-stock relationships.           |
|                                  |                                       |
| SPATIAL ONTOLOGY                 | EVENT ONTOLOGY                        |
| Defines: geographic regions,     | Defines: market events, corporate     |
| exchange locations, listing       | events, macro events, calendar        |
| jurisdictions, market zones.     | events, anomaly events.               |
|                                  |                                       |
| STATE ONTOLOGY                   | KNOWLEDGE ONTOLOGY                    |
| Defines: system states, entity   | Defines: knowledge types, assertions, |
| states, strategy states,         | confidence levels, knowledge sources, |
| market regime states.            | and knowledge provenance.             |
+----------------------------------+---------------------------------------+
| Ontology Amendment Process:                                               |
| New concept proposed → Architecture review → No backward-compat break   |
| confirmed → Added with version increment → All engines re-validated.    |
+==========================================================================+
`

---

### 2.4 Engine Dependency Hierarchy

This diagram shows the complete dependency graph. An arrow from A to B means
A depends on B (A consumes B's services).

`
Master Orchestrator
    |
    +-- Governance Engine
    |       |-- Knowledge Engine
    |       |-- Decision Engine (validation requests)
    |       |-- Simulation Engine (evidence validation)
    |
    +-- Simulation Engine
    |       |-- Strategy Engine
    |       |-- Risk Engine
    |       |-- Knowledge Engine
    |       |-- State Engine
    |
    +-- Strategy Engine
    |       |-- Knowledge Engine
    |       |-- Prediction Engine
    |       |-- Risk Engine
    |       |-- Learning Engine
    |       |-- Simulation Engine
    |
    +-- Portfolio Engine
    |       |-- Risk Engine
    |       |-- Decision Engine
    |       |-- Knowledge Engine
    |       |-- State Engine
    |
    +-- Risk Engine
    |       |-- Knowledge Engine
    |       |-- State Engine
    |       |-- Prediction Engine
    |       |-- Portfolio Engine (portfolio state)
    |
    +-- Decision Engine
    |       |-- Prediction Engine
    |       |-- Risk Engine
    |       |-- Knowledge Engine
    |       |-- Governance Engine (authorization)
    |
    +-- Learning Engine
    |       |-- Knowledge Engine
    |       |-- State Engine
    |       |-- Prediction Engine (model updates)
    |
    +-- Prediction Engine
    |       |-- Knowledge Engine
    |       |-- State Engine
    |       |-- Temporal Engine
    |       |-- Event Engine
    |
    +-- State Engine
    |       |-- Knowledge Engine
    |       |-- Event Engine
    |       |-- Temporal Engine
    |
    +-- Knowledge Engine
    |       |-- Information Engine
    |       |-- Entity Engine
    |       |-- Relationship Engine
    |       |-- Event Engine
    |       |-- Temporal Engine
    |       |-- Spatial Engine
    |
    +-- Information Engine
    |       |-- Database Persistence Architecture
    |
    +-- Entity Engine
    |       |-- Information Engine
    |       |-- Database Persistence Architecture
    |
    +-- Relationship Engine
    |       |-- Entity Engine
    |       |-- Information Engine
    |
    +-- Event Engine
    |       |-- Entity Engine
    |       |-- Temporal Engine
    |       |-- Information Engine
    |
    +-- Temporal Engine
    |       |-- Database Persistence Architecture
    |
    +-- Spatial Engine
            |-- Entity Engine
            |-- Database Persistence Architecture
`

**Dependency Depth by Engine:**

| Engine              | Dependency Depth | Direct Dependencies              |
|---------------------|-----------------|----------------------------------|
| Database Persistence| 0               | None (foundation)                |
| Temporal Engine     | 1               | Database Persistence             |
| Spatial Engine      | 2               | Entity, DB                       |
| Information Engine  | 1               | Database Persistence             |
| Entity Engine       | 2               | Information, DB                  |
| Relationship Engine | 3               | Entity, Information              |
| Event Engine        | 3               | Entity, Temporal, Information    |
| Knowledge Engine    | 4               | Info, Entity, Relationship, Event, Temporal, Spatial |
| State Engine        | 5               | Knowledge, Event, Temporal       |
| Prediction Engine   | 5               | Knowledge, State, Temporal, Event|
| Learning Engine     | 6               | Knowledge, State, Prediction     |
| Decision Engine     | 6               | Prediction, Risk, Knowledge, Gov |
| Risk Engine         | 6               | Knowledge, State, Prediction, Portfolio |
| Portfolio Engine    | 7               | Risk, Decision, Knowledge, State |
| Strategy Engine     | 7               | Knowledge, Prediction, Risk, Learning, Simulation |
| Simulation Engine   | 7               | Strategy, Risk, Knowledge, State |
| Governance Engine   | 5               | Knowledge, Decision, Simulation  |
| Master Orchestrator | 8               | All engines                      |

---

### 2.5 Horizontal Integration Map

Beyond the vertical dependency hierarchy, certain engines have horizontal integration
relationships — they exchange services as peers.

`
HORIZONTAL INTEGRATION RELATIONSHIPS:

Risk Engine <-------> Portfolio Engine
  Risk provides position limits; Portfolio provides current allocations.
  Circular by design; resolved by the ordering protocol in Supplement D.

Decision Engine <----> Governance Engine
  Decision requests authorization; Governance provides/denies certificates.
  This is the critical governance gate in every decision cycle.

Learning Engine <----> Prediction Engine
  Learning updates prediction model parameters; Prediction reports forecast errors.
  Tightly coupled feedback loop, managed by synchronization barriers.

Strategy Engine <----> Simulation Engine
  Strategy submits candidates for simulation; Simulation returns evidence dossiers.
  Strategy cannot deploy a candidate that Simulation has not evaluated.

Knowledge Engine <----> Event Engine
  Knowledge provides entity context for event interpretation;
  Event provides detected events that update the Knowledge Engine.

Temporal Engine <----> Event Engine
  Temporal provides time resolution for event timestamps;
  Event provides temporal anchors for historical lookups.
`

---

### 2.6 Data Flow Architecture Diagram

The primary data flow shows how raw market data is transformed through
successive processing stages into investment decisions.

`
MARKET DATA SOURCES
        |
        | Raw price, volume, option chain, corporate data, macro data
        v
+------------------+
| INFORMATION      |   <--- Validates, classifies, stores
| ENGINE           |
+------------------+
        |
        | Typed information objects (InformationObject<T>)
        v
+------------------+
| ENTITY ENGINE    |   <--- Extracts entity properties
| EVENT ENGINE     |   <--- Detects discrete events
| TEMPORAL ENGINE  |   <--- Attaches time context
| SPATIAL ENGINE   |   <--- Attaches spatial context
| RELATIONSHIP ENG |   <--- Infers relationships
+------------------+
        |
        | Structured entity records, events, relationships
        v
+------------------+
| KNOWLEDGE ENGINE |   <--- Integrates into knowledge graph
+------------------+
        |
        | Factual knowledge assertions (with confidence)
        v
+------------------+    +-----------------------+
| STATE ENGINE     |    | TEMPORAL ENGINE       |
| (current state)  |    | (horizon management)  |
+------------------+    +-----------------------+
        |                         |
        +----------+--------------+
                   |
                   v
        +------------------+
        | PREDICTION ENGINE|   <--- Generates forecasts
        +------------------+
                   |
                   | Prediction objects (with confidence intervals)
                   v
+------------------+    +------------------+
| RISK ENGINE      |    | PORTFOLIO ENGINE |
| (risk assessment)|    | (current state)  |
+------------------+    +------------------+
        |                         |
        +----------+--------------+
                   |
                   v
        +------------------+
        | DECISION ENGINE  |   <--- Produces decision recommendations
        +------------------+
                   |
                   | Decision with authorization request
                   v
        +------------------+
        | GOVERNANCE ENGINE|   <--- Authorizes or vetoes
        +------------------+
                   |
                   | Authorized decision
                   v
        +------------------+
        | MASTER ORCHESTRAT|   <--- Routes to execution
        +------------------+
                   |
                   v
            EXECUTION OUTPUT
`

---

## PART III — END-TO-END SYSTEM WORKFLOWS

### Overview

IIOS defines 18 system-level workflows, each covering a distinct operational
scenario. Workflow IDs take the form WF-SYS-{NN}. Each workflow definition
includes: trigger, preconditions, stages, success criteria, and failure handling.

Sequence diagrams use the notation:
  A --[message]--> B   (A sends message to B)
  A ==[query]==>  B   (A sends synchronous query to B)
  B --[response]--> A  (B returns response to A)

---

### WF-SYS-01 — SYSTEM STARTUP WORKFLOW

**Purpose:** Transition IIOS from cold state to operational state in the correct
order, validating each layer before proceeding to the next.

**Trigger:** Operator executes startup command (typically T-60 minutes before
market open).

**Preconditions:** None (this is the initial workflow).

**Stages:**

`
Stage 1: Foundation Validation (T-60 to T-55)
   Master Orchestrator
     --> validates Database Persistence Architecture availability
     --> loads Ontology Layer (8 ontologies)
     --> confirms ontology version checksums
     --> validates Master Knowledge Architecture foundation document
   Success gate: all 8 ontologies loaded, all checksums valid.

Stage 2: Data Layer Engine Startup (T-55 to T-50)
   Master Orchestrator
     --> starts Information Engine
     --> starts Temporal Engine
     --> starts Spatial Engine
     --> runs engine health checks for each
   Success gate: all 3 engines report HEALTHY.

Stage 3: Knowledge Layer Engine Startup (T-50 to T-42)
   Master Orchestrator
     --> starts Entity Engine (depends on Information Engine)
     --> starts Relationship Engine (depends on Entity Engine)
     --> starts Event Engine (depends on Entity, Temporal)
     --> starts Knowledge Engine (depends on Info, Entity, Relationship, Event, Temporal, Spatial)
     --> requests Knowledge Engine warm-up (pre-load 5-minute cache)
   Success gate: all 4 engines report HEALTHY; Knowledge Engine cache populated.

Stage 4: State Layer Engine Startup (T-42 to T-38)
   Master Orchestrator
     --> starts State Engine
     --> State Engine loads last-known system state from persistence
     --> State Engine confirms entity state restoration
   Success gate: State Engine reports HEALTHY; state restored.

Stage 5: Intelligence Layer Engine Startup (T-38 to T-30)
   Master Orchestrator
     --> starts Prediction Engine (loads prediction models)
     --> starts Learning Engine (loads accumulated learning state)
     --> starts Decision Engine (loads decision thresholds and profiles)
   Success gate: all 3 engines report HEALTHY; models loaded.

Stage 6: Financial Layer Engine Startup (T-30 to T-22)
   Master Orchestrator
     --> starts Risk Engine (loads risk limits and current exposure)
     --> starts Portfolio Engine (loads current portfolio state)
     --> starts Strategy Engine (loads active strategies)
   Success gate: all 3 engines report HEALTHY; state consistent.

Stage 7: Simulation and Governance Engine Startup (T-22 to T-15)
   Master Orchestrator
     --> starts Simulation Engine
     --> starts Governance Engine
     --> Governance Engine performs pre-session compliance check
     --> Governance Engine issues DAILY_SESSION_CERTIFICATE or rejects startup
   Success gate: Governance Engine issues valid DAILY_SESSION_CERTIFICATE.

Stage 8: Operational Readiness (T-15 to T-00)
   Master Orchestrator
     --> performs OHS (Orchestrator Health Score) calculation
     --> activates continuous monitoring (30-second interval)
     --> activates intraday scan scheduler
     --> confirms all 17 engine registrations in Engine Registry
     --> sets system state = OPERATIONAL
   Success gate: OHS >= 0.80 (NOMINAL); system state = OPERATIONAL.
`

**Failure Handling:** Any stage failure blocks progression to the next stage.
If Stage 7 fails (Governance Certificate denied), the system does not enter
OPERATIONAL state. Operator must resolve the blocking condition.

---

### WF-SYS-02 — MARKET OPEN WORKFLOW

**Purpose:** Execute the sequence of activities that must be completed at the
market open (09:15 IST) before the first decision cycle.

**Trigger:** Temporal Engine fires MARKET_OPEN event at 09:15 IST.

**Preconditions:** WF-SYS-01 completed; system state = OPERATIONAL; DAILY_SESSION_CERTIFICATE valid.

**Stages:**

`
09:15:00 — MARKET_OPEN event fired by Temporal Engine
     --> Event Engine records MARKET_OPEN event
     --> Master Orchestrator receives MARKET_OPEN trigger

09:15:10 — Pre-decision scan
     --> Information Engine fetches opening prices for universe
     --> Entity Engine updates entity properties (prices, volume)
     --> Event Engine scans for opening gap events, circuit breakers

09:15:30 — Knowledge refresh
     --> Knowledge Engine refreshes knowledge cache
     --> State Engine updates all entity states with opening data
     --> Risk Engine updates VIX and market breadth readings

09:15:45 — Governance check
     --> Governance Engine confirms VIX <= 45 (kill-switch condition)
     --> Governance Engine confirms overnight news has no override events
     --> If kill-switch condition met: transitions to WF-SYS-17 (Emergency Stop)

09:16:00 — First prediction cycle
     --> Prediction Engine generates opening predictions for all candidates
     --> Decision Engine receives predictions; performs first decision check
     --> Risk Engine validates any emerging decisions against daily limits

09:16:30 — System confirms ACTIVE trading state
     --> Master Orchestrator logs MARKET_OPEN_COMPLETE
     --> System enters INTRADAY_ACTIVE state
`

---

### WF-SYS-03 — OBSERVATION FLOW WORKFLOW

**Purpose:** Define the continuous cycle of market observation that feeds the
entire IIOS intelligence stack.

**Trigger:** Scheduled every 30 seconds during INTRADAY_ACTIVE state; also
triggered by EVENT_DETECTED signals.

**Preconditions:** System state = INTRADAY_ACTIVE; Information Engine HEALTHY.

**Sequence:**

`
[Market Data Sources]
     --[raw OHLCV, option chain, corporate data]--> [Information Engine]

[Information Engine]
     ==validates quality, classifies type==>
     --[InformationObject<PriceBar>, InformationObject<OptionData>]--> [Entity Engine]
     --[InformationObject<MacroData>]--> [Knowledge Engine]
     --[raw events, corporate actions]--> [Event Engine]

[Entity Engine]
     ==updates entity properties==>
     --[updated Entity records]--> [Relationship Engine]
     --[updated Entity records]--> [Knowledge Engine]

[Event Engine]
     ==classifies and validates events==>
     --[structured Event objects]--> [State Engine]
     --[structured Event objects]--> [Knowledge Engine]

[Temporal Engine]
     ==annotates all objects with temporal context==>
     --[time-anchored objects]--> [Knowledge Engine]

[Knowledge Engine]
     ==integrates into knowledge graph, updates cache==>
     --[KNOWLEDGE_UPDATED signal]--> [Master Orchestrator]
     --[OBSERVATION_CYCLE_COMPLETE signal]--> [Master Orchestrator]
`

**Success Criteria:** OBSERVATION_CYCLE_COMPLETE signal received; knowledge
cache refreshed; no quality violations detected.

**On Quality Violation:** Information Engine logs violation, attempts fallback
data source, escalates to P2 incident if fallback fails.

---

### WF-SYS-04 — INFORMATION FLOW WORKFLOW

**Purpose:** Define how raw market data is transformed into structured information
objects that carry provenance, quality scores, and temporal anchors.

**Trigger:** Part of WF-SYS-03; also triggered by batch data arrival events.

**Stages:**

`
Stage 1: Raw Data Receipt
   Information Engine receives raw data from market feeds.
   Each data packet is assigned a reception timestamp (Temporal Engine).
   Source ID is recorded (provenance chain begins here).

Stage 2: Quality Assessment
   Information Engine applies quality rules:
   - Completeness: all required fields present?
   - Timeliness: data received within acceptable latency?
   - Consistency: values within plausible ranges?
   - Source reliability: source reputation score applied.
   Output: quality score [0.0-1.0] attached to each information object.

Stage 3: Classification
   Information Engine classifies the information type:
   - Price information (OHLCV)
   - Options information (chain data, Greeks)
   - Fundamental information (earnings, dividends)
   - Macro information (index data, economic indicators)
   - Event information (corporate actions, news signals)

Stage 4: Ontology Typing
   Each information object is assigned an ontological type from the
   Information Ontology. This ensures downstream engines receive
   typed objects, not raw bytes.

Stage 5: Persistence
   All information objects are persisted through the Database Persistence
   Architecture before any engine reads them.

Stage 6: Distribution
   Information objects are made available to consuming engines:
   Entity Engine, Event Engine, Knowledge Engine.
`

---

### WF-SYS-05 — KNOWLEDGE FLOW WORKFLOW

**Purpose:** Define how structured information is integrated into the IIOS
knowledge graph and made available to prediction and decision engines.

**Trigger:** Triggered by OBSERVATION_CYCLE_COMPLETE; also triggered by
LEARNING_UPDATE events and ENTITY_UPDATE events.

**Stages:**

`
Stage 1: Information Ingestion
   Knowledge Engine receives typed InformationObjects from Information Engine.
   Entity records from Entity Engine.
   Relationship records from Relationship Engine.
   Event records from Event Engine.
   Temporal annotations from Temporal Engine.
   Spatial annotations from Spatial Engine.

Stage 2: Knowledge Graph Update
   Knowledge Engine integrates new information into the knowledge graph:
   - New facts are asserted (with confidence level).
   - Existing facts are updated (previous version archived).
   - Conflicting facts trigger a resolution protocol.
   - Relationships between entities are updated.

Stage 3: Regime Detection
   Knowledge Engine applies market regime classification:
   - BULL, BEAR, SIDEWAYS, HIGH_VOLATILITY, LOW_VOLATILITY, CRISIS
   Regime classification is based on multi-factor analysis:
   - NIFTY trend (5d, 20d, 50d moving average relationships)
   - VIX level
   - Market breadth
   - Sector rotation pattern
   - Global context (S&P, Nikkei, bonds, FX)

Stage 4: Cache Refresh
   5-minute cache is refreshed with new knowledge snapshot.
   Cache invalidation for specific entities when significant changes detected.
   Knowledge freshness timestamps updated.

Stage 5: Knowledge Ready Signal
   KNOWLEDGE_UPDATED signal broadcast to:
   - State Engine (for state re-evaluation)
   - Prediction Engine (for prediction refresh triggers)
   - Master Orchestrator (for workflow progression)
`

---

### WF-SYS-06 — PREDICTION FLOW WORKFLOW

**Purpose:** Generate calibrated investment predictions from current knowledge
that serve as the primary input to the Decision Engine.

**Trigger:** KNOWLEDGE_UPDATED signal; also on 5-minute scheduled cycle.

**Stages:**

`
Stage 1: Prediction Request
   Master Orchestrator triggers prediction cycle.
   Prediction Engine reads current knowledge snapshot from cache.

Stage 2: Model Selection
   Prediction Engine identifies applicable models for current regime:
   - Regime-specific models loaded (BULL/BEAR/SIDEWAYS etc.)
   - Model health scores checked (only HEALTHY models used)
   - Ensemble configuration applied

Stage 3: Feature Generation
   Prediction Engine requests features from Knowledge Engine:
   - Price-based features (momentum, trend, mean-reversion signals)
   - Options-based features (implied volatility, skew, term structure)
   - Macro features (breadth, rotation, global correlation)
   - Event features (upcoming catalysts, recent corporate actions)

Stage 4: Prediction Generation
   Models applied to feature vectors.
   Raw predictions generated for each candidate instrument.
   Each prediction includes: direction, magnitude estimate, confidence [0.0-1.0],
   time horizon, prediction model ID.

Stage 5: Prediction Calibration
   Prediction Engine applies calibration curves (from Learning Engine).
   Calibrated confidence = f(raw confidence, model history, regime match).

Stage 6: Prediction Persistence
   All predictions persisted with full provenance.

Stage 7: Prediction Broadcast
   PREDICTIONS_READY signal sent to Decision Engine and Risk Engine.
   Predictions available for 5-minute validity window.
`

---

### WF-SYS-07 — DECISION FLOW WORKFLOW

**Purpose:** Integrate predictions, risk assessments, and portfolio state into
governed investment decision recommendations.

**Trigger:** PREDICTIONS_READY signal; also on explicit DECISION_REQUEST from
portfolio management.

**Preconditions:** Valid DAILY_SESSION_CERTIFICATE; Governance Engine HEALTHY;
PREDICTIONS_READY within last 5 minutes.

**Stages:**

`
Stage 1: Candidate Assembly
   Decision Engine assembles decision candidates:
   - Instruments with prediction confidence >= threshold
   - Instruments not blocked by active cooldown (30-minute gap)
   - Instruments within strategy universe

Stage 2: Risk Pre-filter
   Risk Engine receives candidate list.
   Risk Engine applies pre-filters:
   - VaR budget available for each candidate?
   - Portfolio correlation constraints satisfied?
   - Strategy-level drawdown limits not breached?
   - Daily loss budget not exhausted?
   Blocked candidates removed from list.

Stage 3: Decision Scoring
   Decision Engine scores each remaining candidate:
   Decision Score = weighted sum:
     - Prediction confidence score (weight: 35%)
     - Risk-adjusted return estimate (weight: 25%)
     - Market regime alignment (weight: 20%)
     - Strategy conviction score (weight: 15%)
     - Historical pattern score (weight: 5%)
   Threshold: Decision Score >= 6.5/10.0 to proceed.

Stage 4: Multi-Agent Debate
   Candidates with score >= 6.5 enter the 5-agent debate:
   - Analyst Agent (technical view)
   - Fundamentals Agent (fundamental view)
   - Risk Agent (risk view)
   - Macro Agent (macro view)
   - Devil's Advocate Agent (challenges the thesis)
   Debate produces consensus score adjustment [+/- 1.5].

Stage 5: Governance Authorization
   Decision Engine submits top candidates to Governance Engine.
   Governance Engine checks:
   - Daily loss limit (< 2%) not already breached
   - VIX <= 45
   - No active governance override blocking the instrument
   - Decision score >= 6.5
   Authorization result: APPROVED, BLOCKED, or CONDITIONAL.

Stage 6: Decision Record Creation
   For each approved decision:
   - Decision Record created with full provenance trail
   - Decision ID assigned (ODEC-{YYYYMMDD}-{SEQ:08d})
   - Routed to execution path

Stage 7: Broadcast
   DECISION_APPROVED event broadcast.
   Decision Record archived permanently.
`

---

### WF-SYS-08 — RISK FLOW WORKFLOW

**Purpose:** Define continuous risk monitoring and the risk assessment that
gates every investment decision.

**Trigger:** Continuous (every 30 seconds); also triggered by DECISION_REQUEST
and by market event signals (VIX spikes, circuit breakers).

**Stages:**

`
Stage 1: Portfolio Risk Snapshot
   Risk Engine computes current portfolio risk metrics:
   - Current daily P&L vs daily loss limit (2%)
   - Current open positions vs position limits
   - Portfolio VaR (1-day 95% confidence)
   - Gross exposure vs gross limit
   - Sector concentration vs sector limits

Stage 2: Market Risk Assessment
   Risk Engine reads from Knowledge Engine:
   - VIX level (kill switch at VIX > 45)
   - Market breadth (broad-market risk proxy)
   - Correlation matrix (current inter-asset correlations)
   - Regime classification (risk budget adjusted per regime)

Stage 3: Strategy-Level Risk
   For each active strategy:
   - Current drawdown vs max allowed drawdown (15%)
   - Win rate vs minimum acceptable (50%)
   - Active position count vs strategy limit

Stage 4: Kill Switch Evaluation
   Risk Engine evaluates kill switch conditions:
   - Daily loss >= 2%: HALT (hard stop, no new decisions)
   - VIX > 45: HALT (external crisis protection)
   - Individual strategy drawdown >= 15%: disable that strategy
   - Any kill switch triggered: forward to Governance Engine for confirmation

Stage 5: Risk Budget Update
   Risk Engine updates available risk budget for each strategy.
   Budget consumed by open positions is subtracted.
   Remaining budget communicated to Decision Engine and Portfolio Engine.

Stage 6: Risk Health Broadcast
   RISK_UPDATE signal broadcast with current metrics.
   RISK_ALERT if any metric crosses warning threshold.
   RISK_HALT if kill switch triggered.
`

---

### WF-SYS-09 — PORTFOLIO FLOW WORKFLOW

**Purpose:** Manage portfolio state, track positions, update allocations, and
provide portfolio context to Risk and Decision engines.

**Trigger:** Every 60 seconds; after every DECISION_APPROVED event; after every
TRADE_EXECUTED event.

**Stages:**

`
Stage 1: Position Reconciliation
   Portfolio Engine reads current position state from State Engine.
   Reconciles against execution confirmations received.
   Flags any discrepancies as P2 incidents.

Stage 2: P&L Calculation
   Portfolio Engine calculates current P&L:
   - Open P&L: mark-to-market on all open positions
   - Realized P&L: from closed positions today
   - Total P&L: open + realized
   - P&L communicated to Risk Engine for daily loss limit check.

Stage 3: Allocation Update
   Portfolio Engine updates strategy-level allocations:
   - Capital allocated vs capital used per strategy
   - Available capital per strategy for new positions
   - Total portfolio utilization

Stage 4: Exposure Analysis
   Portfolio Engine computes exposure breakdown:
   - Long vs short gross exposure
   - Sector-level net exposure
   - Options delta exposure
   - Instrument-level concentration

Stage 5: Portfolio Signal
   Portfolio Engine broadcasts PORTFOLIO_STATE_UPDATED signal.
   State Engine updates portfolio state object.
   Risk Engine reads updated portfolio state.
   Master Orchestrator receives acknowledgment.
`

---

### WF-SYS-10 — STRATEGY FLOW WORKFLOW

**Purpose:** Manage the selection, activation, monitoring, and retirement of
investment strategies during an IIOS session.

**Trigger:** Pre-market (strategy initialization at T-30); also triggered by
STRATEGY_HEALTH_ALERT and by REGIME_CHANGE events.

**Stages:**

`
Stage 1: Strategy Universe Load
   Strategy Engine loads all ACTIVE strategies from persistence.
   For each strategy: loads parameters, last performance metrics, current drawdown.
   Strategies not meeting minimum criteria flagged as SUSPENDED.

Stage 2: Regime Alignment
   Strategy Engine reads current regime from Knowledge Engine.
   Applies regime-strategy compatibility matrix:
   - Which strategies perform in BULL regime?
   - Which strategies perform in HIGH_VOLATILITY regime?
   - Weight adjustments per regime match.
   Incompatible strategies temporarily suspended.

Stage 3: Pre-session Validation
   Governance Engine validates all active strategies before session start:
   - Evidence dossier present and not expired?
   - Risk parameters within constitutional limits?
   - No pending compliance issues?
   Strategies failing governance validation are BLOCKED for the session.

Stage 4: Intraday Strategy Monitoring
   Every 5 minutes during INTRADAY_ACTIVE state:
   Strategy Engine evaluates each active strategy:
   - Current drawdown vs 15% limit
   - Win rate today vs 50% minimum
   - Signal quality metrics
   Strategy auto-disable if drawdown >= 15% or consecutive losses >= threshold.

Stage 5: Strategy Signal Generation
   Active strategies generate trade signals:
   - Entry signals: instrument, direction, size, rationale
   - Exit signals: position to close, rationale
   Signals forwarded to Decision Engine as prediction inputs.

Stage 6: End-of-Session Learning
   Strategy Engine collects session performance metrics.
   Forwards to Learning Engine for model update cycle.
`

---

### WF-SYS-11 — LEARNING FLOW WORKFLOW

**Purpose:** Update prediction models, strategy parameters, and knowledge
representations from observed outcomes. All learning is isolated from live
operations until validated.

**Trigger:** End-of-session (post 15:30 IST); also triggered weekly for
deep learning cycles.

**Stages:**

`
Stage 1: Outcome Collection
   Learning Engine collects all trade outcomes from the current session.
   Each outcome is attributed to the Decision Record that produced it.
   Outcome record: actual result vs predicted result, actual P&L, slippage.

Stage 2: Prediction Error Analysis
   For each outcome:
   - Prediction Engine error computed (predicted direction vs actual)
   - Confidence calibration error computed
   - Feature importance retrospective computed
   All errors stored in learning evidence database.

Stage 3: Model Update (STAGING ONLY)
   Learning Engine updates model parameters in STAGING environment only.
   Live models are NOT modified directly.
   Staging environment is isolated from all live trading paths.

Stage 4: Validation Gate
   Updated models must pass validation before promotion to live:
   - Out-of-sample accuracy check
   - Calibration quality check
   - Regime sensitivity check
   Validation is performed by the Simulation Engine (WF-SYS-12 sub-call).

Stage 5: Governance Approval
   Validated model updates submitted to Governance Engine.
   Governance Engine checks: consistent with constitutional limits?
   Not approved: staged model archived, discarded, log entry created.
   Approved: model promoted to live in next pre-market startup.

Stage 6: Knowledge Update
   Learning insights (not raw model parameters) are written back to Knowledge Engine:
   - Updated strategy performance beliefs
   - Regime-strategy compatibility updates
   - Entity-level signal quality updates
`

---

### WF-SYS-12 — SIMULATION FLOW WORKFLOW

**Purpose:** Evaluate strategies, models, and scenarios in a risk-free environment
before any live deployment. Produce evidence dossiers.

**Trigger:** Explicit request from Strategy Engine (strategy candidate evaluation);
from Learning Engine (model validation); from Governance Engine (pre-deployment verification).

**Stages:**

`
Stage 1: Simulation Request
   Requestor submits SimulationRequest with:
   - Target (strategy candidate, model update, scenario)
   - Requested simulation types (backtest, WFT, Monte Carlo, regime)
   - Historical data range
   - Random seed (for reproducibility)

Stage 2: Data Preparation
   Simulation Engine prepares historical knowledge snapshots.
   Data accessed through Knowledge Engine (historical query mode).
   No live market data is used in simulation.

Stage 3: Backtest Execution
   Strategy/model run against historical data.
   Per-trade P&L computed. Drawdown tracked. Win rate computed.
   Backtest metrics: Sharpe > 0.8, Win Rate >= 50%, Max Drawdown < 15%.

Stage 4: Walk-Forward Testing
   Historical data divided into in-sample / out-of-sample windows.
   Parameters calibrated on in-sample; evaluated on out-of-sample.
   Multiple WFT windows applied to reduce overfitting risk.

Stage 5: Monte Carlo Analysis
   1,000 scenario paths generated.
   Simulation Engine evaluates strategy across all paths.
   Tail risk estimated (5th percentile P&L, max drawdown distribution).

Stage 6: Evidence Dossier Production
   All simulation results compiled into Evidence Dossier.
   Dossier includes: backtest results, WFT results, Monte Carlo summary,
   promotion recommendation (PROMOTE / REJECT / CONDITIONAL).
   Dossier signed with Simulation Engine ID and timestamp.

Stage 7: Governance Submission
   Evidence Dossier forwarded to Governance Engine for final review.
`

---

### WF-SYS-13 — GOVERNANCE FLOW WORKFLOW

**Purpose:** Define the continuous governance cycle that monitors all operational
activities against constitutional rules and produces the authoritative session certificate.

**Trigger:** Pre-session (certificate issuance); every 5 minutes intraday;
on-demand for decision authorization.

**Stages:**

`
Pre-Session Governance (T-15 before market open):
   Governance Engine runs full compliance check:
   - All ACTIVE strategies have valid evidence dossiers (not older than 30 days)
   - No open compliance violations from previous sessions
   - Daily loss limit not pre-breached from overnight adjustments
   - All required engines report HEALTHY
   - VIX reading available and below 45
   Outcome: DAILY_SESSION_CERTIFICATE issued or startup blocked.

Intraday Governance (every 5 minutes):
   Governance Engine runs abbreviated compliance check:
   - VIX still below 45
   - Daily loss limit not breached
   - No kill-switch conditions
   - All active strategies within their drawdown limits
   Outcome: GOVERNANCE_CHECKPOINT_PASS or RISK_HALT trigger.

Decision Authorization (on each Decision Engine request):
   Governance Engine receives authorization request with:
   - Decision candidate details
   - Current portfolio state
   - Decision score
   Governance Engine checks:
   - Score >= 6.5 threshold
   - Risk Engine has not blocked this instrument
   - No compliance issue with the instrument
   Outcome: DECISION_AUTHORIZED or DECISION_BLOCKED.

Post-Session Governance:
   Governance Engine collects all session decisions and outcomes.
   Writes session governance report.
   Flags any constitutional violations for architect review.
   Archives session certificate and all decision records.
`

---

### WF-SYS-14 — SYSTEM SHUTDOWN WORKFLOW

**Purpose:** Gracefully shut down all IIOS engines in the reverse order of startup,
ensuring all state is persisted and all open positions are logged.

**Trigger:** End-of-session signal (15:30 IST); or operator-initiated shutdown;
or WF-SYS-17 (Emergency Stop) completion.

**Stages:**

`
Stage 1: Decision Engine Close (15:30)
   Decision Engine stops accepting new decision requests.
   All pending decisions cleared (no new executions).
   Decision log finalized.

Stage 2: Portfolio & Risk Snapshot
   Portfolio Engine takes final portfolio snapshot.
   Risk Engine takes final risk snapshot.
   Both snapshots persisted permanently.

Stage 3: Learning Trigger
   Master Orchestrator triggers WF-SYS-11 (Learning Flow).
   Session outcomes collected and forwarded to Learning Engine.
   Learning cycle runs post-market (non-blocking).

Stage 4: Governance Report
   Governance Engine writes session governance report.
   All decision records archived.
   Session certificate closed with end timestamp.

Stage 5: Knowledge Persistence
   Knowledge Engine persists full knowledge graph snapshot.
   5-minute cache cleared (will rebuild on next startup).

Stage 6: Engine Shutdown (reverse order)
   Governance Engine → Simulation Engine → Strategy Engine
   → Portfolio Engine → Risk Engine → Decision Engine
   → Learning Engine → Prediction Engine → State Engine
   → Knowledge Engine → Event Engine → Relationship Engine
   → Entity Engine → Temporal Engine → Spatial Engine
   → Information Engine

Stage 7: Database Persistence Final Flush
   All pending writes flushed to SQLite databases.
   Integrity checksums written.
   Backup triggered.
   System state = SHUTDOWN.
`

---

### WF-SYS-15 — RECOVERY WORKFLOW

**Purpose:** Restore IIOS from a partial failure state without modifying any
open positions or live investment decisions.

**Trigger:** OHS drops below CRITICAL (0.35); one or more P1 incidents triggered;
operator initiates RECOVERY mode.

**Core Constraint:** Recovery NEVER modifies open positions (constitutional rule
OCC-I-001 from IIOS-MO-ARCH-001). Recovery is coordination-only.

**Stages:**

`
Stage 1: Failure Assessment
   Master Orchestrator determines which engines are OFFLINE or DEGRADED.
   Classifies failure scope:
   - ISOLATED: single engine failed, rest healthy
   - PARTIAL: 2-4 engines affected
   - CRITICAL: 5+ engines affected or core engine down
   - CATASTROPHIC: coordination layer (Master Orchestrator) impaired

Stage 2: Safe Mode Activation
   Moves to SAFE mode: no new investment decisions permitted.
   Portfolio Engine continues monitoring open positions (read-only).
   Risk Engine continues monitoring risk (read-only).
   Governance Engine notified of SAFE mode entry.

Stage 3: Engine Recovery (ISOLATED and PARTIAL)
   For each OFFLINE engine (in startup order):
   - Attempt restart
   - Validate state restoration from persistence
   - Confirm health check passes
   - Re-register with Master Orchestrator
   If recovery succeeds: engine back in service.
   If recovery fails after 3 attempts: escalate to P1 incident.

Stage 4: Human Escalation (CRITICAL and CATASTROPHIC)
   P1 alert sent to operator via Telegram.
   Operator has 15-minute response window.
   Operator chooses: attempt full restart, or proceed to WF-SYS-17.

Stage 5: State Reconciliation
   After engines recovered:
   State Engine reconciles restored state vs actual state.
   Portfolio Engine reconciles position records.
   Any discrepancies flagged as unresolved incidents for operator review.

Stage 6: OHS Recovery Verification
   Master Orchestrator recomputes OHS.
   OHS >= 0.60 (DEGRADED): resume operations in DEGRADED mode.
   OHS >= 0.80 (NOMINAL): resume full operations.
   OHS < 0.60: remain in SAFE mode; notify operator.
`

---

### WF-SYS-16 — MAINTENANCE WORKFLOW

**Purpose:** Define scheduled maintenance activities that preserve IIOS health
without impacting market-hours operations.

**Trigger:** Scheduled (weekday post-session; weekend deep maintenance).

**Stages:**

`
Post-Session Daily (after WF-SYS-14, ~16:00–18:00 IST):
   - Database compaction and integrity verification
   - Log rotation and archival
   - Knowledge graph optimization
   - Prediction model performance review
   - Governance report generation
   - Backup verification

Weekly (Saturday, after market close):
   - Strategy performance deep review
   - Walk-Forward Test refresh for all active strategies
   - Learning cycle completion verification
   - Risk model recalibration
   - Security audit log review
   - Evidence dossier expiry check (30-day limit)

Monthly:
   - Full system health baseline measurement
   - Architecture compliance review
   - Constitution amendment review (if any pending)
   - Capacity planning review
   - Ontology version check
`

---

### WF-SYS-17 — EMERGENCY STOP WORKFLOW

**Purpose:** Immediately halt all new investment activity in response to a
critical risk condition.

**Trigger:** VIX > 45; Daily loss >= 2%; Operator EMERGENCY_STOP command;
critical system failure during INTRADAY_ACTIVE state.

**Execution is immediate; no approval required for the halt itself.**

**Stages:**

`
T+0 seconds: Kill Switch Triggers
   Risk Engine or Governance Engine detects kill-switch condition.
   EMERGENCY_STOP signal sent to Master Orchestrator.

T+1 second: Decision Engine locked
   Decision Engine stops all pending decision evaluation.
   No new decisions can enter the queue.

T+2 seconds: Portfolio Engine locked
   Portfolio Engine enters READ-ONLY mode.
   No new execution orders permitted.

T+5 seconds: Operator Alert
   Telegram P1 alert sent to operator with condition details.

T+30 seconds: State recorded
   Full system state snapshot taken.
   Emergency Stop Event written to permanent audit log.
   System state = EMERGENCY_STOP.

T+indefinite: Open Positions
   Open positions remain open (IIOS does not auto-liquidate).
   Risk Engine continues monitoring existing positions.
   Operator must make liquidation decision manually.

Resolution:
   Operator reviews condition.
   If condition resolved: manual restart of WF-SYS-01 required.
   If overnight: system waits for next day startup with operator approval.
`

---

### WF-SYS-18 — HUMAN OVERRIDE WORKFLOW

**Purpose:** Define the controlled process by which a human operator overrides
an IIOS decision or parameter within constitutional constraints.

**Constitutional Constraint:** No override can violate a constitutional rule.
No override can change the daily loss limit, VIX threshold, or constitutional
kill switch conditions.

**Stages:**

`
Stage 1: Override Request
   Operator submits override via authorized interface.
   Override types permitted:
   - Block a specific instrument from trading today
   - Reduce position size for a specific strategy today
   - Suspend a specific strategy for the session
   - Change an operational parameter (within policy bounds)
   - Extend or reduce session hours

Stage 2: Override Validation
   Governance Engine receives override request.
   Validates: override type is permitted; no constitutional rule violated;
   requestor has authorized role.
   Invalid override: rejected with explanation logged.
   Valid override: proceeds to Stage 3.

Stage 3: Override Application
   Governance Engine applies override to the OC-22 Configuration Manager.
   Affected engines notified of parameter change.
   Override effective immediately.

Stage 4: Override Audit
   Override record written permanently:
   - Operator ID, timestamp, override type, justification (if provided)
   - Before/after state
   - Authorization level

Stage 5: Override Expiry
   All operational overrides expire at session end.
   Parameter overrides require re-confirmation at next startup.
   No override persists silently.
`

---

## PART IV — GLOBAL ENGINE INTERACTION MATRIX

### 4.1 Matrix Overview

The Global Engine Interaction Matrix maps every engine-to-engine relationship
across the 18 IIOS engines. For each pair, the matrix defines:
P = Producer (sends data or signals)
C = Consumer (receives data or signals)
B = Bidirectional
— = No direct interaction (accessed through intermediary)

`
INTERACTION MATRIX (rows = source, columns = target)
Engines:  DB  INF ENT REL EVT TMP SPA KNW STE PRD LRN DEC RSK PFO STG SIM GOV MO

DB        --  P   P   P   P   P   P   P   P   P   P   P   P   P   P   P   P  P
INF       C   --  P   P   P   P   P   P   —   —   —   —   —   —   —   —   —  C
ENT       C   B   --  P   P   P   B   P   P   —   —   —   —   —   —   —   —  C
REL       C   C   B   --  P   —   —   P   —   —   —   —   —   —   —   —   —  C
EVT       C   C   B   C   --  B   —   P   P   —   —   —   —   —   —   —   —  C
TMP       C   C   C   —   B   --  —   P   P   P   —   —   —   —   —   —   —  C
SPA       C   C   B   —   —   —   --  P   —   —   —   —   —   —   —   —   —  C
KNW       C   C   C   C   C   C   C   --  B   P   P   P   P   P   P   P   P  C
STE       C   —   C   —   C   C   —   B   --  P   P   P   P   P   P   P   —  C
PRD       C   —   —   —   C   C   —   C   C   --  B   P   P   —   C   C   —  C
LRN       C   —   —   —   —   —   —   B   C   B   --  —   —   —   P   C   C  C
DEC       C   —   —   —   —   —   —   C   —   C   —   --  C   C   C   —   B  C
RSK       C   —   —   —   —   —   —   C   C   C   —   B   --  B   P   C   C  C
PFO       C   —   —   —   —   —   —   C   C   —   —   B   B   --  —   —   —  C
STG       C   —   —   —   —   —   —   C   —   C   C   C   C   —   --  B   C  C
SIM       C   —   —   —   —   —   —   C   C   C   C   —   C   —   B   --  C  C
GOV       C   —   —   —   —   —   —   C   —   —   C   B   C   —   C   C   --  C
MO        C   C   C   C   C   C   C   C   C   C   C   C   C   C   C   C   C   --
`

Key: DB=Database, INF=Information, ENT=Entity, REL=Relationship, EVT=Event,
TMP=Temporal, SPA=Spatial, KNW=Knowledge, STE=State, PRD=Prediction,
LRN=Learning, DEC=Decision, RSK=Risk, PFO=Portfolio, STG=Strategy,
SIM=Simulation, GOV=Governance, MO=Master Orchestrator

---

### 4.2 Detailed Producer-Consumer Profiles

Each section below defines one engine's complete interaction profile.

---

**ENGINE: INFORMATION ENGINE (INF)**

Produces for:
- Entity Engine: raw entity property updates (prices, volume, fundamentals)
- Relationship Engine: correlation data, sector membership data
- Event Engine: raw event signals (corporate actions, news flags)
- Knowledge Engine: validated InformationObjects for knowledge graph
- Database: persists all received and classified information

Consumes from:
- Database: historical reference data for validation
- Master Orchestrator: control signals (start, stop, configuration)

Communication Direction: Primarily outbound (data flow source)
Priority: CRITICAL (data starvation immediately impacts all downstream engines)

Failure Impact:
  MINOR (<30s outage): downstream engines use cached data; transparent.
  MODERATE (30s–5min): Knowledge Engine cache stale; prediction quality degrades.
  SEVERE (>5min): all predictions invalid; SAFE mode activation.

Recovery Behaviour: Restart within 60 seconds; state reconstructed from Database;
no manual intervention required for outage < 5 minutes.

---

**ENGINE: ENTITY ENGINE (ENT)**

Produces for:
- Relationship Engine: entity records for relationship computation
- Event Engine: entity records for event attribution
- Knowledge Engine: entity nodes for knowledge graph
- Spatial Engine: entity geographic records

Consumes from:
- Information Engine: raw entity property updates
- Database: historical entity records

Communication Direction: Bidirectional with Relationship Engine, Spatial Engine.
Priority: HIGH

Failure Impact: Knowledge Engine cannot update entity nodes; knowledge graph
becomes stale for the affected entities. Prediction accuracy degrades for
stale entities.

---

**ENGINE: RELATIONSHIP ENGINE (REL)**

Produces for:
- Knowledge Engine: relationship edges for knowledge graph

Consumes from:
- Entity Engine: entity records (endpoints of relationships)
- Information Engine: correlation data for relationship weights

Communication Direction: Inbound-heavy; produces only to Knowledge Engine.
Priority: NORMAL

Failure Impact: Knowledge Engine loses relationship updates; correlation
and causality signals degrade. Impact is gradual; critical only after
2+ hours of outage.

---

**ENGINE: EVENT ENGINE (EVT)**

Produces for:
- State Engine: events that trigger state transitions
- Knowledge Engine: event records for knowledge graph

Consumes from:
- Entity Engine: entity context for event attribution
- Temporal Engine: time context for event timestamps
- Information Engine: raw event signals

Communication Direction: Bidirectional with Temporal Engine.
Priority: HIGH (event detection must be real-time)

Failure Impact: State transitions missed; regime changes not detected.
Decision Engine may miss critical market signals.

---

**ENGINE: TEMPORAL ENGINE (TMP)**

Produces for:
- Knowledge Engine: temporal annotations for all knowledge objects
- State Engine: market session state updates (OPEN, CLOSED, PRE_MARKET)
- Prediction Engine: time horizon references

Consumes from:
- Database: historical calendar data
- Event Engine: market event time anchors

Communication Direction: Primarily outbound (time context provider).
Priority: CRITICAL (all time-dependent operations rely on Temporal Engine)

Failure Impact: System time references become unreliable. Predictions
lose their time horizon. Scheduler may malfunction.

---

**ENGINE: KNOWLEDGE ENGINE (KNW)**

Produces for:
- State Engine: knowledge facts for state evaluation
- Prediction Engine: knowledge snapshots (features, context)
- Learning Engine: historical knowledge for model training
- Decision Engine: knowledge context for decision scoring
- Risk Engine: market knowledge for risk assessment
- Portfolio Engine: entity knowledge for portfolio valuation
- Strategy Engine: regime and signal knowledge for strategy selection
- Simulation Engine: historical knowledge for backtesting
- Governance Engine: compliance-relevant knowledge

Consumes from: ALL data-layer and ontology-layer engines.
5-minute cache reduces direct load from prediction and decision engines.

Communication Direction: Bidirectional with State Engine (knowledge informs state; state informs knowledge updates).
Priority: CRITICAL

Failure Impact:
  30s: cached data serves all consumers; no impact.
  5min: cache stale; all predictions use stale context.
  30min: SAFE mode; prediction and decision engines shut down.

---

**ENGINE: STATE ENGINE (STE)**

Produces for:
- Prediction Engine: current state context for feature generation
- Learning Engine: state sequences for model training
- Decision Engine: system state validation (is trading permitted?)
- Risk Engine: risk-relevant states (open positions, exposure states)
- Portfolio Engine: portfolio position state

Consumes from:
- Knowledge Engine: knowledge facts that drive state transitions
- Event Engine: events that trigger state transitions
- Temporal Engine: time-based state transitions (market open/close)

Communication Direction: Bidirectional with Knowledge Engine.
Priority: HIGH

Failure Impact: System loses state tracking. Risk Engine cannot
validate position states. Portfolio Engine cannot reconcile positions.

---

**ENGINE: PREDICTION ENGINE (PRD)**

Produces for:
- Decision Engine: prediction objects with confidence and direction
- Risk Engine: predictive risk signals (expected volatility)

Consumes from:
- Knowledge Engine: knowledge snapshots (features and context)
- State Engine: current state for state-conditional predictions
- Temporal Engine: time horizon management
- Event Engine: upcoming events for event-driven prediction

Communication Direction: Bidirectional with Learning Engine (receives model updates).
Priority: HIGH

Failure Impact: Decision Engine loses prediction inputs; cannot score candidates.
Decisions blocked until Prediction Engine recovers.

---

**ENGINE: LEARNING ENGINE (LRN)**

Produces for:
- Prediction Engine: model parameter updates (after Governance approval)
- Strategy Engine: strategy performance insights

Consumes from:
- Knowledge Engine: historical data for model training
- State Engine: historical state sequences for state-model training
- Prediction Engine: prediction errors for calibration

Communication Direction: Bidirectional with Prediction Engine (tightly coupled).
Priority: NORMAL (operates primarily post-market; non-critical during trading hours)

Failure Impact: Model improvements delayed. No immediate impact on live trading.

---

**ENGINE: DECISION ENGINE (DEC)**

Produces for:
- Governance Engine: decision authorization requests
- Portfolio Engine: approved investment decisions
- Risk Engine: decision candidates for pre-filter

Consumes from:
- Prediction Engine: predictions for scoring
- Risk Engine: available risk budget, position limits
- Knowledge Engine: knowledge context for scoring
- Portfolio Engine: current portfolio state

Communication Direction: Bidirectional with Governance Engine (authorization request/response).
Priority: HIGH

Failure Impact: IIOS cannot produce new investment decisions. No immediate
risk to open positions. Degrades to monitoring-only mode.

---

**ENGINE: RISK ENGINE (RSK)**

Produces for:
- Decision Engine: risk budget, position limits, blocked instruments
- Portfolio Engine: risk metrics, P&L attribution

Consumes from:
- Knowledge Engine: market data for VaR and VIX calculation
- State Engine: current position states
- Prediction Engine: predictive volatility signals
- Portfolio Engine: current portfolio allocations

Communication Direction: Bidirectional with Portfolio Engine.
Priority: CRITICAL (kill-switch logic lives here)

Failure Impact: Kill-switch cannot fire. Risk limits cannot be enforced.
Immediate SAFE mode required on Risk Engine failure.

---

**ENGINE: PORTFOLIO ENGINE (PFO)**

Produces for:
- Risk Engine: current portfolio allocations and P&L
- Decision Engine: available capital per strategy

Consumes from:
- Risk Engine: position limits and risk metrics
- Decision Engine: approved decisions (position updates)
- Knowledge Engine: entity prices for mark-to-market
- State Engine: execution confirmations for reconciliation

Communication Direction: Bidirectional with Risk Engine.
Priority: HIGH

Failure Impact: Portfolio state becomes untracked. Risk Engine
loses allocation data. SAFE mode required.

---

**ENGINE: STRATEGY ENGINE (STG)**

Produces for:
- Decision Engine: trade signal candidates
- Simulation Engine: strategy candidates for evaluation

Consumes from:
- Knowledge Engine: regime, signals, and performance data
- Prediction Engine: prediction signals as strategy inputs
- Risk Engine: per-strategy risk limits
- Learning Engine: strategy performance updates
- Simulation Engine: evidence dossiers (consumes back from Simulation)

Communication Direction: Bidirectional with Simulation Engine.
Priority: HIGH

---

**ENGINE: SIMULATION ENGINE (SIM)**

Produces for:
- Strategy Engine: evidence dossiers for strategy candidates
- Governance Engine: simulation evidence for compliance review
- Learning Engine: out-of-sample validation results

Consumes from:
- Strategy Engine: strategy candidates
- Risk Engine: risk constraints for simulation
- Knowledge Engine: historical data for backtesting
- State Engine: historical states for state-conditional backtests

Communication Direction: Bidirectional with Strategy Engine.
Priority: NORMAL (non-critical during trading hours; critical pre-deployment)

---

**ENGINE: GOVERNANCE ENGINE (GOV)**

Produces for:
- Decision Engine: decision authorization certificates
- Master Orchestrator: session certificates and halt signals
- All engines: compliance compliance status

Consumes from:
- Knowledge Engine: compliance-relevant facts
- Decision Engine: decision requests for authorization
- Simulation Engine: evidence dossiers for strategy approval
- Learning Engine: model update approvals

Communication Direction: Bidirectional with Decision Engine (authorization loop).
Priority: CRITICAL (nothing authorizes without Governance Engine)

Failure Impact: No new decisions can be authorized. Immediate SAFE mode.

---

**ENGINE: MASTER ORCHESTRATOR (MO)**

Produces for: All engines (control signals, configuration, lifecycle events)
Consumes from: All engines (health signals, workflow completion events)

Priority: CRITICAL
Communication Direction: Bidirectional with all engines.

Failure Impact: CATASTROPHIC — entire system loses coordination.
Automatic standby mode activation required.

---

### 4.3 Failure Cascade Analysis

This section maps how a single engine failure cascades through IIOS.

| Failed Engine    | Immediate Impact                    | Secondary Impact                | Recovery Window |
|-----------------|-------------------------------------|---------------------------------|----------------|
| Database         | All engines lose persistence        | All engines degrade to in-memory only | < 5 min |
| Information Eng  | Data starvation after cache expiry  | Knowledge stale, predictions degrade | < 5 min |
| Temporal Engine  | Time references unreliable          | Predictions lose time horizons  | < 2 min |
| Knowledge Engine | All intelligence loses context      | Predictions invalid after 5 min | SAFE mode |
| State Engine     | Position states untracked           | Risk cannot validate limits     | < 5 min |
| Prediction Engine| Decision Engine inputs lost         | No new decisions; monitoring only | < 5 min |
| Risk Engine      | Kill-switch disabled                | IMMEDIATE SAFE MODE required    | < 2 min |
| Decision Engine  | No new investment decisions         | Open positions unaffected       | < 5 min |
| Governance Engine| No decision authorization           | IMMEDIATE SAFE MODE required    | < 2 min |
| Portfolio Engine | Portfolio state untracked           | Risk loses allocation data      | < 5 min |
| Master Orchestr. | All coordination lost               | CATASTROPHIC; standby mode      | Manual restart |

---

## PART V — GLOBAL DATA AND KNOWLEDGE FLOW

### 5.1 Primary Data Flow Architecture

The IIOS data flow is not a simple linear pipeline. It is a directed graph with
feedback loops, caches, and asynchronous update channels. The primary flow
goes from raw observation through knowledge integration to decision output. The
secondary flow carries learning feedback back to improve prediction models.
The governance flow runs parallel, observing everything.

`
PRIMARY FLOW:
============

[Market Data Sources]                      [Governance Engine]
      |                                          |
      | (raw data)                              | (observes all flows)
      v                                          |
[Information Engine]                            |
      |                                          |
      | (InformationObjects)                     |
      v                                          |
+----+----+----+----+----+                       |
|ENT |REL |EVT |TMP |SPA |                       |
+----+----+----+----+----+                       |
      |    |    |    |    |                       |
      v    v    v    v    v                       |
[      KNOWLEDGE ENGINE (5-min cache)      ] <---+
             |
     (knowledge snapshot)
             |
      +------+------+
      v             v
[STATE ENGINE]  [PREDICTION ENGINE]
      |               |
(current state)  (predictions + confidence)
      |               |
      +-------+-------+
              |
        [RISK ENGINE] <---> [PORTFOLIO ENGINE]
              |
        (risk budget, limits)
              |
        [DECISION ENGINE] <--> [GOVERNANCE ENGINE]
              |
        (authorized decisions)
              |
        [MASTER ORCHESTRATOR]
              |
        EXECUTION OUTPUT

SECONDARY FLOW (Learning Feedback):
===================================

[Execution Outcomes]
       |
       v
[LEARNING ENGINE]
   |         |
   | (model  | (insights)
   | updates)|
   v         v
[PREDICTION][KNOWLEDGE ENGINE]
   ENGINE   (performance beliefs updated)
`

---

### 5.2 The Observation-to-Decision Chain

The complete chain from raw market tick to authorized investment decision
involves exactly these steps, in this order, with no shortcuts permitted:

`
Step 1:  Raw data received by Information Engine
Step 2:  Quality assessment and classification in Information Engine
Step 3:  Typed InformationObject persisted and distributed
Step 4:  Entity Engine updates entity properties
Step 5:  Event Engine detects and classifies any events
Step 6:  Temporal Engine annotates with time context
Step 7:  Relationship Engine updates relationship weights
Step 8:  Knowledge Engine integrates into knowledge graph
Step 9:  Knowledge Engine refreshes 5-minute cache
Step 10: State Engine updates entity and system states
Step 11: Prediction Engine generates predictions from knowledge snapshot
Step 12: Risk Engine assesses risk for prediction-driven candidates
Step 13: Decision Engine assembles candidates and scores them
Step 14: Multi-agent debate on candidates scoring >= 6.5
Step 15: Decision Engine requests authorization from Governance Engine
Step 16: Governance Engine validates and issues authorization certificate
Step 17: Decision Record created with full provenance trail
Step 18: Master Orchestrator routes authorized decision to execution
`

**Total nominal chain latency (per WF-SYS-07 design):**
Steps 1-9: ~17ms (Knowledge Engine with cache in 5-min cycle)
Steps 10-12: ~15ms
Steps 13-16: ~140ms (includes debate + governance check)
Total: ~172ms per cycle

---

### 5.3 Knowledge Accumulation Loop

IIOS accumulates knowledge with every market session. The knowledge graph
grows as new entities, relationships, events, and temporal patterns are observed.
This is the basis for IIOS's improving intelligence over time.

`
Session N Knowledge State
        |
        v
Session N market data observed
        |
        v
New entities discovered
New relationships inferred
New events recorded
New temporal patterns noted
        |
        v
Knowledge Engine integrates all new observations
        |
        v
Session N+1 Knowledge State (richer than Session N)
        |
        v
Prediction Engine has more context for Session N+1 predictions
Decision Engine has more historical precedents to reference
Risk Engine has more accurate risk models
`

**Knowledge accumulation metrics (design targets):**
- Entity count grows by ~50 entities per month (new stocks, events, corporate actions)
- Relationship count grows by ~500 per month (new correlations, sector updates)
- Event count grows by ~200 per month (corporate, macro, market events)
- Knowledge graph completeness improves with time asymptotically toward full coverage

---

### 5.4 Learning Feedback Loop

The Learning Engine creates a closed-loop improvement cycle:

`
LEARNING FEEDBACK LOOP:
=======================

[Trade Outcomes]
     |
     v
[LEARNING ENGINE — Outcome Attribution]
     |
     | "For Decision ODEC-20260704-00001234,
     |  predicted direction was UP (confidence 0.72).
     |  Actual outcome was DOWN. Loss = -0.8%."
     v
[LEARNING ENGINE — Error Analysis]
     |
     | Which features predicted wrongly?
     | Which regime was this? (BULL)
     | Which model made this prediction? (MOD-BULL-MOMENTUM-v3)
     v
[LEARNING ENGINE — Model Update (STAGING)]
     |
     | MOD-BULL-MOMENTUM-v3 parameters updated.
     | Staging model validated vs out-of-sample data.
     v
[GOVERNANCE ENGINE — Update Approval]
     |
     | Updated model consistent with constitutional limits?
     | Evidence dossier shows improvement?
     v
[PREDICTION ENGINE — Model Promotion]
     |
     | MOD-BULL-MOMENTUM-v4 promoted to live.
     | Previous version archived.
     v
[Improved Predictions in Next Session]
`

---

### 5.5 Governance Integration Points

The Governance Engine integrates with every major data flow at defined
checkpoints. These checkpoints are non-bypassable.

`
Integration Point 1 — Pre-Session Certification:
Location: Between WF-SYS-01 Stage 7 and Stage 8.
Function: No session runs without a DAILY_SESSION_CERTIFICATE.

Integration Point 2 — Strategy Deployment Gate:
Location: Between Simulation Engine output and Strategy Engine activation.
Function: No strategy is activated without an approved evidence dossier.

Integration Point 3 — Decision Authorization:
Location: Between Decision Engine scoring and execution routing.
Function: No decision executes without DECISION_AUTHORIZED certificate.

Integration Point 4 — Model Update Approval:
Location: Between Learning Engine staging and Prediction Engine promotion.
Function: No model update is promoted without LEARNING_UPDATE_APPROVED.

Integration Point 5 — Kill-Switch Confirmation:
Location: Between Risk Engine halt signal and system SAFE mode.
Function: Kill-switch confirmation is double-checked by Governance Engine.

Integration Point 6 — Emergency Stop Authorization:
Location: At EMERGENCY_STOP trigger.
Function: Records the triggering condition for permanent audit.

Integration Point 7 — Human Override Validation:
Location: At every human override request.
Function: Validates override is constitutional before applying it.
`

---

## PART VI — SYSTEM GOVERNANCE

### 6.1 Governance Ownership Model

IIOS governance is organized as a three-tier ownership model:

**Tier 1 — Architecture Council:**
Responsible for: IIOS Constitution; engine architecture documents; ontology definitions.
Composition: Principal Architect + System Owner.
Authority: Can amend constitutional rules with 30-day review period.
Accountability: All architectural changes require Tier 1 sign-off.

**Tier 2 — Operations Lead:**
Responsible for: Operational parameters; session configuration; override authorization.
Authority: Can modify operational parameters within policy bounds (constitutional limits inviolable).
Accountability: All operational changes logged permanently; weekly review with Tier 1.

**Tier 3 — Automated Governance Engine:**
Responsible for: Real-time compliance monitoring; decision authorization; session certification.
Authority: Can block decisions, halt sessions, trigger SAFE mode.
Accountability: All Governance Engine decisions logged permanently; reviewed in weekly report.

---

### 6.2 Governance Responsibilities by Domain

**Knowledge Governance:**
- Ontology integrity is governed by Architecture Council.
- Knowledge graph accuracy is the responsibility of the Knowledge Engine.
- Knowledge provenance (source, timestamp, confidence) must accompany every fact.
- Knowledge conflicts are resolved by provenance quality (higher quality wins).

**Strategy Governance:**
- No strategy operates without an evidence dossier (Simulation Engine + Governance approval).
- Evidence dossiers expire after 30 days and must be renewed by re-simulation.
- Strategy parameters are immutable during live trading.
- Strategy retirement requires documented performance evidence, not just underperformance.

**Decision Governance:**
- Every decision requires a Decision Record with full provenance.
- Decisions below the 6.5 score threshold are prohibited.
- The 30-minute cooldown between decisions on the same instrument is a hard rule.
- No position size can exceed per-strategy risk budget.

**Risk Governance:**
- Daily loss limit (2%) is constitutional; cannot be overridden.
- VIX kill switch (> 45) is constitutional; cannot be overridden.
- Strategy-level drawdown limit (15%) is constitutional; cannot be overridden.
- Risk parameters are reviewed monthly by Operations Lead; amendments require Tier 1 approval.

**Learning Governance:**
- All model updates go through STAGING before LIVE promotion.
- No model is promoted without Simulation Engine validation.
- No model is promoted without Governance Engine approval.
- Learning outcomes are archived permanently; no learning is silently discarded.

---

### 6.3 Approval Framework

Every significant IIOS action is classified by required approval level:

`
CLASSIFICATION    APPROVER              EXAMPLES
=============     ========              ========
AUTOMATED         Governance Engine     Individual trade decision, intraday parameter change
OPERATIONAL       Operations Lead       Session override, strategy suspension, parameter bound change
ARCHITECTURAL     Architecture Council  New engine addition, ontology extension, constitution amendment
EMERGENCY         Operations Lead + Tier 1  Constitutional rule temporary relaxation (PROHIBITED in current design)
`

Note: Emergency classification exists for documentation completeness.
No mechanism exists in IIOS to relax constitutional rules operationally.
Constitutional amendment requires the full 30-day Architecture Council review.

---

### 6.4 Audit Framework

IIOS maintains a permanent, append-only audit record. Every audit event
is time-stamped, attributed, and cannot be modified after creation.

**Audit Layers:**

Layer 1 — Decision Audit: Every investment decision with full provenance trail.
Layer 2 — Governance Audit: Every governance action (certificate issue, authorization, override).
Layer 3 — Learning Audit: Every model update, promotion, and rejection.
Layer 4 — Operational Audit: Every operational parameter change.
Layer 5 — Incident Audit: Every P1–P4 incident with resolution details.
Layer 6 — Override Audit: Every human override with operator ID and justification.

**Audit Retention:** Indefinite. Audit records are never deleted.
**Audit Access:** Read-only after creation. No update or delete operations on audit tables.

---

### 6.5 Monitoring Framework

**Tier 1 — Real-Time Monitoring (30-second interval):**
- OHS (Orchestrator Health Score) calculated every 30 seconds.
- Kill-switch conditions monitored continuously (VIX, daily loss).
- Engine health heartbeats checked every 30 seconds.

**Tier 2 — Session Monitoring (5-minute interval):**
- Strategy-level performance monitored every 5 minutes.
- Intraday P&L vs daily limit checked every 5 minutes.
- Governance checkpoint run every 5 minutes.

**Tier 3 — Operational Monitoring (daily):**
- Session governance report generated post-session.
- Strategy performance report generated post-session.
- Evidence dossier expiry calendar reviewed.

**Tier 4 — Strategic Monitoring (weekly/monthly):**
- OQS (Orchestrator Quality Score) trend analyzed weekly.
- Model performance compared to baseline monthly.
- Risk model recalibration assessment monthly.

---

### 6.6 Security Framework

**Authentication:** All human operator actions require authenticated sessions.
No anonymous modifications are possible in the production environment.

**Authorization:** Role-based; three roles defined:
- READ: Can view all metrics and reports.
- OPERATIONAL: Can execute operational overrides within policy bounds.
- ARCHITECTURAL: Can modify architectural configuration; requires dual sign-off.

**Credential Management:** All credentials stored in the secrets manager (OC-22 Configuration Manager).
No credentials in code, configuration files, or audit logs.

**Communication Security:** All inter-engine communication occurs within the internal network boundary.
No engine is directly accessible from external networks.

**Audit Trail Integrity:** Audit tables use append-only access patterns.
Audit record integrity verified through hash chains at each session close.

---

### 6.7 Compliance Framework

**Market Compliance:**
- All investment decisions are within the defined regulatory framework.
- Position sizes respect SEBI reporting thresholds.
- Insider trading prevention: no event-driven decisions made on data that could constitute insider information.

**Operational Compliance:**
- VIX > 45 halt is a risk management requirement, not regulatory, but treated as constitutional.
- Daily loss limit is an internal control, not regulatory, but treated as constitutional.
- Strategy evidence requirements ensure no strategy operates on unvalidated assumptions.

**Data Compliance:**
- All market data usage complies with data provider terms of service.
- Personal data (operator identities) stored in compliance with applicable privacy regulations.

---

### 6.8 Recovery Governance

Recovery operations are subject to governance oversight:

**Recovery Authorization Levels:**
- ISOLATED recovery: automated (Master Orchestrator).
- PARTIAL recovery: automated with Tier 2 notification.
- CRITICAL recovery: requires Tier 2 authorization.
- CATASTROPHIC recovery: requires Tier 1 + Tier 2 authorization.

**Recovery Audit:**
Every recovery event produces a recovery record:
- Recovery ID: REC-{YYYYMMDD}-{SEQ:04d}
- Scope, duration, affected engines, resolution, operator.

**Post-Recovery Review:**
All CRITICAL and CATASTROPHIC recoveries trigger a formal post-incident review
within 48 hours.

---

### 6.9 Versioning Governance

**Architecture Document Versioning:**
- All architecture documents are version-controlled (semantic versioning: MAJOR.MINOR.PATCH).
- MAJOR: breaking change to public interfaces or constitutional rules.
- MINOR: additive change (new component, new workflow).
- PATCH: correction, clarification, documentation.

**Engine Configuration Versioning:**
- Operational parameters carry version numbers.
- Parameter history is retained permanently.
- Rollback to any previous version is possible within 30 days.

**Model Versioning:**
- All prediction models carry version numbers (e.g., MOD-BULL-MOMENTUM-v4).
- Previous versions are archived, not deleted.
- Each model version has an associated evidence dossier.

---

### 6.10 Lifecycle Governance

**Strategy Lifecycle:** NEW → CANDIDATE → SIMULATION → EVIDENCE_REVIEW → ACTIVE → MONITORING → SUSPENDED → RETIRED
**Engine Lifecycle:** REGISTERED → STARTING → HEALTHY → DEGRADED → RECOVERING → OFFLINE → DECOMMISSIONED
**Ontology Lifecycle:** DRAFT → REVIEW → APPROVED → PUBLISHED → DEPRECATED → ARCHIVED
**Model Lifecycle:** TRAINING → STAGING → VALIDATION → APPROVED → LIVE → MONITORING → RETIRED

Each lifecycle transition requires documented approval at the appropriate tier.

---

## PART VII — SYSTEM OPERATIONAL MODEL

### 7.1 Daily Operations

**Pre-Market Phase (08:00–09:15 IST):**

08:00 — Automated startup initiated (Windows Task Scheduler / cron).
         WF-SYS-01 begins.

08:00–08:15 — Foundation validation and data layer engine startup.
08:15–08:35 — Knowledge layer and state layer engine startup.
08:35–08:55 — Intelligence, financial, and governance engine startup.
09:00 — Governance Engine issues DAILY_SESSION_CERTIFICATE (or blocks startup).
09:00–09:15 — Final readiness check; OHS confirmed >= 0.80.
09:10 — Operator receives Telegram startup confirmation report.

**Market Hours Phase (09:15–15:30 IST):**

09:15:00 — WF-SYS-02 (Market Open) triggered by Temporal Engine.
09:15–15:30 — Continuous operation cycle:
  Every 30 seconds: WF-SYS-03 (Observation cycle)
  Every 5 minutes: WF-SYS-06 (Prediction cycle) + WF-SYS-13 (Governance check)
  Every 60 seconds: WF-SYS-09 (Portfolio update)
  Continuously: WF-SYS-08 (Risk monitoring)
  On signal: WF-SYS-07 (Decision flow)

**Post-Market Phase (15:30–18:00 IST):**

15:30 — WF-SYS-14 (System Shutdown) triggered.
15:30–16:00 — Learning flow triggered; session outcomes attributed.
16:00–17:00 — Learning Engine model update cycle.
17:00–18:00 — Database maintenance, log rotation, backup.
18:00 — System shutdown complete; all state persisted.

**Daily Monitoring Checklist (Tier 2 review, 15:45 IST):**
- Review session governance report
- Review any P1-P2 incidents from the day
- Confirm all strategies within performance bounds
- Confirm no evidence dossiers expiring in next 7 days
- Review decision accuracy metrics

---

### 7.2 Weekly Operations

**Saturday Morning Review (10:00–12:00 IST):**
- Full strategy performance review vs weekly baseline
- Walk-Forward Test refresh for any strategy showing degradation
- Evidence dossier expiry calendar update
- Risk model parameter review
- OQS trend analysis for the week
- Identify any strategies requiring re-simulation

**Saturday Maintenance (12:00–14:00 IST):**
- Database integrity verification
- Full backup to off-site storage
- Log archival for the week
- Security audit log review
- Model performance comparison: this week vs 4-week average

**Saturday Report Generation:**
- Weekly performance summary
- Model accuracy report
- Governance compliance report
- Incident summary (all P1-P4)
- Strategy health report

---

### 7.3 Monthly Operations

**First Saturday of Month (full-day event):**

Morning Block (09:00–12:00):
- Full system health baseline measurement vs prior month
- Risk model recalibration assessment
- All strategy evidence dossiers reviewed (30-day expiry check)
- Constitution compliance review (no rules violated this month?)

Afternoon Block (13:00–16:00):
- Capacity planning review (data storage growth, model complexity)
- Ontology version audit (any new concepts needed?)
- Integration test suite run on all engine interactions
- New strategy candidates reviewed for simulation eligibility

Evening Block (17:00–19:00):
- Monthly performance report finalization
- Architecture Council briefing document prepared
- Risk parameter amendment proposals (if any) prepared for Tier 1 review

---

### 7.4 Quarterly Operations

**First Monday of Quarter (Architecture Council Meeting):**
- Review all monthly reports from the quarter
- Constitution amendment proposals reviewed (30-day clock started if any)
- New engine proposals reviewed
- Ontology extension proposals reviewed
- Technology infrastructure review
- Risk parameter amendment review (requires Tier 1 approval)

**Quarterly Deep Simulation:**
- All active strategies re-simulated with most recent 12-month data window
- Evidence dossiers renewed for all active strategies
- Learning Engine deep training cycle run on full year data

---

### 7.5 Annual Operations

**Year-End Review (December 31):**
- Full IIOS architecture compliance audit
- All architecture documents version-reviewed
- System-wide performance attribution analysis
- Model versioning audit (identify any models not updated in >90 days)
- Ontology completeness assessment vs new instruments/markets considered

**Annual Strategy Retirement Assessment:**
Any strategy that has not met minimum performance criteria (Win Rate >= 50%,
Sharpe > 0.8) over the full calendar year is flagged for retirement.
Retirement requires documented evidence and Architecture Council approval.

---

### 7.6 Market Holiday Operations

**On market holidays, IIOS does not enter INTRADAY_ACTIVE state.**

Holiday operation procedure:
08:00 — Startup proceeds through Stages 1–5 only (data and knowledge layers).
08:15 — Governance Engine performs holiday compliance check.
08:30 — System enters MARKET_HOLIDAY state (not OPERATIONAL).
         No decision cycles run.
         Portfolio monitoring continues (read-only).
         Risk monitoring continues (read-only).
         Learning Engine runs holiday deep training cycle.
         Simulation Engine runs any pending simulations.
         Maintenance tasks run.
18:00 — Holiday cycle complete; system shutdown.

---

### 7.7 Disaster Recovery Operations

**Disaster Definition:** Any event that causes system unavailability for > 30 minutes
during market hours, or data loss affecting the audit record.

**Disaster Recovery Tiers:**

DR Tier 1 — Single-engine failure:
Recovery within 5 minutes; automated; no data loss.

DR Tier 2 — Multi-engine failure (2-4 engines):
Recovery within 15 minutes; automated with Tier 2 notification; minimal data loss (< 30 second window).

DR Tier 3 — System failure (5+ engines or Master Orchestrator):
Recovery within 60 minutes; requires Tier 2 authorization; state reconciliation required.

DR Tier 4 — Infrastructure failure (VPS down, storage failure):
Recovery from backup within 4 hours; requires Tier 1 + Tier 2; knowledge graph restored from last daily backup.

**Recovery Priority Order (in Tier 3/4 events):**
1. Database Persistence (foundation for all else)
2. Temporal Engine (market time reference)
3. Information Engine (data ingestion)
4. Knowledge Engine (intelligence foundation)
5. Risk Engine (position protection)
6. Portfolio Engine (position tracking)
7. Governance Engine (operational control)
8. All other engines

---

### 7.8 Maintenance Operations

Maintenance activities are planned, scheduled, and non-disruptive.
No maintenance is performed during market hours.

**Planned Maintenance Windows:**
- Daily: 16:00–18:00 IST (post-session)
- Weekly: Saturday 12:00–14:00 IST
- Monthly deep maintenance: First Saturday of month, all day

**Maintenance Activities Requiring Tier 2 Authorization:**
- Database schema migration (requires Architecture Council review first)
- Engine version upgrade
- Operating system / infrastructure upgrade

**Maintenance Activities Automated (no authorization required):**
- Database compaction
- Log rotation
- Backup
- Integrity verification

---

### 7.9 Cold Start Procedure

Cold start is a complete startup from zero state (no prior session data).

**Occurs when:**
- First-ever deployment
- Database was reset (recovery from catastrophic data loss)
- System moved to new infrastructure

**Cold Start Steps:**
1. Deploy all engine containers.
2. Initialize Database Persistence Architecture (fresh schema).
3. Load Ontologies from canonical definitions.
4. Initialize Knowledge Engine with seed knowledge (manually loaded).
5. Initialize Strategy Engine with manually loaded strategy candidates.
6. Run full Simulation Engine backtest suite for each candidate strategy.
7. Governance Engine reviews simulation results.
8. Governance Engine issues first session certificate after all strategies approved.
9. Startup proceeds as normal WF-SYS-01.

Cold start is expected to take 2-4 days to complete the simulation and governance
cycle before the first operational session is permitted.

---

### 7.10 Warm Restart Procedure

Warm restart is a restart with existing state intact (most common restart scenario).

**Occurs when:**
- Daily startup (standard)
- Recovery from engine crash (sessions interrupted)
- Software update deployment

**Warm Restart Steps:**
1. Master Orchestrator starts.
2. Database Persistence Architecture confirmed available.
3. Each engine restores state from Database (WF-SYS-01 Stages 1–8).
4. Knowledge Engine rebuilds 5-minute cache from persisted state.
5. Governance Engine issues session certificate.
6. System enters OPERATIONAL state.

Warm restart nominally completes in 60 minutes (T-60 to T-00 before market open).

---

### 7.11 Emergency Shutdown Procedure

**Trigger:** WF-SYS-17; or operator EMERGENCY_STOP command.

See WF-SYS-17 for step-by-step emergency shutdown procedure.

Key characteristics:
- Decision Engine locked within 1 second.
- Portfolio Engine read-only within 2 seconds.
- Operator alert within 5 seconds.
- Full state snapshot taken before any engine stops.
- Open positions NOT liquidated automatically (human decision required).
- System resumes only after Tier 2 authorization at next startup.

---

## PART VIII — SYSTEM QUALITY FRAMEWORK

### 8.1 Quality Framework Overview

The IIOS Quality Framework defines 13 quality dimensions, each with measurable
targets, measurement methods, and health thresholds. The System Quality Score (SQS)
is a weighted composite of all 13 dimensions. SQS >= 0.75 is the minimum acceptable
quality standard for an operational IIOS session.

**SQS Formula:**
SQS = sum of (dimension_score_i × dimension_weight_i) for i in 1..13

---

### 8.2 Reliability

**Definition:** The probability that IIOS produces correct outputs over a defined
time period.

**Measurement:** Session success rate (sessions completing without P1 incident / total sessions).
Target: >= 99% monthly session success rate.
Warning threshold: < 98%. Critical threshold: < 95%.

**Key reliability contributors:**
- Engine health monitoring (early detection of degradation)
- Recovery procedures (rapid recovery from failures)
- Constitutional rules enforcement (prevents decision-making in degraded state)

---

### 8.3 Availability

**Definition:** The percentage of scheduled market hours during which IIOS is
fully operational.

**Measurement:** (Actual operational minutes / Scheduled market minutes) per month.
Target: >= 99.5% monthly availability.
Warning: < 99.0%. Critical: < 98.0%.

**Availability degraders:** Engine startup failures, infrastructure issues, data
feed outages, governance certificate denial.

---

### 8.4 Scalability

**Definition:** IIOS's ability to maintain performance quality as the instrument
universe, data volume, or knowledge graph grows.

**Measurement:** Decision cycle latency at current load vs baseline load.
Target: Latency growth < 20% per 2x load increase.

**Scalability design features:** 5-minute Knowledge Engine cache (absorbs per-tick
load); strategy-level parallelism in Simulation Engine; event-driven architecture
(no polling loops).

---

### 8.5 Consistency

**Definition:** All components of IIOS agree on the current state of the system,
portfolio, and market at any given time.

**Measurement:** State reconciliation discrepancy rate (reconciliation failures / total reconciliations).
Target: < 0.1% discrepancy rate.

**Consistency mechanisms:** State Engine as single source of truth; Portfolio Engine
reconciliation on every TRADE_EXECUTED event; Temporal Engine as authoritative time reference.

---

### 8.6 Integrity

**Definition:** Data and knowledge stored by IIOS is accurate, unmodified since
creation, and consistent with its stated provenance.

**Measurement:** Integrity check failure rate at daily database verification.
Target: 0 integrity failures. Any integrity failure is a P1 incident.

**Integrity mechanisms:** Append-only audit tables; hash chains at session close;
immutable decision records; ontology version checksums.

---

### 8.7 Security

**Definition:** IIOS prevents unauthorized access, modification, or disclosure
of system data, credentials, and operational state.

**Measurement:** Security audit findings per quarter.
Target: 0 Critical, 0 High findings.

**Security controls:** Role-based access; secrets manager for credentials;
internal network only for engine communication; append-only audit trails;
all overrides require authenticated sessions.

---

### 8.8 Performance

**Definition:** IIOS meets its operational latency and throughput targets under
normal and peak load conditions.

**Measurement:** P95 decision cycle latency (target: < 200ms); Knowledge Engine
cache hit rate (target: > 95%); prediction cycle latency (target: < 50ms).

**Performance design features:** Background Knowledge Engine cache refresh;
Knowledge Engine 5-minute cache eliminates per-cycle data retrieval;
parallel engine startup in non-dependent stages.

---

### 8.9 Observability

**Definition:** The state of IIOS can be understood at any point by inspecting
its metrics, logs, and traces without modifying the system.

**Measurement:** Dashboard coverage (metrics displayed / total tracked metrics).
Target: > 90% of all tracked metrics visible on Streamlit dashboard.

**Observability features:** Streamlit dashboard (L17 ControlTower); Telegram P1
alerts; OHS score on dashboard; session governance reports; decision trace display.

---

### 8.10 Maintainability

**Definition:** IIOS can be modified, extended, and corrected with predictable
effort and without unintended consequences.

**Measurement:** Mean time to implement a tested, deployed architectural change.
Target: < 5 business days for a MINOR version increment.

**Maintainability design features:** Engine isolation (change one engine without
impacting others); registration-based extension (new engine = register, declare, integrate);
documented interfaces (every engine's public interface is in its architecture document).

---

### 8.11 Extensibility

**Definition:** New capabilities can be added to IIOS without modifying existing components.

**Measurement:** Number of new engine integrations completed without modification
to existing engine code.
Target: All new engine integrations achieved without modification to existing engines.

**Extensibility mechanism:** Master Orchestrator Engine Registry; workflow registration;
ontology extension protocol; learning engine plugin model.

---

### 8.12 Auditability

**Definition:** Every IIOS decision and action can be reconstructed with its full
context, rationale, and outcome from the audit record.

**Measurement:** Decision provenance completeness (decisions with full provenance trail / total decisions).
Target: 100%. Any decision without full provenance is a P2 incident.

**Auditability mechanisms:** Decision Record with 7-layer provenance; append-only
audit tables; immutable learning records; governance audit log.

---

### 8.13 Resilience and Business Continuity

**Definition:** IIOS can withstand, recover from, and adapt to adverse conditions
without losing critical capabilities.

**Measurement:** Mean Time to Recovery (MTTR) for P1 incidents. Target: < 15 minutes.

**Resilience features:** SAFE mode (operations continue in degraded state);
engine restart procedures; state restoration from persistence; DAILY_SESSION_CERTIFICATE
pre-validates conditions before every session.

**Business Continuity:** For CRITICAL and CATASTROPHIC failures, recovery from
daily backup within 4 hours. No single point of failure in the knowledge and data
layers (Knowledge Engine cache provides buffer against data feed outages).

---

### Summary: System Quality Score (SQS) Dimension Weights

| Dimension         | Weight | Target     | Critical Threshold     |
|-------------------|--------|------------|------------------------|
| Reliability       | 0.12   | 99.0%      | < 95%                  |
| Availability      | 0.12   | 99.5%      | < 98%                  |
| Integrity         | 0.12   | 0 failures | Any failure = P1       |
| Security          | 0.10   | 0 Critical | Any Critical = P1      |
| Performance       | 0.10   | < 200ms P95| > 500ms P95 = alert    |
| Auditability      | 0.10   | 100%       | < 99% = P2             |
| Consistency       | 0.08   | < 0.1%     | > 1% = P2              |
| Resilience        | 0.08   | MTTR < 15m | MTTR > 60m = P1        |
| Observability     | 0.07   | > 90% cov. | < 70% = P2             |
| Scalability       | 0.05   | < 20% lat. | > 50% lat. growth = P2 |
| Maintainability   | 0.05   | < 5 days   | > 15 days = review     |
| Extensibility     | 0.05   | 100% clean | Any forced mod = P2    |
| Business Continuity | 0.06 | < 4h RTO   | > 8h RTO = P1          |
| **TOTAL**         | **1.00**|            |                        |

SQS >= 0.88: EXCELLENT | 0.75–0.87: GOOD | 0.60–0.74: ACCEPTABLE | 0.40–0.59: MARGINAL | < 0.40: FAILED

---

## PART IX — IIOS CONSTITUTION

### Preamble

This Constitution is the supreme governing document of the Investment Intelligence
Operating System. Every rule stated herein governs all engines, all workflows,
all operational procedures, all human interactions, and all future extensions of IIOS.

No engine, operator, or process may override a constitutional rule.
Constitutional rules are enforced by the Governance Engine in real time.
Constitutional amendments require Architecture Council review with a 30-day
public comment period.

Constitutional rules are classified:
- NON-NEGOTIABLE HARD (NNH): Never overridden under any circumstance.
- HARD (H): Cannot be overridden during live trading; amendment requires Tier 1.
- SOFT (S): Can be adjusted within bounds by Tier 2 within a policy window.

---

### CATEGORY A — ARCHITECTURE RULES (SCC-A)

**SCC-A-001 [NNH]** Every IIOS capability is implemented by a specialized engine.
No engine performs the function of another engine. The separation of concerns
is architecturally absolute.

**SCC-A-002 [NNH]** The dependency graph of IIOS engines is directed and acyclic,
except for explicitly permitted horizontal integration relationships (Risk-Portfolio,
Decision-Governance, Learning-Prediction). No other circular dependencies are permitted.

**SCC-A-003 [H]** Every IIOS engine is registered in the Master Orchestrator's Engine
Registry before participating in any workflow. Unregistered engines have no
standing in the system.

**SCC-A-004 [H]** Every IIOS engine declares its capabilities, dependencies, and
health check interface in its architecture document. The Engine Registry enforces
this declaration.

**SCC-A-005 [H]** The IIOS architecture is open for extension (new engines, new ontologies,
new workflows) and closed for modification of existing interfaces.

**SCC-A-006 [H]** The seven IIOS ontologies define all concepts that IIOS reasons about.
Reasoning about undefined concepts is prohibited. If a concept does not exist in the
ontology, it cannot be processed by any engine.

**SCC-A-007 [H]** Ontology extensions must maintain backward compatibility. Existing
ontological types and their properties cannot be removed or renamed.

**SCC-A-008 [H]** The Master Orchestrator is the sole coordinator of all inter-engine
workflows. No engine may invoke another engine directly without the Orchestrator's mediation.

**SCC-A-009 [H]** All communication between engines is mediated by the Master
Orchestrator's Communication Manager (OC-10). Direct engine-to-engine calls
outside this channel are prohibited except for the three explicitly permitted
horizontal integration relationships.

**SCC-A-010 [S]** Architecture documents are the authoritative specification of each
engine's behavior. Any discrepancy between implementation and architecture document
must be resolved in favor of the architecture document.

---

### CATEGORY B — KNOWLEDGE RULES (SCC-B)

**SCC-B-001 [NNH]** All knowledge used by IIOS must have a provenance record.
Sourceless knowledge (no origin, no timestamp, no quality score) is prohibited.

**SCC-B-002 [H]** The Knowledge Engine is the sole authoritative source of
structured knowledge for all intelligence engines (Prediction, Decision, Risk,
Strategy). No engine may bypass the Knowledge Engine to access raw data directly.

**SCC-B-003 [H]** Knowledge facts are immutable once persisted. Updates create
new versions; old versions are archived but never deleted.

**SCC-B-004 [H]** The Knowledge Engine's 5-minute cache is the performance
mechanism that allows the intelligence stack to operate at intraday speed.
Cache invalidation is permissible for specific entities when significant changes
are detected; bulk cache invalidation requires Tier 2 authorization.

**SCC-B-005 [H]** Conflicting knowledge facts are resolved by provenance quality.
The higher-quality source wins. When sources are equal quality, the more recent
fact prevails. All conflicts are logged.

**SCC-B-006 [H]** Market regime classification (BULL, BEAR, SIDEWAYS, HIGH_VOLATILITY,
CRISIS) is the exclusive function of the Knowledge Engine. No other engine may
declare or change the current regime.

**SCC-B-007 [H]** Knowledge acquired from simulations or hypothetical scenarios
is tagged as SIMULATED and is never mixed with REAL knowledge in the live knowledge
graph.

**SCC-B-008 [S]** The Knowledge Engine's confidence threshold for accepting new
facts (default: 0.3) may be adjusted within the range [0.1, 0.8] by Tier 2 within
the defined policy window.

---

### CATEGORY C — INFORMATION RULES (SCC-C)

**SCC-C-001 [H]** All market data entering IIOS passes through the Information
Engine before any other engine processes it. The Information Engine is the system's
sole data ingestion boundary.

**SCC-C-002 [H]** Every InformationObject carries a quality score [0.0, 1.0].
InformationObjects with quality < 0.3 are rejected. Objects with quality 0.3–0.6
are flagged for downstream awareness.

**SCC-C-003 [H]** Data source failures are handled by the Information Engine.
If the primary source fails, the fallback source is activated. If both fail,
KNOWLEDGE_STALE signal is broadcast and SAFE mode is evaluated.

**SCC-C-004 [H]** All information objects are persisted before any engine reads them.
In-flight, unpersisted information is not consumed by downstream engines.

**SCC-C-005 [S]** The Information Engine's quality thresholds may be adjusted
within the range [0.2, 0.5] for rejection and [0.5, 0.8] for flag, by Tier 2.

---

### CATEGORY D — ENTITY RULES (SCC-D)

**SCC-D-001 [H]** Every financial instrument processed by IIOS has a corresponding
entity record in the Entity Engine. Instruments without entity records cannot be
part of any workflow.

**SCC-D-002 [H]** Entity IDs are permanent and immutable. Once assigned, an entity
ID never changes even if the entity's properties change.

**SCC-D-003 [H]** Entity properties that change over time (price, volume, state)
are tracked with temporal versioning. Point-in-time queries must return the
property value at the requested time.

**SCC-D-004 [H]** Entity taxonomy is defined by the Entity Ontology. New entity
types are added through the ontology extension protocol, not through ad hoc
engine-level creation.

---

### CATEGORY E — RELATIONSHIP RULES (SCC-E)

**SCC-E-001 [H]** All relationships between entities are modeled by the Relationship
Engine. Implied or informal relationships (e.g., "NIFTY correlates with banking stocks")
are only operational when formalized in the Relationship Engine.

**SCC-E-002 [H]** Relationship weights are time-varying. Historical relationship
weights are preserved. No relationship weight is permanently deleted.

**SCC-E-003 [H]** Circular relationships (A depends on B depends on A) are permissible
in the relationship model because markets contain genuine circular dependencies.
The Relationship Engine handles them through the defined circular dependency protocol.

---

### CATEGORY F — EVENT RULES (SCC-F)

**SCC-F-001 [H]** All market events are classified and attributed by the Event Engine.
Unclassified events are flagged for review but not propagated to downstream engines.

**SCC-F-002 [H]** Events are immutable once recorded. An event that occurred is
permanently part of the system's event record, even if it was later found to be
a false signal. The original event is annotated; it is not deleted.

**SCC-F-003 [H]** The MARKET_OPEN and MARKET_CLOSE events are the authoritative
time boundaries of the trading session. All intraday activity must occur between
these events.

**SCC-F-004 [S]** Event detection sensitivity thresholds may be adjusted within
defined bounds by Tier 2 (e.g., gap size for GAP_EVENT detection).

---

### CATEGORY G — TEMPORAL RULES (SCC-G)

**SCC-G-001 [H]** The Temporal Engine is the authoritative time reference for all
IIOS operations. All timestamps in IIOS must derive from the Temporal Engine.

**SCC-G-002 [H]** IIOS operates in Indian Standard Time (IST). All time references
are IST unless explicitly qualified otherwise (e.g., for global data contexts).

**SCC-G-003 [H]** The trading calendar (market holidays, early close days) is
maintained by the Temporal Engine and is the authoritative reference for all
schedule-dependent operations.

**SCC-G-004 [H]** No time-travel is permitted in IIOS live operations. Prediction
features can only use data available at the prediction time. Look-ahead bias is a
constitutional violation.

---

### CATEGORY H — SPATIAL RULES (SCC-H)

**SCC-H-001 [H]** Every entity with geographic relevance (exchange-listed instruments,
macro data sources) has a spatial annotation from the Spatial Engine.

**SCC-H-002 [H]** Global context data (S&P, Nikkei, bonds, FX) is classified by
spatial region and integrated into the global intelligence assessment by the
Knowledge Engine.

---

### CATEGORY I — STATE RULES (SCC-I)

**SCC-I-001 [H]** The State Engine is the authoritative source of current system
state, entity state, and portfolio state. All engines read state from the State Engine;
they do not maintain their own authoritative state copies.

**SCC-I-002 [H]** State transitions must be valid (permitted by the State Ontology's
state machine definitions). Illegal state transitions are rejected and logged as incidents.

**SCC-I-003 [H]** State is persisted at every transition. State loss across restarts
is a data integrity violation.

**SCC-I-004 [H]** The system cannot be in two states simultaneously. State transitions
are atomic.

---

### CATEGORY J — OBSERVATION RULES (SCC-J)

**SCC-J-001 [H]** The observation cycle (WF-SYS-03) runs every 30 seconds during
INTRADAY_ACTIVE state. The observation interval may not be extended beyond 60 seconds
without Tier 2 authorization.

**SCC-J-002 [H]** Observations are never selectively suppressed. All market data
received by the Information Engine is processed, regardless of its implications.

**SCC-J-003 [S]** The observation cycle interval (default 30 seconds) may be adjusted
within the range [15 seconds, 60 seconds] by Tier 2.

---

### CATEGORY K — PREDICTION RULES (SCC-K)

**SCC-K-001 [H]** Every prediction carries a confidence score [0.0, 1.0]. Only
predictions with confidence >= 0.5 are forwarded to the Decision Engine.

**SCC-K-002 [H]** Predictions have a validity window (default: 5 minutes). Expired
predictions are not consumed. The Decision Engine must verify prediction freshness
before scoring candidates.

**SCC-K-003 [H]** Prediction models are versioned. The model version that produced
each prediction is recorded in the prediction provenance.

**SCC-K-004 [H]** Prediction models are never updated in live trading. Model updates
happen post-session and are validated before the next session.

**SCC-K-005 [NNH]** No prediction is made using data that was not available at the
prediction time (no look-ahead bias). This rule applies to both live predictions
and backtesting.

**SCC-K-006 [S]** The prediction confidence threshold for forwarding to Decision
Engine (default: 0.5) may be adjusted within the range [0.4, 0.7] by Tier 2.

---

### CATEGORY L — LEARNING RULES (SCC-L)

**SCC-L-001 [H]** Learning operates exclusively in post-session mode. No model
parameter update occurs during INTRADAY_ACTIVE state.

**SCC-L-002 [H]** All learning outcomes are attributed to specific decisions and
specific predictions. Anonymous learning (where the model learns from outcomes it
cannot attribute) is prohibited.

**SCC-L-003 [H]** Learning outputs (model updates) must be validated by the Simulation
Engine and approved by the Governance Engine before promotion to live.

**SCC-L-004 [H]** The Learning Engine maintains the complete history of all model
versions, all training outcomes, and all validation results. This history is never
deleted.

**SCC-L-005 [H]** If the Learning Engine is offline, sessions proceed normally.
Learning is beneficial but not required for live operations.

---

### CATEGORY M — DECISION RULES (SCC-M)

**SCC-M-001 [NNH]** No investment decision is made without a valid DAILY_SESSION_CERTIFICATE
from the Governance Engine.

**SCC-M-002 [NNH]** No investment decision is made with a Decision Score below 6.5/10.0.
Candidates below this threshold are not forwarded for authorization.

**SCC-M-003 [NNH]** Every investment decision has a Decision Record with full provenance
(observation → knowledge → prediction → scoring → debate → authorization → decision).
Decisions without complete provenance records are a constitutional violation.

**SCC-M-004 [H]** The 30-minute cooldown between decisions on the same instrument
is enforced by the Decision Engine. Cooldown bypass requires Tier 2 authorization
and is permanently logged.

**SCC-M-005 [H]** The Decision Engine's 5-agent debate protocol is not optional.
Every candidate that passes the score threshold enters the debate protocol.

**SCC-M-006 [H]** Decision Records are immutable once created. They cannot be
modified, backdated, or deleted.

**SCC-M-007 [S]** The decision score threshold (default 6.5/10.0) may be adjusted
within the range [6.0, 8.0] by Tier 2.

**SCC-M-008 [S]** The cooldown period (default 30 minutes) may be adjusted within
the range [15 minutes, 60 minutes] by Tier 2.

---

### CATEGORY N — RISK RULES (SCC-N)

**SCC-N-001 [NNH]** When daily cumulative loss reaches 2% of portfolio value, all
new investment activity halts for the remainder of the session. This limit cannot
be overridden.

**SCC-N-002 [NNH]** When the VIX exceeds 45, all new investment activity halts for
the remainder of the session. This limit cannot be overridden.

**SCC-N-003 [NNH]** When any active strategy's drawdown reaches 15%, that strategy
is immediately disabled. This limit cannot be overridden.

**SCC-N-004 [H]** The Risk Engine is always operational during INTRADAY_ACTIVE state.
Risk Engine failure immediately triggers SAFE mode. There is no grace period.

**SCC-N-005 [H]** Risk limits are applied per-strategy (individual budget) and per-portfolio
(aggregate budget). A strategy cannot consume the entire portfolio risk budget.

**SCC-N-006 [H]** VaR calculations use the 95th confidence level with a 1-day horizon.
VaR methodology may not be changed without Architecture Council approval.

**SCC-N-007 [H]** Risk model parameters are recalibrated monthly. Any deviation from
the monthly recalibration schedule requires Tier 2 authorization with documented justification.

**SCC-N-008 [S]** The VaR limit per position (default: 1% of portfolio value) may be
adjusted within the range [0.5%, 2%] by Tier 2 within monthly recalibration.

---

### CATEGORY O — PORTFOLIO RULES (SCC-O)

**SCC-O-001 [H]** Portfolio state is the authoritative record of what IIOS believes
is currently owned. Portfolio state is reconciled after every trade execution.

**SCC-O-002 [H]** Position sizes are determined by the Risk Engine's position sizing
algorithm. No position is sized by the Decision Engine or Strategy Engine.

**SCC-O-003 [H]** Portfolio state is persisted at every update. Loss of portfolio
state data is a P1 incident requiring immediate recovery.

**SCC-O-004 [H]** Open positions are never automatically liquidated by IIOS except
through the strategy's defined exit conditions. Emergency position management
requires human authorization.

---

### CATEGORY P — STRATEGY RULES (SCC-P)

**SCC-P-001 [NNH]** No strategy enters live trading without a valid evidence dossier
produced by the Simulation Engine and approved by the Governance Engine.

**SCC-P-002 [H]** Evidence dossiers expire after 30 days. A strategy whose evidence
dossier expires is automatically SUSPENDED until re-simulation and re-approval.

**SCC-P-003 [H]** Strategy parameters are immutable during live trading. Parameters
may only change through the full re-simulation and re-approval cycle.

**SCC-P-004 [H]** The minimum performance criteria for a strategy to remain ACTIVE
are: Win Rate >= 50%, Sharpe Ratio > 0.8, Max Drawdown < 15%.

**SCC-P-005 [H]** Strategies are versioned. Each time a strategy's parameters change,
a new version is created with its own evidence dossier. Previous versions are archived.

**SCC-P-006 [S]** The evidence dossier validity period (default 30 days) may be
adjusted within the range [14 days, 90 days] by Tier 2.

---

### CATEGORY Q — SIMULATION RULES (SCC-Q)

**SCC-Q-001 [H]** Simulation results are computed from historical data only.
No simulation uses live market data. The boundary between simulation and live
operation is architecturally enforced.

**SCC-Q-002 [H]** Simulation evidence dossiers are permanent. They cannot be deleted,
even for retired strategies. They serve as the historical record of why each strategy
was or was not deployed.

**SCC-Q-003 [H]** Monte Carlo simulations use a minimum of 1,000 paths. The minimum
path count may not be reduced without Architecture Council approval.

**SCC-Q-004 [H]** Walk-Forward Testing uses a minimum of 3 in-sample/out-of-sample
windows. Single-window backtesting is insufficient for strategy promotion.

**SCC-Q-005 [H]** Simulation results that do not meet minimum criteria (Sharpe > 0.8,
Win Rate >= 50%, Max Drawdown < 15%) may not be promoted regardless of subjective
assessment. The Governance Engine enforces these thresholds mechanically.

---

### CATEGORY R — GOVERNANCE RULES (SCC-R)

**SCC-R-001 [NNH]** No trading session begins without a valid DAILY_SESSION_CERTIFICATE
from the Governance Engine.

**SCC-R-002 [NNH]** The Governance Engine is always operational during INTRADAY_ACTIVE
state. Governance Engine failure immediately triggers SAFE mode.

**SCC-R-003 [NNH]** Constitutional rules cannot be overridden by human operators,
operational procedures, or emergency conditions. If a situation arises where
a constitutional rule prevents necessary action, the Architecture Council must
review and amend the constitution through the defined process.

**SCC-R-004 [H]** The Governance Engine maintains an audit record of every governance
action. Governance actions without audit records are invalid.

**SCC-R-005 [H]** All five Governance Integration Points (pre-session, strategy deployment,
decision authorization, model update, kill-switch) are enforced simultaneously.
Disabling any governance integration point requires Tier 1 authorization and is
logged as a constitutional exception.

**SCC-R-006 [H]** The Governance Engine has the authority to block any decision,
suspend any strategy, or halt any session. Its authority within its constitutional
domain supersedes all other engines.

**SCC-R-007 [H]** Governance reports (session, weekly, monthly) are produced on
schedule. Missed governance reports are P2 incidents.

---

### CATEGORY S — MASTER ORCHESTRATION RULES (SCC-S)

**SCC-S-001 [NNH]** The Master Orchestrator does not perform investment analysis.
It has no opinion on markets, instruments, or investment opportunities.

**SCC-S-002 [NNH]** The Master Orchestrator does not interpret the outputs of
investment engines. It routes, schedules, and coordinates; it does not analyze.

**SCC-S-003 [H]** All workflows are defined in the Workflow Catalog before execution.
No ad hoc workflow is created during live trading.

**SCC-S-004 [H]** Every workflow execution has a unique Workflow Instance ID
(WF-{PIPELINE_CODE}-{YYYYMMDD}-{SEQ:08d}). No two workflow instances share an ID.

**SCC-S-005 [H]** The Orchestrator Health Score (OHS) is computed every 30 seconds.
If OHS falls below CRITICAL (0.35), immediate SAFE mode activation is mandatory.

**SCC-S-006 [H]** Recovery operations never modify open positions (IIOS-MO-ARCH-001
OCC-I-001). The Master Orchestrator's recovery procedures are coordination-only.

**SCC-S-007 [S]** The OHS calculation frequency (default 30 seconds) may be adjusted
within the range [15 seconds, 60 seconds] by Tier 2.

---

### CATEGORY T — SECURITY RULES (SCC-T)

**SCC-T-001 [NNH]** No credentials, secrets, API keys, or authentication tokens are
stored in source code, configuration files, logs, or audit records.
All secrets are managed exclusively through the designated secrets manager.

**SCC-T-002 [H]** All human operator actions require authenticated sessions.
Unauthenticated modifications to system state are prohibited.

**SCC-T-003 [H]** All inter-engine communication occurs within the internal network
boundary. No engine exposes its interface to external networks.

**SCC-T-004 [H]** Audit trail integrity is protected through cryptographic hash chains.
Any audit record modification is detectable.

**SCC-T-005 [H]** Access to system state is role-based (READ, OPERATIONAL, ARCHITECTURAL).
No user has access beyond their defined role.

**SCC-T-006 [H]** Security audit logs are reviewed weekly by the Operations Lead.
Unreviewed security findings older than 14 days are escalated to Tier 1.

**SCC-T-007 [H]** New engine integrations must pass security review before being
registered in the production Engine Registry. Security review confirms: no external
network exposure, no credential storage violations, no audit bypass paths.

---

### CATEGORY U — COMPLIANCE RULES (SCC-U)

**SCC-U-001 [H]** All investment decisions comply with the defined regulatory framework.
No decision targets instruments or sizes that would breach regulatory thresholds.

**SCC-U-002 [H]** Insider trading prevention: no investment decision may be based
on information that is not publicly available to all market participants.
The Information Engine classifies all information sources; non-public sources
are blocked from the decision-making chain.

**SCC-U-003 [H]** Position sizing respects SEBI large-cap concentration limits.
The Risk Engine enforces these limits as hard constraints.

**SCC-U-004 [H]** All market data usage complies with data provider terms of service.
Data provider compliance review is conducted quarterly by the Operations Lead.

**SCC-U-005 [S]** Compliance reports are produced monthly. The reporting schedule
may be changed with Tier 2 authorization.

---

### CATEGORY V — RECOVERY RULES (SCC-V)

**SCC-V-001 [NNH]** Recovery operations never modify open positions. Recovery is
coordination-only. No recovery procedure has the authority to execute, modify,
or close any investment position.

**SCC-V-002 [H]** Recovery procedures are defined and documented before live deployment.
There are no improvisational recovery procedures in production.

**SCC-V-003 [H]** Every recovery event produces a Recovery Record. Recovery events
without documentation are P2 incidents.

**SCC-V-004 [H]** System state is taken from persistence during recovery. Recovery
never relies on in-memory state from a crashed process.

**SCC-V-005 [H]** CRITICAL and CATASTROPHIC recovery events trigger a post-incident
review within 48 hours. The review produces a documented root cause and improvement action.

**SCC-V-006 [H]** The Master Orchestrator transitions to SAFE mode before any
recovery attempt. No recovery attempt occurs while the system is still trying
to accept new investment decisions.

---

### CATEGORY W — HUMAN OVERRIDE RULES (SCC-W)

**SCC-W-001 [NNH]** No human override may violate a constitutional rule.
Human operators have full authority to operate within constitutional constraints;
zero authority to override them.

**SCC-W-002 [H]** Every human override is logged permanently with operator ID,
timestamp, override type, and justification.

**SCC-W-003 [H]** Human overrides expire at session end. No override is silently
carried forward to the next session without re-authorization.

**SCC-W-004 [H]** Human operators retain authority to halt all trading activity
at any time. The EMERGENCY_STOP command is always available to authorized operators.

**SCC-W-005 [H]** Human operators cannot instruct the system to bypass the Governance
Engine's decision authorization requirement.

**SCC-W-006 [H]** All override authorizations require the OPERATIONAL role or higher.
READ-only users cannot apply overrides.

---

### CATEGORY X — FUTURE EXPANSION RULES (SCC-X)

**SCC-X-001 [H]** New engines are integrated through the Master Orchestrator's
Engine Registry. No engine is integrated by modifying any existing engine.

**SCC-X-002 [H]** New instrument types are integrated through ontology extension.
The Entity Ontology, Relationship Ontology, and Event Ontology are extended
before any engine supports new instrument types.

**SCC-X-003 [H]** New markets (e.g., futures markets, foreign exchanges) require
a new Spatial Ontology region definition, new Entity types, and new calendar
entries in the Temporal Engine before any intelligence engine is extended.

**SCC-X-004 [H]** All future extensions are evaluated for constitutional compliance
before deployment. A new capability that requires a constitutional amendment is
not deployed until the amendment is ratified.

**SCC-X-005 [H]** New prediction models are validated by the Simulation Engine and
approved by the Governance Engine before deployment. This requirement applies to
all models regardless of their origin.

**SCC-X-006 [H]** New strategies are treated as CANDIDATE until they accumulate
an evidence dossier. No fast-track deployment exists.

**SCC-X-007 [H]** The IIOS architecture can be extended with new intelligence engines
(e.g., a Natural Language Processing engine for news analysis) through the same
registration process used for all existing engines.

**SCC-X-008 [S]** New extensions are deployed first in the STAGING environment with
at minimum a 5-session validation period before production deployment.

---

### Constitution Summary

| Category | Domain         | Rules | NNH | HARD | SOFT |
|----------|----------------|-------|-----|------|------|
| A        | Architecture   |  10   |  0  |  9   |  1   |
| B        | Knowledge      |  8    |  0  |  7   |  1   |
| C        | Information    |  5    |  0  |  4   |  1   |
| D        | Entities       |  4    |  0  |  4   |  0   |
| E        | Relationships  |  3    |  0  |  3   |  0   |
| F        | Events         |  4    |  0  |  3   |  1   |
| G        | Temporal       |  4    |  0  |  4   |  0   |
| H        | Spatial        |  2    |  0  |  2   |  0   |
| I        | State          |  4    |  0  |  4   |  0   |
| J        | Observation    |  3    |  0  |  2   |  1   |
| K        | Prediction     |  6    |  1  |  4   |  1   |
| L        | Learning       |  5    |  0  |  5   |  0   |
| M        | Decision       |  8    |  3  |  3   |  2   |
| N        | Risk           |  8    |  3  |  4   |  1   |
| O        | Portfolio      |  4    |  0  |  4   |  0   |
| P        | Strategy       |  6    |  1  |  4   |  1   |
| Q        | Simulation     |  5    |  0  |  5   |  0   |
| R        | Governance     |  7    |  3  |  4   |  0   |
| S        | Orchestration  |  7    |  2  |  4   |  1   |
| T        | Security       |  7    |  1  |  6   |  0   |
| U        | Compliance     |  5    |  0  |  4   |  1   |
| V        | Recovery       |  6    |  1  |  5   |  0   |
| W        | Human Override |  6    |  1  |  5   |  0   |
| X        | Future Expansion | 8   |  0  |  7   |  1   |
|**TOTAL** |                |**164**|**16**|**125**|**13**|

**16 NON-NEGOTIABLE HARD rules govern the most fundamental IIOS properties.**
**125 HARD rules govern all standard operational behavior.**
**13 SOFT rules allow bounded operational flexibility within policy.**

---

## PART X — SYSTEM READINESS CERTIFICATION

### 10.1 Certification Framework Overview

The IIOS Readiness Certification Framework defines 12 certification phases.
IIOS must achieve certification in all 12 phases before entering PRODUCTION_READY state.
Partial certification (some phases passed, some not) is not a valid production state.

**Certification ID Format:** ISYS-CERT-{YYYYMMDD}-{SESSION}-{SEQ:04d}

---

### Phase CP-01: ARCHITECTURE READY

**Gate items:**

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| AR-01| HARD | All 20 architecture documents published and version-marked | Document audit |
| AR-02| HARD | All ontologies have Architecture Council sign-off  | Approval records |
| AR-03| HARD | Constitutional hierarchy fully documented          | Document review |
| AR-04| HARD | No open architectural issues with CRITICAL status  | Issue tracker |
| AR-05| SOFT | Architecture cross-reference complete              | Manual review |

---

### Phase CP-02: ONTOLOGY READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| ON-01| HARD | All 7 ontologies loaded into Knowledge Engine      | Health check |
| ON-02| HARD | Ontology checksums verified against canonical versions | Checksum comparison |
| ON-03| HARD | No undefined entity types in active strategy universe | Entity Engine query |
| ON-04| HARD | Temporal ontology includes full trading calendar for current year | Calendar audit |
| ON-05| SOFT | Spatial ontology covers all active data source regions | Manual review |

---

### Phase CP-03: ENGINE READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| ER-01| HARD | All 18 engines registered in Engine Registry       | Registry query |
| ER-02| HARD | All 18 engines pass health check                   | OHS >= 0.95 |
| ER-03| HARD | All engine startup sequences tested in staging     | Staging test results |
| ER-04| HARD | Engine dependency graph validated (no cycles)      | Dependency check |
| ER-05| HARD | All engine interfaces match architecture documents | Interface audit |
| ER-06| HARD | Knowledge Engine cache populated correctly         | Cache inspection |
| ER-07| SOFT | Engine startup latency < 60 minutes total          | Timing test |

---

### Phase CP-04: GOVERNANCE READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| GR-01| HARD | Governance Engine starts and issues test certificate | Certificate test |
| GR-02| HARD | All 7 Governance Integration Points tested         | Integration test |
| GR-03| HARD | Decision authorization flow tested end-to-end      | E2E test |
| GR-04| HARD | Kill-switch conditions tested (VIX > 45, loss > 2%)| Kill-switch test |
| GR-05| HARD | Strategy evidence dossier validation tested        | Evidence test |
| GR-06| SOFT | Governance report generation tested                | Report test |

---

### Phase CP-05: OPERATIONAL READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| OR-01| HARD | Full WF-SYS-01 startup workflow completed in staging| Staging test |
| OR-02| HARD | WF-SYS-02 market open workflow tested              | Staging test |
| OR-03| HARD | WF-SYS-14 shutdown workflow tested                 | Staging test |
| OR-04| HARD | WF-SYS-17 emergency stop tested                   | E2E test |
| OR-05| HARD | All 18 workflows tested in staging environment     | Workflow test suite |
| OR-06| HARD | Intraday cycle (30s observation, 5m prediction) tested | Cycle test |
| OR-07| SOFT | Operational runbook walkthrough completed          | Manual test |

---

### Phase CP-06: SECURITY READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| SR-01| HARD | No credentials in source code or config files      | Code scan |
| SR-02| HARD | All secrets in secrets manager                     | Secrets audit |
| SR-03| HARD | Role-based access tested for all 3 roles           | Access test |
| SR-04| HARD | Audit trail integrity hash chains verified         | Hash verification |
| SR-05| HARD | No external network exposure for any engine        | Network scan |
| SR-06| SOFT | Security review completed for all new engines      | Review records |

---

### Phase CP-07: RECOVERY READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| RR-01| HARD | WF-SYS-15 recovery workflow tested for ISOLATED case | Recovery test |
| RR-02| HARD | WF-SYS-15 recovery workflow tested for PARTIAL case | Recovery test |
| RR-03| HARD | CRITICAL recovery (Tier 2 authorization) tested    | Recovery test |
| RR-04| HARD | State restoration from persistence verified        | State test |
| RR-05| HARD | Backup and restore tested end-to-end               | DR test |
| RR-06| SOFT | MTTR < 15 minutes verified for ISOLATED recovery   | Timing test |

---

### Phase CP-08: MONITORING READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| MR-01| HARD | Streamlit dashboard operational with OHS display   | Dashboard test |
| MR-02| HARD | Telegram P1 alert delivery tested                  | Alert test |
| MR-03| HARD | All 13 SQS dimensions being measured               | Metrics audit |
| MR-04| HARD | Incident escalation path tested for P1 through P4  | Escalation test |
| MR-05| SOFT | Session governance report auto-generation confirmed| Report test |

---

### Phase CP-09: DOCUMENTATION READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| DR-01| HARD | All 20 architecture documents complete and published | Document audit |
| DR-02| HARD | This document (IIOS-INTEG-ARCH-001) complete       | Document review |
| DR-03| HARD | Operational runbook complete and reviewed           | Runbook review |
| DR-04| HARD | All governance forms and templates available       | Template audit |
| DR-05| SOFT | All architecture decision records documented       | ADR audit |

---

### Phase CP-10: DEPLOYMENT READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| DP-01| HARD | Docker composition tested with both containers healthy | Container test |
| DP-02| HARD | Data volume persistence tested across restarts     | Volume test |
| DP-03| HARD | No-cache Docker build tested                       | Build test |
| DP-04| HARD | VPS deployment (git pull + build + up) tested      | Deployment test |
| DP-05| HARD | Health check endpoints return correct status       | Health test |
| DP-06| SOFT | Cold start procedure fully documented and tested   | Cold start test |

---

### Phase CP-11: AI READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| AI-01| HARD | At least 3 strategies with valid evidence dossiers | Dossier audit |
| AI-02| HARD | Prediction models loaded and passing accuracy baseline | Model test |
| AI-03| HARD | Learning Engine has at least 20 days of training data | Data audit |
| AI-04| HARD | Decision Engine scoring calibration verified       | Calibration test |
| AI-05| HARD | Risk model parameters calibrated for current regime | Risk calibration |
| AI-06| SOFT | Knowledge graph contains > 500 entity records      | Entity count query |

---

### Phase CP-12: PRODUCTION READY

| Item | Type | Requirement                                        | Verification |
|------|------|----------------------------------------------------|-------------|
| PR-01| HARD | All CP-01 through CP-11 gates passed               | Gate summary |
| PR-02| HARD | Architecture Council sign-off on production approval | Sign-off record |
| PR-03| HARD | First session runs with paper trading mode; no errors | Paper trade test |
| PR-04| HARD | Paper trading session governance report reviewed   | Report review |
| PR-05| HARD | Emergency stop tested in paper trading environment | E2E test |
| PR-06| SOFT | At least 5 paper trading sessions completed        | Session logs |

---

### Readiness Certification Summary

| Phase  | Name                   | Gates | HARD | SOFT |
|--------|------------------------|-------|------|------|
| CP-01  | Architecture Ready     |  5    |  4   |  1   |
| CP-02  | Ontology Ready         |  5    |  4   |  1   |
| CP-03  | Engine Ready           |  7    |  6   |  1   |
| CP-04  | Governance Ready       |  6    |  5   |  1   |
| CP-05  | Operational Ready      |  7    |  6   |  1   |
| CP-06  | Security Ready         |  6    |  5   |  1   |
| CP-07  | Recovery Ready         |  6    |  5   |  1   |
| CP-08  | Monitoring Ready       |  5    |  4   |  1   |
| CP-09  | Documentation Ready    |  5    |  4   |  1   |
| CP-10  | Deployment Ready       |  6    |  5   |  1   |
| CP-11  | AI Ready               |  6    |  5   |  1   |
| CP-12  | Production Ready       |  6    |  5   |  1   |
|**TOTAL**|                       |**70** |**58**|**12**|

**58 HARD gates must pass. All 12 SOFT gates are strongly recommended.**

---

## SUPPLEMENT A — COMPLETE ENGINE CATALOGUE

This supplement provides the authoritative catalogue of all IIOS engines.
Each entry provides the full operational profile of the engine.

---

### ENGINE A-01: DATABASE PERSISTENCE ARCHITECTURE

**Document Code:** IIOS-DB-ARCH-001
**Stratum:** 2 (Persistence)
**Purpose:** Provides the durable, structured storage foundation for all IIOS
data, audit records, knowledge artifacts, and operational state.

**Responsibilities:**
- Define schema governance for all IIOS data stores.
- Enforce data integrity through constraints and checksums.
- Provide append-only access patterns for audit tables.
- Manage backup and restore procedures.
- Provide the persistence layer for all engines.

**Key Characteristics:**
- Storage: SQLite databases with defined schema per functional domain.
- Audit model: Append-only; no update or delete on audit tables.
- Backup: Automated daily; weekly full; monthly off-site.
- Integrity: Hash chains on audit tables; integrity check at session close.
- Recovery: Full state restoration from persistence within 30 minutes.

**Critical Dependencies:** None (foundation layer).

**Failure Impact:** All engines degrade to in-memory only; data loss risk after session.
Category: CRITICAL.

---

### ENGINE A-02: INFORMATION ENGINE

**Document Code:** IIOS-INFO-ENG-001
**Stratum:** 4 (Knowledge)
**Purpose:** Transform raw market data into typed, quality-scored, provenance-marked
information objects that downstream engines can reason about.

**Responsibilities:**
- Ingest raw OHLCV, options chain, fundamental, and macro data.
- Validate data quality; apply quality scores.
- Classify information by type (using Information Ontology).
- Persist all received information before distribution.
- Manage primary and fallback data sources.
- Distribute typed InformationObjects to consuming engines.

**Key Characteristics:**
- Quality scale: 0.0 (rejected) to 1.0 (perfect).
- Rejection threshold: quality < 0.3.
- Fallback: yfinance secondary source when primary (Dhan) fails.
- Data types: PriceBar, OptionData, FundamentalData, MacroData, EventSignal.

**Critical Dependencies:** Database Persistence Architecture.
**Failure Impact:** All downstream engines stale after cache expiry. SEVERE after 5 minutes.

---

### ENGINE A-03: KNOWLEDGE ENGINE

**Document Code:** IIOS-KNW-ENG-001
**Stratum:** 4 (Knowledge)
**Purpose:** Integrate all information, entity, relationship, event, temporal, and
spatial data into a unified, queryable knowledge graph that serves as the
intelligence foundation for all higher-layer engines.

**Responsibilities:**
- Maintain the IIOS knowledge graph.
- Classify market regime (BULL/BEAR/SIDEWAYS/HIGH_VOLATILITY/CRISIS).
- Provide 5-minute cache for performance-optimized access.
- Resolve knowledge conflicts through provenance quality rules.
- Accumulate institutional memory across sessions.

**Key Characteristics:**
- Cache refresh interval: 5 minutes (configurable within [1 min, 15 min]).
- Confidence threshold for fact acceptance: >= 0.3.
- Knowledge versioning: every fact version archived permanently.
- Regime classification: 6 regimes; multi-factor computation.

**Critical Dependencies:** Information, Entity, Relationship, Event, Temporal, Spatial Engines.
**Failure Impact:** All intelligence engines lose context. SAFE mode after 5 minutes.

---

### ENGINE A-04: ENTITY ENGINE

**Document Code:** IIOS-ENT-ENG-001
**Stratum:** 4 (Knowledge)
**Purpose:** Manage the entity graph — the registry of all financial instruments,
indices, sectors, issuers, and markets that IIOS can reason about.

**Key Characteristics:**
- Entity ID: permanent, immutable upon assignment.
- Property versioning: temporal versioning of all time-varying properties.
- Entity types: Equity, Index, Option, Sector, Market, Issuer, ETF, Derivative.

**Critical Dependencies:** Information Engine, Database Persistence.
**Failure Impact:** Knowledge Engine cannot update entity nodes.

---

### ENGINE A-05: RELATIONSHIP ENGINE

**Document Code:** IIOS-REL-ENG-001
**Stratum:** 4 (Knowledge)
**Purpose:** Model, maintain, and query relationships between entities, providing
correlation, causality, and dependency information to the Knowledge Engine.

**Key Characteristics:**
- Relationship types: Correlation, Causality, Membership, Containment, Dependency, Hedge.
- Weight range: [-1.0, 1.0] for correlation; [0.0, 1.0] for strength of other types.
- Temporal versioning: relationship weights tracked over time.
- Circular relationships: permitted and handled through circular dependency protocol.

**Critical Dependencies:** Entity Engine, Information Engine.
**Failure Impact:** Knowledge graph loses relationship dimension; correlation signals degrade.

---

### ENGINE A-06: EVENT ENGINE

**Document Code:** IIOS-EVT-ENG-001
**Stratum:** 4 (Knowledge)
**Purpose:** Detect, classify, attribute, and propagate market events that drive
state transitions and knowledge updates throughout IIOS.

**Key Characteristics:**
- Event types: MarketEvent (OPEN/CLOSE/HALT), CorporateEvent (earnings/dividend/split),
  MacroEvent (RBI/GDP/inflation), AnomalyEvent (gap/circuit/spike).
- Event detection sensitivity: configurable per event type.
- Events are immutable once created; false positives are annotated, not deleted.

**Critical Dependencies:** Entity Engine, Temporal Engine, Information Engine.
**Failure Impact:** State transitions missed; regime changes undetected.

---

### ENGINE A-07: TEMPORAL ENGINE

**Document Code:** IIOS-TMP-ENG-001
**Stratum:** 4 (Knowledge)
**Purpose:** Provide authoritative time context for all IIOS operations, including
session calendars, time horizon management, and temporal annotations.

**Key Characteristics:**
- Authoritative time zone: IST (Indian Standard Time).
- Market calendar: NSE trading calendar; holidays pre-loaded annually.
- Session events: MARKET_OPEN (09:15), MARKET_CLOSE (15:30), PRE_MARKET (08:00–09:15).
- Time horizon support: intraday, daily, weekly, monthly, quarterly, annual.

**Critical Dependencies:** Database Persistence Architecture.
**Failure Impact:** System loses authoritative time reference; scheduler may malfunction.

---

### ENGINE A-08: SPATIAL ENGINE

**Document Code:** IIOS-SPA-ENG-001
**Stratum:** 4 (Knowledge)
**Purpose:** Attach geographic and market-region context to entities, enabling
global-context-aware intelligence and cross-market analysis.

**Key Characteristics:**
- Regions: India (NSE/BSE), USA (NYSE/NASDAQ), Japan (TSE), Europe (major exchanges), Global indices.
- Spatial annotations: listing jurisdiction, regional economic zone, regulatory jurisdiction.

**Critical Dependencies:** Entity Engine, Database Persistence.
**Failure Impact:** Knowledge Engine loses global context dimension; global intelligence degrades.

---

### ENGINE A-09: STATE ENGINE

**Document Code:** IIOS-STE-ENG-001
**Stratum:** 5 (State)
**Purpose:** Maintain authoritative system state, entity state, portfolio state,
and strategy state, serving as the single source of truth for all state-dependent operations.

**Key Characteristics:**
- State types: SystemState, EntityState, PortfolioState, StrategyState, MarketState.
- State transitions: validated against State Ontology state machines.
- Persistence: every state transition persisted; full state restoration from DB.
- Atomicity: no two simultaneous state transitions; all transitions are atomic.

**Critical Dependencies:** Knowledge Engine, Event Engine, Temporal Engine.
**Failure Impact:** System loses state tracking; Risk Engine cannot validate positions.

---

### ENGINE A-10: PREDICTION ENGINE

**Document Code:** IIOS-PRD-ENG-001
**Stratum:** 6 (Intelligence)
**Purpose:** Generate calibrated directional and magnitude predictions for
investment candidates from current knowledge context.

**Key Characteristics:**
- Prediction types: directional (UP/DOWN/FLAT), magnitude (% move estimate), volatility.
- Confidence range: [0.0, 1.0]; threshold for forwarding: 0.5.
- Validity window: 5 minutes; stale predictions not consumed.
- Model types: regime-specific ensembles (BULL model, BEAR model, SIDEWAYS model).
- Calibration: confidence calibration curves updated by Learning Engine.

**Critical Dependencies:** Knowledge Engine, State Engine, Temporal Engine, Event Engine.
**Failure Impact:** Decision Engine loses prediction inputs; no new investment decisions.

---

### ENGINE A-11: LEARNING ENGINE

**Document Code:** IIOS-LRN-ENG-001
**Stratum:** 6 (Intelligence)
**Purpose:** Continuously improve prediction models and strategy parameters
through systematic analysis of trade outcomes against predictions.

**Key Characteristics:**
- Operates exclusively post-session (never during INTRADAY_ACTIVE).
- All model updates in STAGING before LIVE promotion.
- Governance approval required for all model promotions.
- Complete training history retained permanently.
- Outcome attribution: every outcome linked to a specific prediction and decision.

**Critical Dependencies:** Knowledge Engine, State Engine, Prediction Engine.
**Failure Impact:** Model improvements delayed. No live trading impact.

---

### ENGINE A-12: DECISION ENGINE

**Document Code:** IIOS-DEC-ENG-001
**Stratum:** 6 (Intelligence)
**Purpose:** Integrate predictions, risk assessments, and portfolio state into
governed investment decision recommendations using a multi-agent debate framework.

**Key Characteristics:**
- Decision score scale: 0.0–10.0; threshold: 6.5.
- 5-agent debate: Analyst, Fundamentals, Risk, Macro, Devil's Advocate.
- Cooldown: 30 minutes between decisions on same instrument.
- Every decision produces a Decision Record with full provenance.

**Critical Dependencies:** Prediction Engine, Risk Engine, Knowledge Engine, Governance Engine.
**Failure Impact:** No new investment decisions; monitoring-only mode.

---

### ENGINE A-13: RISK ENGINE

**Document Code:** IIOS-RSK-ENG-001
**Stratum:** 6 (Financial)
**Purpose:** Provide real-time risk assessment, position sizing, risk budget
management, and kill-switch enforcement for all IIOS investment activity.

**Key Characteristics:**
- Kill switches: daily loss >= 2%, VIX > 45, strategy drawdown >= 15%.
- VaR: 95th percentile, 1-day horizon.
- Position sizing: risk-budget-derived per strategy and per instrument.
- Monitoring frequency: continuous (every 30 seconds).

**Critical Dependencies:** Knowledge Engine, State Engine, Prediction Engine, Portfolio Engine.
**Failure Impact:** Kill-switch disabled. IMMEDIATE SAFE MODE required.

---

### ENGINE A-14: PORTFOLIO ENGINE

**Document Code:** IIOS-PFO-ENG-001
**Stratum:** 6 (Financial)
**Purpose:** Track portfolio state, compute P&L, manage position records, and
provide portfolio context to Risk and Decision engines.

**Key Characteristics:**
- P&L: open (mark-to-market) + realized; computed every 60 seconds.
- Position reconciliation: after every trade execution.
- Exposure analysis: gross, net, sector, options delta.
- Capital allocation: tracked per strategy.

**Critical Dependencies:** Risk Engine, Decision Engine, Knowledge Engine, State Engine.
**Failure Impact:** Portfolio state untracked; Risk Engine loses allocation data.

---

### ENGINE A-15: STRATEGY ENGINE

**Document Code:** IIOS-STG-ENG-001
**Stratum:** 6 (Financial)
**Purpose:** Manage the lifecycle of investment strategies, generate trade signals,
and maintain the strategy evidence requirements.

**Key Characteristics:**
- Strategy lifecycle: CANDIDATE → SIMULATION → EVIDENCE_REVIEW → ACTIVE → MONITORING → SUSPENDED → RETIRED.
- Regime alignment: strategy selection weighted by current regime.
- Auto-disable: drawdown >= 15% or consecutive losses >= threshold.
- Trade signals: entry and exit signals forwarded to Decision Engine.

**Critical Dependencies:** Knowledge Engine, Prediction Engine, Risk Engine, Learning Engine, Simulation Engine.
**Failure Impact:** No new trade signals; Decision Engine loses strategy-driven candidates.

---

### ENGINE A-16: SIMULATION ENGINE

**Document Code:** IIOS-SIM-ENG-001
**Stratum:** 6 (Validation)
**Purpose:** Evaluate strategies and models in a risk-free environment using
historical data, producing evidence dossiers for governance review.

**Key Characteristics:**
- Simulation types: Backtest, Walk-Forward Test, Monte Carlo (1,000 paths), Regime Test.
- Promotion criteria: Sharpe > 0.8, Win Rate >= 50%, Max Drawdown < 15%.
- Evidence dossier validity: 30 days.
- Isolation: simulation environment completely separated from live data paths.

**Critical Dependencies:** Strategy Engine, Risk Engine, Knowledge Engine, State Engine.
**Failure Impact:** No new strategy deployments; no model promotions.

---

### ENGINE A-17: GOVERNANCE ENGINE

**Document Code:** IIOS-GOV-ENG-ARCH-001
**Stratum:** 6 (Governance)
**Purpose:** Enforce constitutional rules, issue session certificates, authorize
decisions, approve model updates, and maintain continuous compliance monitoring.

**Key Characteristics:**
- Pre-session certificate: required for every trading session.
- 5 integration points: pre-session, strategy deployment, decision authorization, model update, kill-switch.
- Authority level: supersedes all other engines within its constitutional domain.
- Audit: every governance action permanently logged.

**Critical Dependencies:** Knowledge Engine, Decision Engine, Simulation Engine.
**Failure Impact:** No decision authorization possible. IMMEDIATE SAFE MODE.

---

### ENGINE A-18: MASTER ORCHESTRATOR

**Document Code:** IIOS-MO-ARCH-001
**Stratum:** 7 (Coordination)
**Purpose:** Coordinate all IIOS engines through defined workflows, manage system
lifecycle, monitor health, and recover from failures — without performing any
investment analysis.

**Key Characteristics:**
- 22 components across 4 tiers (Scheduling, Coordination, Operational, Infrastructure).
- 14 workflow pipelines.
- OHS (Orchestrator Health Score) computed every 30 seconds.
- SAFE mode: activated when OHS < 0.35 or critical engine offline.
- Recovery: coordination-only; never modifies positions.

**Critical Dependencies:** All engines.
**Failure Impact:** Complete coordination loss. CATASTROPHIC. Manual restart required.

---

## SUPPLEMENT B — COMPLETE ONTOLOGY CATALOGUE

---

### ONTOLOGY B-01: KNOWLEDGE ONTOLOGY

**Domain:** General knowledge representation
**Purpose:** Define the structure of all knowledge that IIOS accumulates and reasons about.

**Core concepts defined:**
- KnowledgeAssertion: a fact claimed to be true, with confidence and provenance.
- KnowledgeSource: the origin of a knowledge assertion (market data, model output, simulation, human input).
- KnowledgeProvenanceChain: the full attribution trail from raw data to assertion.
- ConfidenceLevel: quantified certainty [0.0, 1.0] assigned to every assertion.
- KnowledgeConflict: a condition where two assertions contradict each other; resolved by provenance quality.
- KnowledgeDomain: thematic grouping (market knowledge, entity knowledge, regime knowledge, etc.).

**Constitutional relationship:** Provides the vocabulary for SCC-B rules.

---

### ONTOLOGY B-02: INFORMATION ONTOLOGY

**Domain:** Market information classification
**Purpose:** Define all types of information that IIOS can receive and process.

**Core concepts defined:**
- InformationObject: base type for all processed market data.
- InformationQuality: [0.0, 1.0] quality score with graded acceptance thresholds.
- InformationProvenance: source, reception timestamp, transformation chain.
- InformationType: PriceInformation, OptionsInformation, FundamentalInformation,
  MacroInformation, EventInformation, CorpActionInformation.
- InformationReliability: source reputation score factored into quality assessment.
- InformationFreshness: age-based decay applied to information quality over time.

**Constitutional relationship:** Provides the vocabulary for SCC-C rules.

---

### ONTOLOGY B-03: ENTITY ONTOLOGY

**Domain:** Financial instrument taxonomy
**Purpose:** Define every type of financial entity that IIOS can track and reason about.

**Core concepts defined:**
- Entity: base type; immutable ID; mutable properties.
- EquityEntity: NSE-listed stock with ISIN, sector, market cap category.
- IndexEntity: market index (NIFTY, BANKNIFTY, NIFTY500, etc.).
- OptionEntity: derivative with underlying, strike, expiry, type (CE/PE).
- SectorEntity: GICS-style sector classification.
- IssuerEntity: corporate issuer with registration, listing status.
- MarketEntity: exchange or market (NSE, BSE) with operating hours.
- EntityLifecycle: NEW → ACTIVE → SUSPENDED → DELISTED.

**Constitutional relationship:** Provides the vocabulary for SCC-D rules.

---

### ONTOLOGY B-04: RELATIONSHIP ONTOLOGY

**Domain:** Inter-entity relationships
**Purpose:** Define all types of relationships between financial entities.

**Core concepts defined:**
- Relationship: directed or undirected link between two entities.
- CorrelationRelationship: statistical price correlation [-1.0, 1.0]; time-varying.
- CausalRelationship: directional causal link (A influences B).
- SectorMembership: equity is a member of a sector entity.
- IndexConstituentship: equity is a constituent of an index.
- HedgeRelationship: option or inverse instrument hedges an equity.
- RelationshipWeight: numerical strength of a relationship.
- RelationshipTemporalProfile: how relationship strength varies over time and regimes.

**Constitutional relationship:** Provides the vocabulary for SCC-E rules.

---

### ONTOLOGY B-05: EVENT ONTOLOGY

**Domain:** Market and corporate events
**Purpose:** Define all types of events that IIOS detects and attributes.

**Core concepts defined:**
- Event: discrete occurrence at a point in time, attributed to entities.
- MarketSessionEvent: MARKET_OPEN, MARKET_CLOSE, MARKET_HALT, CIRCUIT_BREAKER.
- CorporateEvent: EARNINGS_RELEASE, DIVIDEND_DECLARATION, STOCK_SPLIT, RIGHTS_ISSUE, BUYBACK.
- MacroEvent: RBI_POLICY, GDP_RELEASE, CPI_RELEASE, GLOBAL_RISK_OFF.
- AnomalyEvent: PRICE_GAP, VOLUME_SPIKE, VOLATILITY_SPIKE, LIQUIDITY_DRY.
- EventImpact: quantified market impact of a detected event.
- EventFalsificationAnnotation: annotation applied when an event is later found to be a false detection.

**Constitutional relationship:** Provides the vocabulary for SCC-F rules.

---

### ONTOLOGY B-06: TEMPORAL ONTOLOGY

**Domain:** Time and calendar management
**Purpose:** Define all temporal concepts used in IIOS.

**Core concepts defined:**
- TimePoint: a specific moment in IST.
- TimeInterval: [start, end] bounded period.
- TradingSession: a defined market trading day with open/close times.
- TradingCalendar: the annual schedule of trading sessions, holidays, and half-days.
- TimeHorizon: named investment time horizons (INTRADAY, DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUAL).
- SeasonalPattern: recurring temporal pattern (e.g., monthly expiry effects).
- LookAheadGuard: the temporal boundary enforced to prevent future data leakage.

**Constitutional relationship:** Provides the vocabulary for SCC-G rules.

---

### ONTOLOGY B-07: SPATIAL ONTOLOGY

**Domain:** Geographic and market regions
**Purpose:** Define spatial classifications for global market context.

**Core concepts defined:**
- GeographicRegion: a geographic area associated with a market (India, USA, Japan, Europe).
- MarketRegion: an exchange or trading venue (NSE, BSE, NYSE, NASDAQ, LSE, TSE).
- RegulatoryJurisdiction: regulatory authority domain (SEBI, SEC, FSA).
- ListingJurisdiction: where a specific instrument is listed.
- GlobalContextRegion: regions contributing to IIOS global intelligence (Asia, Europe, Americas).
- SpatialCorrelation: relationship between geographic market performance.

**Constitutional relationship:** Provides the vocabulary for SCC-H rules.

---

### ONTOLOGY B-08: STATE ONTOLOGY

**Domain:** System and entity state machines
**Purpose:** Define all valid states and permitted state transitions for all stateful
entities in IIOS.

**Core concepts defined:**
- SystemState: INITIALIZING → STARTING → OPERATIONAL → SAFE → DEGRADED → EMERGENCY_STOP → SHUTDOWN.
- MarketState: MARKET_CLOSED → PRE_MARKET → INTRADAY_ACTIVE → POST_MARKET → MARKET_HOLIDAY.
- EntityState: ACTIVE, SUSPENDED, DELISTED, CIRCUIT_BREAK.
- StrategyState: CANDIDATE → SIMULATION → EVIDENCE_REVIEW → ACTIVE → MONITORING → SUSPENDED → RETIRED.
- PortfolioState: tracks open positions, realized P&L, daily P&L.
- ModelState: TRAINING → STAGING → VALIDATED → APPROVED → LIVE → MONITORING → RETIRED.
- StateTransition: permitted transitions between states; illegal transitions rejected.

**Constitutional relationship:** Provides the vocabulary for SCC-I rules.

---

## SUPPLEMENT C — DEPENDENCY CATALOGUE

This supplement provides the complete dependency registry for all IIOS engines
and workflows. Every dependency is classified by type, criticality, and failure behavior.

---

### C.1 Engine Dependency Registry

Each row describes a direct dependency relationship: the consumer engine
depends on the provider engine.

`
+-----+----------------------+----------------------+----------+---------+----------+
| ID  | Consumer             | Provider             | Type     | Crit.   | Degrade  |
+-----+----------------------+----------------------+----------+---------+----------+
| D01 | Information Engine   | Database Persistence | Storage  | HIGH    | In-memory|
| D02 | Entity Engine        | Information Engine   | Data     | HIGH    | Stale    |
| D03 | Entity Engine        | Database Persistence | Storage  | HIGH    | In-memory|
| D04 | Relationship Engine  | Entity Engine        | Data     | NORMAL  | Stale    |
| D05 | Relationship Engine  | Information Engine   | Data     | NORMAL  | Stale    |
| D06 | Event Engine         | Entity Engine        | Data     | HIGH    | Partial  |
| D07 | Event Engine         | Temporal Engine      | Time     | HIGH    | Approx   |
| D08 | Event Engine         | Information Engine   | Data     | HIGH    | Stale    |
| D09 | Temporal Engine      | Database Persistence | Storage  | CRITICAL| None     |
| D10 | Spatial Engine       | Entity Engine        | Data     | NORMAL  | Stale    |
| D11 | Spatial Engine       | Database Persistence | Storage  | NORMAL  | In-memory|
| D12 | Knowledge Engine     | Information Engine   | Data     | CRITICAL| Cache    |
| D13 | Knowledge Engine     | Entity Engine        | Data     | CRITICAL| Cache    |
| D14 | Knowledge Engine     | Relationship Engine  | Data     | HIGH    | Cache    |
| D15 | Knowledge Engine     | Event Engine         | Data     | HIGH    | Cache    |
| D16 | Knowledge Engine     | Temporal Engine      | Time     | HIGH    | Cache    |
| D17 | Knowledge Engine     | Spatial Engine       | Context  | NORMAL  | Skip     |
| D18 | State Engine         | Knowledge Engine     | Knowledge| HIGH    | Stale    |
| D19 | State Engine         | Event Engine         | Events   | HIGH    | Partial  |
| D20 | State Engine         | Temporal Engine      | Time     | HIGH    | Approx   |
| D21 | Prediction Engine    | Knowledge Engine     | Knowledge| CRITICAL| None     |
| D22 | Prediction Engine    | State Engine         | State    | HIGH    | Stale    |
| D23 | Prediction Engine    | Temporal Engine      | Time     | HIGH    | Approx   |
| D24 | Prediction Engine    | Event Engine         | Events   | NORMAL  | Reduced  |
| D25 | Learning Engine      | Knowledge Engine     | Knowledge| HIGH    | Delayed  |
| D26 | Learning Engine      | State Engine         | History  | HIGH    | Partial  |
| D27 | Learning Engine      | Prediction Engine    | Errors   | HIGH    | Delayed  |
| D28 | Decision Engine      | Prediction Engine    | Predict  | CRITICAL| None     |
| D29 | Decision Engine      | Risk Engine          | Budget   | CRITICAL| None     |
| D30 | Decision Engine      | Knowledge Engine     | Context  | HIGH    | Degraded |
| D31 | Decision Engine      | Governance Engine    | Auth     | CRITICAL| None     |
| D32 | Risk Engine          | Knowledge Engine     | Market   | CRITICAL| None     |
| D33 | Risk Engine          | State Engine         | Positions| CRITICAL| None     |
| D34 | Risk Engine          | Prediction Engine    | Volatility| HIGH   | Degraded |
| D35 | Risk Engine          | Portfolio Engine     | Alloc    | CRITICAL| None     |
| D36 | Portfolio Engine     | Risk Engine          | Limits   | CRITICAL| None     |
| D37 | Portfolio Engine     | Decision Engine      | Decisions| HIGH    | None     |
| D38 | Portfolio Engine     | Knowledge Engine     | Prices   | HIGH    | Stale    |
| D39 | Portfolio Engine     | State Engine         | Reconcil | HIGH    | Stale    |
| D40 | Strategy Engine      | Knowledge Engine     | Regime   | HIGH    | Degraded |
| D41 | Strategy Engine      | Prediction Engine    | Signals  | HIGH    | Reduced  |
| D42 | Strategy Engine      | Risk Engine          | Limits   | HIGH    | Suspended|
| D43 | Strategy Engine      | Learning Engine      | Perf     | NORMAL  | Stale    |
| D44 | Strategy Engine      | Simulation Engine    | Evidence | HIGH    | Blocked  |
| D45 | Simulation Engine    | Strategy Engine      | Candidates| HIGH   | Wait     |
| D46 | Simulation Engine    | Risk Engine          | Constr.  | HIGH    | Degraded |
| D47 | Simulation Engine    | Knowledge Engine     | History  | HIGH    | Partial  |
| D48 | Simulation Engine    | State Engine         | Hist.St  | NORMAL  | Approx   |
| D49 | Governance Engine    | Knowledge Engine     | Compliance| HIGH   | SAFE     |
| D50 | Governance Engine    | Decision Engine      | Requests | HIGH    | Block    |
| D51 | Governance Engine    | Simulation Engine    | Evidence | HIGH    | Block    |
| D52 | Governance Engine    | Learning Engine      | Updates  | HIGH    | Block    |
| D53 | Master Orchestrator  | All engines          | Control  | CRITICAL| Manual   |
+-----+----------------------+----------------------+----------+---------+----------+
`

**Criticality Scale:**
- CRITICAL: Dependency failure requires immediate SAFE mode activation.
- HIGH: Dependency failure degrades quality; recovery within 5 minutes.
- NORMAL: Dependency failure reduces capability; recovery within 30 minutes.

---

### C.2 Dependency Resolution Order

When starting IIOS from cold state, engines must start in the following order
to satisfy all dependencies before the dependent engine starts.

`
Tier 1 (No dependencies):
  [1a] Database Persistence Architecture

Tier 2 (Depends only on Tier 1):
  [2a] Temporal Engine
  [2b] Information Engine

Tier 3 (Depends on Tier 1 and 2):
  [3a] Entity Engine
  [3b] Spatial Engine

Tier 4 (Depends on Tier 1, 2, 3):
  [4a] Relationship Engine
  [4b] Event Engine

Tier 5 (Depends on all lower tiers):
  [5a] Knowledge Engine

Tier 6 (Depends on Knowledge Engine):
  [6a] State Engine

Tier 7 (Depends on Knowledge and State):
  [7a] Prediction Engine
  [7b] Portfolio Engine (partial init)

Tier 8 (Depends on Knowledge, State, Prediction):
  [8a] Learning Engine
  [8b] Risk Engine (requires Portfolio Engine)
  [8c] Decision Engine (requires Prediction + Risk)
  [8d] Strategy Engine

Tier 9 (Depends on Strategy, Risk, Knowledge):
  [9a] Simulation Engine

Tier 10 (Depends on Decision, Simulation, Knowledge):
  [10a] Governance Engine

Tier 11 (All engines registered):
  [11a] Master Orchestrator activation complete
`

---

### C.3 Circular Dependency Handling

Three circular dependencies exist by design:

**Circular-01: Risk Engine and Portfolio Engine**
Risk Engine needs portfolio state (from Portfolio Engine).
Portfolio Engine needs risk limits (from Risk Engine).
Resolution: Portfolio Engine initializes with zero positions; Risk Engine
initializes with maximum budgets. After both are up, they synchronize through
the defined handshake protocol. The ordering protocol: Portfolio Engine
provides allocation first; Risk Engine applies limits; Portfolio Engine confirms.

**Circular-02: Decision Engine and Governance Engine**
Decision Engine requests authorization from Governance Engine.
Governance Engine must be aware of Decision Engine requests.
Resolution: Governance Engine is always initialized before Decision Engine
starts accepting requests (Tier 10 before Tier 8 requests are enabled).

**Circular-03: Learning Engine and Prediction Engine**
Learning Engine updates Prediction Engine models.
Prediction Engine reports errors to Learning Engine.
Resolution: Learning Engine operates in one-way mode (model update only) until
both engines have completed a full session cycle. Error reporting begins only
after the first session.

---

## SUPPLEMENT D — WORKFLOW CATALOGUE

This supplement provides the complete catalog of all IIOS workflows.
Workflow IDs are of the form WF-SYS-{NN} for system-level workflows.

---

### D.1 Workflow Registry

`
+----------+---------------------------+-------------+----------+---------+--------+
| ID       | Name                      | Trigger     | State    | Priority| SLA    |
+----------+---------------------------+-------------+----------+---------+--------+
| WF-SYS-01| System Startup            | T-60 command| Any      | CRITICAL| 60 min |
| WF-SYS-02| Market Open               | 09:15 event | OPERTNL  | CRITICAL| 60 sec |
| WF-SYS-03| Observation Flow          | 30s schedule| ACTIVE   | HIGH    | 30 sec |
| WF-SYS-04| Information Flow          | Data arrival| ACTIVE   | HIGH    | 10 sec |
| WF-SYS-05| Knowledge Flow            | Obs complete| ACTIVE   | HIGH    | 15 sec |
| WF-SYS-06| Prediction Flow           | Know updated| ACTIVE   | HIGH    | 50 ms  |
| WF-SYS-07| Decision Flow             | Preds ready | ACTIVE   | HIGH    | 200 ms |
| WF-SYS-08| Risk Flow                 | Continuous  | ACTIVE   | CRITICAL| 30 sec |
| WF-SYS-09| Portfolio Flow            | 60s schedule| ACTIVE   | HIGH    | 60 sec |
| WF-SYS-10| Strategy Flow             | 5m / signal | ACTIVE   | NORMAL  | 5 min  |
| WF-SYS-11| Learning Flow             | Post-session| SHUTDWN  | NORMAL  | 2 hr   |
| WF-SYS-12| Simulation Flow           | Request     | Any      | NORMAL  | varies |
| WF-SYS-13| Governance Flow           | 5m / request| ACTIVE   | HIGH    | 30 sec |
| WF-SYS-14| System Shutdown           | 15:30 event | ACTIVE   | CRITICAL| 30 min |
| WF-SYS-15| Recovery                  | Failure det | Any      | CRITICAL| 15 min |
| WF-SYS-16| Maintenance               | Scheduled   | SHUTDOWN | NORMAL  | 2 hr   |
| WF-SYS-17| Emergency Stop            | Kill switch | Any      | CRITICAL| 5 sec  |
| WF-SYS-18| Human Override            | Operator req| Any      | HIGH    | 30 sec |
+----------+---------------------------+-------------+----------+---------+--------+
`

---

### D.2 Workflow Dependency Map

Some workflows are nested (one workflow triggers another as a sub-workflow):

`
WF-SYS-01 (Startup)
  └── WF-SYS-04 (Information Flow: activated as part of data layer startup)
  └── WF-SYS-05 (Knowledge Flow: activated to warm up cache)
  └── WF-SYS-13 (Governance Flow: pre-session certification)

WF-SYS-02 (Market Open)
  └── WF-SYS-03 (first Observation cycle)
  └── WF-SYS-06 (first Prediction cycle)
  └── WF-SYS-08 (Risk monitoring activated)
  └── WF-SYS-13 (opening Governance check)

WF-SYS-03 (Observation)
  └── WF-SYS-04 (Information Flow for this observation cycle)
  └── WF-SYS-05 (Knowledge Flow for this observation cycle)

WF-SYS-07 (Decision)
  └── WF-SYS-08 (Risk pre-filter)
  └── WF-SYS-13 (Governance authorization)

WF-SYS-14 (Shutdown)
  └── WF-SYS-11 (Learning Flow triggered post-session)

WF-SYS-17 (Emergency Stop)
  └── WF-SYS-14 (Orderly shutdown after stop)
`

---

### D.3 Workflow Conflict Resolution

When two workflows request the same resource simultaneously:

**Priority order:** CRITICAL > HIGH > NORMAL > LOW > DEFERRED
**Conflict types:**
- CRITICAL vs CRITICAL: first-come-first-served; second waits.
- CRITICAL vs any lower: CRITICAL preempts after completing atomic operations.
- Emergency Stop vs any: Emergency Stop always wins with 1-second preemption.

**Workflow timeout policy:**
- CRITICAL workflows: if no progress in 2 minutes, P1 incident raised.
- HIGH workflows: if no progress in 5 minutes, P2 incident raised.
- NORMAL workflows: if no progress in 30 minutes, P3 incident raised.

---

### D.4 Workflow Instance Lifecycle

Every workflow execution follows this lifecycle:

`
REQUESTED → QUEUED → RUNNING → [COMPLETED | FAILED | TIMED_OUT | CANCELLED]
`

State transitions:
- REQUESTED: workflow trigger received by Master Orchestrator.
- QUEUED: workflow scheduled (may be waiting for resource or prior workflow).
- RUNNING: actively executing; OC-02 tracking progress.
- COMPLETED: all stages completed successfully; success criteria met.
- FAILED: stage failed; failure handling invoked; Recovery Manager notified.
- TIMED_OUT: workflow exceeded SLA; escalated to incident.
- CANCELLED: operator cancelled or Emergency Stop issued.

All workflow instance state transitions are logged permanently.

---

## SUPPLEMENT E — INTERFACE CATALOGUE (LOGICAL)

This supplement documents the logical interfaces between IIOS engines.
This is an architectural description only — not an API specification.

---

### E.1 Interface Naming Convention

Engine-level interfaces are named: INTF-{SOURCE_ENGINE_CODE}-{CONSUMER_ENGINE_CODE}-{FUNCTION}

---

### E.2 Knowledge Engine Interfaces

**INTF-KNW-PRD-SNAPSHOT:** Knowledge Engine provides knowledge snapshots to Prediction Engine.
- Logical content: Current knowledge snapshot including entity properties, regime classification,
  recent events, relationship weights, and confidence scores.
- Freshness guarantee: snapshot is at most 5 minutes old (cache refresh interval).
- Access pattern: Prediction Engine reads at start of each prediction cycle.

**INTF-KNW-DEC-CONTEXT:** Knowledge Engine provides decision context to Decision Engine.
- Logical content: Entity context, regime assessment, recent knowledge updates relevant
  to decision candidates.

**INTF-KNW-RSK-MARKET:** Knowledge Engine provides market risk data to Risk Engine.
- Logical content: VIX level, market breadth, sector rotation, regime, global context.

**INTF-KNW-STG-REGIME:** Knowledge Engine provides regime classification to Strategy Engine.
- Logical content: Current regime, regime confidence, regime history.

**INTF-KNW-SIM-HISTORY:** Knowledge Engine provides historical data to Simulation Engine.
- Logical content: Historical knowledge snapshots for any point-in-time query.
  No live data is accessible through this interface from Simulation Engine.

---

### E.3 Risk Engine Interfaces

**INTF-RSK-DEC-BUDGET:** Risk Engine provides risk budget to Decision Engine.
- Logical content: Available risk budget per strategy; blocked instruments list;
  current daily P&L vs limit; current VIX.
- Update frequency: Every 30 seconds; also on demand (pre-decision check).

**INTF-RSK-PFO-LIMITS:** Risk Engine provides position limits to Portfolio Engine.
- Logical content: Maximum position size per instrument, maximum exposure per strategy,
  current VaR utilization.

**INTF-RSK-STG-CONSTRAINTS:** Risk Engine provides risk constraints to Strategy Engine.
- Logical content: Per-strategy risk budget, strategy-level limits, active drawdown warnings.

---

### E.4 Governance Engine Interfaces

**INTF-GOV-DEC-AUTH:** Governance Engine provides decision authorization to Decision Engine.
- Logical content: AUTHORIZED or BLOCKED status, reason code, certificate ID.
- Latency SLA: < 30 milliseconds.

**INTF-GOV-MO-CERT:** Governance Engine provides session certificate to Master Orchestrator.
- Logical content: DAILY_SESSION_CERTIFICATE with issuance timestamp, validity window,
  authorized strategies list, and compliance status.

**INTF-GOV-MO-HALT:** Governance Engine sends HALT signal to Master Orchestrator.
- Logical content: HALT type (VIX/LOSS/GOVERNANCE), triggering condition, timestamp.

---

### E.5 Prediction Engine Interfaces

**INTF-PRD-DEC-PREDICTIONS:** Prediction Engine provides predictions to Decision Engine.
- Logical content: List of prediction objects with instrument ID, direction, magnitude estimate,
  confidence [0.0-1.0], model version, validity timestamp.
- Validity window: 5 minutes from generation.

**INTF-PRD-RSK-VOLATILITY:** Prediction Engine provides volatility forecasts to Risk Engine.
- Logical content: Expected volatility per instrument for risk modeling.

---

### E.6 Portfolio Engine Interfaces

**INTF-PFO-RSK-ALLOCATION:** Portfolio Engine provides allocations to Risk Engine.
- Logical content: Current position list, current exposure per strategy, total portfolio value,
  current daily P&L.

**INTF-PFO-DEC-CAPITAL:** Portfolio Engine provides available capital to Decision Engine.
- Logical content: Available capital per strategy for new positions.

---

### E.7 Decision Engine Interfaces

**INTF-DEC-GOV-REQUEST:** Decision Engine submits authorization request to Governance Engine.
- Logical content: Decision candidate details, current score, risk assessment summary,
  requesting strategy ID.

**INTF-DEC-PFO-DECISION:** Decision Engine sends approved decisions to Portfolio Engine.
- Logical content: Approved decision with instrument, direction, size, strategy ID, Decision ID.

---

### E.8 State Engine Interfaces

**INTF-STE-ALL-STATE:** State Engine provides current state to all consuming engines.
- Access pattern: Read-on-demand; consuming engines query State Engine for relevant state.
- Logical content: Typed state objects per category (SystemState, MarketState, EntityState,
  StrategyState, PortfolioState).

---

### E.9 Master Orchestrator Interfaces

**INTF-MO-ALL-CONTROL:** Master Orchestrator sends control signals to all engines.
- Logical content: Lifecycle commands (START, STOP, RESTART, HEALTH_CHECK),
  configuration updates, workflow progress signals.

**INTF-ALL-MO-HEALTH:** All engines send health signals to Master Orchestrator.
- Logical content: Health status (HEALTHY/DEGRADED/OFFLINE), component metrics,
  incident notifications.

---

### E.10 Interface Governance

All interfaces are:
- **Typed:** Every field in every interface has a defined type from the relevant ontology.
- **Versioned:** Interface versions are tracked; breaking changes require new version.
- **Monitored:** Interface call latency and success rate are tracked by the Monitoring Manager.
- **Audited:** All authorization interfaces (Governance) log every request and response.

---

## SUPPLEMENT F — OPERATIONAL RUNBOOK

The Operational Runbook provides step-by-step procedures for all planned and
unplanned operational activities.

---

### F.1 Standard Daily Startup (Tier 2 Operations Lead)

**Start time:** 08:00 IST daily (weekdays)
**Duration:** Approximately 60 minutes

`
08:00 — Verify VPS containers are starting (check Telegram startup notification)
08:05 — Confirm Foundation validation complete (Telegram: "Foundation OK")
08:15 — Confirm data layer engines healthy (Telegram: "Data layer OK")
08:30 — Confirm knowledge layer engines healthy (Telegram: "Knowledge layer OK")
08:45 — Review previous day's session governance report
         - Check for any outstanding compliance issues
         - Verify no evidence dossiers expired overnight
09:00 — Confirm Governance Engine has issued DAILY_SESSION_CERTIFICATE
         (Telegram: "Session certificate issued for YYYY-MM-DD")
09:10 — Review strategy list (Telegram: "X strategies active for today's session")
09:12 — Confirm OHS >= 0.80 (Telegram: "OHS=0.NN — NOMINAL/OPTIMAL")
09:15 — Market opens; IIOS enters INTRADAY_ACTIVE state automatically
`

If any step fails: See F.2 (Startup Failure Procedure).

---

### F.2 Startup Failure Procedure

If startup has not reached OPERATIONAL state by 09:10:

`
1. Check Telegram for last status notification and identify failing stage.
2. For Stage 1-2 failures (Foundation/Data Layer):
   - SSH to VPS and check container logs: docker logs ai-trading-brain --tail 100
   - If DB error: check disk space; run database integrity check.
   - If data source error: check Dhan/yfinance connectivity.
3. For Stage 3-5 failures (Knowledge/State/Intelligence Layer):
   - Check specific engine startup log.
   - Attempt engine restart: docker compose restart ai-trading-brain
4. For Stage 7 failure (Governance Certificate denied):
   - Review Governance Engine report for denial reason.
   - Common causes: evidence dossier expired, compliance violation from previous day.
   - Resolve blocking condition and trigger re-certification.
5. If unresolved by 09:05: send SAFE_MODE_TODAY message to stakeholders.
   IIOS will not trade today; operator monitors positions manually.
`

---

### F.3 Intraday Monitoring (Tier 2)

`
Every 30 minutes during trading hours (active monitoring if P1 alert pending):

09:45 — Check Telegram for any alerts from previous 30 minutes
10:15 — Review strategy P&L vs daily targets
10:45 — [same as above]
...continuing every 30 minutes through 15:00...
15:00 — Note any open positions that need monitoring through close
15:30 — Confirm IIOS transitions to SHUTDOWN state at market close
15:45 — Review session governance report
`

---

### F.4 Incident Response: P1 — Engine OFFLINE

`
Alert received: "P1 ALERT: [Engine Name] OFFLINE at [timestamp]"

1. Immediately open VPS SSH connection.
2. Run: docker logs ai-trading-brain --tail 200 | Select-String "[Engine Name]"
3. Determine failure cause:
   a. Memory exhaustion: increase container memory limit; restart.
   b. Dependency failure: check the engine's dependencies first.
   c. Data corruption: restore from last backup; verify integrity.
   d. Network partition: check internal network; restart affected containers.
4. If SAFE mode is active (expected during P1):
   - Verify open positions are being monitored by Risk Engine in read-only mode.
   - Do NOT manually close positions unless explicitly instructed by System Owner.
5. After recovery: confirm OHS returns to >= 0.80 within 15 minutes.
6. If OHS does not recover in 15 minutes: escalate to CRITICAL recovery (WF-SYS-15).
7. Complete incident record within 2 hours.
`

---

### F.5 Incident Response: P1 — Daily Loss Limit Triggered

`
Alert received: "P1 HALT: Daily loss limit 2% reached. All trading halted."

1. IIOS has already halted all new decisions. NO ACTION REQUIRED for halt itself.
2. Do NOT attempt to re-enable trading today. The limit is constitutional.
3. Review open positions:
   - If positions have active stop-loss orders: monitor automated exit.
   - If positions lack exit orders: assess manually with System Owner.
4. Document the triggering session in the incident log.
5. At end of day: review what strategies contributed to the loss.
6. Next morning: Governance Engine will require review of the loss event
   before issuing a new session certificate.
`

---

### F.6 Incident Response: P1 — Emergency VIX Spike

`
Alert received: "P1 HALT: VIX=47.3 exceeds kill threshold 45. Session halted."

1. IIOS has halted automatically. NO ACTION REQUIRED for halt itself.
2. Confirm via external source that VIX is genuinely elevated (not data error).
3. If data error (VIX is not actually elevated):
   - Identify the faulty data source.
   - Initiate a data source correction through Information Engine override.
   - Document the false alarm.
4. If genuine crisis:
   - Monitor open positions; assess risk exposure.
   - Brief System Owner on current portfolio state.
   - IIOS resumes automatically next trading day if VIX returns to <= 45.
5. All actions documented in incident log within 4 hours.
`

---

### F.7 Weekly Maintenance (Saturday Operations Lead)

`
09:00 — Connect to VPS; verify system is in WEEKEND_SHUTDOWN state.
09:15 — Run strategy performance report for the week.
09:30 — Review all P3 and P4 incidents from the week; close or escalate.
10:00 — Run evidence dossier expiry check (any expiring in next 14 days?).
10:30 — Trigger Walk-Forward Test for any strategy showing degradation.
11:00 — Run database integrity check.
11:15 — Verify backup completed successfully; test restore of one file.
11:30 — Review Governance compliance log for the week.
12:00 — Perform maintenance database compaction.
13:00 — Generate weekly report for Architecture Council distribution.
`

---

### F.8 Evidence Dossier Renewal

When a strategy's evidence dossier approaches its 30-day expiry:

`
Day -7 from expiry: Telegram reminder "Strategy [X] evidence dossier expires in 7 days"

1. Submit strategy [X] to Simulation Engine (WF-SYS-12).
2. Confirm simulation completes with most recent 12-month historical window.
3. Review evidence dossier: Sharpe > 0.8, Win Rate >= 50%, MaxDD < 15%?
4. Submit to Governance Engine for review.
5. If approved: strategy continues active with renewed dossier.
6. If rejected (criteria not met): strategy enters SUSPENDED state automatically.
   Notify System Owner of rejection with evidence dossier summary.
`

---

### F.9 New Strategy Deployment

`
Step 1: Strategy candidate definition
  - Define strategy logic (in Strategy Engine format)
  - Define all parameters with ranges for optimization
  - Define target instruments and regime conditions

Step 2: Simulation submission
  - Submit to Simulation Engine (WF-SYS-12)
  - Allow 1-4 days for full backtest + WFT + Monte Carlo
  - Review evidence dossier

Step 3: Governance review
  - If evidence dossier meets criteria: submit to Governance Engine
  - Governance Engine reviews compliance and constitutional alignment
  - If approved: strategy enters ACTIVE state

Step 4: Paper trading validation
  - New strategies run in PAPER mode for minimum 5 sessions
  - Review paper trading outcomes
  - If consistent with simulation: promote to LIVE

Step 5: Live monitoring
  - Strategy monitored for first 20 sessions with heightened attention
  - Any significant deviation from simulated behavior triggers re-simulation
`

---

## SUPPLEMENT G — FAILURE CATALOGUE

This supplement catalogs all defined failure modes for IIOS, classified by
severity, detection mechanism, and initial response.

**Failure Record ID Format:** IIOS-FAIL-{CATEGORY}-{SEQ:04d}

---

### G.1 System-Level Failures

**FAIL-SYS-0001: Cold Start Failure**
Severity: P2
Description: System fails to complete WF-SYS-01 (startup) within the 60-minute window.
Detection: Master Orchestrator startup timeout.
Root causes: Database unavailable; ontology load failure; governance certificate denied.
Initial response: Review startup logs; identify failing stage; resolve and retry.

**FAIL-SYS-0002: OHS Below CRITICAL**
Severity: P1
Description: Orchestrator Health Score falls below 0.35.
Detection: OHS calculation cycle.
Root causes: Multiple engine failures; infrastructure degradation.
Initial response: SAFE mode activated; P1 alert to operator; WF-SYS-15 initiated.

**FAIL-SYS-0003: Coordination Loss**
Severity: P1-CRITICAL
Description: Master Orchestrator becomes unresponsive.
Detection: External health check on container health endpoint.
Root causes: Memory exhaustion; deadlock; infrastructure failure.
Initial response: Container restart; state restoration from persistence.

**FAIL-SYS-0004: Calendar Desync**
Severity: P3
Description: Temporal Engine calendar data is out of sync (missing holiday).
Detection: Market opens on a day the Temporal Engine classifies as holiday.
Root causes: Incomplete calendar update; holiday calendar refresh failure.
Initial response: Manual calendar correction; Temporal Engine state refresh.

---

### G.2 Data Layer Failures

**FAIL-DATA-0001: Primary Data Source Failure**
Severity: P2
Description: Dhan data feed becomes unavailable.
Detection: Information Engine source health check.
Root causes: Broker API failure; network partition; token expiry (Dhan 451 error).
Initial response: Automatic failover to yfinance; alert generated.
Escalation: If yfinance also fails, KNOWLEDGE_STALE signal; SAFE mode evaluation.

**FAIL-DATA-0002: Data Quality Degradation**
Severity: P3
Description: High volume of InformationObjects failing quality threshold.
Detection: Information Engine quality metrics exceed rejection rate threshold.
Root causes: Upstream data provider quality issue; network packet loss.
Initial response: Flag downstream engines; accept reduced-quality data with annotation.

**FAIL-DATA-0003: Knowledge Cache Miss Rate Spike**
Severity: P3
Description: Knowledge Engine cache miss rate exceeds 20%.
Detection: Cache metrics in Monitoring Manager.
Root causes: Cache invalidation overload; regime change causing many cache refreshes.
Initial response: Review cache invalidation triggers; temporary cache refresh rate increase.

**FAIL-DATA-0004: Historical Data Gap**
Severity: P3
Description: Missing historical data for a significant time window in the knowledge graph.
Detection: Simulation Engine query returning incomplete data.
Root causes: Data source historical gap; migration issue.
Initial response: Identify missing window; re-fetch from available source; document gap.

---

### G.3 Intelligence Layer Failures

**FAIL-INT-0001: Prediction Quality Collapse**
Severity: P2
Description: Prediction Engine confidence scores systematically below 0.5 for all candidates.
Detection: Prediction quality metrics in Decision Engine.
Root causes: Regime shift with no regime-appropriate model; stale knowledge input;
  model corruption.
Initial response: Decision Engine stops producing decisions (no candidates pass threshold).
  Learning Engine flagged for emergency regime-model analysis.

**FAIL-INT-0002: Decision Score Threshold Not Reached**
Severity: P4
Description: All candidates score below 6.5; no decisions produced for an extended period.
Detection: Decision Engine zero-decision monitoring.
Root causes: Market conditions not conducive to high-confidence decisions.
  This is NORMAL and DESIRED behavior — IIOS does not force decisions.
Initial response: Log and monitor. No remediation needed unless caused by engine failure.

**FAIL-INT-0003: Learning Engine Model Promotion Failure**
Severity: P3
Description: Updated model fails Simulation Engine validation and cannot be promoted.
Detection: Governance Engine rejection of model update.
Root causes: Model overfit on limited data; model improvement insufficient vs baseline.
Initial response: Current live model continues unchanged; investigation of training data.

**FAIL-INT-0004: State Reconciliation Failure**
Severity: P2
Description: Portfolio Engine position reconciliation fails (position count mismatch).
Detection: Portfolio Engine reconciliation error flag.
Root causes: Execution confirmation missing; state corruption; restart during execution.
Initial response: Halt new decisions; manual portfolio state verification; P1 escalation
  if discrepancy involves live positions.

---

### G.4 Risk and Financial Layer Failures

**FAIL-RSK-0001: Risk Engine Unresponsive**
Severity: P1-CRITICAL
Description: Risk Engine fails to respond to health check.
Detection: Master Orchestrator heartbeat timeout.
Root causes: Memory exhaustion; unhandled exception; circular dependency deadlock.
Initial response: IMMEDIATE SAFE MODE. No new decisions. Automatic restart attempt.
  If restart fails in 2 minutes: P1 escalation to operator.

**FAIL-RSK-0002: VaR Computation Failure**
Severity: P2
Description: Risk Engine cannot compute VaR for current portfolio.
Detection: Risk Engine internal error flag.
Root causes: Missing historical data; correlation matrix computation failure.
Initial response: Use last-known VaR with degraded-mode flag; alert operator.

**FAIL-RSK-0003: Kill-Switch False Trigger**
Severity: P2
Description: Kill switch triggers on incorrect data (e.g., VIX data spike from feed error).
Detection: Operator review after halt; cross-reference VIX on alternative source.
Root causes: Information Engine data quality failure not caught by quality filter.
Initial response: Document false trigger; review data quality thresholds;
  consider requiring cross-source confirmation for VIX kill-switch.

**FAIL-RSK-0004: Daily Loss Limit Pre-Breach**
Severity: P1
Description: Daily loss reaches 2% limit.
Detection: Risk Engine continuous monitoring.
Root causes: Adverse market conditions; strategy losses; position sizing error.
Initial response: This is correct system behavior. All decisions halted automatically.
  Document in incident log; review contributing strategies; no remediation to circuit breaker.

---

### G.5 Governance Layer Failures

**FAIL-GOV-0001: Session Certificate Denial**
Severity: P1
Description: Governance Engine refuses to issue DAILY_SESSION_CERTIFICATE.
Detection: Governance Engine session certification attempt.
Root causes: Evidence dossier expired; previous-day compliance violation unresolved;
  system health below governance minimum.
Initial response: Identify denial reason; resolve blocking condition;
  re-submit for certification. IIOS does not trade without certificate.

**FAIL-GOV-0002: Governance Engine Unresponsive**
Severity: P1-CRITICAL
Description: Governance Engine fails to respond to requests.
Detection: Master Orchestrator heartbeat timeout.
Root causes: Engine crash; resource exhaustion.
Initial response: IMMEDIATE SAFE MODE. No decision authorizations possible.
  Automatic restart. If restart fails in 2 minutes: P1 escalation.

**FAIL-GOV-0003: Compliance Rule Violation Detected**
Severity: P2
Description: Governance Engine detects a constitutional violation in recent operations.
Detection: Governance Engine continuous compliance monitoring.
Root causes: Implementation bug; configuration drift; override applied without proper logging.
Initial response: Halt the affected workflow or strategy; document violation;
  review with Architecture Council.

---

### G.6 Failure Severity Classification

| Severity | Definition                                       | Response Time | Escalation |
|----------|--------------------------------------------------|--------------|------------|
| P1       | Active trading at risk; kill switch relevant     | < 5 minutes  | Immediate Telegram |
| P2       | Quality degraded; recovery needed               | < 30 minutes | Telegram + email |
| P3       | Non-critical issue; scheduled fix acceptable    | < 4 hours    | Daily report |
| P4       | Low priority; normal behavior or cosmetic       | < 1 week     | Weekly report |

---

## SUPPLEMENT H — RECOVERY CATALOGUE

This supplement catalogs recovery procedures for all defined failure modes.

**Recovery Record ID Format:** REC-{SEVERITY}-{YYYYMMDD}-{SEQ:04d}

---

### H.1 Recovery Principles

1. **Safety First:** Every recovery starts in SAFE mode. No recovery attempt
   while IIOS is still trying to process live decisions.

2. **State from Persistence:** Recovery never relies on in-memory state from
   a crashed process. All state is restored from the Database Persistence layer.

3. **No Position Modification:** Recovery never creates, modifies, or closes
   investment positions. Position management is exclusively a human decision
   during and after recovery.

4. **Documented Response:** Every recovery event produces a Recovery Record
   before the recovery is considered complete.

5. **Verification Before Resume:** After recovery, OHS must confirm >= 0.60
   (DEGRADED) or >= 0.80 (NOMINAL) before operations resume.

---

### H.2 Recovery Procedures by Failure Mode

**REC-PROC-01: Single Engine Recovery (FAIL-SYS-0002 / FAIL-RSK-0001)**

`
Step 1: Master Orchestrator detects engine OFFLINE.
Step 2: SAFE mode activated (decision-making halted).
Step 3: Identify dependency chain — check if failed engine's dependencies are healthy.
Step 4: Resolve dependencies if needed (recursive recovery up the dependency chain).
Step 5: Restart failed engine container component.
Step 6: Engine loads state from Database Persistence.
Step 7: Engine passes internal health check.
Step 8: Engine re-registers with Master Orchestrator Engine Registry.
Step 9: Master Orchestrator recomputes OHS.
Step 10: If OHS >= 0.80: exit SAFE mode; resume NOMINAL operations.
         If OHS >= 0.60: exit SAFE mode; resume DEGRADED operations.
         If OHS < 0.60: remain in SAFE mode; escalate to operator.
`

**Recovery Time Target:** < 5 minutes for ISOLATED single-engine failures.

---

**REC-PROC-02: Data Feed Failover (FAIL-DATA-0001)**

`
Step 1: Information Engine detects primary source (Dhan) unavailable.
Step 2: Automatic failover to secondary source (yfinance).
Step 3: KNOWLEDGE_DEGRADED signal broadcast (not SAFE mode — degraded operation continues).
Step 4: Downstream engines annotate outputs as DEGRADED_SOURCE.
Step 5: Operations Lead notified via Telegram P3 alert.
Step 6: Monitor primary source recovery; switch back when available.
Step 7: On switchback: no re-computation needed (cache will refresh on next cycle).
`

**Recovery Time Target:** < 30 seconds (automatic failover).

---

**REC-PROC-03: Knowledge Engine Cache Rebuild (FAIL-DATA-0003)**

`
Step 1: Knowledge Engine detects cache health degraded.
Step 2: Knowledge Engine triggers full cache rebuild.
Step 3: Rebuild reads from Database Persistence (not from live feed).
Step 4: Rebuild typically completes within 2 minutes.
Step 5: All consuming engines notified via KNOWLEDGE_CACHE_READY signal.
Step 6: Normal operations resume.
`

**Recovery Time Target:** < 2 minutes.

---

**REC-PROC-04: State Reconciliation Recovery (FAIL-INT-0004)**

`
Step 1: Portfolio Engine detects reconciliation failure.
Step 2: SAFE mode activated.
Step 3: Portfolio Engine reads position records from Database Persistence.
Step 4: Portfolio Engine requests position confirmation from execution records.
Step 5: Discrepancies identified and logged.
Step 6: Operations Lead reviews discrepancies; resolves manually.
Step 7: Portfolio Engine updated with correct state.
Step 8: Reconciliation re-run; confirmed clean.
Step 9: SAFE mode deactivated; operations resume.
`

**Recovery Time Target:** < 30 minutes.

---

**REC-PROC-05: Governance Certificate Recovery (FAIL-GOV-0001)**

`
Step 1: Identify reason for certificate denial.

Case A: Evidence dossier expired:
  a. Identify expired strategies.
  b. Trigger emergency simulation (WF-SYS-12) for expired strategies.
  c. If simulation passes: resubmit for certification.
  d. If simulation fails: strategies suspended for the session.
  e. Certification re-attempted with remaining active strategies.

Case B: Compliance violation unresolved:
  a. Review previous day's compliance violation details.
  b. Operations Lead resolves the issue (parameter correction, strategy suspension).
  c. Governance Engine re-run with resolved state.
  d. Certification re-attempted.

Case C: System health below governance minimum:
  a. Resolve health issue (engine recovery per REC-PROC-01).
  b. Governance Engine re-run after health confirmation.
  c. Certification re-attempted.
`

---

**REC-PROC-06: Full System Recovery from Backup (Tier 4 Disaster)**

`
Step 1: Declare CATASTROPHIC failure; notify Tier 1 + Tier 2.
Step 2: Provision new VPS or restore existing VPS.
Step 3: Deploy Docker composition from source code.
Step 4: Restore Database from most recent backup.
Step 5: Verify database integrity (hash check).
Step 6: Start system via WF-SYS-01 (Cold Start variant).
Step 7: Knowledge Engine rebuilds cache from restored database.
Step 8: Governance Engine reviews restored state for compliance.
Step 9: System enters paper trading mode for 1 session before live trading.
Step 10: Declare recovery complete; document in post-incident review.
`

**Recovery Time Target:** < 4 hours from backup restore initiation.

---

### H.3 Recovery Escalation Matrix

| Failure Scope | Auto-Recovery | Tier 2 Required | Tier 1 Required |
|---------------|--------------|-----------------|-----------------|
| ISOLATED (1 engine) | Yes (auto) | Notification only | No |
| PARTIAL (2-4 engines) | Yes (auto) | Authorization | No |
| CRITICAL (5+ engines) | No | Authorization + Oversight | Notification |
| CATASTROPHIC (MO/Infra) | No | Authorization + Oversight | Authorization |

---

### H.4 Post-Recovery Verification

After any recovery, the following verification steps apply:

1. OHS recomputed and confirmed at appropriate threshold.
2. Knowledge Engine cache confirmed fresh.
3. Portfolio Engine reconciliation confirmed clean.
4. Governance Engine confirms no compliance violations introduced during recovery.
5. Recovery Record created and archived.
6. For P1/P2 recoveries: Operations Lead confirms decision to resume.

---

## SUPPLEMENT I — ARCHITECTURE DECISION RECORDS

Architecture Decision Records (ADRs) document the significant architectural
decisions made during IIOS design. Each ADR captures the context, options
considered, decision made, and consequences.

**ADR ID Format:** ISDR-{SEQ:03d}

---

### ISDR-001: IIOS as a Multi-Engine Operating System, Not a Monolith

**Status:** ACCEPTED
**Date:** Architecture inception
**Decision Makers:** Architecture Council

**Context:**
The first IIOS design question was whether to build one integrated investment
intelligence system or a collection of specialized engines. A monolithic system
is simpler initially but becomes harder to maintain, test, and evolve. A
multi-engine system is more complex to coordinate but allows each domain to be
mastered independently.

**Options Considered:**
1. Monolithic system: one codebase, all functions integrated.
2. Microservices architecture: each engine a separate service.
3. Layered engine architecture with centralized coordination.

**Decision:** Option 3 — Layered engine architecture with Master Orchestrator.

**Rationale:** Monolith violates the separation of concerns principle; every
domain expert would be working in the same codebase. Microservices add networking
complexity without architectural benefit at IIOS's scale. Layered engines with
a coordinator provides isolation, testability, and extensibility while keeping
coordination manageable.

**Consequences:** Requires a Master Orchestrator; requires interface definitions
between engines; startup sequence is more complex. These costs are worth paying
for the architectural clarity.

---

### ISDR-002: Ontology-First Information Model

**Status:** ACCEPTED
**Date:** Architecture inception

**Context:**
IIOS processes many types of information (prices, fundamentals, events, macro data).
A design choice must be made: do engines receive typed data or raw bytes?

**Options Considered:**
1. Raw data: engines handle their own parsing and classification.
2. Semi-structured: loosely typed dictionaries or JSON passed between engines.
3. Ontology-typed: all data assigned to ontological types before distribution.

**Decision:** Option 3 — Ontology-typed data model.

**Rationale:** Raw data creates N parsing implementations for N engines, each with
its own bugs. Semi-structured data provides no guarantees about content.
Ontology-typed data provides a single authoritative classification at the boundary
(Information Engine) and ensures all downstream engines reason about the same
well-defined concepts.

**Consequences:** Requires 7 ontologies to be defined before any engine starts.
All engines must be updated when ontologies are extended. The ontology-first
approach adds initial design time but pays compound dividends in downstream clarity.

---

### ISDR-003: Five-Minute Knowledge Cache for Performance

**Status:** ACCEPTED
**Date:** Performance optimization phase

**Context:**
The Knowledge Engine is on the critical path of every decision cycle. If every
prediction or decision required a fresh knowledge query, the decision cycle would
be limited by Knowledge Engine throughput.

**Options Considered:**
1. No cache: every engine query fetches fresh data.
2. Per-request cache: cached on demand with short TTL.
3. Background-refresh 5-minute cache: Knowledge Engine maintains fresh snapshot
   independently; engines read from snapshot.

**Decision:** Option 3 — Background-refresh 5-minute cache.

**Rationale:** A 5-minute cache aligns with the intraday investment decision time frame.
IIOS does not trade on second-by-second signals; the 5-minute knowledge window is
appropriate for the investment horizon. Background refresh decouples the cache lifecycle
from the request cycle, eliminating per-request latency spikes.

**Measured Impact:** Reduced GlobalIntelligence layer time from > 500ms to 17ms.
Decision cycle from > 2,000ms to 172ms.

**Consequences:** Knowledge used in decisions can be up to 5 minutes old. For
IIOS's investment horizon (intraday, not high-frequency), this is acceptable.
The 5-minute limit is configurable within [1, 15] minutes.

---

### ISDR-004: Constitutional Kill Switches as Inviolable Rules

**Status:** ACCEPTED
**Date:** Risk governance phase

**Context:**
IIOS needed to define what happens when market conditions become extremely adverse.
Two approaches: (1) risk engine adjusts parameters dynamically, or (2) hard limits
that halt all activity unconditionally.

**Options Considered:**
1. Dynamic risk adjustment: reduce position sizes as losses accumulate.
2. Hard kill switches at defined thresholds with no override.
3. Soft kill switches that can be overridden by operator.

**Decision:** Option 2 — Hard kill switches as constitutional rules.

**Rationale:** Option 1 creates an illusion of control but allows losses to compound
incrementally. Option 3 creates temptation to override exactly when it is most
dangerous to do so. Hard kill switches provide the only robust protection against
behavioral biases in crisis conditions. The 2% daily loss limit and VIX > 45
thresholds were chosen because they represent clearly abnormal conditions.

**Consequences:** IIOS cannot trade on extreme-volatility days. This is intentional
and beneficial: the expected cost of missed opportunity on crisis days is far lower
than the expected cost of unrestricted trading during a crisis.

---

### ISDR-005: Governance Engine as Constitutional Authority

**Status:** ACCEPTED
**Date:** Governance design phase

**Context:**
IIOS requires a mechanism to enforce constitutional rules. Two approaches:
(1) distribute constitutional checks across all engines, or (2) centralize
constitutional enforcement in a dedicated Governance Engine.

**Options Considered:**
1. Distributed enforcement: each engine enforces its own rules.
2. Centralized Governance Engine: single authoritative enforcer.
3. Hybrid: local enforcement + governance audit.

**Decision:** Option 2 — Centralized Governance Engine.

**Rationale:** Distributed enforcement creates N implementations of constitutional
logic with N points of failure or inconsistency. The Governance Engine is the
single point of truth for constitutional compliance. Its authority is unambiguous:
it is the final authority within its constitutional domain.

**Consequences:** Governance Engine is a critical single point of failure.
The OHS weights the Governance Engine highly; any impairment triggers SAFE mode.
The Governance Engine's privileged position is a deliberate architectural choice,
not an oversight.

---

### ISDR-006: Learning Isolated from Live Trading

**Status:** ACCEPTED
**Date:** Learning Engine design phase

**Context:**
Should the Learning Engine update models continuously (online learning) during
trading hours, or only post-session (offline learning)?

**Options Considered:**
1. Online learning: models update continuously from live outcomes.
2. Offline learning: learning runs only post-session.
3. Deferred online learning: updates computed live but applied only post-session.

**Decision:** Option 2 — Offline learning only.

**Rationale:** Online learning creates the risk of model drift during a live session.
A model that was performing well at 09:30 might behave differently at 14:00 due to
mid-session learning updates. For an investment system where decisions have P&L
consequences, model stability during a session is more valuable than marginal
within-session model improvement.

**Consequences:** Models improve between sessions, not within sessions. This is
the correct tradeoff for IIOS's investment horizon and risk tolerance.

---

### ISDR-007: Strategy Evidence Dossier Requirement

**Status:** ACCEPTED
**Date:** Strategy governance phase

**Context:**
How should IIOS decide which strategies are permitted to run in live trading?
Options range from unrestricted (any strategy can run) to highly controlled (extensive
validation required).

**Options Considered:**
1. No restriction: any strategy can run in live trading.
2. Basic backtest requirement: strategies must show positive historical performance.
3. Full evidence dossier: backtest + WFT + Monte Carlo + Governance approval.

**Decision:** Option 3 — Full evidence dossier required.

**Rationale:** Option 1 creates unacceptable risk. Option 2 is vulnerable to
overfitting. The full evidence dossier (backtest + WFT + Monte Carlo) is the
minimum standard for institutional-grade strategy deployment. The Governance Engine
review adds the compliance and constitutional alignment check that a pure statistical
approach cannot provide.

**Consequences:** New strategy deployment takes 1-4 days (simulation time) plus
governance review. This is an intentional friction that prevents hasty deployments.

---

### ISDR-008: Master Orchestrator Without Investment Knowledge

**Status:** ACCEPTED
**Date:** Orchestrator design phase

**Context:**
Should the Master Orchestrator have any knowledge of investment logic to make
better scheduling decisions? For example, should it prioritize prediction cycles
during high-volatility periods?

**Options Considered:**
1. Investment-aware orchestrator: schedules based on market conditions.
2. Investment-neutral orchestrator: schedules based purely on workflow rules.

**Decision:** Option 2 — Investment-neutral orchestrator.

**Rationale:** An investment-aware orchestrator blurs the boundary between
coordination and analysis. If the Orchestrator can interpret market conditions
to prioritize cycles, it is already performing a form of investment analysis.
This violates ISDR-001's principle of separation of concerns. The correct approach:
investment engines request priority escalation when needed; the Orchestrator
responds to those requests without understanding their market rationale.

**Consequences:** The Orchestrator may occasionally schedule a prediction cycle
later than ideal from a market timing perspective. This is acceptable: the
Orchestrator's neutrality is architecturally more valuable than marginal scheduling
optimization.

---

### ISDR-009: SQLite as Primary Persistence Layer

**Status:** ACCEPTED
**Date:** Infrastructure design phase

**Context:**
What database technology should IIOS use for its primary persistence layer?

**Options Considered:**
1. PostgreSQL: full-featured relational database; requires separate server process.
2. SQLite: embedded relational database; no server process required.
3. MongoDB: document store; flexible schema.
4. In-memory only with periodic file dumps.

**Decision:** Option 2 — SQLite.

**Rationale:** IIOS is a single-instance system (one VPS, one set of processes).
PostgreSQL adds operational complexity (separate server, connection management,
backup complexity) without meaningful benefit at IIOS's data volume. SQLite
provides full ACID compliance, structured query support, and excellent performance
for IIOS's access patterns (mostly append-heavy writes + structured reads).
The operational simplicity of SQLite aligns with IIOS's deployment model.

**Consequences:** SQLite has concurrency limitations (one writer at a time).
IIOS's architecture is compatible with this limitation — engines queue writes
through the Database Persistence Architecture rather than writing directly.

---

### ISDR-010: Docker Compose for Deployment

**Status:** ACCEPTED
**Date:** Deployment design phase

**Context:**
IIOS runs on a VPS with two primary components: the trading brain and the Streamlit
dashboard. How should these be deployed?

**Decision:** Docker Compose with two containers (ai-trading-brain, trading-dashboard).

**Rationale:** Docker provides environment consistency between development and production.
Docker Compose allows both containers to be managed together with defined networking
and shared volume (data/ directory). The --no-cache build ensures source code changes
are always included. The health check endpoints enable automated monitoring.

**Consequences:** All code changes require a full docker compose build + redeploy cycle.
The deployment rule (git commit → push → SSH deploy → verify healthy) ensures no
split-brain between local and VPS code.

---

### ISDR-011: 30-Day Evidence Dossier Validity

**Status:** ACCEPTED
**Date:** Strategy governance phase

**Context:**
Evidence dossiers must expire to ensure strategies are periodically re-validated.
How long should a dossier remain valid?

**Options Considered:**
1. 7 days: very frequent re-simulation; high operational overhead.
2. 30 days: monthly re-validation; reasonable overhead.
3. 90 days: quarterly; lower overhead but strategies may drift.
4. No expiry: one-time validation forever.

**Decision:** Option 2 — 30 days.

**Rationale:** Financial market regimes can shift meaningfully within weeks.
A 30-day validity window ensures strategies are re-validated against recent market
conditions approximately monthly. This aligns with the monthly operational review
cycle. The 7-day window would create too much operational overhead for the
simulation pipeline.

**Consequences:** Operations must monitor evidence dossier expiry. The 7-day
advance warning in the operational runbook (Supplement F.8) provides adequate
lead time for renewal.

---

### ISDR-012: Paper Trading Mode as Production Validation Gate

**Status:** ACCEPTED
**Date:** Deployment design phase

**Context:**
How should new deployments be validated before live trading? Should there be a
paper trading phase?

**Decision:** All new deployments run in paper trading mode for at minimum 5 sessions
before live trading is enabled.

**Rationale:** Paper trading validates that the full system (not just simulation)
behaves as expected in live market conditions. Simulations use historical data; paper
trading uses live data. Discrepancies between simulation and paper trading behavior
reveal implementation issues before real capital is at risk.

**Consequences:** New strategy and system deployments have a minimum 5-session
(1-week) paper trading validation period before live trading. This is a valuable
investment in operational confidence.

---

### ISDR-013: Telegram as Primary Alerting Channel

**Status:** ACCEPTED
**Date:** Monitoring design phase

**Context:**
IIOS needs a real-time alerting channel for P1 and P2 incidents. What channel?

**Decision:** Telegram Bot as primary channel; email as secondary for daily reports.

**Rationale:** Telegram provides immediate push notifications to any device.
The operator is assumed to monitor Telegram throughout trading hours. The Telegram
Bot integration already exists and provides 13 operational commands.

**Consequences:** IIOS alerting depends on Telegram infrastructure availability.
If Telegram is unavailable, P1 alerts may be missed. Mitigation: the Streamlit
dashboard provides an alternative monitoring interface.

---

### ISDR-014: Single-Instance Architecture

**Status:** ACCEPTED
**Date:** Architecture inception

**Context:**
Should IIOS support horizontal scaling (multiple instances)?

**Decision:** Single-instance architecture.

**Rationale:** IIOS's investment decisions must be made from a single consistent
portfolio state. Multiple instances would require distributed consensus on portfolio
state, position limits, and risk budgets — introducing complexity and failure modes
that are not warranted at IIOS's current scale.

**Consequences:** IIOS cannot distribute computation across multiple servers.
Performance must be achieved through architecture (caching, parallel engine startup,
background processes) rather than horizontal scaling.

---

### ISDR-015: Human Override Authority Scope

**Status:** ACCEPTED
**Date:** Governance design phase

**Context:**
To what extent should human operators be able to override IIOS decisions?

**Decision:** Full authority within constitutional constraints; zero authority over
constitutional rules.

**Rationale:** Human operators must retain full control over operational decisions
(which strategies to run, whether to trade today, what parameters to use within
bounds). But constitutional rules exist precisely because they must not bend under
the psychological pressures of live trading. An operator who can override the 2%
daily loss limit will be tempted to do so exactly when they should not.

**Consequences:** Operators may occasionally find constitutional rules frustrating
when they believe the rules are preventing a good trade. This frustration is the
price of the protection the rules provide.

---

## SUPPLEMENT J — COMPREHENSIVE GLOSSARY

This glossary defines every term, acronym, and identifier used in IIOS architecture
documents. Definitions are authoritative; any ambiguity in architecture documents
resolves by referring to this glossary.

Terms are organized alphabetically within four sections:
J.1 — Core System Terms
J.2 — Engine and Component Terms
J.3 — Ontology Terms
J.4 — Operational and Process Terms

---

### J.1 CORE SYSTEM TERMS

**ADR (Architecture Decision Record):**
A document capturing a significant architectural decision made during IIOS design.
Each ADR records: context, options considered, decision, rationale, and consequences.
ADR IDs take the form ISDR-{SEQ:03d}.

**Architectural Stratum:**
One of the seven layers of the IIOS engine architecture. Strata are numbered 1 (Foundation)
through 7 (Coordination). Higher-stratum engines depend on lower-stratum engines.
Dependencies never flow downward (higher-stratum engines are never called by lower-stratum engines).

**Architecture Council:**
The Tier 1 governance authority responsible for IIOS architecture documents, ontologies,
and constitutional rules. Consists of the Principal Architect and System Owner.

**AUTOMATED classification:**
The governance approval classification for actions that the Governance Engine may
authorize without human intervention. Examples: individual trade decisions, intraday
parameter checks.

**Backward Compatibility:**
The property of ontology extensions that ensures existing ontological types and
properties are never removed or renamed. Backward compatibility is a constitutional
requirement.

**Backtest:**
A simulation of a strategy's performance using historical data. Backtest results are
one component of an evidence dossier. Backtest alone is not sufficient for strategy
promotion; Walk-Forward Testing and Monte Carlo are also required.

**Budget (Risk):**
The maximum amount of portfolio risk that a strategy or the overall portfolio may
consume in a defined period. Risk budgets are managed by the Risk Engine. Consumed
budget reduces available budget for new positions.

**Business Continuity:**
IIOS's ability to resume operations after a disruption with defined Recovery Time
Objective (RTO) targets. See SQS dimension 8.13.

**Cache (Knowledge Engine):**
The 5-minute performance optimization in the Knowledge Engine that pre-computes a
knowledge snapshot and makes it available to consuming engines without per-request
database queries. The cache is refreshed in background every 5 minutes.

**Calibration (Prediction):**
The process of ensuring that stated prediction confidence scores correspond to actual
prediction accuracy. A well-calibrated model that states 70% confidence should be
correct approximately 70% of the time. Calibration curves are maintained by the
Learning Engine and applied by the Prediction Engine.

**Candidate:**
A financial instrument that has been selected by the Decision Engine for scoring
consideration. Candidates must have prediction confidence >= 0.5 to enter the
scoring process.

**Certificate:**
A signed record issued by the Governance Engine certifying that a condition has been
met. Types: DAILY_SESSION_CERTIFICATE (per trading session), DECISION_AUTHORIZED
(per decision), STRATEGY_APPROVED (per strategy deployment), MODEL_PROMOTION_APPROVED
(per model update). All certificates are timestamped and stored permanently.

**Circuit Breaker:**
A market mechanism that halts trading in a security or market when price moves
exceed defined limits. The Event Engine detects circuit breaker events. IIOS treats
circuit-broken instruments as untradeable for the remainder of the circuit period.

**Constitutional Rule:**
An inviolable architectural rule in the IIOS Constitution. Constitutional rules
cannot be overridden by operators, engine configuration, or emergency conditions.
They are classified NNH (Non-Negotiable HARD), HARD, or SOFT.

**Cooldown:**
The mandatory waiting period between two investment decisions on the same instrument
(default: 30 minutes). The cooldown prevents rapid-fire decisions driven by noisy
signals on the same instrument.

**DAILY_SESSION_CERTIFICATE:**
The pre-session certificate issued by the Governance Engine that authorizes IIOS to
enter INTRADAY_ACTIVE state. Without a valid certificate, no trading session can begin.

**Debate (Decision Engine):**
The 5-agent multi-perspective evaluation that every decision candidate undergoes
before final scoring. Agents: Analyst (technical), Fundamentals, Risk, Macro,
Devil's Advocate. The debate produces a consensus score adjustment [+/- 1.5] applied
to the raw decision score.

**Decision Record:**
The permanent audit record created for every authorized investment decision. Contains:
observation chain, knowledge snapshot, predictions, risk assessment, debate summary,
authorization certificate, and final decision parameters.
ID format: ODEC-{YYYYMMDD}-{SEQ:08d}.

**Decision Score:**
The composite score [0.0, 10.0] computed by the Decision Engine for each candidate.
Threshold for proceeding: 6.5. Score below 6.5 results in candidate rejection.
Score components: prediction confidence (35%), risk-adjusted return estimate (25%),
market regime alignment (20%), strategy conviction (15%), historical pattern (5%).

**Dependency Depth:**
The number of engine layers a given engine sits above the foundation layer.
Database Persistence = depth 0. Master Orchestrator = depth 8.

**DEGRADED (OHS tier):**
OHS 0.60–0.79. System is operational but with reduced quality. Not all engines
may be healthy. Operations continue with annotations.

**Dossier (Evidence):**
See Evidence Dossier.

**Dynamic Risk Adjustment:**
The real-time modification of risk parameters by the Risk Engine based on current
market conditions. Distinct from Constitutional Kill Switches: dynamic adjustment
operates within constitutional limits; kill switches enforce constitutional limits.

---

**Engine:**
A specialized software component implementing one functional domain of IIOS intelligence.
IIOS has 18 defined engines. Each engine has an architecture document with document code.
Engines communicate through the Master Orchestrator.

**Engine Registry:**
The Master Orchestrator's authoritative list of registered engines. Only registered
engines participate in workflows. The Engine Registry is managed by OC-08 (Engine
Registry component of the Master Orchestrator).

**Evidence Dossier:**
The complete evidence package produced by the Simulation Engine for a strategy candidate,
required before any strategy enters live trading. Contains: backtest results, Walk-Forward
Test results, Monte Carlo analysis, promotion recommendation, and simulation metadata.
Validity: 30 days from issuance. Produced by WF-SYS-12.

**Execution Engine:**
The IIOS component (outside the IIOS intelligence boundary) that receives authorized
investment decisions from the Master Orchestrator and routes them to the broker interface.
The Execution Engine is referenced in IIOS architecture but is not an intelligence engine.

**Extensibility:**
The property of IIOS that allows new capabilities (engines, ontology types, workflows)
to be added without modifying existing components. Extensibility is a constitutional
requirement (SCC-X).

---

**Failure Cascade:**
The propagation of a single engine failure to impact other engines through dependency
relationships. Failure cascades are modeled in Supplement G and the Engine Interaction
Matrix (Part IV).

**False Positive (Event):**
A detected event that is later determined to not have occurred or to have been detected
in error. False positive events are annotated in the Event Engine record rather than
deleted (immutability rule SCC-F-002).

**Foundation Document:**
The Master Knowledge Architecture document that establishes IIOS's governing philosophy,
architectural identity, and design principles. The Foundation Document is the first
constitutional input to this integration architecture.

**Freshness:**
The property of information or knowledge that indicates how recently it was obtained.
Freshness degrades over time. Stale information is annotated with a freshness flag.
The Knowledge Engine cache provides a freshness guarantee bounded by the 5-minute
refresh interval.

---

**Global Intelligence:**
IIOS's overnight assessment of global market context (S&P 500, Nikkei, bonds, FX,
commodity markets) that informs the first knowledge snapshot of each trading day.
Provided by the GlobalDataAI component in the current IIOS implementation.

**Governance Certificate:**
See Certificate.

**Governance Engine:**
The Stratum 6 engine responsible for enforcing constitutional rules, issuing
session certificates, authorizing decisions, and maintaining continuous compliance
monitoring. The Governance Engine is the supreme authority within its constitutional
domain.

**Governance Integration Point (GIP):**
One of the 7 defined points in IIOS workflows where the Governance Engine performs
a mandatory check. No workflow can bypass a GIP. The 7 GIPs are: pre-session
certification, strategy deployment gate, decision authorization, model update approval,
kill-switch confirmation, emergency stop authorization, and human override validation.

**Governance Tier (Tier 1, 2, 3):**
The three-tier governance ownership model: Architecture Council (Tier 1), Operations
Lead (Tier 2), Governance Engine (Tier 3).

---

**HARD (constitutional rule classification):**
A constitutional rule that cannot be overridden during live trading. Amendment requires
Architecture Council approval. Less strict than NNH but still binding in operations.

**Health Check:**
The periodic verification that an engine is functioning correctly. Health checks are
performed by the Master Orchestrator's Health Manager (OC-15). Engines that fail health
checks are transitioned to DEGRADED or OFFLINE state.

**Horizontal Integration:**
A defined peer relationship between two engines that both produce for and consume from
each other. Three horizontal integrations exist in IIOS: Risk-Portfolio, Decision-Governance,
Learning-Prediction. All others are vertical (producer-to-consumer in one direction).

---

**Immutability:**
The property of records that prevents modification after creation. Decision Records,
audit records, event records, and knowledge assertions are all immutable. Updates
create new versions; old versions are archived.

**Incident:**
A classified deviation from expected behavior requiring a documented response.
Incidents are classified P1 (critical) through P4 (low). All incidents have defined
response times and escalation paths. Incident Records are permanent.

**Information Freshness Decay:**
The automatic reduction in an InformationObject's quality score as time passes since
its reception. Old information is less reliable; freshness decay models this.

**InformationObject:**
The typed data container produced by the Information Engine for all market data.
InformationObjects carry: type classification, quality score, provenance, temporal
annotation, and content.

**INTRADAY_ACTIVE:**
The system state during live market hours (09:15–15:30 IST) when IIOS is fully
operational and producing investment decisions.

**IST (Indian Standard Time):**
The authoritative time zone for all IIOS operations. UTC+5:30. Market hours:
09:15–15:30 IST. Pre-market: 08:00–09:15 IST.

---

**Kill Switch:**
A constitutional mechanism that immediately halts all new investment activity when
a defined threshold is breached. The two primary kill switches are: daily loss >= 2%
and VIX > 45. Kill switches cannot be overridden.

**Knowledge Accumulation:**
The ongoing growth of the IIOS knowledge graph as new entities, relationships,
events, and patterns are observed across sessions. Knowledge accumulation is the
mechanism through which IIOS develops institutional memory over time.

**Knowledge Graph:**
The integrated, structured representation of everything IIOS knows about the
market, entities, relationships, and events. Maintained by the Knowledge Engine.
The foundation of all IIOS intelligence.

**Knowledge Snapshot:**
A point-in-time read of the Knowledge Engine's cache, containing a consistent
view of current knowledge for use in a single prediction or decision cycle.

---

**Latency Budget:**
The maximum total time allocation for a complete decision cycle. IIOS's nominal
latency budget is 172ms (17ms knowledge + 15ms risk/state + 140ms decision/governance).

**Learning Feedback Loop:**
The closed-loop process through which trade outcomes are attributed to predictions,
prediction errors are computed, models are updated, and better predictions are produced
in future sessions. The Learning Engine manages this loop.

**Lifecycle:**
The defined state machine for a IIOS component (strategy, engine, model, ontology).
Each lifecycle has defined states and permitted transitions governed by the State Ontology.

**Look-Ahead Bias:**
The use of future data in a historical prediction or backtest calculation. Look-ahead
bias is a constitutional violation (SCC-K-005, SCC-G-004). All prediction features
must use only data available at prediction time.

---

**Mark-to-Market:**
The calculation of open position value using current market prices. The Portfolio Engine
performs mark-to-market on all open positions every 60 seconds.

**Market Regime:**
The classified state of the overall market environment. IIOS recognizes six regimes:
BULL, BEAR, SIDEWAYS, HIGH_VOLATILITY, LOW_VOLATILITY, CRISIS. Regime classification
is the exclusive function of the Knowledge Engine. Regime drives strategy selection,
prediction model selection, and risk parameter adjustments.

**Master Knowledge Architecture:**
The Foundation Document that establishes the governing philosophy and architectural
principles of IIOS. The Master Knowledge Architecture is the first constitutional
input to all IIOS design.

**Model:**
A prediction algorithm trained on historical data to forecast market direction,
magnitude, or volatility. Models are versioned, validated, and governed. See ModelState
in the State Ontology.

**Model Promotion:**
The process of moving a model from STAGING (testing) to LIVE (production).
Requires Simulation Engine validation and Governance Engine approval.
Constitutionally governed by SCC-L-003.

**Monte Carlo Analysis:**
A simulation technique using randomly generated scenario paths (minimum 1,000 paths)
to estimate the distribution of strategy outcomes under uncertainty. Required for all
evidence dossiers.

---

**NNH (Non-Negotiable HARD):**
The strictest constitutional rule classification. NNH rules are permanently binding
under all circumstances. No constitutional amendment process can relax an NNH rule;
NNH rules can only be amended by replacing the entire constitutional framework.

**Nominal (OHS tier):**
OHS 0.80–0.94. System is in standard operating condition. All major engines healthy.
Normal operations permitted.

**Observation Cycle:**
The 30-second recurring workflow (WF-SYS-03) that refreshes all market data,
updates knowledge, and provides the input stream for prediction and decision cycles.

**OHS (Orchestrator Health Score):**
The weighted composite health score [0.0, 1.0] computed by the Master Orchestrator
every 30 seconds from all 22 component health scores. Thresholds: OPTIMAL (>=0.95),
NOMINAL (>=0.80), DEGRADED (>=0.60), CRITICAL (>=0.35), FAILED (<0.35).

**Operations Lead:**
The Tier 2 governance authority responsible for day-to-day operational decisions,
monitoring, and override authorization within constitutional bounds.

**OPTIMAL (OHS tier):**
OHS >= 0.95. System is performing at peak; all components healthy with no degradation.

**Orchestrator Health Score:**
See OHS.

**Out-of-Sample Testing:**
See Walk-Forward Testing.

**Overfitting:**
The statistical problem where a model learns the noise in training data rather than
genuine patterns, resulting in poor performance on new data. The evidence dossier
requirement (backtest + WFT + Monte Carlo) is designed to detect and reject overfit strategies.

---

**P&L (Profit and Loss):**
The financial performance metric tracked by the Portfolio Engine. Open P&L is
mark-to-market on all positions; realized P&L is from closed positions.
Total P&L = open + realized. The daily P&L is compared against the 2% loss limit.

**P1/P2/P3/P4:**
Incident severity classifications. P1: critical, immediate response required.
P2: significant, 30-minute response. P3: non-critical, 4-hour response. P4: low, weekly.

**Paper Trading:**
Investment decision simulation where decisions are recorded but no real orders are placed.
IIOS paper trading mode produces identical decision records and performance tracking
without capital exposure. Required for new deployment validation (minimum 5 sessions).

**Portfolio State:**
The authoritative record of all open positions, capital allocations, and P&L.
Maintained by the Portfolio Engine, stored in the State Engine.

**Prediction Validity Window:**
The 5-minute period during which a prediction is considered fresh and may be consumed
by the Decision Engine. Predictions older than 5 minutes are expired and not used.

**Promotion Criteria:**
The minimum performance thresholds that a strategy or model must meet to be promoted
from simulation to live trading: Sharpe Ratio > 0.8, Win Rate >= 50%, Max Drawdown < 15%.

**Provenance:**
The complete attribution trail for a piece of information, knowledge assertion, or
investment decision. Provenance includes: source, timestamp, transformation chain,
quality score, and attributing engine.

---

**Quality Score:**
The numerical measure [0.0, 1.0] of information or prediction reliability.
Information quality is assessed by the Information Engine. Prediction quality
(confidence) is assessed by the Prediction Engine. Both feed into the Decision Engine
scoring process.

**Readiness Certification:**
The 12-phase process (CP-01 through CP-12) that must be completed before IIOS enters
PRODUCTION_READY state. See Part X for full certification framework.

**Regime:**
See Market Regime.

**Regime-Strategy Compatibility:**
The mapping between market regimes and strategy performance expectations.
Strategies are weighted by their compatibility with the current regime. Strategies
with low compatibility for the current regime are temporarily suspended.

**Relationship Weight:**
The numerical strength of a relationship between two entities. Correlation weights
range [-1.0, 1.0]. Other relationship strengths range [0.0, 1.0]. All weights are
time-varying and archived historically.

**Recovery Record:**
The permanent documentation of a recovery event, including scope, duration,
affected engines, resolution steps, and operator involved.
ID format: REC-{SEVERITY}-{YYYYMMDD}-{SEQ:04d}.

**Recovery Time Objective (RTO):**
The maximum acceptable time to restore a function after failure. IIOS RTOs:
ISOLATED: 5 min; PARTIAL: 15 min; CRITICAL: 60 min; CATASTROPHIC: 4 hours.

**Reconciliation:**
The process of verifying consistency between Portfolio Engine position records
and execution confirmation records. Reconciliation runs after every trade execution.
Discrepancies are P2 incidents.

**Resilience:**
IIOS's ability to withstand, recover from, and adapt to adverse conditions.
The Master Orchestrator's SAFE mode and recovery procedures implement resilience.

**RTO:**
See Recovery Time Objective.

---

**SAFE mode:**
The operating state that IIOS enters when health is compromised. In SAFE mode:
no new investment decisions are produced; existing position monitoring continues;
Risk Engine remains active in read-only mode.

**Session:**
A single trading day in which IIOS enters INTRADAY_ACTIVE state. A session begins
with the DAILY_SESSION_CERTIFICATE and ends with system shutdown at 15:30 IST.

**Sharpe Ratio:**
A risk-adjusted performance metric = (portfolio return - risk-free rate) / standard deviation.
IIOS requires Sharpe > 0.8 for strategy promotion.

**Signal:**
A strategy-generated recommendation to enter or exit a position. Signals are forwarded
to the Decision Engine as prediction inputs. A signal does not directly create a trade;
it enters the Decision Engine's scoring process.

**SOFT (constitutional rule classification):**
A constitutional rule that can be adjusted within defined bounds by Tier 2 during
normal operations. Unlike HARD and NNH rules, SOFT rules acknowledge operational
flexibility within the defined policy range.

**SQS (System Quality Score):**
The weighted composite quality score [0.0, 1.0] computed from all 13 quality dimensions.
Tiers: EXCELLENT (>=0.88), GOOD (>=0.75), ACCEPTABLE (>=0.60), MARGINAL (>=0.40), FAILED (<0.40).

**Staging Environment:**
The isolated environment where model updates and configuration changes are tested
before promotion to live. Staging is completely isolated from live data paths.

**State Engine:**
The Stratum 5 engine that maintains authoritative system, entity, portfolio, and
strategy state. The single source of truth for all state-dependent operations.

**State Machine:**
A formal model of an entity's lifecycle as a set of states and permitted transitions.
All IIOS state machines are defined in the State Ontology.

**State Transition:**
A permitted change from one state to another, as defined in the State Ontology.
Invalid state transitions are rejected and logged as incidents.

**Strategy:**
A defined investment approach with explicit parameters, entry/exit rules, risk limits,
and target instruments. Strategies must have valid evidence dossiers to operate in
live trading. Strategies have a defined lifecycle (CANDIDATE through RETIRED).

**Stratum:**
See Architectural Stratum.

**System Owner:**
The individual responsible for IIOS at the business and operational level.
Together with the Principal Architect, forms the Architecture Council (Tier 1).

---

**Temporal Annotation:**
The time context attached to every IIOS data object, knowledge assertion, and decision
record by the Temporal Engine. Temporal annotations include: event timestamp, validity period,
time horizon, and market session reference.

**Temporal Engine:**
The Stratum 4 engine that provides authoritative time context for all IIOS operations.
Manages the trading calendar, session events, and time horizon references.

**Threshold:**
A defined value that triggers a state change or action when crossed. Constitutional
thresholds include: decision score >= 6.5, daily loss >= 2%, VIX > 45,
strategy drawdown >= 15%, prediction confidence >= 0.5.

**Tier 1:**
See Architecture Council.

**Tier 2:**
See Operations Lead.

**Tier 3:**
The automated governance layer (Governance Engine). Enforces rules in real time.

**Time Horizon:**
The investment perspective for a prediction or decision. IIOS recognizes:
INTRADAY (< 1 day), DAILY (1 day), WEEKLY (5 days), MONTHLY (20+ days).

**Trading Calendar:**
The authoritative schedule of NSE trading days, market holidays, and half-days.
Maintained by the Temporal Engine. Refreshed annually.

**Trading Session:**
See Session.

**Traceability:**
The property of every IIOS decision that allows its full provenance to be reconstructed
from the audit record. See Decision Record. Traceability is a constitutional requirement.

---

**Universe:**
The set of financial instruments that IIOS actively tracks and can make investment
decisions on. The universe is defined by the Entity Engine and governs which instruments
can be candidates in any given session.

**Update (Knowledge):**
The process of incorporating new information into the knowledge graph. Updates create
new fact versions; they do not modify existing versions.

**Update (Model):**
The process of revising prediction model parameters based on learning outcomes.
All updates go through STAGING before LIVE promotion.

---

**Validation:**
The process of confirming that a model, strategy, or system component meets defined
quality criteria before promotion to live. Validation is performed by the Simulation
Engine for strategies and models, and by the full certification process (Part X) for
the system.

**VaR (Value at Risk):**
The maximum expected loss at a given confidence level over a defined time period.
IIOS uses 95th percentile VaR with a 1-day horizon for position risk assessment.

**VIX:**
The CBOE Volatility Index, a measure of implied market volatility. IIOS uses the
NSE VIX equivalent. VIX > 45 triggers the constitutional kill switch.

**Volatility:**
A measure of the degree of variation in a financial instrument's price over time.
Volatility predictions are generated by the Prediction Engine and used by the Risk
Engine for position sizing and risk assessment.

---

**Walk-Forward Testing (WFT):**
A validation technique that tests strategy performance on out-of-sample data by
training on a historical window and testing on a subsequent window not seen during training.
IIOS requires a minimum of 3 WFT windows for strategy promotion.

**Win Rate:**
The fraction of closed trades that are profitable (P&L > 0). IIOS requires
Win Rate >= 50% for strategy promotion and continued operation.

**Workflow:**
A defined sequence of steps coordinated by the Master Orchestrator to accomplish
a specific operational objective. IIOS defines 18 system-level workflows (WF-SYS-01
through WF-SYS-18). All workflows are defined before live trading begins;
no ad hoc workflows are created during live sessions.

**Workflow Instance:**
A specific execution of a defined workflow. Each workflow instance has a unique ID
(WF-{PIPELINE_CODE}-{YYYYMMDD}-{SEQ:08d}).

**Workflow Instance Lifecycle:**
The defined state progression of a workflow execution:
REQUESTED → QUEUED → RUNNING → [COMPLETED | FAILED | TIMED_OUT | CANCELLED].

---

### J.2 ENGINE AND COMPONENT TERMS

**OC-01 through OC-22:** The 22 Master Orchestrator components, divided into 4 tiers:
- Tier A (Scheduling): OC-01 Master Scheduler, OC-02 Workflow Manager, OC-03 Dependency Manager, OC-04 Execution Coordinator, OC-05 Priority Manager.
- Tier B (Coordination): OC-06 Resource Manager, OC-07 Agent Coordinator, OC-08 Engine Registry, OC-09 Engine Discovery, OC-10 Communication Manager, OC-11 Message Router, OC-12 Conflict Resolver, OC-13 Synchronization Manager.
- Tier C (Operational): OC-14 State Manager, OC-15 Health Manager, OC-16 Monitoring Manager, OC-17 Incident Manager, OC-18 Recovery Manager, OC-19 Analytics Manager, OC-20 Reporting Manager.
- Tier D (Infrastructure): OC-21 Version Manager, OC-22 Configuration Manager.

**OHS:** See Orchestrator Health Score.

**OS-01 through OS-15:** The 15 Master Orchestrator services. Examples include:
Scheduling Service, Workflow Lifecycle Service, Health Monitoring Service,
Communication Service, Recovery Service, Audit Service.

**OP-01 through OP-14:** The 14 Master Orchestrator workflow pipelines.

**OT-01 through OT-16:** The 16 Orchestration Taxonomy domains (Workflow, Knowledge,
Observation, Prediction, Decision, Risk, Portfolio, Learning, Strategy, Simulation,
Governance, AI Agent, Resource, Infrastructure, Incident, Recovery Orchestration).

---

### J.3 ONTOLOGY TERMS

**Entity ID:** The permanent, immutable identifier assigned to a financial entity when
first discovered. Format defined by the Entity Ontology.

**Knowledge Assertion:** A factual claim in the knowledge graph with confidence score,
source, and timestamp. The atomic unit of knowledge in IIOS.

**KnowledgeProvenanceChain:** The complete attribution record for a knowledge assertion,
from raw data source through all transformation steps to final fact.

**MarketState:** The ontological state of the market: MARKET_CLOSED, PRE_MARKET,
INTRADAY_ACTIVE, POST_MARKET, MARKET_HOLIDAY.

**ModelState:** The lifecycle state of a prediction model: TRAINING, STAGING, VALIDATED,
APPROVED, LIVE, MONITORING, RETIRED.

**OQS (Ontology Quality Score):** A quality score assessing the completeness and
consistency of the ontology layer. High OQS indicates comprehensive coverage of all
concepts needed by active engines.

**StrategyState:** The lifecycle state of a strategy: CANDIDATE, SIMULATION, EVIDENCE_REVIEW,
ACTIVE, MONITORING, SUSPENDED, RETIRED.

**SystemState:** The overall operating state of IIOS: INITIALIZING, STARTING, OPERATIONAL,
SAFE, DEGRADED, EMERGENCY_STOP, SHUTDOWN.

---

### J.4 OPERATIONAL AND PROCESS TERMS

**ARCHITECTURAL classification:** The governance approval classification for changes
requiring Architecture Council (Tier 1) sign-off. Examples: new engine integration,
ontology extension, constitutional amendment.

**Cold Start:** System startup with no prior session data. Requires seed knowledge loading
and full simulation cycle before first live session. Takes 2-4 days.

**Decision Cycle:** The end-to-end process from knowledge snapshot to authorized decision.
Nominal latency: 172ms.

**Deployment Checklist:** The DEPLOYMENT_CHECKLIST.md document in the IIOS workspace
that defines the mandatory steps for every code deployment.

**Emergency Stop:** The immediate halt of all new investment activity triggered by a
constitutional kill switch or operator command. See WF-SYS-17.

**Evidence Dossier:** See Evidence Dossier under J.1.

**GDR (Governance Decision Record):** A document recording a significant governance
design decision. For the Master Orchestrator, GDRs are numbered GDR-MO-001 through GDR-MO-010.

**IIOS (Investment Intelligence Operating System):** The complete system defined by
this architecture document and its 20 predecessor architecture documents.

**IIOS-INTEG-ARCH-001:** The document code for this integration architecture document.

**Incident Record:** The permanent documentation of a classified incident. All incidents
P1 through P4 have incident records.
ID format: OINC-{SEVERITY}-{YYYYMMDD}-{SEQ:04d}.

**ISDR:** See ADR. The IIOS-specific ADR identifier prefix.

**Maintenance Window:** Scheduled time periods for database compaction, log rotation,
backup, and other non-disruptive maintenance activities. See Section 7.8.

**Market Holiday Operations:** The defined procedure for system behavior on non-trading
days. IIOS does not enter INTRADAY_ACTIVE on holidays; maintenance and learning cycles run.

**OER (Orchestrator Engine Registration):** The record produced when an engine registers
with the Master Orchestrator Engine Registry.
ID format: OER-{ENGINE_CODE}-{YYYYMMDD}-{SEQ:04d}.

**OPERATIONAL classification:** The governance approval classification for operational
parameter changes within constitutional bounds. Applied by Operations Lead (Tier 2).

**ORP (Orchestrator Recovery Procedure):** The collection of documented recovery
procedures for Master Orchestrator component failures.

**Paper Trading:** See Paper Trading under J.1.

**Post-Incident Review:** The formal review conducted after all CRITICAL and CATASTROPHIC
incidents within 48 hours. Produces documented root cause and improvement action.

**Readiness Certificate:** The certification record issued when IIOS passes all 12
readiness phases (CP-01 through CP-12).
ID format: ISYS-CERT-{YYYYMMDD}-{SESSION}-{SEQ:04d}.

**Recovery Record:** See Recovery Record under J.1.

**Risk Budget:** See Budget (Risk).

**Safe Mode:** See SAFE mode.

**Warm Restart:** System startup with existing state intact (most common scenario).
Completed within 60 minutes (T-60 to T-00 before market open).

---

## FINAL CHAPTER — ROADMAP TO IMPLEMENTATION

### FC.1 The Bridge from Architecture to Engineering to Code

This document, and the 20 preceding architecture documents, define WHAT IIOS is
and HOW it is organized. They do not specify the implementation. The transition
from architecture to working system requires three disciplines:

**Architecture** (completed in the 21 documents of the IIOS Architecture Series):
Defines the system's structure, components, interfaces, governance, and constraints.
Architecture answers: "What shall we build, and why shall we build it this way?"

**Engineering:**
Translates architectural intent into concrete technical specifications. Engineering
answers: "Exactly how shall each component be implemented to satisfy the architecture?"
Engineering produces: data schemas, algorithm specifications, configuration schemas,
deployment manifests, test plans.

**Coding:**
Translates engineering specifications into executable software. Coding answers:
"What is the exact instruction sequence that implements this specification?"

This chapter defines how IIOS should be transitioned through engineering to coding,
respecting the architectural constraints established throughout this document.

---

### FC.2 Implementation Principles

**Principle 1 — Architecture Is the Law:**
Every implementation decision must be justified by the architecture. Any implementation
that contradicts an architecture document is wrong. The implementation is corrected;
the architecture is not relaxed to accommodate a shortcut.

**Principle 2 — Smallest Responsible Increment:**
IIOS is implemented in layers, from the foundation upward. No layer N is coded
before layer N-1 is complete, tested, and stable. Attempting to implement all
layers simultaneously creates integration chaos.

**Principle 3 — Test at Every Boundary:**
Every engine interface is tested in isolation before integration. The test suite
for each engine verifies the engine's behavior against its architecture specification.
Integration tests verify cross-engine interactions.

**Principle 4 — Constitution Enforcement in Code:**
Every constitutional rule has a corresponding enforcement mechanism in code.
NNH rules are implemented as architectural invariants (constraints that cannot
be disabled at the code level). HARD rules are implemented as runtime checks.
SOFT rules are implemented as configurable parameters with defined range constraints.

**Principle 5 — No Premature Optimization:**
IIOS is optimized at the architectural level (caching, background refresh, parallel
startup). Implementation does not introduce micro-optimizations at the cost of clarity.

**Principle 6 — Observable From Day 1:**
Every component is instrumented for observability from its first line of implementation.
Logging, metrics, and health checks are not retrofitted — they are implemented with
the component.

**Principle 7 — Security From Day 1:**
Credentials in secrets manager, append-only audit tables, and role-based access
are implemented from the beginning. Security is not added as a layer — it is woven
into the implementation.

**Principle 8 — Immutable Records in Storage:**
All audit tables, decision records, governance records, and knowledge fact records
are implemented as append-only from day one. No update or delete operations are
permitted on these tables.

---

### FC.3 Migration Strategy

The migration from current IIOS state (trading system with existing components)
to fully IIOS-architecture-compliant system requires a defined migration path.

**Current State:**
IIOS currently operates with many of the architectural components described in this
document, implemented across multiple Python modules. The existing system provides
functional investment intelligence but without the full architectural discipline defined
in the 21 architecture documents.

**Target State:**
IIOS fully compliant with all 21 architecture documents, all 164 constitutional rules
enforced, all ontologies formally instantiated, all engines registered.

**Migration Phases:**

**Phase M1 — Foundation Alignment (Priority: CRITICAL)**
Ensure Database Persistence Architecture is fully compliant.
Verify ontology types are correctly instantiated.
Confirm Knowledge Engine 5-minute cache is operating correctly.
Duration estimate: 2-4 weeks.

**Phase M2 — Data Layer Alignment**
Ensure Information Engine, Entity Engine, Relationship Engine, Event Engine,
Temporal Engine, Spatial Engine all produce ontologically typed outputs.
Implement quality scoring on all information inputs.
Confirm provenance chain is attached to all InformationObjects.
Duration estimate: 4-6 weeks.

**Phase M3 — Intelligence Layer Alignment**
Ensure Prediction Engine uses ontologically typed knowledge snapshots.
Implement confidence calibration curves from Learning Engine.
Verify State Engine is the authoritative state source.
Duration estimate: 4-8 weeks.

**Phase M4 — Financial Layer Alignment**
Ensure Risk Engine enforces all constitutional kill switches mechanically.
Implement Portfolio Engine reconciliation on every trade.
Verify Strategy Engine evidence dossier requirements.
Duration estimate: 4-6 weeks.

**Phase M5 — Governance Layer Alignment**
Implement full Governance Engine with all 7 integration points.
Implement DAILY_SESSION_CERTIFICATE issuance and verification.
Implement decision authorization flow.
Duration estimate: 6-8 weeks.

**Phase M6 — Orchestrator Alignment**
Implement all 22 Master Orchestrator components.
Implement all 18 system workflows.
Implement OHS computation and SAFE mode.
Duration estimate: 6-10 weeks.

**Phase M7 — Full Certification**
Run full 12-phase readiness certification (CP-01 through CP-12).
Complete all 58 HARD gate requirements.
Run minimum 5 paper trading sessions with no constitutional violations.
Duration estimate: 4-6 weeks.

---

### FC.4 Development Order

Within each migration phase, components are developed in dependency order:

**Foundation first:** Database Persistence → Ontologies → Foundation Document anchoring.

**Outward from data:** Information Engine → Entity Engine → Event Engine + Temporal Engine → Relationship Engine + Spatial Engine → Knowledge Engine.

**Intelligence stack:** State Engine → Prediction Engine → Learning Engine.

**Financial stack:** Risk Engine → Portfolio Engine → Strategy Engine → Simulation Engine.

**Governance and coordination:** Governance Engine → Master Orchestrator.

This order ensures that every component has its dependencies available before it is tested.

---

### FC.5 Testing Philosophy

**Unit Testing:**
Every engine has unit tests that verify its behavior in isolation with mock dependencies.
Unit tests verify: correct output format, constitutional rule enforcement,
quality threshold enforcement, error handling.

**Integration Testing:**
Engine pairs are tested together to verify interface contracts.
The 53 dependency relationships in Supplement C each have an integration test.

**End-to-End Testing:**
All 18 workflows are tested end-to-end in a staging environment with real (but
non-live) data. Each workflow produces a workflow instance record that is verified
against expected behavior.

**Constitutional Compliance Testing:**
A dedicated test suite verifies that every constitutional rule is enforced mechanically.
NNH rules are tested by attempting to violate them and confirming the violation is rejected.

**Regression Testing:**
Every code change runs the full unit + integration test suite. No deployment proceeds
with failing tests.

**Performance Testing:**
Decision cycle latency is benchmarked with the target of < 200ms P95.
Knowledge Engine cache hit rate is benchmarked against the > 95% target.

---

### FC.6 Validation Strategy

IIOS validation runs at three levels:

**Level 1 — Component Validation:**
Each engine passes its architecture compliance checklist before integration.
Compliance checklist verifies: ontological typing of inputs/outputs, constitutional
rule enforcement, health check availability, audit record creation, recovery behavior.

**Level 2 — System Validation:**
The full 12-phase readiness certification (Part X). 58 HARD gates must pass.
System validation is a gate: no live trading before all 58 HARD gates are cleared.

**Level 3 — Operational Validation:**
A minimum 5-session paper trading period validates live market behavior against
simulation expectations. Any significant behavioral deviation triggers investigation.

---

### FC.7 Deployment Philosophy

**Single deployment pipeline:**
All changes go through: local development → commit → push to origin →
automated test suite → VPS deployment → health verification.
No changes bypass this pipeline.

**Deploy every change:**
No local-only changes accumulate. Every committed change is deployed.
The deployment rule (Copilot Instructions, Deployment Rule section) is mandatory.

**Blue-green deployment for major changes:**
For architectural changes affecting the coordination layer, blue-green deployment
(new version deployed alongside existing; traffic switched after health confirmation)
is preferred over in-place upgrade.

**Rollback capability:**
All deployments can be rolled back to the previous version within 5 minutes.
Docker image versioning and SQLite backup ensure both code and data can be restored.

**Paper trading gate:**
No architectural change goes directly to live trading. All major changes run
in paper trading mode for a minimum of 5 sessions.

---

### FC.8 Long-Term Maintenance Strategy

**Session-by-session improvement:**
Every session produces learning. Every week's learning session runs. Every month's
deep learning cycle runs. The system improves continuously without requiring
architectural re-engineering.

**Evidence dossier renewal discipline:**
The 30-day evidence dossier renewal cycle ensures strategies are regularly
re-evaluated against current market conditions. This discipline is the primary
mechanism preventing strategy drift.

**Architecture document as living reference:**
Architecture documents are updated when architectural decisions change.
They are never allowed to become stale relative to the implementation.
Quarterly architecture reviews confirm implementation matches documentation.

**Constitutional stability:**
The constitution is designed to be stable. Amendments are rare and deliberate.
The architectural review process (30-day public comment period) ensures amendments
receive appropriate consideration.

**Technology evolution:**
As Python versions, infrastructure options, and data source APIs evolve,
IIOS accommodates changes through the Extension Without Modification principle:
new adapters register as new engines or information sources; existing engines
do not require modification.

---

### FC.9 Future Extensibility

**New Instrument Types:**
Options on indices, futures contracts, ETFs, and other instruments can be added
by extending the Entity Ontology and Relationship Ontology with new entity types,
then registering new strategy candidates that target those instruments.

**New Markets:**
Expansion to US markets, Futures markets, or other international markets requires:
- Spatial Ontology region extension
- Trading Calendar additions in Temporal Engine
- New Entity Ontology types for market-specific instruments
- Information Engine source adapter for new market data
No existing engine requires modification.

**New Intelligence Capabilities:**
A Natural Language Processing engine for news analysis, a Fundamental Analysis engine
for deeper financial statement analysis, or a Sentiment Analysis engine for social
media data can all be added through the standard engine registration process.

**Regulatory Technology:**
A Regulatory Reporting engine that automatically generates required regulatory
filings from IIOS audit records can be added as a new Stratum 6 engine without
modifying any existing engine.

**Multi-Asset Portfolio Management:**
As IIOS expands beyond NSE equity and options to multi-asset portfolios, the
Portfolio Engine, Risk Engine, and Strategy Engine require internal extensions.
The architectural framework remains unchanged; new asset class support is added
as new entity types, new relationship types, and new strategy candidates.

---

### FC.10 Architectural Maturity Stages

IIOS's implementation maturity can be assessed against five stages:

**Stage 1 — Functional:**
Basic investment intelligence operating. Observations, predictions, decisions, executions.
No formal governance; no formal ontologies; limited audit trail.
Current state of many systems before architectural discipline is applied.

**Stage 2 — Governed:**
Governance Engine operating. Kill switches enforced. Evidence dossiers required.
Audit trail established. Constitutional rules enforced mechanically.
IIOS target for initial production deployment.

**Stage 3 — Intelligent:**
Learning Engine accumulating institutional memory. Prediction models calibrated
from historical outcomes. Regime-adaptive strategy selection operating.
IIOS target at 3-month mark from production deployment.

**Stage 4 — Self-Improving:**
Full learning feedback loop running. Model performance improving measurably session
over session. Strategy hit rate and Sharpe improving measurably quarter over quarter.
IIOS target at 12-month mark from production deployment.

**Stage 5 — Institutionally Mature:**
OQS and SQS consistently in EXCELLENT tier. All 20 architecture documents
implemented to specification. Constitutional compliance audit clean.
IIOS target at 36-month mark from production deployment.

---

### FC.11 The IIOS Promise

The Investment Intelligence Operating System makes four architectural promises
that this document and the 20 preceding documents uphold:

**Promise 1 — Every decision is traceable:**
From raw market tick to authorized investment decision, every step is recorded,
attributed, and permanently accessible. No decision is made in a black box.

**Promise 2 — Every strategy is evidenced:**
No strategy operates in live trading without documented historical evidence that it
works. Evidence dossiers are not optional; they are constitutional requirements.

**Promise 3 — Every risk is bounded:**
Constitutional risk limits are inviolable. The daily loss limit, VIX kill switch,
and strategy drawdown limit cannot be overridden regardless of perceived opportunity.

**Promise 4 — The system learns:**
IIOS accumulates institutional memory. It improves with every session. The intelligence
that operates IIOS at year 5 will be meaningfully better than the intelligence at
year 1, because every trade outcome is attributed, analyzed, and incorporated.

These four promises are not marketing claims. They are architecturally guaranteed
by the 164 constitutional rules, 18 governed workflows, 12 readiness certification
phases, and the operational discipline defined in this document.

---

### FC.12 Closing Statement

This document — IIOS-INTEG-ARCH-001 — is the capstone of the IIOS Architecture Series.

The 21 documents that constitute this series have defined an investment intelligence
operating system of institutional quality, built on principles of separation of concerns,
ontological typing, constitutional governance, evidence-based strategy deployment,
continuous learning, and human authority preservation.

The architecture is complete. The blueprint exists.

What remains is the engineering discipline to implement it faithfully, the operational
discipline to operate it consistently, and the patience to let it accumulate the
institutional memory and learning that will make it genuinely exceptional.

**IIOS is not a system that is finished. It is a system that improves.**

*Every trade it makes is an experiment.*
*Every outcome it observes is a lesson.*
*Every lesson is a step toward the four promises it makes.*

This document is the map. The journey is the implementation.

---

## DOCUMENT SUMMARY

| Attribute                | Value                                            |
|--------------------------|--------------------------------------------------|
| Document Code            | IIOS-INTEG-ARCH-001                              |
| Version                  | 1.0.0                                            |
| Classification           | Supreme Authoritative Architecture               |
| Authoritative Inputs     | 20 preceding IIOS architecture documents         |
| Parts                    | I through X (10 parts)                           |
| Supplements              | A through J (10 supplements)                     |
| Final Chapter            | Roadmap to Implementation (12 sections)          |
| Constitution             | 164 rules: 16 NNH, 125 HARD, 13 SOFT            |
| Readiness Phases         | 12 phases, 70 gates (58 HARD, 12 SOFT)          |
| Engines catalogued       | 18 engines (Strata 1-7)                          |
| Ontologies catalogued    | 8 ontologies                                     |
| Workflows defined        | 18 system-level workflows                        |
| ADRs                     | 15 Architecture Decision Records                 |
| Failure modes catalogued | 22 failure modes                                 |
| Recovery procedures      | 6 documented recovery procedures                 |
| Glossary entries         | 170+ terms                                       |

---

## REVISION HISTORY

| Version | Date       | Author              | Change Description              |
|---------|------------|---------------------|---------------------------------|
| 1.0.0   | 2026-07-04 | Architecture Council| Initial release — IIOS capstone |

---

*IIOS-INTEG-ARCH-001 Version 1.0.0*
*Investment Intelligence Operating System — Supreme Integration Architecture*
*Architecture Council — Released 2026-07-04*

---

## EXTENDED REFERENCE — SYSTEM-WIDE CROSS-REFERENCE TABLES

### ER.1 Constitutional Rule Cross-Reference: Rules to Enforcement

This table maps every NNH constitutional rule to its operational enforcement
mechanism and the readiness gate that verifies it.

`
RULE        | DOMAIN        | ENFORCEMENT MECHANISM                    | VERIFIED BY
============|===============|==========================================|============
SCC-A-001   | Architecture  | Engine Registry: no unregistered engine  | CP-03 ER-01
SCC-A-002   | Architecture  | Dependency Manager: acyclic check        | CP-03 ER-04
SCC-A-009   | Architecture  | OC-10 Communication Manager              | CP-03 ER-05
SCC-K-005   | Prediction    | Temporal guard in Prediction Engine      | CP-11 AI-02
SCC-M-001   | Decision      | Decision Engine cert. check pre-decision | CP-04 GR-01
SCC-M-002   | Decision      | Decision Engine score threshold gate     | CP-11 AI-04
SCC-M-003   | Decision      | Decision Record creation enforced        | CP-03 ER-06
SCC-N-001   | Risk          | Risk Engine daily loss counter: halt     | CP-04 GR-04
SCC-N-002   | Risk          | Risk Engine VIX monitor: halt            | CP-04 GR-04
SCC-N-003   | Risk          | Risk Engine per-strategy drawdown check  | CP-04 GR-04
SCC-P-001   | Strategy      | Governance Engine: dossier required      | CP-04 GR-05
SCC-R-001   | Governance    | Pre-session cert gate in WF-SYS-01       | CP-04 GR-01
SCC-R-002   | Governance    | MO: SAFE mode on Governance offline      | CP-07 RR-01
SCC-R-003   | Governance    | No override UI for constitutional rules  | CP-06 SR-01
SCC-S-001   | Orchestration | MO architecture review: no market code  | Architecture review
SCC-T-001   | Security      | Secrets manager; code scan at build      | CP-06 SR-01
SCC-V-001   | Recovery      | Recovery procedures: coordination-only   | CP-07 RR-02
SCC-W-001   | Human Override| No override option in Governance UI     | CP-06 SR-01
`

---

### ER.2 Workflow-to-Engine Responsibility Matrix

This table shows which engines are activated in each workflow.

`
WORKFLOW        | Active Engines (abbreviated list)
================|====================================================
WF-SYS-01       | DB, TMP, INF, ENT, SPA, REL, EVT, KNW, STE, PRD,
(Startup)       | LRN, DEC, RSK, PFO, STG, SIM, GOV, MO
----------------+----------------------------------------------------
WF-SYS-02       | TMP, EVT, INF, ENT, KNW, STE, RSK, PRD, GOV, MO
(Market Open)   |
----------------+----------------------------------------------------
WF-SYS-03       | INF, ENT, REL, EVT, TMP, SPA, KNW, MO
(Observation)   |
----------------+----------------------------------------------------
WF-SYS-04       | INF, DB
(Info Flow)     |
----------------+----------------------------------------------------
WF-SYS-05       | KNW, ENT, REL, EVT, TMP, SPA, INF
(Knowledge)     |
----------------+----------------------------------------------------
WF-SYS-06       | PRD, KNW, STE, TMP, EVT
(Prediction)    |
----------------+----------------------------------------------------
WF-SYS-07       | DEC, PRD, RSK, KNW, GOV, MO
(Decision)      |
----------------+----------------------------------------------------
WF-SYS-08       | RSK, KNW, STE, PRD, PFO
(Risk)          |
----------------+----------------------------------------------------
WF-SYS-09       | PFO, RSK, DEC, KNW, STE
(Portfolio)     |
----------------+----------------------------------------------------
WF-SYS-10       | STG, KNW, PRD, RSK, LRN, SIM, GOV
(Strategy)      |
----------------+----------------------------------------------------
WF-SYS-11       | LRN, KNW, STE, PRD, SIM, GOV
(Learning)      |
----------------+----------------------------------------------------
WF-SYS-12       | SIM, STG, RSK, KNW, STE
(Simulation)    |
----------------+----------------------------------------------------
WF-SYS-13       | GOV, KNW, DEC, SIM, LRN
(Governance)    |
----------------+----------------------------------------------------
WF-SYS-14       | DEC, PFO, RSK, GOV, KNW, LRN, DB
(Shutdown)      |
----------------+----------------------------------------------------
WF-SYS-15       | MO, STE, PFO, RSK, GOV, DB
(Recovery)      |
----------------+----------------------------------------------------
WF-SYS-16       | DB, KNW, STG, SIM, GOV, LRN
(Maintenance)   |
----------------+----------------------------------------------------
WF-SYS-17       | RSK, GOV, DEC, PFO, MO
(Emergency Stop)|
----------------+----------------------------------------------------
WF-SYS-18       | GOV, MO, OC-22
(Human Override)|
`

---

### ER.3 Ontology-to-Engine Consumption Matrix

This table shows which engines consume each ontology.

`
ONTOLOGY          | Primary Consuming Engines
==================|====================================================
Knowledge Ont.    | KNW (primary), DEC, PRD, GOV
Information Ont.  | INF (primary), KNW, ENT, EVT
Entity Ont.       | ENT (primary), REL, EVT, SPA, KNW, STG
Relationship Ont. | REL (primary), KNW, RSK
Event Ont.        | EVT (primary), STE, KNW
Temporal Ont.     | TMP (primary), EVT, PRD, KNW, SIM
Spatial Ont.      | SPA (primary), ENT, KNW
State Ont.        | STE (primary), PFO, RSK, STG, MO
`

---

### ER.4 Quality Dimensions to Engine Accountability Matrix

Each quality dimension is owned by a primary engine.

`
QUALITY DIMENSION  | Primary Owner  | Measurement Source
===================|================|============================
Reliability        | Master Orchestr| OHS; session success rate
Availability       | Master Orchestr| Market-hours operational time
Integrity          | DB Persistence | Integrity check; hash chain
Security           | Governance Eng | Security audit; secrets mgr
Performance        | Master Orchestr| Decision cycle latency P95
Auditability       | DB Persistence | Decision record completeness
Consistency        | State Engine   | Reconciliation discrepancy
Resilience         | Master Orchestr| MTTR for P1 incidents
Observability      | Monitoring Mgr | Dashboard metric coverage
Scalability        | Knowledge Eng  | Latency growth per load
Maintainability    | Architecture   | Time per MINOR version change
Extensibility      | Orchestrator   | New engine integration clean
Business Continuity| DB Persistence | RTO from backup restore
`

---

### ER.5 Risk Constitutional Limits Cross-Reference

All constitutional risk limits, with their enforcement engine and monitoring frequency.

`
LIMIT                         | VALUE | ENGINE  | MONITOR FREQ  | RULE
==============================|=======|=========|===============|===========
Daily loss limit              | 2%    | RSK     | Continuous    | SCC-N-001
VIX kill switch               | > 45  | RSK     | Every 30 sec  | SCC-N-002
Strategy drawdown limit       | 15%   | RSK/STG | Every 5 min   | SCC-N-003
Decision score threshold      | 6.5   | DEC     | Per candidate | SCC-M-002
Prediction confidence threshold| 0.5  | PRD/DEC | Per prediction| SCC-K-001
Prediction validity window    | 5 min | DEC     | Per cycle     | SCC-K-002
Cooldown period               | 30min | DEC     | Per decision  | SCC-M-004
Min Win Rate (strategy)       | 50%   | STG/GOV | Per session   | SCC-P-004
Min Sharpe (strategy)         | 0.8   | STG/GOV | At promotion  | SCC-P-004
Max Drawdown (strategy)       | 15%   | STG/GOV | At promotion  | SCC-P-004
Evidence dossier validity     | 30d   | GOV     | Daily         | SCC-P-002
Monte Carlo paths minimum     | 1000  | SIM     | At simulation | SCC-Q-003
WFT windows minimum           | 3     | SIM     | At simulation | SCC-Q-004
OHS SAFE mode threshold       | 0.35  | MO      | Every 30 sec  | SCC-S-005
OHS NOMINAL threshold         | 0.80  | MO      | Every 30 sec  | Operational
VaR confidence level          | 95%   | RSK     | Per cycle     | SCC-N-006
VaR horizon                   | 1 day | RSK     | Per cycle     | SCC-N-006
`

---

### ER.6 IIOS Architecture Series Completion Status

The complete list of all 21 IIOS Architecture Series documents.

`
+----+-----------------------------------+---------------------+------------------+
| No | Document Name                     | Document Code       | Status           |
+----+-----------------------------------+---------------------+------------------+
|  1 | Database Persistence Architecture | IIOS-DB-ARCH-001    | COMPLETE         |
|  2 | Master Knowledge Architecture     | Foundation Document | COMPLETE         |
|  3 | Information Ontology              | Ontology Document   | COMPLETE         |
|  4 | Entity Ontology                   | Ontology Document   | COMPLETE         |
|  5 | Relationship Ontology             | Ontology Document   | COMPLETE         |
|  6 | Event Ontology                    | Ontology Document   | COMPLETE         |
|  7 | Temporal Ontology                 | Ontology Document   | COMPLETE         |
|  8 | Spatial Ontology                  | Ontology Document   | COMPLETE         |
|  9 | State Ontology                    | Ontology Document   | COMPLETE         |
| 10 | Information Engine Architecture   | IIOS-INFO-ENG-001   | COMPLETE         |
| 11 | Knowledge Engine Architecture     | IIOS-KNW-ENG-001    | COMPLETE         |
| 12 | Entity Engine Architecture        | IIOS-ENT-ENG-001    | COMPLETE         |
| 13 | Relationship Engine Architecture  | IIOS-REL-ENG-001    | COMPLETE         |
| 14 | Event Engine Architecture         | IIOS-EVT-ENG-001    | COMPLETE         |
| 15 | Temporal Engine Architecture      | IIOS-TMP-ENG-001    | COMPLETE         |
| 16 | Spatial Engine Architecture       | IIOS-SPA-ENG-001    | COMPLETE         |
| 17 | State Engine Architecture         | IIOS-STE-ENG-001    | COMPLETE         |
| 18 | Prediction Engine Architecture    | IIOS-PRD-ENG-001    | COMPLETE         |
| 19 | Learning Engine Architecture      | IIOS-LRN-ENG-001    | COMPLETE         |
| 20 | Decision Engine Architecture      | IIOS-DEC-ENG-001    | COMPLETE         |
| 21 | Risk Engine Architecture          | IIOS-RSK-ENG-001    | COMPLETE         |
| 22 | Portfolio Engine Architecture     | IIOS-PFO-ENG-001    | COMPLETE         |
| 23 | Strategy Engine Architecture      | IIOS-STG-ENG-001    | COMPLETE         |
| 24 | Simulation Engine Architecture    | IIOS-SIM-ENG-001    | COMPLETE (260KB) |
| 25 | Governance Engine Architecture    | IIOS-GOV-ENG-001    | COMPLETE (280KB) |
| 26 | Master Orchestrator Architecture  | IIOS-MO-ARCH-001    | COMPLETE (300KB) |
| 27 | IIOS Integration and Operational  | IIOS-INTEG-ARCH-001 | COMPLETE (this)  |
+----+-----------------------------------+---------------------+------------------+
`

---

### ER.7 Operational Schedule Reference

Complete schedule of all automated and manual IIOS operational events.

`
DAILY SCHEDULE (weekdays):
08:00  Automated startup (Windows Task Scheduler / cron)
08:00  WF-SYS-01 begins: Foundation + Data Layer startup
08:30  Knowledge Layer startup complete
09:00  Governance Engine issues DAILY_SESSION_CERTIFICATE
09:10  Startup confirmation to Operations Lead (Telegram)
09:15  MARKET_OPEN event; WF-SYS-02 triggers
09:15  Continuous operations: WF-SYS-03 every 30s
09:15  Continuous operations: WF-SYS-08 continuous
09:15  Scheduled operations: WF-SYS-06 every 5 min
09:15  Scheduled operations: WF-SYS-09 every 60 sec
09:15  Governance checkpoint: WF-SYS-13 every 5 min
15:30  MARKET_CLOSE event; WF-SYS-14 triggers
16:00  WF-SYS-11 (Learning Flow) begins
17:00  Database maintenance
18:00  System shutdown complete; state persisted

WEEKLY SCHEDULE (Saturday):
09:00  Strategy performance deep review
10:00  Evidence dossier expiry check
10:30  WFT refresh for degraded strategies
12:00  Database compaction and backup verification
13:00  Weekly report generation

MONTHLY SCHEDULE (first Saturday):
09:00  Full system health baseline
10:00  Risk model recalibration assessment
11:00  Evidence dossier audit (all active strategies)
13:00  Deep simulation for any strategy with 14+ day expiry
16:00  Monthly governance report finalization

QUARTERLY SCHEDULE (first Monday of quarter):
09:00  Architecture Council meeting
09:30  Constitution amendment review
10:00  New engine proposals review
11:00  Risk parameter amendment review
13:00  Technology infrastructure review

ANNUAL SCHEDULE (December 31):
Full architecture compliance audit
All architecture documents version review
Annual strategy retirement assessment
Annual performance attribution analysis
`

---

### ER.8 Naming Convention Reference

All IIOS identifier formats for consistent documentation and implementation.

`
IDENTIFIER TYPE              | FORMAT                                     | EXAMPLE
=============================|============================================|===============
Document Code                | IIOS-{ENGINE_ABBREV}-ARCH-{NNN}           | IIOS-MO-ARCH-001
Workflow Instance ID         | WF-{PIPELINE_CODE}-{YYYYMMDD}-{SEQ:08d}   | WF-SYS-20260704-00000001
Decision Record ID           | ODEC-{YYYYMMDD}-{SEQ:08d}                 | ODEC-20260704-00001234
Engine Registration ID       | OER-{ENGINE_CODE}-{YYYYMMDD}-{SEQ:04d}    | OER-PRD-20260704-0001
Readiness Certificate ID     | ISYS-CERT-{YYYYMMDD}-{SESSION}-{SEQ:04d}  | ISYS-CERT-20260704-AM-0001
Governance Certificate ID    | GCERT-{YYYYMMDD}-{SEQ:04d}                | GCERT-20260704-0001
Incident Record ID           | OINC-{SEVERITY}-{YYYYMMDD}-{SEQ:04d}      | OINC-P1-20260704-0001
Recovery Record ID           | REC-{SEVERITY}-{YYYYMMDD}-{SEQ:04d}       | REC-P2-20260704-0001
ADR ID                       | ISDR-{SEQ:03d}                            | ISDR-001
Strategy ID                  | STG-{TYPE}-{REGIME}-{NNN}                 | STG-MOMENTUM-BULL-001
Model ID                     | MOD-{REGIME}-{TYPE}-v{N}                  | MOD-BULL-MOMENTUM-v4
Governance Decision Record   | GDR-MO-{SEQ:03d}                          | GDR-MO-001
Failure Record ID            | IIOS-FAIL-{CATEGORY}-{SEQ:04d}            | IIOS-FAIL-SYS-0001
Evidence Dossier ID          | EVID-{STRATEGY_ID}-{YYYYMMDD}-{SEQ:04d}   | EVID-STG-BULL-001-20260704-0001
`

---

### ER.9 IIOS Decision Cycle — Detailed Timing Reference

The complete breakdown of the nominal 172ms decision cycle latency.

`
PHASE                         | COMPONENT              | NOMINAL | SLA MAX
==============================|========================|---------|========
Knowledge cache read          | Knowledge Engine       |   3ms   |  10ms
Feature generation            | Prediction Engine      |  12ms   |  30ms
Prediction computation        | Prediction Engine      |  35ms   |  80ms
Risk pre-filter               | Risk Engine            |   8ms   |  20ms
Candidate scoring             | Decision Engine        |  20ms   |  40ms
Multi-agent debate            | Decision Engine        |  50ms   | 120ms
Governance authorization      | Governance Engine      |  30ms   |  60ms
Decision Record creation      | Decision Engine        |  10ms   |  20ms
Routing to execution          | Master Orchestrator    |   4ms   |  10ms
----------------------------------------------------------------------
TOTAL NOMINAL                 |                        | 172ms   | 390ms
`

Note: The 172ms figure assumes the Knowledge Engine cache is fresh (hit).
On a cache miss (probability < 5%), the Knowledge Engine must fetch from DB,
adding up to 300ms. Total on cache miss: up to 470ms, still within SLA.

---

### ER.10 System-Wide Telemetry Reference

IIOS collects telemetry across all engines. Key metrics reference:

`
METRIC CATEGORY   | METRIC NAME                    | COLLECTION PT | FREQUENCY
==================|================================|===============|===========
Health            | OHS (Orchestrator Health Score)| Master Orch.  | 30 sec
Health            | Engine health per engine (18)  | Each engine   | 30 sec
Performance       | Decision cycle latency P95     | Decision Eng. | Per session
Performance       | Knowledge cache hit rate       | Knowledge Eng.| Per cycle
Performance       | Prediction accuracy (7d window)| Learning Eng. | Daily
Financial         | Daily P&L vs limit             | Risk Engine   | Continuous
Financial         | Portfolio VaR                  | Risk Engine   | Per cycle
Financial         | Open exposure per strategy     | Portfolio Eng.| 60 sec
Strategy          | Win rate (30d rolling)         | Strategy Eng. | Per session
Strategy          | Sharpe ratio (30d rolling)     | Strategy Eng. | Per session
Strategy          | Drawdown current               | Strategy Eng. | Per cycle
Governance        | Decisions authorized today     | Governance    | Per session
Governance        | Kill switch events (30d)       | Governance    | Per session
Governance        | Governance compliance score    | Governance    | Per session
Data Quality      | InformationObject rejection %  | Info Engine   | Per cycle
Data Quality      | Knowledge cache freshness      | Knowledge Eng.| Per cycle
Learning          | Model accuracy vs baseline     | Learning Eng. | Per session
System            | DB write latency P95           | DB Persistence| Per session
System            | Container memory utilization   | Infrastructure| 60 sec
System            | VPS disk utilization           | Infrastructure| Daily
`

---

## EXTENDED REFERENCE — SYSTEM ANTI-PATTERNS

Anti-patterns document the architectural mistakes that IIOS explicitly avoids.
Understanding what NOT to build is as important as understanding what to build.

---

### AP-01: THE OMNISCIENT ORCHESTRATOR

**Description:** An orchestrator that contains investment logic, makes market assessments,
or interprets the outputs of intelligence engines to improve scheduling decisions.

**Why it fails:** The orchestrator becomes a hidden investment engine. It develops
opinions about markets. Those opinions are not governed, not traced, and not auditable.
When the system makes a bad decision, the cause is untraceable because the orchestrator's
hidden logic contributed to it.

**How IIOS avoids it:** Master Orchestrator is constitutionally prohibited from
performing investment analysis (SCC-S-001, SCC-S-002). These are NNH rules. The
Orchestrator routes, schedules, monitors, and recovers — it has no market opinion.

---

### AP-02: THE UNGOVERNED STRATEGY

**Description:** A strategy that runs in live trading without a validated evidence
dossier. Perhaps it "looked good" in a quick visual backtest. Perhaps the backtest
code was reviewed but not the Walk-Forward Test. Perhaps the dossier expired and
nobody noticed.

**Why it fails:** Without out-of-sample validation, the strategy is likely overfit.
Its historical performance is an artifact of optimization, not genuine edge. It will
underperform or lose money in live trading. The exact conditions that made it look
good in backtest will not repeat.

**How IIOS avoids it:** The evidence dossier requirement is constitutional (SCC-P-001
NNH). The 30-day expiry (SCC-P-002) prevents stale dossiers from persisting.
The Governance Engine enforces both mechanically.

---

### AP-03: THE LEARNING CONTAMINATION

**Description:** A machine learning model that updates its parameters from live
trade outcomes during the trading session. The model at 14:00 has been trained on
the same session it is now making decisions for. This is a subtle form of look-ahead bias.

**Why it fails:** The model learns the specific conditions of the current day and
becomes overfit to intraday patterns that will not persist. Decisions made late
in the session reflect the session's noise, not genuine signal.

**How IIOS avoids it:** Learning is constitutionally restricted to post-session mode
(SCC-L-001). No model parameter changes occur during INTRADAY_ACTIVE state.

---

### AP-04: THE SILENTLY STALE KNOWLEDGE

**Description:** The Knowledge Engine cache becomes stale because the data source
has silently stopped delivering updates. The system continues generating predictions
from 30-minute-old market knowledge, without any engine being aware of the staleness.

**Why it fails:** Predictions based on stale market state generate decisions that
are inconsistent with actual market conditions. Losses occur from acting on information
that no longer reflects reality.

**How IIOS avoids it:** Information freshness decay is tracked. KNOWLEDGE_STALE
signals are broadcast when cache age exceeds thresholds. The Risk Engine treats
stale-knowledge decisions with higher uncertainty. SAFE mode is evaluated when
staleness exceeds 5 minutes.

---

### AP-05: THE UNGATED DECISION

**Description:** An investment decision is executed without passing through the
Governance Engine's authorization check. Perhaps the Governance Engine was slow
and the decision pathway bypassed it for performance reasons.

**Why it fails:** The decision may violate a constitutional rule (daily loss limit,
decision score threshold). The decision has no authorization record. The audit trail
is broken.

**How IIOS avoids it:** SCC-R-002 states the Governance Engine is always operational
during INTRADAY_ACTIVE state and is a NNH rule. Governance Engine failure causes
SAFE mode (SCC-R-002) — decisions stop rather than bypass governance.

---

### AP-06: THE ACCUMULATED OVERRIDE

**Description:** Human operators apply a series of small overrides over multiple sessions,
each one individually justifiable, that collectively push the system outside its
intended operating envelope. For example: progressively reducing the decision score
threshold, then extending the cooldown period, then increasing position sizes.

**Why it fails:** Each override seemed reasonable. But the cumulative effect is a
system operating with different parameters than those tested in simulation. The
evidence dossier was validated for the original parameters, not the drifted ones.

**How IIOS avoids it:** Overrides expire at session end (SCC-W-003). No override
persists silently. Constitutional SOFT rule bounds (SCC-M-007, SCC-M-008, etc.)
prevent any individual override from exceeding the documented range.

---

### AP-07: THE ORPHANED MODEL

**Description:** A prediction model that was validated and promoted months ago but
has never been updated since. The market has changed; the model's calibration has drifted.
But since no one is monitoring model performance, nobody notices.

**Why it fails:** A stale model produces poorly calibrated confidence scores.
The Decision Engine makes decisions based on confidence levels that no longer
correspond to actual accuracy. Losses occur from overconfident incorrect predictions.

**How IIOS avoids it:** Model performance monitoring is a continuous process
(SQS Observability dimension). The telemetry reference (ER.10) includes
"Model accuracy vs baseline" as a tracked metric. The Learning Engine reports
model accuracy weekly. Models with declining accuracy trigger investigation.

---

### AP-08: THE INCONSISTENT UNIVERSE

**Description:** Different engines in the system have different views of which
instruments are in the active trading universe. The Entity Engine considers RELIANCE
active; the Strategy Engine has it in a "monitoring-only" list; the Portfolio Engine
doesn't know about it at all.

**Why it fails:** Inconsistent universe definitions lead to decisions being made
for instruments that risk and portfolio engines aren't tracking, creating unmonitored exposure.

**How IIOS avoids it:** The universe is defined by the Entity Engine and synchronized
through the Knowledge Engine. The State Engine is the authoritative source of
entity state (ACTIVE, SUSPENDED, CIRCUIT_BREAK). All engines query the State Engine
for entity status before processing an instrument.

---

### AP-09: THE INVISIBLE INCIDENT

**Description:** A significant system event (data feed failure, prediction accuracy
collapse, engine restart) occurs but is not classified as an incident. No alert
is sent. No audit record is created. The operator discovers the problem two days
later when reviewing logs.

**Why it fails:** Without incident detection, problems compound. A 30-second data
feed outage that causes stale predictions is recoverable; a 5-hour outage that was
never detected is not. Invisible incidents prevent learning from operational problems.

**How IIOS avoids it:** The incident classification framework (Supplement G) defines
22 specific failure modes with detection mechanisms. P1 incidents trigger immediate
Telegram alerts. All incidents produce permanent records.

---

### AP-10: THE UNVERIFIED DEPLOYMENT

**Description:** Code is changed locally and deployed to VPS without running
the test suite, verifying both containers are healthy, or running paper trading
validation. The change goes live immediately.

**Why it fails:** An unverified deployment can introduce a bug into a live trading
system. The bug may cause financial losses before it is detected.

**How IIOS avoids it:** The Deployment Rule (Copilot Instructions) is mandatory:
every deployment runs git commit → push → SSH deploy → docker compose ps verification.
The paper trading gate (FC.7, 5-session minimum) applies to architectural changes.

---

## EXTENDED REFERENCE — GOVERNANCE DECISION RECORDS

These records document significant governance design decisions for the
integration architecture itself.

---

### IGDR-001: All Engines Subject to Same Constitution

**Decision:** Every IIOS engine, regardless of when it was designed or by whom,
is subject to the same constitutional framework. No engine is exempt.

**Rationale:** A constitution that has exceptions is not a constitution. If any
engine could claim exemption from constitutional rules, the constitutional framework
would be meaningless. All 18 engines, including the Master Orchestrator, comply with
all applicable constitutional rules.

---

### IGDR-002: Integration Architecture Integrates, Does Not Redesign

**Decision:** This document (IIOS-INTEG-ARCH-001) does not modify any prior
architecture document. All 20 preceding documents are final and immutable.

**Rationale:** An integration document that redesigns the components it integrates
undermines the authority of those components. The integration layer adds value by
synthesizing, coordinating, and contextualizing — not by re-architecting.

---

### IGDR-003: Constitution Is More Than Rules

**Decision:** The IIOS Constitution (Part IX) is not merely a list of rules.
It is an architectural statement of values: traceability, evidence, prudence,
learning, human authority. Constitutional rules express these values operationally.

**Rationale:** Rules without values are brittle. When an unanticipated situation
arises that no rule explicitly covers, the values guide the response. "Evidence
before deployment" and "traceability over convenience" are values; their constitutional
expressions are rules.

---

### IGDR-004: Readiness Certification as Gate, Not Checklist

**Decision:** The 12-phase readiness certification is a gate to live trading,
not an advisory checklist. All 58 HARD gates must pass before production deployment.

**Rationale:** A checklist that can be overridden is a suggestion. A gate that
must be passed before operations is a structural constraint. IIOS's reliability
and safety properties depend on the system being fully ready before capital is exposed.

---

### IGDR-005: Learning and Governance Are Complementary, Not Competing

**Decision:** The Learning Engine and Governance Engine serve different functions
and must operate cooperatively. Learning improves performance; Governance ensures
improvements are safe. They are not competing priorities.

**Rationale:** Without learning, IIOS stagnates. Without governance, learning
corrupts. Both are required for long-term excellence. The model promotion workflow
(Learning Engine → Simulation Engine → Governance Engine → Prediction Engine)
embodies this cooperation.

---

## EXTENDED REFERENCE — IIOS PRINCIPLES QUICK REFERENCE

The 15 Core Architectural Principles (Section 1.3) in abbreviated form for
operational reference:

`
P01: Separation of Concerns — every function belongs to its designated engine.
P02: Ontology First — information must be ontologically typed before processing.
P03: Constitutional Governance — rules are inviolable constraints, not guidelines.
P04: Traceability Over Convenience — audit trails are never sacrificed for speed.
P05: Layered Independence — higher layers depend on lower; never reverse.
P06: Evidence Before Deployment — no strategy without a validated evidence dossier.
P07: Learning Without Contamination — learning is isolated from live operations.
P08: Fail Safely — IIOS fails toward safety, not toward opportunity.
P09: Human Authority Preserved — operators retain override authority within constitution.
P10: Extensibility Without Modification — add new engines; don't modify existing ones.
P11: Performance Through Architecture — caching and design solve performance problems.
P12: Governance Is Not Overhead — governance is woven into the operational fabric.
P13: Distributed Intelligence, Unified Behavior — 14 specialists, one orchestrator.
P14: Market Indifference at Orchestration Level — the Orchestrator knows no markets.
P15: Constitutional Permanence — constitutional rules are most important under pressure.
`

---

## EXTENDED REFERENCE — COMPLETE WORKFLOW SEQUENCE DIAGRAMS

### Extended Sequence: WF-SYS-07 Decision Flow (Full Detail)

`
MASTER ORCHESTRATOR
     |
     |--[TRIGGER: PREDICTIONS_READY]--> DECISION ENGINE
                                             |
                                             |--[QUERY: available risk budget]-->
                                             |                         RISK ENGINE
                                             |<--[RESPONSE: budget, blocked list]--
                                             |
                                             |--[QUERY: portfolio state]-->
                                             |                    PORTFOLIO ENGINE
                                             |<--[RESPONSE: capital available]--
                                             |
                                             |--[QUERY: knowledge context]-->
                                             |                    KNOWLEDGE ENGINE
                                             |<--[RESPONSE: knowledge snapshot]--
                                             |
                                             | (score candidates)
                                             | (filter: score >= 6.5)
                                             | (initiate 5-agent debate)
                                             |
                                             |--[REQUEST: authorization]-->
                                             |                   GOVERNANCE ENGINE
                                             |                         |
                                             |                         |--[check: VIX]
                                             |                         |--[check: loss limit]
                                             |                         |--[check: dossier]
                                             |                         |--[check: score]
                                             |<--[RESPONSE: AUTHORIZED/BLOCKED]--
                                             |
                                             | (create Decision Record)
                                             |
                                             |--[DECISION_APPROVED]--> MASTER ORCHESTRATOR
                                             |
                                             |--[PORTFOLIO_UPDATE]--> PORTFOLIO ENGINE
                                             |
                                             |--[RISK_UPDATE]--> RISK ENGINE
`

---

### Extended Sequence: WF-SYS-13 Governance Flow (Intraday Checkpoint)

`
MASTER ORCHESTRATOR
     |
     |--[5-min trigger]--> GOVERNANCE ENGINE
                                 |
                                 |--[QUERY: VIX current]-->    RISK ENGINE
                                 |<--[RESPONSE: VIX=22.1]--
                                 |
                                 |--[QUERY: daily P&L]-->     PORTFOLIO ENGINE
                                 |<--[RESPONSE: P&L=+0.3%]--
                                 |
                                 |--[QUERY: strategy states]--> STRATEGY ENGINE
                                 |<--[RESPONSE: all ACTIVE]--
                                 |
                                 | (check: VIX <= 45: PASS)
                                 | (check: P&L > -2%: PASS)
                                 | (check: strategies in limits: PASS)
                                 |
                                 |--[GOVERNANCE_CHECKPOINT_PASS]--> MASTER ORCHESTRATOR
                                 |--[CHECKPOINT_RECORD]--> DATABASE
`

---

### Extended Sequence: Full Learning Cycle (WF-SYS-11, Post-Session)

`
MASTER ORCHESTRATOR
     |
     |--[15:35 trigger]--> LEARNING ENGINE
                                 |
                                 |--[QUERY: today's closed trades]-->  DATABASE
                                 |<--[RESPONSE: 12 trades, outcomes]--
                                 |
                                 |--[QUERY: associated predictions]--> DATABASE
                                 |<--[RESPONSE: prediction records]--
                                 |
                                 | (attribute each outcome to prediction)
                                 | (compute prediction errors)
                                 | (identify which features predicted correctly)
                                 |
                                 |--[UPDATE: staging models only]--> (STAGING ENV)
                                 |
                                 |--[REQUEST: validate staged model]--> SIMULATION ENGINE
                                 |                                           |
                                 |                                           | (run OOS validation)
                                 |<--[RESPONSE: validation results]----------
                                 |
                                 |--[REQUEST: approve model update]--> GOVERNANCE ENGINE
                                 |                                          |
                                 |                                          | (check: improvement)
                                 |                                          | (check: constitutional)
                                 |<--[RESPONSE: APPROVED]-----------------
                                 |
                                 |--[PROMOTE: model to live]--> PREDICTION ENGINE
                                 |
                                 |--[INSIGHTS: update beliefs]--> KNOWLEDGE ENGINE
                                 |
                                 |--[LEARNING_COMPLETE]--> MASTER ORCHESTRATOR
`

---

## EXTENDED REFERENCE — COMPREHENSIVE ENGINE INTERACTION PROFILES

This section provides full operational profiles for each engine's role within
the integrated IIOS system.

---

### EI-01: Information Engine — System Integration Profile

**Role in IIOS:** The Information Engine is the system's sentinel — the first
processing layer that every market datum passes through. Its quality decisions
determine what enters the intelligence stack. An information quality failure
propagates forward; a quality success propagates forward faster.

**Critical integration points:**
1. Primary data source (Dhan): receives real-time OHLCV, option chain data.
2. Fallback data source (yfinance): activated automatically on primary failure.
3. Entity Engine: pushes entity property updates after every observation cycle.
4. Event Engine: pushes raw event signals for classification.
5. Knowledge Engine: pushes validated InformationObjects for graph integration.

**Operational rhythm:**
- On observation trigger: ingest → validate → classify → persist → distribute.
- On source failure: detect → switch fallback → notify → continue with degradation annotation.

**Constitutional compliance:**
- Implements SCC-C-001 (sole data ingestion boundary) architecturally.
- Implements SCC-C-002 (quality threshold) as runtime filter.
- Implements SCC-C-004 (persist before distribute) as invariant in distribution logic.

**Performance profile:**
- Nominal ingest cycle: < 2 seconds for full observation ingest.
- Fallback switch: < 30 seconds from primary failure detection to fallback active.

---

### EI-02: Knowledge Engine — System Integration Profile

**Role in IIOS:** The Knowledge Engine is the system's memory. Every session it
observes more; every month it accumulates more; every year it has a richer, more
accurate picture of how markets behave. The engines that consume it — Prediction,
Decision, Risk — are all smarter because of it.

**Critical integration points:**
1. 5-minute cache: the performance mechanism that makes the decision cycle feasible.
2. Regime classification: the single most impactful signal for strategy selection.
3. Knowledge accumulation: the mechanism for institutional memory growth.
4. Conflict resolution: the mechanism for maintaining knowledge graph integrity.

**Operational rhythm:**
- Background refresh: cache rebuilt every 5 minutes from full graph query.
- Event-driven update: significant entity changes invalidate specific cache entries.
- Session-close persistence: full graph snapshot persisted to Database.

**Constitutional compliance:**
- Implements SCC-B-002 (sole authoritative source for intelligence engines).
- Implements SCC-B-003 (fact immutability through versioning).
- Implements SCC-B-006 (exclusive regime classification authority).

**Long-term evolution:**
The Knowledge Engine is the most long-lived component in IIOS from a data perspective.
While engines can be upgraded and replaced, the knowledge graph it maintains is the
accumulated institutional memory of IIOS. This graph grows in value with every session.
After 3 years of operation, the Knowledge Engine's graph will contain thousands of
entities, millions of relationships, and decades-equivalent of pattern data.

---

### EI-03: Risk Engine — System Integration Profile

**Role in IIOS:** The Risk Engine is the system's immune system. When the body
is healthy, the immune system is invisible. When the body is under threat, the immune
system activates and its responses can seem harsh. The Risk Engine's kill switches
are the harsh responses that prevent catastrophic outcomes.

**Critical integration points:**
1. Kill switches: the three constitutional halt conditions (2% loss, VIX > 45, 15% drawdown).
2. Risk budget: the resource allocation mechanism that prevents over-concentration.
3. VaR calculation: the quantitative risk assessment that gates individual positions.
4. Portfolio integration: bidirectional relationship with Portfolio Engine for real-time
   position-aware risk assessment.

**Operational rhythm:**
- Continuous monitoring: VIX, daily P&L, open position risk — all monitored every 30 seconds.
- Pre-decision check: risk budget availability checked before every decision is scored.
- Kill switch check: evaluated on every monitoring cycle and on every decision request.

**Constitutional compliance:**
- Implements SCC-N-001 through SCC-N-003 (kill switches) as inviolable code paths.
- Implements SCC-N-004 (always operational during live trading) through OHS weighting.

**Why it matters:**
The Risk Engine is the most safety-critical engine in IIOS. More safety-critical even
than the Governance Engine, because the Risk Engine operates in real time on every
single decision, while the Governance Engine's most critical check (pre-session
certification) runs once per day. A Risk Engine that is degraded or offline creates
immediate exposure. IIOS's architecture reflects this: Risk Engine failure triggers
SAFE mode with zero delay, with no grace period.

---

### EI-04: Governance Engine — System Integration Profile

**Role in IIOS:** The Governance Engine is the system's conscience. It does not
make investment decisions, but it ensures that investment decisions are made correctly.
Its seven integration points are the checkpoints that prevent the system from becoming
ungoverned in its pursuit of returns.

**Critical integration points:**
1. DAILY_SESSION_CERTIFICATE: the pre-session gate that confirms all conditions for trading.
2. Decision authorization: the real-time gate on every investment decision.
3. Strategy deployment gate: the structural gate preventing ungoverned strategy deployment.
4. Model update approval: the gate ensuring learning improvements are safe.
5. Kill-switch confirmation: the post-kill-switch record confirming the halt is valid.
6. Emergency stop authorization: the permanent record of emergency stop conditions.
7. Human override validation: the constitutional compliance check on every override.

**Operational rhythm:**
- Pre-session: full compliance check → certificate issuance.
- Intraday: 5-minute compliance checkpoint → continuous authorization service.
- Post-session: governance report generation → session certificate closure.

**The governance paradox:**
The Governance Engine is simultaneously the most powerful engine in IIOS (it can
halt any decision, suspend any strategy, block any session) and the most constrained
(it cannot override constitutional rules, cannot authorize illegal decisions, cannot
be disabled without triggering SAFE mode). This combination of power and constraint
is intentional: the power is necessary for enforcement; the constraint is necessary
for safety.

---

### EI-05: Master Orchestrator — System Integration Profile

**Role in IIOS:** The Master Orchestrator is the system's conductor. It does not
play any instrument, but without it, the ensemble produces noise rather than music.

**Critical integration points:**
1. Engine Registry: the authoritative list of all participating engines.
2. Workflow scheduler: the mechanism that sequences all 18 workflows correctly.
3. OHS computation: the real-time system health signal.
4. SAFE mode activation: the system-wide protection mechanism.
5. Recovery procedures: the fault tolerance layer.

**What the Orchestrator does not do:**
This cannot be overstated. The Orchestrator does not:
- Look at market prices.
- Generate predictions.
- Make investment decisions.
- Modify positions.
- Interpret the outputs of any intelligence engine.

It sees health signals, workflow completion signals, and control events.
It responds by scheduling workflows, routing messages, and managing recovery.
It is completely neutral about the market content of everything it coordinates.

**Constitutional compliance:**
- SCC-S-001 (no investment analysis): enforced architecturally — no market data
  flows into the Orchestrator's decision-making path.
- SCC-S-002 (no output interpretation): enforced architecturally — the Orchestrator
  treats all engine outputs as opaque signals.
- SCC-S-006 (recovery without position modification): enforced in recovery procedure
  design — no recovery procedure calls any position-modifying interface.

---

## EXTENDED REFERENCE — IIOS PERFORMANCE ARCHITECTURE

IIOS achieves its performance targets through architectural choices, not
low-level optimization. This section documents the key performance decisions.

---

### PA-01: The Knowledge Cache Architecture

**Problem:** The Knowledge Engine integrates data from 6 source engines and
must provide a consistent, up-to-date view to 7 consuming engines — all within
a 172ms decision cycle.

**Solution:** Background-refresh 5-minute cache. The Knowledge Engine continuously
maintains a pre-computed knowledge snapshot. Consuming engines read from the snapshot
without triggering any database query or computation. The background refresh thread
updates the snapshot every 5 minutes regardless of consumer activity.

**Performance impact:** Without cache, each decision cycle would require 300-500ms
for Knowledge Engine integration. With cache, the read takes < 3ms.

**Accuracy tradeoff:** Knowledge is at most 5 minutes old. For IIOS's investment
horizon (intraday, not high-frequency), this is an acceptable tradeoff.

---

### PA-02: The Parallel Engine Startup Architecture

**Problem:** IIOS has 18 engines with complex dependencies. Sequential startup
would take 18 × average_startup_time = potentially 30+ minutes.

**Solution:** Parallel startup within dependency tiers (see Supplement C.2).
All engines in the same tier start simultaneously. The result:
- Tier 1 (1 engine): ~2 minutes
- Tier 2 (2 engines): ~3 minutes (parallel)
- Tier 3 (2 engines): ~4 minutes (parallel)
- Tier 4 (2 engines): ~3 minutes (parallel)
- Tier 5 (1 engine): ~5 minutes
- Tiers 6-11: ~30 minutes

Total: ~47 minutes of the 60-minute startup window. Parallel startup is essential.

---

### PA-03: The Event-Driven Architecture

**Problem:** A polling architecture (every engine checks every other engine for
updates every N seconds) creates N-squared communication load as engine count grows.

**Solution:** Event-driven architecture. Engines emit events when their state changes.
The Master Orchestrator's Message Router (OC-11) delivers events to registered
subscribers. No polling. No N-squared load.

**Performance impact:** A polling architecture with 18 engines at 1-second polling
would generate 18×17 = 306 inter-engine checks per second. The event-driven approach
generates only the events that actually occur.

---

### PA-04: The Background Global Intelligence Pre-Warm

**Problem:** The overnight global intelligence assessment (S&P, Nikkei, bonds, FX)
requires external data fetches that can take 3-5 seconds.

**Solution:** Background pre-warm thread starts at system startup (T-60) and fetches
global intelligence data before any engine needs it. By T-00, global intelligence
data is pre-loaded in the Knowledge Engine cache.

**Performance impact:** Eliminates a 3-5 second synchronous fetch from the pre-market
readiness check. Global intelligence contribution to decision cycle: 3ms (cache read)
rather than 3,000ms (live fetch).

---

## EXTENDED REFERENCE — IIOS ARCHITECTURAL INVARIANTS

Architectural invariants are properties that must always hold in a correctly
functioning IIOS system. They are stronger than constitutional rules in that they
are properties of the system state, not behavioral rules.

**INVARIANT-01: Engine Registry Completeness**
At any moment during INTRADAY_ACTIVE state, all 18 engines are registered in
the Engine Registry. No engine operates outside the registry.

**INVARIANT-02: Knowledge Cache Freshness**
At any moment during INTRADAY_ACTIVE state, the Knowledge Engine cache is at most
5 minutes old. If this invariant is violated, KNOWLEDGE_STALE is broadcast.

**INVARIANT-03: Portfolio State Consistency**
At any moment, the Portfolio Engine's position records are consistent with
execution confirmations in the Database. Any inconsistency is an incident.

**INVARIANT-04: Decision Provenance Completeness**
Every Decision Record has a complete 7-step provenance chain (observation through
authorization). No Decision Record exists without full provenance.

**INVARIANT-05: Governance Certificate Validity**
During INTRADAY_ACTIVE state, a valid DAILY_SESSION_CERTIFICATE always exists.
If the certificate becomes invalid mid-session (e.g., kill switch triggered),
SAFE mode activates immediately.

**INVARIANT-06: Risk Budget Non-Negativity**
Available risk budget per strategy is always >= 0. Negative risk budgets indicate
a state inconsistency and are a P1 incident.

**INVARIANT-07: Audit Table Append-Only**
Audit tables contain only rows added since database creation. No row in an audit
table has been modified or deleted since creation.

**INVARIANT-08: Constitutional Rule Enforcement**
Every NNH constitutional rule is enforced by the running system. No configuration
or runtime override can disable a NNH rule's enforcement.

**INVARIANT-09: Ontology Type Completeness**
Every entity, relationship, event, and information object in the system has a
valid ontological type assignment. Objects without types are not processed.

**INVARIANT-10: Learning Isolation**
During INTRADAY_ACTIVE state, no model parameters in the live prediction path
have been modified since the session began. Learning outputs are held in staging.

---

## EXTENDED REFERENCE — SYSTEM HEALTH STATE MACHINE

The complete IIOS system health state machine, including all states and transitions.

`
STATES:
- INITIALIZING: System starting up; no engines operational
- STARTING: Engines coming online; WF-SYS-01 in progress
- OPERATIONAL: All critical engines healthy; OHS >= 0.80; session active
- DEGRADED: Some engines degraded; OHS 0.60-0.79; reduced operations
- SAFE: No new decisions; OHS < 0.60 or kill-switch triggered
- EMERGENCY_STOP: Hard halt; all decisions stopped; positions locked
- RECOVERY: Active recovery attempt in progress
- SHUTDOWN: Orderly shutdown; state being persisted
- OFFLINE: System not running

TRANSITIONS:
OFFLINE --> INITIALIZING       : Startup command received
INITIALIZING --> STARTING      : Foundation validated
STARTING --> OPERATIONAL       : OHS >= 0.80 and cert issued
STARTING --> SAFE              : OHS < 0.60 during startup
OPERATIONAL --> DEGRADED       : OHS 0.60-0.79 detected
OPERATIONAL --> SAFE           : OHS < 0.60 or kill-switch
OPERATIONAL --> EMERGENCY_STOP : VIX>45 or loss>=2%
OPERATIONAL --> SHUTDOWN       : 15:30 IST or operator command
DEGRADED --> OPERATIONAL       : OHS returns to >= 0.80
DEGRADED --> SAFE              : OHS drops below 0.60
DEGRADED --> SHUTDOWN          : Operator shutdown command
SAFE --> RECOVERY              : Recovery attempt initiated
SAFE --> EMERGENCY_STOP        : Kill-switch confirmed
RECOVERY --> OPERATIONAL       : OHS >= 0.80 after recovery
RECOVERY --> DEGRADED          : OHS 0.60-0.79 after recovery
RECOVERY --> SAFE              : OHS < 0.60 after recovery
RECOVERY --> SHUTDOWN          : Operator command post-recovery
EMERGENCY_STOP --> OFFLINE     : Shutdown complete
SHUTDOWN --> OFFLINE           : Shutdown complete
`

---

## EXTENDED REFERENCE — DOCUMENT METRICS

| Metric                    | Value                                        |
|---------------------------|----------------------------------------------|
| Parts                     | 10 (I through X)                             |
| Supplements               | 10 (A through J)                             |
| Final Chapter             | 1 (12 sections)                              |
| Extended References       | 14 (ER.1 through ER.10 + EI, PA, AI, SH)    |
| Constitutional rules      | 164 total (16 NNH, 125 HARD, 13 SOFT)        |
| Readiness phases          | 12 (CP-01 through CP-12)                     |
| Readiness gates           | 70 (58 HARD, 12 SOFT)                        |
| System workflows          | 18 (WF-SYS-01 through WF-SYS-18)            |
| Engines catalogued        | 18 (Strata 1-7)                              |
| Ontologies catalogued     | 8                                            |
| Dependencies catalogued   | 53 (Supplement C)                            |
| Failure modes             | 22 (Supplement G)                            |
| Recovery procedures       | 6 (Supplement H)                             |
| ADRs                      | 15 (ISDR-001 through ISDR-015)               |
| Governance Decision Recs  | 5 (IGDR-001 through IGDR-005)                |
| Anti-patterns             | 10 (AP-01 through AP-10)                     |
| Architectural invariants  | 10 (INVARIANT-01 through INVARIANT-10)       |
| Glossary entries          | 170+                                         |
| Sequence diagrams         | 10+                                          |
| Architecture diagrams     | 8+                                           |
| Document series position  | Capstone (document 27 of 27 in IIOS series)  |

---

*IIOS-INTEG-ARCH-001 Version 1.0.0*
*Investment Intelligence Operating System — Supreme Integration Architecture*
*This is the capstone and integration layer of the IIOS Architecture Series.*
*All 27 IIOS architecture documents are COMPLETE.*
*Architecture Council — Released 2026-07-04*
*End of Document.*

---

## EXTENDED REFERENCE — IIOS REGIME-STRATEGY COMPATIBILITY MATRIX

The Regime-Strategy Compatibility Matrix documents which strategy classes are
recommended, acceptable, and discouraged for each market regime. This matrix is
the primary input to the MetaLearning Engine's weight computation.

### Regime Taxonomy

| Code | Regime Name               | Duration Typical | P&L Profile  |
|------|---------------------------|-----------------|--------------|
| R-01 | BULL_TRENDING             | Weeks           | Positive     |
| R-02 | BEAR_TRENDING             | Days–Weeks      | Variable     |
| R-03 | SIDEWAYS_RANGE            | Days            | Low          |
| R-04 | HIGH_VOLATILITY           | Hours–Days      | High/Risky   |
| R-05 | LOW_VOLATILITY            | Days–Weeks      | Low          |
| R-06 | PRE_EVENT                 | Hours           | Risky        |
| R-07 | POST_EVENT_EXPANSION      | Hours           | High         |
| R-08 | SECTOR_ROTATION           | Weeks           | Sector-biased|
| R-09 | GLOBAL_RISK_OFF           | Days–Weeks      | Defensive    |
| R-10 | GLOBAL_RISK_ON            | Days            | Aggressive   |

---

### Compatibility Classification

**RECOMMENDED (R):** Strategy class has historically produced positive Sharpe ratio
in this regime with statistical significance. MetaLearning weight increase of 30-50%.

**ACCEPTABLE (A):** Strategy class works adequately in this regime. MetaLearning
weight unchanged.

**CAUTION (C):** Strategy class has mixed results in this regime. MetaLearning
weight decrease of 10-20%.

**AVOID (V):** Strategy class consistently underperforms in this regime. MetaLearning
weight decrease of 40-60%.

---

### Strategy Class × Regime Matrix

| Strategy Class           | R-01 | R-02 | R-03 | R-04 | R-05 | R-06 | R-07 | R-08 | R-09 | R-10 |
|--------------------------|------|------|------|------|------|------|------|------|------|------|
| Trend-Following (Long)   | R    | V    | V    | C    | A    | C    | A    | A    | V    | R    |
| Trend-Following (Short)  | V    | R    | V    | C    | A    | C    | A    | C    | R    | V    |
| Mean Reversion           | C    | C    | R    | V    | R    | V    | C    | C    | C    | C    |
| Momentum                 | R    | C    | V    | C    | V    | C    | R    | R    | V    | R    |
| Volatility Expansion     | C    | C    | V    | R    | V    | R    | R    | C    | C    | C    |
| Volatility Compression   | C    | C    | R    | V    | R    | V    | V    | C    | C    | C    |
| Breakout                 | R    | R    | V    | R    | V    | R    | R    | R    | C    | R    |
| Sector Rotation          | A    | C    | C    | C    | A    | C    | A    | R    | C    | A    |
| Defensive                | C    | A    | A    | C    | A    | A    | C    | C    | R    | C    |
| Options Strategies       | A    | A    | R    | R    | A    | R    | R    | A    | A    | A    |

**Note:** Assessments are based on theoretical regime alignment. MetaLearning
Engine refines these with empirical IIOS session performance data. After 100+
sessions in a given regime, empirical weights override static classification.

---

## EXTENDED REFERENCE — IIOS KNOWLEDGE ACCUMULATION MODEL

The IIOS Knowledge Engine accumulates structured knowledge over time. This section
documents the expected growth curve for the knowledge graph.

### Knowledge Graph Entity Categories

| Category              | Initial (Day 1) | Year 1 (est.) | Year 3 (est.) |
|-----------------------|-----------------|---------------|---------------|
| Market Entities       | 100             | 800           | 2,000         |
| Macro Entities        | 30              | 120           | 300           |
| Strategy Entities     | 50              | 200           | 500           |
| Agent Entities        | 62              | 62            | 80            |
| Session Records       | 0               | 250           | 750           |
| Decision Records      | 0               | 20,000+       | 60,000+       |
| Performance Records   | 0               | 50,000+       | 150,000+      |

---

### Relationship Growth

| Relationship Type           | Growth Rate          | Driver                    |
|-----------------------------|----------------------|---------------------------|
| MarketEntity-Correlation    | ~50/day (active)     | Correlation computation   |
| Strategy-Market-Fitness     | ~20/day              | Session observations      |
| RegimePattern               | ~5/week              | Regime classification     |
| EvidenceLink                | ~100/decision        | Decision provenance       |
| LearnedPattern              | ~10/week             | Learning engine output    |

---

### Quality Gates for Knowledge

The Knowledge Engine applies quality gates before accepting any entity or
relationship into the persistent graph:

**Entity Quality Gate:**
- Minimum observation count: 5 observations before entity becomes "established"
- Minimum confidence score: 0.70 before entity is classified
- Completeness: all required properties must be present

**Relationship Quality Gate:**
- Statistical significance: p < 0.05 for correlation-type relationships
- Recency: relationships older than 90 days without reinforcement are "stale"
- Consistency: new relationship must not contradict an established relationship
  at significance level p < 0.01

**Knowledge Graph Integrity Checks (daily):**
- No orphan nodes (all entities connected by at least one relationship)
- No circular temporal dependencies in causal chains
- No duplicate entities (deduplicated by canonical identifier)

---

## EXTENDED REFERENCE — IIOS INTRADAY DECISION CYCLE TIMELINE

### Full 172ms Decision Cycle (target)

`
T+000ms : Observation trigger received by Information Engine
T+002ms : Market data ingested and validated
T+004ms : Information object classification complete
T+006ms : Knowledge cache read (freshness confirmed < 5 min)
T+010ms : Entity state updates computed
T+015ms : Regime signal confirmed from Knowledge Engine
T+020ms : MetaLearning Engine reads regime; computes strategy weights
T+030ms : Prediction Engine receives weighted strategy signals
T+060ms : Prediction outputs generated (5 strategies × 3 signals)
T+070ms : Risk budget check (< 3ms with in-memory budget cache)
T+075ms : Debate Engine receives prediction signals and risk envelope
T+115ms : 5-agent debate complete; consensus score computed
T+120ms : Decision Engine evaluates score against 6.5 threshold
T+125ms : Governance Engine validates decision (authorization check)
T+130ms : Decision Record created with full 7-step provenance
T+140ms : Portfolio Engine receives decision with position sizing
T+145ms : Portfolio allocation computed; order parameters generated
T+155ms : Execution Engine receives order (paper or live)
T+165ms : Order simulated/submitted; confirmation received
T+170ms : Monitoring Engine records decision + order outcome
T+172ms : Cycle complete; engines return to observation state
`

**Note:** This is the target performance profile at 172ms full cycle. Actual
cycle times vary based on debate complexity, network latency, and Knowledge
Engine cache freshness. The 172ms figure is the NOMINAL OPTIMAL benchmark.

---

### Cycle Timing Budget Allocation

| Stage                        | Budget (ms) | Criticality  |
|------------------------------|-------------|--------------|
| Observation & Ingestion      | 6           | CRITICAL     |
| Knowledge Cache Read         | 4           | CRITICAL     |
| MetaLearning Computation     | 14          | HIGH         |
| Prediction Engine            | 30          | CRITICAL     |
| Risk Budget Check            | 5           | CRITICAL     |
| Debate Engine (5 agents)     | 40          | HIGH         |
| Decision Engine              | 5           | CRITICAL     |
| Governance Authorization     | 5           | CRITICAL     |
| Portfolio & Sizing           | 15          | HIGH         |
| Execution Engine             | 20          | CRITICAL     |
| Monitoring & Telemetry       | 7           | MEDIUM       |
| Overhead / Routing           | 21          | OVERHEAD     |
| **TOTAL**                    | **172**     | -            |

---

## EXTENDED REFERENCE — GLOBAL INTELLIGENCE INTEGRATION MAP

IIOS incorporates global macro intelligence as the first layer of context for
every investment decision. This section documents the integration architecture.

### Global Signal Sources

| Source          | Instrument Class    | IIOS Impact Pathway            |
|-----------------|--------------------|---------------------------------|
| S&P 500 Futures | US Equity           | NIFTY direction prior +/- 25bp  |
| Nikkei 225      | Asia-Pacific Equity | NIFTY opening gap predictor     |
| US 10Y Treasury | Risk-free rate      | Equity risk premium recalc      |
| DXY (USD Index) | Currency            | FII flow direction signal       |
| VIX             | US Implied Vol      | Kill switch (>45) + risk budget |
| Gold            | Safe haven          | Risk-off/Risk-on classifier     |
| Crude Oil       | Commodity           | Sector (Energy, OMCs) impact    |
| INR/USD         | Indian FX           | Direct import cost signal       |

### Correlation Architecture

The Information Engine computes rolling correlations between global signals and
NIFTY performance to establish which global signals currently have the strongest
predictive relationship.

**Correlation Window:** 20-session rolling window (approximately 1 month).
**Minimum Correlation for Use:** |r| > 0.30.
**Maximum Correlation for Solo Signal:** r < 0.85 with any other active signal
(avoids multicollinearity in the prediction model).

### Global Intelligence Contribution to Decision Score

Global intelligence contributes to the Prediction Engine's signal through a
dedicated "macro factor" agent in the Debate Engine. This agent receives:
- Current global intelligence snapshot from Knowledge Engine
- Historical NIFTY response to similar macro configurations (from Knowledge graph)
- Current regime classification

The macro factor agent's output is one of the 5 scores in the Debate Engine.
Its weight is amplified during GLOBAL_RISK_OFF and GLOBAL_RISK_ON regimes and
reduced during regime-neutral periods.

---

## EXTENDED REFERENCE — PAPER TRADING INFRASTRUCTURE SPECIFICATION

The paper trading mode is not a test mode — it is a fully operational mode with
production-identical logic, production-identical data, and production-identical
decision-making, except that orders are executed against a simulated fill engine
rather than a live broker.

### Paper Trading Mode Guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| Identical prediction logic | Paper mode uses same Prediction Engine path |
| Identical risk controls | All kill switches active in paper mode |
| Identical governance | Full governance certification required in paper mode |
| Identical learning | Learning Engine updates from paper trades |
| Complete trade journal | Every paper trade persisted to data/paper_trades.csv |
| P&L tracking | Cumulative P&L tracked from paper mode inception |

### Paper vs. Live Key Differences

| Aspect | Paper Mode | Live Mode |
|--------|-----------|-----------|
| Fill simulation | Virtual fill at mid-price | Broker fill at bid/ask |
| Slippage model | Configurable (default 0.05%) | Actual market slippage |
| Brokerage | Configurable (default 0.01%) | Dhan actual brokerage |
| Capital at risk | None (virtual capital) | Real capital |
| Order routing | OrderManager → PaperFillEngine | OrderManager → DhanBroker |
| Position limits | Same constitutional limits | Same constitutional limits |

### Transition from Paper to Live

The transition from paper trading to live trading requires:
1. Completion of CP-12 (Operational Readiness) with all gates PASS.
2. Minimum 90-session paper trading record with SQS >= 0.75 average.
3. Positive paper trading Sharpe ratio >= 0.8 over the 90-session window.
4. Architecture Council sign-off on transition readiness.
5. Explicit operator command to enable live mode (cannot be auto-triggered).

---

## CLOSING DEDICATION

*This document — IIOS-INTEG-ARCH-001 — is the culmination of the IIOS Architecture Series.*

*It represents an attempt to build investment decision-making with the same rigor,*
*discipline, and architectural integrity applied to the best systems engineering*
*projects in other domains. Markets are uncertain; systems need not be.*

*The 27 documents in the IIOS Architecture Series establish every layer of the*
*system — from the ontological representation of financial entities, through the*
*governance framework that prevents ungoverned risk-taking, to the learning system*
*that ensures the system improves with every session.*

*The measure of this architecture is not elegance. It is outcomes: better*
*investment decisions, better risk management, better learning, and better*
*protection of capital. Every architectural choice documented here serves*
*those four purposes.*

*— IIOS Architecture Series, Version 1.0.0*
*— Completed 2026*

---

*END OF IIOS-INTEG-ARCH-001*
*INVESTMENT INTELLIGENCE OPERATING SYSTEM — SUPREME INTEGRATION ARCHITECTURE*

---

## EXTENDED REFERENCE — IIOS ARCHITECTURE SERIES COMPLETE INDEX

The following documents constitute the IIOS Architecture Series.

| # | Document Code       | Title                                          | Status   |
|---|---------------------|------------------------------------------------|----------|
| 1 | IIOS-FOUND-001      | Foundation Architecture                        | COMPLETE |
| 2 | IIOS-FOUND-002      | System Philosophy and Principles               | COMPLETE |
| 3 | IIOS-FOUND-003      | Constitutional Framework                       | COMPLETE |
| 4 | IIOS-ONT-001        | Entity Ontology                                | COMPLETE |
| 5 | IIOS-ONT-002        | Event Ontology                                 | COMPLETE |
| 6 | IIOS-ONT-003        | Information Ontology                           | COMPLETE |
| 7 | IIOS-ONT-004        | Relationship Ontology                          | COMPLETE |
| 8 | IIOS-ONT-005        | Temporal Ontology                              | COMPLETE |
| 9 | IIOS-ONT-006        | Agent Ontology                                 | COMPLETE |
| 10| IIOS-ONT-007        | Knowledge Ontology                             | COMPLETE |
| 11| IIOS-ONT-008        | Governance Ontology                            | COMPLETE |
| 12| IIOS-ENG-001        | Information Engine Architecture                | COMPLETE |
| 13| IIOS-ENG-002        | Knowledge Engine Architecture                  | COMPLETE |
| 14| IIOS-ENG-003        | Prediction Engine Architecture                 | COMPLETE |
| 15| IIOS-ENG-004        | Risk Engine Architecture                       | COMPLETE |
| 16| IIOS-ENG-005        | Execution Engine Architecture                  | COMPLETE |
| 17| IIOS-ENG-006        | Learning Engine Architecture                   | COMPLETE |
| 18| IIOS-ENG-007        | Governance Engine Architecture                 | COMPLETE |
| 19| IIOS-ENG-008        | Portfolio Engine Architecture                  | COMPLETE |
| 20| IIOS-ENG-009        | Debate Engine Architecture                     | COMPLETE |
| 21| IIOS-ENG-010        | Simulation Engine Architecture                 | COMPLETE |
| 22| IIOS-ENG-011        | Monitoring Engine Architecture                 | COMPLETE |
| 23| IIOS-GOV-001        | Governance Framework                           | COMPLETE |
| 24| IIOS-OPS-001        | Operational Architecture                       | COMPLETE |
| 25| IIOS-MO-ARCH-001    | Master Orchestrator Architecture               | COMPLETE |
| 26| IIOS-QUAL-001       | System Quality Framework                       | COMPLETE |
| 27| IIOS-INTEG-ARCH-001 | Integration and Operational Architecture       | COMPLETE |

**Series Total:** 27 documents. All COMPLETE as of 2026.

The IIOS Architecture Series documents the complete architecture of the Investment
Intelligence Operating System from philosophical foundation through operational
deployment. Each document is authoritative within its domain. This document,
IIOS-INTEG-ARCH-001, is the capstone that integrates all others.

*IIOS Architecture Series — Complete.*
*Document IIOS-INTEG-ARCH-001 Version 1.0.0 — Final.*
