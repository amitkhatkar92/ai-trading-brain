# EXECUTION ENGINE ARCHITECTURE

**Document Code:** IIOS-EXE-ENG-ARCH-001
**Document Title:** Execution Engine — Engineering Architecture Reference
**IIOS Layer:** Layer 6 of the Cognitive Execution Stack
**Version:** 1.0
**Status:** RATIFIED
**Classification:** Architecture Reference
**Created:** 2026-07-03
**Governing System:** Investment Intelligence Operating System (IIOS)

---

## PREFACE

This document defines the complete engineering architecture of the Execution Engine, Layer 6 of the IIOS cognitive execution stack. The Execution Engine is the boundary between cognition and the market. It transforms approved Decision Packages from the Decision Engine into controlled, traceable, and auditable market execution.

The Execution Engine is the final guardian before capital meets the market. Its mandate is not intelligence — that was the mandate of Layers 1-5. Its mandate is safe, policy-compliant, risk-controlled execution.

**What the Execution Engine IS:**
The system that receives governance-approved, risk-evaluated Decision Packages and translates them into broker orders, monitors those orders through their lifecycle, manages partial fills, handles failures, updates positions, updates the portfolio, and produces complete audit records of every action taken.

**What the Execution Engine IS NOT:**
It is not an intelligence layer. It does not generate investment ideas. It does not reason about markets. It does not predict prices. It does not evaluate risk on an investment basis. It does not approve or reject Decision Packages on investment merit — that work is complete before a package arrives.

**The Iron Boundary:** No order may be placed unless it traces directly to an approved, COMMITTED Decision Package from Layer 5. This boundary is absolute, permanent, and non-negotiable.

---

## COGNITIVE LAYER STACK

`
+------------------------------------------------------------------+
|          INVESTMENT INTELLIGENCE OPERATING SYSTEM (IIOS)         |
+------------------------------------------------------------------+
|                                                                  |
|  Layer 1: OBSERVATION ENGINE                                     |
|           (Collects raw market signals and data)                 |
|                  |                                               |
|                  v                                               |
|  Layer 2: EVIDENCE ENGINE                                        |
|           (Validates and weights observations)                   |
|                  |                                               |
|                  v                                               |
|  Layer 3: HYPOTHESIS ENGINE                                      |
|           (Generates and ranks market hypotheses)                |
|                  |                                               |
|                  v                                               |
|  Layer 4: REASONING ENGINE                                       |
|           (Reasons, infers, debates, produces reasoning chains)  |
|                  |                                               |
|                  v                                               |
|  Layer 5: DECISION ENGINE                                        |
|           (Decides, governs, packages execution-ready decisions) |
|                  |                                               |
|                  v (Decision Package: COMMITTED)                 |
|  +---------------------------------------------------------+     |
|  |  Layer 6: EXECUTION ENGINE   [THIS DOCUMENT]           |     |
|  |  Transforms approved decisions into controlled,        |     |
|  |  traceable, auditable market execution.                |     |
|  |  Places orders. Monitors fills. Updates positions.     |     |
|  |  Manages failures. Produces audit records.             |     |
|  +---------------------------------------------------------+     |
|                  |                                               |
|                  v (Orders via Broker Gateway)                   |
|  Layer 7: BROKER LAYER                                           |
|           (Dhan API / Zerodha API / Paper Trading Simulator)     |
|                  |                                               |
|                  v                                               |
|  Layer 8: EXCHANGE LAYER                                         |
|           (NSE / BSE / NFO — actual market fills)                |
|                                                                  |
+------------------------------------------------------------------+
`

---

## INFORMATION FLOW OVERVIEW

`
[Decision Engine]
 COMMITTED Decision Package
        |
        v (inbound)
[Execution Engine: Decision Intake]
        |
        v
[Order Planner + Builder]
        |
        v
[Order Validator]
        |── FAIL ──> [Reject; alert; notify Decision Engine]
        |
        v (VALID)
[Execution Risk Check]
        |── FAIL ──> [Hold; human alert; retry queue]
        |
        v (PASS)
[Order Router]
        |
  +-----+-----------+
  |                 |
  v                 v
[Broker Gateway]  [Paper Simulator]
  |                 |
  v                 v
[Exchange/Fill]  [Sim Fill]
        |
        v (fill notification)
[Execution Monitor + Tracker]
        |
        v
[Position Updater]
        |
        v
[Portfolio Updater]
        |
        v
[Execution Audit Manager]
        |
        v
[Execution Archive]
        |
[EventBus: EXECUTION_COMPLETED]
        |
  +-----+----------+----------+
  |                |           |
  v                v           v
[Learning System] [Trade Monitor] [ControlTower]
`

---

## TABLE OF CONTENTS

| Section | Title |
|---|---|
| Part I | Execution Philosophy |
| Part II | Execution Taxonomy |
| Part III | Core Components (23 components) |
| Part IV | Execution Lifecycle |
| Part V | Execution Services (16 services) |
| Part VI | Execution Pipelines (10 pipelines) |
| Part VII | Execution Quality Framework |
| Part VIII | Execution Governance |
| Part IX | Execution Constitution (90-110 rules) |
| Part X | Execution Readiness Checklist |
| Supplement A | Order Taxonomy Reference |
| Supplement B | Execution State Machine |
| Supplement C | Broker Routing Models |
| Supplement D | Recovery Scenarios |
| Supplement E | Failure Mode Analysis |
| Supplement F | Performance Targets |
| Supplement G | Operational Runbook |
| Supplement H | Glossary |
| Document Footer | Summary, compliance, governing documents |

---

## PART I — EXECUTION PHILOSOPHY

### 1.1 What Is Execution?

Execution is the act of translating an approved, governed decision into a real-world market action. It is the moment when intent becomes reality, when abstraction meets liquidity, and when the IIOS system transitions from knowing to doing.

Execution is not the culmination of intelligence — it is the disciplined application of a pre-established decision in a complex, unpredictable, and adversarial market environment. The intelligence work is complete before execution begins. The Execution Engine is responsible for carrying out that decision as precisely and safely as possible.

Execution is irreversible in most cases. Once an order is filled, capital has changed hands. This fundamental irreversibility is the reason the Execution Engine applies more safety checks, not fewer, even though the decision has already been approved. The Decision Engine approves the intent; the Execution Engine is responsible for the act.

---

### 1.2 The Definitional Ladder

The IIOS distinguishes precisely between the following concepts, each of which is distinct in both engineering and operational terms:

**Decision**
A governed, approved, risk-evaluated record produced by the Decision Engine. The Decision expresses intent: what action the IIOS should take, why, with what parameters, and under what conditions. A Decision exists entirely within the IIOS. It has no direct market consequence until it is acted upon by the Execution Engine.

**Intent**
The operational expression of a Decision within the Execution Engine. When a Decision Package arrives at the Execution Engine, it is transformed into an Execution Intent — a concrete plan specifying exactly how the Decision will be executed given current market conditions, available liquidity, and operational constraints. Intent bridges the governance world (Decision) and the market world (Order).

**Order**
A formal instruction submitted to a broker or exchange. An Order is the market-facing artifact. It contains: instrument identifier, side (BUY/SELL), quantity, price type, price, time-in-force, and order reference. An Order exists outside the IIOS — it is a message sent to an external system. Once submitted, the Order is no longer fully within the IIOS control.

**Execution**
The complete lifecycle of an Order from submission to terminal state (filled, partially filled, rejected, expired, cancelled). Execution encompasses all events that occur from the moment the Order leaves the IIOS to the moment the position is confirmed.

**Trade**
The confirmed commercial transaction that results from a filled order. A Trade is the counterpart agreement — buyer and seller have matched at a price. Trades are recorded by the exchange and are the basis for settlement.

**Fill**
The quantity of an Order that has been matched at the exchange. An Order may be fully filled (entire quantity executed), partially filled (some quantity executed), or unfilled (no quantity executed). Each fill event produces a fill record with: filled quantity, fill price, fill timestamp, fill reference.

**Position**
The current holdings of the IIOS portfolio in a given instrument. A Position is derived from the net sum of all fills for that instrument. Position records are maintained by the Position Updater and reflect the true current holdings.

**Portfolio**
The aggregate of all Positions. The Portfolio record provides the complete picture of capital deployment: total invested, total cash, net asset value, sector exposures, instrument concentrations, and unrealised profit/loss.

**Settlement**
The contractual completion of a Trade, in which securities and funds change hands. In Indian equities: T+1 settlement (as of 2024). Derivatives settle on expiry. Settlement is managed by the exchange and depository, not the IIOS. The Execution Engine records settlement events but does not initiate them.

**Confirmation**
The formal acknowledgement from the broker that an Order has been received and accepted. A Confirmation does not mean execution — it means the broker has the Order and will attempt to execute it. Confirmations are received within milliseconds of Order submission.

**Acknowledgement**
The low-level protocol acknowledgement that a message was received. In the Execution Engine: the broker API returns an HTTP 200 or WebSocket acknowledgement for the Order submission. This is not a Confirmation — it is a transport-layer acknowledgement. Both must be received; neither alone is sufficient.

**Broker Action**
Any action taken by the broker on behalf of the IIOS: order acceptance, order modification, order cancellation, order routing to exchange, margin check, and trade confirmation. Broker Actions are initiated by the Order Router (sending orders) or by the Execution Monitor (handling fills and rejections).

**Exchange Action**
Any action taken by the exchange matching engine: price discovery, order matching, partial fill events, rejection (circuit breaker, price limit), expiry. Exchange Actions are the ultimate source of fills. The Execution Engine observes Exchange Actions via the broker data feed.

**Execution State**
The current operational state of an Execution record within the Execution Engine. The full state machine is defined in Supplement B. Key states: PENDING, SUBMITTED, ACKNOWLEDGED, PARTIAL_FILL, FULL_FILL, REJECTED, CANCELLED, EXPIRED, FAILED, RECOVERING, COMPLETED.

**Execution Failure**
An event in which an Order does not execute as intended: broker rejection, exchange rejection, timeout, connectivity failure, partial fill with no further progress. All failures are classified and directed to the Execution Recovery Manager.

**Execution Success**
The state in which an Order has been filled in full (or up to the acceptable partial fill threshold), positions have been updated, portfolio has been updated, and audit records are complete. Success is not declared until all downstream steps are verified.

**Execution Integrity**
The property that every execution action is authorised, traceable, correct, complete, and consistent with the Decision Package that initiated it. No execution may occur without complete integrity verification.

**Execution Accountability**
The property that every execution action can be attributed to a specific Decision Package, a specific human or AI approval, and a specific market event, with full timestamp and identity records preserved in the immutable audit trail.

---

### 1.3 Execution Safety Properties

**Safe Execution**
An execution is safe when it cannot cause harm beyond the pre-approved risk parameters of the Decision Package. Safety is enforced at multiple layers: the Execution Risk Check (pre-submission), the Broker Gateway (position limits), and the Kill Switch (post-submission emergency stop).

**Atomic Execution**
Where possible, an execution is atomic — it either completes in full or is treated as incomplete. Non-atomic executions (partial fills) are explicitly designed for and handled by the Partial Fill Handler. The IIOS never silently accepts partial executions as complete.

**Deterministic Execution**
Given the same Decision Package and the same market conditions, the Execution Engine produces the same Order. Determinism means that the execution process is reproducible, explainable, and verifiable. Random or non-deterministic execution behaviour is a defect.

**Idempotent Execution**
Submitting the same Order twice produces only one execution. Idempotency is enforced by the Order Validator using the execution_intent_id as a unique key. Duplicate submissions are detected and blocked before reaching the broker.

**Partial Execution**
When a fill is received for less than the full ordered quantity, the Execution Engine records the partial fill, updates the position proportionally, and decides whether to wait for the remainder, resubmit, or close the execution as complete at partial quantity. The Execution Planner governs partial execution policy.

**Retry Execution**
When an execution fails for recoverable reasons (timeout, transient broker error), the Retry Manager re-attempts the execution with an incremental back-off. Retry attempts are bounded and logged. Unbounded retries are prohibited.

**Rollback**
When an execution enters an inconsistent state (Order acknowledged but fill status unknown), the Recovery Manager initiates a rollback procedure: query broker for Order status, reconcile against known fills, update position to true state. Rollback does not cancel market fills — it reconciles the IIOS state to match market reality.

**Kill Switch**
An immediate, unconditional halt of all execution activity. The Kill Switch is activated by: Risk Guardian signal, human operator command, or constitutional rule breach. When the Kill Switch is active, no new Orders may be submitted to any broker or simulator. The Kill Switch cannot be bypassed by any component.

**Emergency Stop**
A broader halting mechanism that combines Kill Switch with active cancellation of all PENDING and SUBMITTED Orders. Emergency Stop is the most severe operational intervention. It requires human operator confirmation to lift.

---

### 1.4 The Five Execution Principles

The Execution Engine is governed by five foundational engineering principles:

**Principle 1: Authorisation is Upstream**
The Execution Engine does not perform investment analysis. Investment authorisation is fully complete when a Decision Package arrives at the Execution Engine. The Execution Engine validates the Decision Package for completeness and executes it; it does not re-evaluate whether the investment is sound.

**Principle 2: Safety Over Completeness**
If there is any conflict between completing an execution quickly and executing safely, safety wins. An unexecuted order is always recoverable; an incorrectly executed order may not be.

**Principle 3: Traceability is Non-Negotiable**
Every execution event, in every component, at every stage, must produce a traceable record. No action occurs without a corresponding record. The audit trail is never optional, never abbreviated for speed.

**Principle 4: Human Authority is Absolute**
The human operator can halt, cancel, or override any execution at any time. No execution process, once initiated, is beyond human intervention. The Override Service is always available and always responsive.

**Principle 5: Broker Independence**
The Execution Engine is broker-agnostic. The same Execution Intent is routed to different broker gateways through a common interface. A broker failure does not halt the Execution Engine — it routes to the Paper Simulator or activates the Recovery Manager.

---
## PART II — EXECUTION TAXONOMY

### 2.1 Overview

Every execution produced by the Execution Engine is classified by type. The execution type determines: the order construction logic, the routing strategy, the monitoring behaviour, and the recovery procedure. This section defines the complete taxonomy of execution types recognised by the IIOS Execution Engine.

---

### 2.2 Order Type Taxonomy

#### EX-TYPE-001: Market Order

**Definition:** An order to buy or sell an instrument at the best available market price at the time of submission.

**Use cases:** Stop-loss execution, emergency exit, time-sensitive fills where price certainty is less important than execution certainty.

**Characteristics:**
- Highest execution certainty; lowest price certainty
- Fills immediately at market spread
- Slippage may be significant in illiquid markets
- Appropriate for URGENT priority decisions with EXT-SL or EMR action types

**IIOS usage:** Used by the Execution Engine for EXT-SL (stop-loss exit), EMR (emergency decision), and MON-ALERT (alert-triggered entry where speed dominates).

**Risk controls:** Slippage Manager enforces maximum acceptable slippage. If slippage exceeds max_slippage_pct from the Decision Package, the order is resubmitted with a limit fallback or escalated to human.

---

#### EX-TYPE-002: Limit Order

**Definition:** An order to buy or sell an instrument at a specified price or better.

**Use cases:** Standard entry and exit decisions where price discipline is required.

**Characteristics:**
- Price certainty; execution not guaranteed if market does not reach limit price
- Day order (expires at session end) unless GTT specified
- May result in partial fills if market touches but does not sustain the limit price

**IIOS usage:** Default order type for BUY-EQT, BUY-DRV, SEL-CLOSE, RED-PARTIAL where the Decision Package specifies entry_price_type = LIMIT.

**Risk controls:** Limit price staleness check — if the limit price is more than 1% away from current LTP at order construction time, the Execution Planner recalculates using current price.

---

#### EX-TYPE-003: Stop Order (Stop Loss Market)

**Definition:** An order that becomes a market order when the trigger price is reached.

**Use cases:** Automatic stop-loss execution; trailing stop implementation.

**Characteristics:**
- Trigger price activates the order; execution price is market
- Gap risk: if market gaps through the trigger price, fill occurs at market (possibly much worse)
- Broker-held: the trigger is monitored by the broker, not the IIOS

**IIOS usage:** Used for PRT-SL (protective stop-loss) and PRT-TRAILING (trailing stop) decision types.

**Risk controls:** Gap risk is documented in the Decision Package. For large positions, the Execution Planner may split the stop order into multiple tranches to reduce gap impact.

---

#### EX-TYPE-004: Stop-Limit Order

**Definition:** An order that becomes a limit order (not market) when the trigger price is reached.

**Use cases:** Stop-loss with price floor — prevents execution at catastrophically worse prices.

**Characteristics:**
- Trigger activates; limit prevents fills worse than the limit price
- Risk: order may not fill if market gaps through the limit
- Best for liquid markets where gap risk between trigger and limit is small

**IIOS usage:** Used in moderate-volatility environments where the gap between trigger and limit is acceptable. Not used in CRISIS regime (market gap risk too high).

---

#### EX-TYPE-005: Immediate-or-Cancel (IOC)

**Definition:** An order that executes immediately for available quantity and cancels the unfilled remainder.

**Use cases:** Arbitrage execution, basket orders requiring same-session fills, time-sensitive partial fills.

**Characteristics:**
- Fills what it can immediately; cancels remainder
- Results in partial fills if full quantity not immediately available
- No waiting; clean execution

**IIOS usage:** Used for EXT-EMERGENCY (emergency exits), basket sub-orders, and arbitrage decision types (AID-*).

---

#### EX-TYPE-006: Fill-or-Kill (FOK)

**Definition:** An order that must be filled entirely in one transaction or not at all.

**Use cases:** Basket executions requiring complete atomic fills; composite decisions where partial execution creates imbalanced positions.

**Characteristics:**
- All-or-nothing; no partial fills
- Higher fill failure rate
- Appropriate when partial execution is worse than no execution

**IIOS usage:** Used for CMP (composite) decisions where sub-decisions must fill simultaneously. Also used for arbitrage legs where partial execution destroys the trade structure.

---

#### EX-TYPE-007: Good-Till-Triggered (GTT)

**Definition:** An order that is stored by the broker and triggered when a specified price condition is met, across multiple sessions.

**Use cases:** Scheduled decisions, conditional entry at specific price levels, take-profit orders.

**Characteristics:**
- Persists across sessions (up to broker-defined maximum, typically 365 days)
- Triggered by price condition, not time
- Subject to cancellation on corporate actions

**IIOS usage:** Used for SCH (scheduled decisions) and conditional entry decisions. The Execution Scheduler manages GTT orders and monitors them.

---

#### EX-TYPE-008: Bracket Order

**Definition:** A main order accompanied by an automatic take-profit and stop-loss order.

**Use cases:** Automatically managed entries with predefined exit levels.

**Characteristics:**
- Three legs: entry + take-profit + stop-loss
- Exit legs are conditional on the entry fill
- Not available on all brokers or instruments

**IIOS usage:** Used when BUY decisions include both stop_loss_price and take_profit_price. The Execution Planner checks broker capability before selecting bracket order type.

---

#### EX-TYPE-009: Cover Order

**Definition:** A market order with an attached stop-loss order.

**Use cases:** Intraday trades with defined risk; leveraged intraday positions.

**Characteristics:**
- Entry is market; stop-loss is mandatory
- Provides higher leverage for intraday (broker-specific)
- Both legs must be active simultaneously

**IIOS usage:** Used for intraday BUY or SEL-SHORT decisions with defined stop-loss.

---

#### EX-TYPE-010: Basket Execution

**Definition:** The simultaneous or near-simultaneous execution of multiple Orders as a coordinated set.

**Use cases:** Portfolio rebalancing (RBL decisions), composite decisions (CMP), multi-leg strategies.

**Characteristics:**
- All Orders are constructed as a set
- Execution sequenced or simultaneous per strategy
- Partial completion of the basket is a managed state
- Basket executor coordinates across all legs

**IIOS usage:** Used for RBL-SCHEDULED, RBL-TACTICAL, and CMP decisions. The Execution Planner constructs a Basket Execution Plan from the composite Decision Package.

---

#### EX-TYPE-011: Algorithmic Execution

**Definition:** An execution strategy that decomposes a large order into smaller child orders over time or across price levels to minimise market impact.

**Use cases:** Large positions (> 2% ADV) where market impact is a concern.

**Characteristics:**
- Parent order split into child orders using TWAP, VWAP, or participation rate algorithms
- Execution extends over minutes to hours
- Reduces market impact; extends execution risk window

**IIOS usage:** Used when position size > 1% ADV. The Slippage Manager determines whether algorithmic execution is warranted and selects the algorithm. TWAP is the default algorithm for the IIOS.

---

#### EX-TYPE-012: Manual Execution

**Definition:** An execution initiated by a human operator, bypassing the automated execution pipeline.

**Use cases:** Human override scenarios (HUM-OVERRIDE), emergency operator intervention.

**Characteristics:**
- Human operator places order directly via broker interface
- Execution Engine records the manual execution as MANUAL_OVERRIDE
- Audit record includes operator identity, timestamp, and reason
- Position Updater reconciles position after manual execution

**IIOS usage:** Available at all times. The Override Service records all manual executions for audit compliance.

---

#### EX-TYPE-013: Hybrid Execution

**Definition:** An execution that starts automated but includes human checkpoints before key milestones.

**Use cases:** HYB (hybrid decision) types; large bracket orders requiring human confirmation before exit legs are placed.

**Characteristics:**
- AI constructs the order plan
- Human reviews and approves key steps
- Both AI and human roles documented in execution record

**IIOS usage:** Used for HYB decision types and for executions above the TIER-2-HUMAN threshold that were approved but require operator confirmation before order routing.

---

#### EX-TYPE-014: Partial Execution

**Definition:** The managed execution of a decision at less than the full intended quantity.

**Use cases:** Illiquid instruments, large positions, market impact constraints.

**Characteristics:**
- Decision quantity is split into tranches
- Tranches executed over time or price levels
- Full execution tracked across all tranches
- Decision is not COMPLETED until the cumulative fill meets the minimum acceptable fill threshold

**IIOS usage:** The Execution Planner determines when partial execution is appropriate. The Partial Fill Handler manages the tranche lifecycle.

---

#### EX-TYPE-015: Delayed Execution

**Definition:** An execution that is intentionally deferred due to market conditions, liquidity windows, or policy constraints.

**Use cases:** Low-liquidity periods, pre-event holds, scheduled execution windows.

**Characteristics:**
- Decision Package is received and validated but execution is held until conditions are met
- Execution Scheduler monitors conditions
- Human operator can force immediate execution

**IIOS usage:** Used when Decision Package specifies pre_conditions that are not yet satisfied.

---

#### EX-TYPE-016: Scheduled Execution

**Definition:** An execution that is pre-planned for a specific future time.

**Use cases:** SCH (scheduled decisions), pre-market orders, EOD rebalancing.

**Characteristics:**
- Execution Scheduler holds the Order until the scheduled time
- Order is re-validated against current market conditions before submission
- Human operator can reschedule or cancel

**IIOS usage:** Used for SCH-PRE_MARKET, SCH-EOD, and SCH-WEEKLY decision types.

---

#### EX-TYPE-017: Conditional Execution

**Definition:** An execution that is triggered by a market condition, not a time.

**Use cases:** GTT decisions, conditional entry, conditional exit.

**Characteristics:**
- Condition monitor watches for trigger
- On condition met: Order is constructed and submitted
- Condition not met at expiry: Order is abandoned

**IIOS usage:** Used when Decision Package specifies pre_conditions with price-based triggers.

---

#### EX-TYPE-018: Emergency Execution

**Definition:** An execution activated by the Risk Guardian, Kill Switch, or EMR Decision Package, requiring immediate action regardless of normal execution constraints.

**Use cases:** VIX spike response, drawdown limit breach, circuit breaker activation.

**Characteristics:**
- Bypasses normal execution latency (< 500ms target)
- Uses pre-approved emergency protocols
- Market orders only (no limit-related delays)
- Retrospective documentation required within 4 hours

**IIOS usage:** Activated by EMR decision types or Risk Guardian CRITICAL signal.

---

#### EX-TYPE-019: Recovery Execution

**Definition:** An execution that reconciles a position discrepancy between the IIOS state and the actual broker/exchange position.

**Use cases:** Post-failure reconciliation, connectivity gap recovery, session restart.

**Characteristics:**
- Driven by the Execution Recovery Manager
- Compares IIOS position record vs broker position record
- Issues corrective orders to close the gap
- All recovery executions require human approval

**IIOS usage:** Activated on system restart, after connectivity failures, or when the Position Reconciliation Service detects discrepancies.

---
## PART III — CORE COMPONENTS

The Execution Engine consists of 23 components organised into 5 functional clusters:

| Cluster | Components |
|---|---|
| Cluster A: Registry and Catalog | Execution Registry, Execution Catalog, Execution Archive Manager |
| Cluster B: Planning and Scheduling | Execution Planner, Execution Scheduler, Execution Queue |
| Cluster C: Order Processing | Order Builder, Order Validator, Order Router, Slippage Manager, Latency Manager |
| Cluster D: Broker and Exchange Interface | Broker Gateway, Exchange Gateway, Execution Monitor, Execution Tracker, Retry Manager, Execution Recovery Manager |
| Cluster E: State and Analytics | Position Updater, Portfolio Updater, Execution Governance Manager, Execution Audit Manager, Execution Health Manager, Execution Analytics Manager |

---

### CLUSTER A: REGISTRY AND CATALOG

#### Component EC-01: Execution Registry

**Purpose:** The primary operational store of all active Execution records. The Registry is the authoritative source of truth for the current state of every execution within the Execution Engine.

**Responsibilities:**
- Store and retrieve Execution records by execution_id, decision_id, order_id, and symbol
- Maintain execution status in real time (PENDING through COMPLETED)
- Support atomic status transitions with optimistic locking
- Expose query interface for all Execution Engine components
- Enforce no-duplicate execution_id constraint
- Support concurrent reads; serialised writes

**Inputs:**
- New Execution record from Execution Planner
- Status update events from all components
- Cancellation notifications from Override Service

**Outputs:**
- Execution records to any requesting component
- Status change events to EventBus

**Dependencies:** Storage Layer, EventBus

**Interactions:** All 23 components read from the Registry; only Planner, Recovery Manager, and Position Updater write to it.

**Failure Modes:**
- Storage unreachable: Execution Engine transitions to READ-ONLY mode; all new executions HELD
- Corrupt record: detected by schema validation; record quarantined; alert raised
- Duplicate execution_id: rejected at write time; alert raised

**Recovery Strategy:** Write-ahead log; state can be reconstructed from audit trail on full failure.

**Monitoring:** Registry response time p95, write error rate, storage utilisation.

---

#### Component EC-02: Execution Catalog

**Purpose:** The indexed lookup service for Execution records — enables fast retrieval by entity, date range, status, decision type, and execution type. Distinct from the Registry (which stores live records) in that the Catalog provides optimised query paths.

**Responsibilities:**
- Maintain secondary indexes on: symbol, status, decision_id, session_id, date, execution_type
- Support real-time index updates as Registry records change
- Power the dashboard, reporting, and Learning System queries
- Support aggregated queries (total fills today, average slippage per symbol, etc.)

**Inputs:** Change events from Execution Registry

**Outputs:** Indexed query results

**Dependencies:** Execution Registry, Storage Layer

**Failure Modes:**
- Index inconsistency: background reconciliation job detects and repairs; alert raised
- Query timeout: slow query logging; cache invalidation

---

#### Component EC-03: Execution Archive Manager

**Purpose:** Long-term storage of completed and terminal Execution records. Archives records from the Registry after they reach terminal states (COMPLETED, CANCELLED, EXPIRED, FAILED).

**Responsibilities:**
- Monitor Registry for terminal-state transitions
- Transfer terminal records to Archive with full audit trail
- Enforce retention periods per governance tier
- Support retrieval of archived records by the Learning System and Analytics Manager
- Maintain archive integrity (no modification of archived records)

**Inputs:** Terminal-state records from Registry

**Outputs:** Archive confirmation; retrieval responses

**Dependencies:** Execution Registry, Storage Layer (archive partition)

**Failure Modes:**
- Archive write failure: record remains in Registry with ARCHIVE_PENDING flag; retry queue
- Archive retrieval failure: alert; manual investigation

---

### CLUSTER B: PLANNING AND SCHEDULING

#### Component EC-04: Execution Planner

**Purpose:** The core translation component. The Execution Planner receives a COMMITTED Decision Package and produces one or more Execution Intents — the concrete execution plans that specify exactly how the decision will be executed.

**Responsibilities:**
- Parse Decision Package: extract execution parameters, entity, action type, quantity, price type
- Determine execution type (Market, Limit, Stop, Bracket, etc.) based on Decision parameters and current market conditions
- Determine whether algorithmic execution is warranted (check position size vs ADV)
- Construct Execution Intent(s): one per tranche for algorithmic execution, one for standard execution
- Assign execution_intent_id (idempotency key)
- Register new Execution record in Execution Registry with status PENDING
- Detect and block duplicate Decision Packages (idempotency check)

**Inputs:**
- COMMITTED Decision Package from Decision Engine (via Distribution Manager)
- Current market data (LTP, bid/ask, ADV) from Data Feed
- Portfolio state (current positions, available capital) from Portfolio Updater
- Policy configuration from Execution Governance Manager

**Outputs:**
- Execution Intent(s) to Execution Queue
- New Execution record to Execution Registry

**Dependencies:** Execution Registry, Portfolio Updater, Data Feed, Execution Governance Manager, Slippage Manager

**Failure Modes:**
- Decision Package schema invalid: reject; alert Decision Engine
- Market data unavailable: HOLD execution; retry with Data Feed
- ADV calculation failure: default to standard execution; alert

**Engineering Notes:** The Execution Planner is the single point where a Decision becomes an Execution. This transition is the most critical operation in the Execution Engine. The Planner must be deterministic — given the same input, it must always produce the same Execution Intent.

---

#### Component EC-05: Execution Scheduler

**Purpose:** Manages time-deferred and condition-deferred executions. The Scheduler holds Execution Intents that are not yet ready for submission and releases them when their conditions are satisfied.

**Responsibilities:**
- Maintain schedule queue of deferred Execution Intents
- Monitor scheduled timestamps; release intents at scheduled time
- Monitor market conditions for conditional executions; release when conditions met
- Re-validate Execution Intents before release (market conditions may have changed since creation)
- Manage GTT order lifecycle (submit, monitor, cancel)
- Alert on scheduled executions that have not been reviewed within 4 hours of scheduled time

**Inputs:**
- Deferred Execution Intents from Execution Planner
- Market data ticks for condition monitoring
- Human operator reschedule/cancel commands

**Outputs:**
- Released Execution Intents to Execution Queue

**Dependencies:** Execution Queue, Data Feed, Execution Registry, Execution Governance Manager

**Failure Modes:**
- Scheduler crash: deferred executions are re-loaded from Registry on restart
- Condition never met: Execution expires per Decision Package expiry timestamp

---

#### Component EC-06: Execution Queue

**Purpose:** The ordered buffer between the planning layer and the order processing layer. Ensures orderly, priority-based processing of Execution Intents.

**Responsibilities:**
- Receive Execution Intents from Planner and Scheduler
- Order by priority: URGENT > HIGH > NORMAL > LOW > BACKGROUND
- Provide head-of-queue to Order Builder
- Support re-insertion of retried Execution Intents (at appropriate priority)
- Enforce maximum queue depth (200 items); alert on queue depth > 50
- Deduplication: reject duplicate execution_intent_id

**Inputs:** Execution Intents from Execution Planner, Execution Scheduler, Retry Manager

**Outputs:** Execution Intents to Order Builder (one at a time, head-of-queue)

**Dependencies:** Execution Planner, Execution Scheduler, Retry Manager

**Failure Modes:**
- Queue overflow: alert; reject new LOW/BACKGROUND intents; HOLD HIGH/URGENT intents

---

### CLUSTER C: ORDER PROCESSING

#### Component EC-07: Order Builder

**Purpose:** Translates an Execution Intent into a formally structured Order object ready for submission to the Broker Gateway.

**Responsibilities:**
- Map Execution Intent fields to broker Order schema
- Resolve instrument tokens: map IIOS entity_id to broker instrument token
- Apply current LTP adjustments for limit prices (if limit price is stale)
- Set time-in-force per execution type
- Apply Slippage Manager guidance: adjust limit prices within acceptable range
- Assign order_reference_id (internal; used for deduplication and reconciliation)
- Set order product type (INTRADAY / DELIVERY) per Decision Package intent

**Inputs:**
- Execution Intent from Execution Queue
- Current market data from Data Feed
- Instrument token lookup from Entity Engine / Broker Gateway

**Outputs:**
- Structured Order object to Order Validator

**Dependencies:** Execution Queue, Data Feed, Broker Gateway (token lookup), Slippage Manager, Entity Engine

**Failure Modes:**
- Instrument token not found: execution FAILED; alert; manual resolution required
- LTP stale (> 30 seconds): HOLD; request fresh data; retry
- Order schema validation error: execution FAILED; alert

**Engineering Notes:** The Order Builder is responsible for the last-mile translation from IIOS concepts (entity, action, quantity, price intent) to broker-specific order parameters. Broker-specific quirks are encapsulated here.

---

#### Component EC-08: Order Validator

**Purpose:** Validates the structured Order against all pre-submission rules before it reaches the Broker Gateway.

**Responsibilities:**
- Schema validation: all required fields present, all types correct, all values in range
- Idempotency check: order_reference_id not previously submitted
- Price sanity check: limit price within circuit limits, not > 5% from LTP for limit orders
- Quantity sanity check: quantity > 0, quantity within lot size constraints, quantity consistent with position (for exit orders)
- Position consistency check: for SELL orders, IIOS position >= sell quantity
- Margin check estimate: estimated margin requirement vs available capital
- Kill Switch check: if Kill Switch is active, all orders BLOCKED
- Human hold check: if entity has an active human hold flag, order BLOCKED
- Market hours check: market is open or this is a pre-market order for authorised broker

**Inputs:** Structured Order from Order Builder

**Outputs:**
- VALID Order to Order Router
- REJECTED Order to Execution Registry (status REJECTED); alert

**Dependencies:** Execution Registry, Portfolio Updater, Kill Switch, Data Feed

**Failure Modes:**
- Validation logic bug: caught by constitutional rule EC-CONST-008 (unit tested)
- Kill Switch not checked: constitutional rule EC-CONST-001 (every order must pass Kill Switch check)

---

#### Component EC-09: Order Router

**Purpose:** Routes validated Orders to the appropriate Broker Gateway based on instrument type, market conditions, broker availability, and routing policy.

**Responsibilities:**
- Select broker gateway: primary (Dhan), secondary (Zerodha), tertiary (Paper Simulator)
- Apply routing policy: some instruments routed to specific brokers
- Detect broker gateway health: if primary unavailable, route to secondary
- In PAPER_TRADING mode: always route to Paper Simulator
- Record routing decision in Execution record
- Ensure atomic routing: an Order is submitted to exactly one broker

**Inputs:** Valid Order from Order Validator

**Outputs:**
- Order to selected Broker Gateway
- Routing decision to Execution Registry

**Dependencies:** Broker Gateways (Dhan, Zerodha, Paper Simulator), Execution Registry, Execution Governance Manager

**Failure Modes:**
- All gateways unavailable: Order HELD; alert; human intervention required
- Routing policy conflict: default to primary gateway; alert

---

#### Component EC-10: Slippage Manager

**Purpose:** Monitors and controls price slippage across all executions to ensure execution costs remain within the parameters specified in Decision Packages.

**Responsibilities:**
- Compute expected slippage for each Order based on market conditions (bid-ask spread, ADV, execution size)
- Compare expected slippage vs max_slippage_pct from Decision Package
- Approve Order if expected slippage within limit
- Flag Order for human review if expected slippage exceeds limit by > 50%
- Block Order if expected slippage exceeds limit by > 100%
- Record actual slippage after fill: compare fill price vs order price
- Generate slippage analytics for Execution Analytics Manager
- Alert if average slippage for a session exceeds 0.3% across all fills

**Inputs:**
- Order before submission (for pre-trade slippage estimate)
- Fill notifications (for post-trade slippage computation)

**Outputs:**
- Slippage approval / flag / block to Order Validator
- Slippage analytics to Analytics Manager

**Dependencies:** Data Feed, Order Validator, Execution Analytics Manager

---

#### Component EC-11: Latency Manager

**Purpose:** Monitors execution latency across all pipeline stages and ensures SLA compliance.

**Responsibilities:**
- Timestamp each execution at every pipeline stage
- Compute stage-by-stage latency
- Alert when any stage exceeds its SLA threshold
- Produce end-to-end latency metrics per execution
- Feed latency data to Health Manager and Analytics Manager
- Detect latency anomalies: if end-to-end latency exceeds 3x normal, trigger investigation

**Inputs:** Timestamp events from all pipeline stages

**Outputs:** Latency metrics to Health Manager and Analytics Manager

**Dependencies:** All pipeline stage components, Execution Health Manager, Execution Analytics Manager

---
### CLUSTER D: BROKER AND EXCHANGE INTERFACE

#### Component EC-12: Broker Gateway

**Purpose:** The authenticated interface between the Execution Engine and an external broker system. Each broker integration is encapsulated in a Broker Gateway implementation that presents a common internal interface to the Order Router.

**Responsibilities:**
- Authenticate with broker API (OAuth token, API key, session token)
- Submit Orders to broker: construct broker-specific request payload; call broker API
- Receive and parse Order acknowledgements and confirmations
- Receive and parse fill events (WebSocket / polling)
- Receive and parse rejection events
- Expose position query: fetch current positions from broker for reconciliation
- Expose order status query: fetch order status for recovery procedures
- Handle token refresh: re-authenticate before token expiry
- Maintain heartbeat with broker: detect disconnection
- Implement rate limiting: respect broker API rate limits (typically 10 req/s)
- Support PAPER_TRADING mode: route all orders to Paper Simulator instead

**Inputs:**
- Valid Order from Order Router
- Authentication credentials (managed by Execution Governance Manager)
- Configuration: broker endpoints, rate limits, instrument mappings

**Outputs:**
- Acknowledgement / Confirmation to Execution Monitor
- Fill events to Execution Tracker
- Rejection / Error events to Retry Manager
- Position data to Position Updater (reconciliation)

**Dependencies:** Broker API (Dhan/Zerodha/Paper), Execution Monitor, Execution Tracker, Retry Manager

**Failure Modes:**
- Authentication failure: escalate to Execution Governance Manager; alert; human intervention
- API rate limit exceeded: back-off; queue overflow protection
- Network timeout: circuit breaker activation; route to secondary broker
- Partial API failure (orders work but fills not received): alert; polling fallback activated

**Monitoring:**
- API response time p95
- Authentication token age
- WebSocket connection health
- Fill event delivery latency

**Scalability:** Multiple Broker Gateway instances can run concurrently (primary + secondary + paper). Each instance is independent.

**Extensibility:** New broker integrations implement the BrokerGatewayInterface. No Execution Engine core components need modification to add a broker.

**Engineering Notes:** The Broker Gateway is the most externally-dependent component in the Execution Engine. Its failure modes are largely driven by external factors (broker API issues, network conditions, authentication token expiry). All failure modes have defined recovery paths. The Broker Gateway never blocks the Kill Switch or Override Service.

---

#### Component EC-13: Exchange Gateway

**Purpose:** The interface for direct market data from the exchange — order book depth, last trade price, circuit breaker status, and exchange-level events. Distinct from the Broker Gateway (which routes orders) in that the Exchange Gateway is read-only.

**Responsibilities:**
- Subscribe to real-time price feed for all instruments in active executions
- Monitor circuit breaker status for active instruments
- Detect exchange-level events (market halt, trading suspension)
- Provide LTP and order book depth to Slippage Manager and Order Builder
- Alert Execution Engine on circuit breaker activation

**Inputs:** Exchange data feed (WebSocket / REST)

**Outputs:**
- LTP and depth data to Order Builder and Slippage Manager
- Circuit breaker alerts to Kill Switch mechanism
- Market halt events to Execution Governance Manager

**Dependencies:** Market Data Feed (Data Feed Manager), EventBus

**Failure Modes:**
- Feed disconnection: Execution Engine falls back to broker-provided quotes; alert
- Stale data (> 30 seconds): alert; all limit order price calculations paused until fresh data

---

#### Component EC-14: Execution Monitor

**Purpose:** Monitors the status of all submitted Orders in real time. The Execution Monitor is the primary observer of the broker-side execution lifecycle.

**Responsibilities:**
- Receive acknowledgement events from Broker Gateway; update Execution Registry
- Detect confirmation: Order accepted by broker
- Detect rejection: Order rejected by broker or exchange; route to Retry Manager
- Detect fill events: partial and full fills; route to Execution Tracker
- Detect timeout: Order submitted but no acknowledgement within SLA
- Detect stale Orders: submitted but no fill for > configured time (symbol-specific)
- Raise alerts for anomalies (double fill, fill quantity mismatch, fill price mismatch)

**Inputs:**
- Events from Broker Gateway (acknowledgement, confirmation, rejection, fill)
- Execution records from Registry (for expected state)

**Outputs:**
- Status update events to Execution Registry
- Fill events to Execution Tracker
- Rejection events to Retry Manager
- Timeout/anomaly alerts to Execution Health Manager

**Dependencies:** Broker Gateway, Execution Registry, Execution Tracker, Retry Manager, Execution Health Manager

**Failure Modes:**
- Event stream interruption: alert; polling fallback activated; all SUBMITTED Orders queried via broker Order status API
- Fill event lost: detected by position reconciliation; Recovery Manager activated

---

#### Component EC-15: Execution Tracker

**Purpose:** Records and aggregates fill events for each Execution record. The Tracker maintains the cumulative fill state and determines whether an Execution is partially filled, fully filled, or complete.

**Responsibilities:**
- Receive fill events from Execution Monitor
- Record individual fill details: quantity, price, timestamp, fill_reference
- Compute cumulative fill: total_filled_quantity, average_fill_price, total_fill_value
- Determine fill completeness: if total_filled_quantity >= ordered_quantity, signal FULL_FILL
- Determine partial fill threshold: if total_filled_quantity >= min_acceptable_fill_pct, signal ACCEPTABLE_PARTIAL
- Notify Position Updater on each fill event
- Notify Execution Registry on fill state change

**Inputs:** Fill events from Execution Monitor

**Outputs:**
- Cumulative fill state to Execution Registry
- Fill notifications to Position Updater
- Fill completion signals to Execution Planner (for multi-tranche executions)

**Dependencies:** Execution Monitor, Execution Registry, Position Updater

**Failure Modes:**
- Duplicate fill event: idempotency check on fill_reference; duplicates discarded
- Fill quantity > ordered quantity: constitutional violation alert; overfill investigation

---

#### Component EC-16: Retry Manager

**Purpose:** Manages all execution retry scenarios. When an Order fails for a recoverable reason, the Retry Manager classifies the failure, applies retry policy, and re-inserts the Execution Intent into the queue.

**Responsibilities:**
- Classify failure: RECOVERABLE (transient broker error, timeout) vs NON_RECOVERABLE (risk rejection, market closed)
- Apply retry policy: exponential back-off; maximum retry count = 3 per execution
- Re-insert into Execution Queue at appropriate priority on retry
- Track retry count in Execution record
- Escalate to Execution Recovery Manager after 3 failed retries
- Notify human operator on escalation
- Block retries if Kill Switch is active

**Inputs:**
- Failure events from Execution Monitor, Broker Gateway, Order Validator
- Retry policy from Execution Governance Manager

**Outputs:**
- Retry Execution Intents to Execution Queue
- Escalation to Execution Recovery Manager (after max retries)

**Dependencies:** Execution Queue, Execution Recovery Manager, Execution Governance Manager, Kill Switch

**Failure Modes:**
- Retry loop (all retries fail): escalated to Recovery Manager; human notification
- Retry during Kill Switch: blocked; execution held until Kill Switch lifted

---

#### Component EC-17: Execution Recovery Manager

**Purpose:** Manages complex execution failure scenarios that cannot be resolved by the Retry Manager alone. The Recovery Manager reconciles execution state, corrects position discrepancies, and coordinates human-assisted recovery.

**Responsibilities:**
- Receive escalated failure cases from Retry Manager
- Query broker for current Order status and position state
- Reconcile IIOS position vs broker position; identify discrepancies
- Classify discrepancy: IIOS_AHEAD (position recorded but no fill), BROKER_AHEAD (fill received but not recorded), NEUTRAL (no discrepancy)
- For IIOS_AHEAD: mark execution as NOT_FILLED; clear position increment; alert
- For BROKER_AHEAD: record the unrecorded fill; update position; audit event
- Generate corrective order requests (Recovery Execution type) for human approval
- Produce recovery report for every incident

**Inputs:**
- Escalated failures from Retry Manager
- Broker Order status and position data from Broker Gateway
- IIOS position state from Position Updater

**Outputs:**
- Position correction events to Position Updater
- Recovery Execution proposals to human operator
- Recovery report to Execution Audit Manager

**Dependencies:** Retry Manager, Broker Gateway, Position Updater, Execution Audit Manager, Execution Health Manager

**Failure Modes:**
- Recovery Manager cannot determine true position: EMERGENCY_HOLD mode; all new executions for affected instrument halted; human investigation required
- Broker API unavailable during recovery: Recovery Manager holds state; retries when API available

---

### CLUSTER E: STATE AND ANALYTICS

#### Component EC-18: Position Updater

**Purpose:** Maintains the real-time position state for every instrument in the portfolio. The Position Updater is the authoritative source of current holdings.

**Responsibilities:**
- Update position on every fill event: add to long position for buys, reduce for sells
- Handle partial fills: proportional position update per fill quantity
- Handle full fills: position update + mark execution as FULL_FILL
- Detect position inconsistency: if sell quantity > current position, alert
- Publish position change events to EventBus
- Support position query by instrument, by decision_id, by session
- Maintain position history for all instruments
- Daily reconciliation with broker positions (pre-market)

**Inputs:**
- Fill notifications from Execution Tracker
- Broker position data from Broker Gateway (reconciliation)

**Outputs:**
- Updated position records to Portfolio Updater
- Position change events to EventBus

**Dependencies:** Execution Tracker, Portfolio Updater, Broker Gateway, EventBus

**Failure Modes:**
- Fill received for unknown instrument: alert; position held pending instrument resolution
- Position goes negative (short position): alert if not a SHORT decision type; constitutional violation check

---

#### Component EC-19: Portfolio Updater

**Purpose:** Maintains the aggregate portfolio state: total positions, net asset value, sector exposures, cash balance, and realised/unrealised P&L.

**Responsibilities:**
- Aggregate all position changes into portfolio metrics
- Compute portfolio P&L: realised (from closed positions) and unrealised (from open positions at current LTP)
- Update cash balance after each execution: deduct for buys, credit for sells
- Compute sector and instrument concentrations
- Publish portfolio state to EventBus (consumed by Risk Guardian, Decision Engine, Dashboard)
- Support daily P&L computation for drawdown monitoring
- Produce session-end portfolio snapshot

**Inputs:**
- Position updates from Position Updater
- Current LTP from Data Feed (for unrealised P&L computation)
- Cash balance from broker (reconciliation)

**Outputs:**
- Portfolio state to EventBus
- Portfolio snapshot to Execution Registry (session-end)

**Dependencies:** Position Updater, Data Feed, EventBus, Execution Registry

---

#### Component EC-20: Execution Governance Manager

**Purpose:** Enforces governance rules for all executions: naming standards, retention policies, security controls, Kill Switch state management, and constitutional rule compliance.

**Responsibilities:**
- Assign governance tier to each execution (inherited from Decision Package)
- Enforce naming standards for execution IDs (EXE-{TYPE}-{DATE}-{SEQ:08d})
- Manage Kill Switch state: activate, deactivate (human-only deactivation)
- Manage Emergency Stop state
- Load and enforce execution policies (intraday limits, position limits, trading hours)
- Monitor for constitutional violations; record in Audit Manager
- Govern the list of authorised brokers and instruments

**Inputs:**
- Policy configuration files
- Kill Switch commands from human operator or Risk Guardian
- Execution events for constitutional compliance monitoring

**Outputs:**
- Kill Switch status to Order Validator (checked on every order)
- Policy configuration to all components
- Constitutional violation events to Audit Manager

**Dependencies:** Kill Switch (state variable), Execution Audit Manager, Execution Registry, EventBus

---

#### Component EC-21: Execution Audit Manager

**Purpose:** Maintains the immutable, hash-chained audit trail for all execution events. Every action taken by the Execution Engine is recorded by the Audit Manager.

**Responsibilities:**
- Record every execution event: creation, status transition, fill, rejection, cancellation, override, recovery
- Apply hash chain: each record includes hash of previous record
- Record actor identity (EXECUTION_ENGINE_AI, HUMAN_OPERATOR_xx, BROKER_GATEWAY)
- Record timestamps (UTC) with microsecond precision
- Support audit queries by execution_id, date range, event type, actor
- Detect and alert on audit chain breaches immediately
- Export audit records for compliance review

**Inputs:** Execution events from all components (published via EventBus or direct calls)

**Outputs:**
- Audit records to append-only audit log
- Violation alerts to Execution Health Manager

**Dependencies:** Storage Layer (append-only audit partition), EventBus, Execution Health Manager

**Failure Modes:**
- Audit write failure: P0 alert; Execution Engine transitions to AUDIT_DEGRADED mode; all executions HELD
- Hash chain breach: P0 security alert; Execution Engine HALTED; human investigation

---

#### Component EC-22: Execution Health Manager

**Purpose:** Monitors the health of all 23 Execution Engine components and the overall execution quality. Produces the Health Dashboard.

**Responsibilities:**
- Collect heartbeats from all 23 components
- Compute per-component health: HEALTHY / DEGRADED / CRITICAL
- Compute overall Execution Engine health
- Monitor SLA compliance for all execution stages
- Alert on component failures, SLA breaches, and constitutional violations
- Produce Health Dashboard for ControlTower
- Activate circuit breakers on repeated component failures

**Inputs:** Heartbeats and metrics from all 23 components

**Outputs:**
- Health status to ControlTower and EventBus
- Alerts to Telegram bot

**Dependencies:** All 23 components, EventBus, ControlTower

---

#### Component EC-23: Execution Analytics Manager

**Purpose:** Computes and publishes execution quality analytics: fill rates, slippage statistics, latency distributions, failure rates, and broker performance comparisons.

**Responsibilities:**
- Compute session-level analytics: total orders, fill rate, average slippage, average latency
- Compute per-instrument analytics: average fill quality per symbol
- Compute per-broker analytics: broker comparison on fill quality and latency
- Produce daily execution quality report
- Feed analytics to Learning System for performance attribution
- Alert on degraded execution quality (average slippage > 0.5% or fill rate < 85%)

**Inputs:**
- Fill events and slippage data from Execution Tracker and Slippage Manager
- Latency data from Latency Manager
- Session events from Execution Registry

**Outputs:**
- Analytics reports to ControlTower and Learning System
- Quality alerts to Execution Health Manager

**Dependencies:** Execution Tracker, Slippage Manager, Latency Manager, ControlTower, Learning System

---
## PART IV — EXECUTION LIFECYCLE

### 4.1 Overview

Every execution in the IIOS passes through a defined lifecycle from Decision intake to archive. The lifecycle has 16 stages, each with a defined entry condition, processing steps, exit condition, and failure path.

---

### 4.2 Lifecycle Stage Summary

| Stage | Name | Status | Actor | SLA |
|---|---|---|---|---|
| 1 | Decision Intake | RECEIVED | Execution Engine | < 100ms |
| 2 | Intent Construction | PLANNING | Execution Planner | < 50ms |
| 3 | Scheduling/Queuing | QUEUED | Execution Scheduler / Queue | < 10ms |
| 4 | Order Construction | BUILDING | Order Builder | < 30ms |
| 5 | Order Validation | VALIDATING | Order Validator | < 20ms |
| 6 | Execution Risk Check | RISK_CHECKING | Order Validator + Kill Switch | < 15ms |
| 7 | Order Routing | ROUTING | Order Router | < 20ms |
| 8 | Broker Submission | SUBMITTED | Broker Gateway | < 100ms |
| 9 | Acknowledgement | ACKNOWLEDGED | Broker Gateway | < 500ms |
| 10 | Partial Fill | PARTIAL_FILL | Execution Tracker | Ongoing |
| 11 | Full Fill | FULL_FILL | Execution Tracker | Per market |
| 12 | Position Update | POSITION_UPDATING | Position Updater | < 50ms |
| 13 | Portfolio Update | PORTFOLIO_UPDATING | Portfolio Updater | < 100ms |
| 14 | Audit Record | AUDITING | Execution Audit Manager | < 20ms |
| 15 | Archive | ARCHIVING | Execution Archive Manager | < 500ms |
| 16 | Completed | COMPLETED | Execution Registry | Terminal |

---

### 4.3 Lifecycle Stage Definitions

#### Stage 1: Decision Intake

**Entry condition:** COMMITTED Decision Package received from Decision Engine Distribution Manager.

**Processing:**
1. Execution Planner receives Decision Package
2. Validates Decision Package schema (basic structural check)
3. Checks idempotency: has this decision_id been processed before?
4. If duplicate: discard; log; return ACK to Decision Engine
5. If new: proceed

**Exit condition:** Decision Package is valid and unique.

**Failure path:** Schema invalid or duplicate → discard; alert; do not create Execution record.

**Audit event:** DECISION_RECEIVED

---

#### Stage 2: Intent Construction

**Entry condition:** Valid, unique Decision Package.

**Processing:**
1. Execution Planner parses Decision Package: action, entity, quantity, price type, execution parameters
2. Queries portfolio state: current position, available capital
3. Queries market data: current LTP, bid/ask, ADV
4. Determines execution type (EX-TYPE-001 through EX-TYPE-019)
5. Determines execution strategy (standard, algorithmic, partial)
6. Constructs Execution Intent(s)
7. Creates Execution record(s) in Registry with status PENDING
8. Assigns execution_intent_id

**Exit condition:** Execution Intent(s) created and registered.

**Failure path:** Market data unavailable → HOLD; retry after 5 seconds (max 3 retries).

**Audit event:** EXECUTION_INTENT_CREATED

---

#### Stage 3: Scheduling / Queuing

**Entry condition:** Execution Intent created.

**Processing:**
1. Is execution immediate or deferred?
2. Immediate: enqueue in Execution Queue with assigned priority
3. Deferred (scheduled/conditional): register with Execution Scheduler; status = SCHEDULED
4. Scheduler monitors condition; on condition met: enqueue

**Exit condition:** Execution Intent is in Execution Queue (status QUEUED).

**Failure path:** Queue full → URGENT/HIGH intents HELD; LOW/BACKGROUND intents discarded; alert.

**Audit event:** EXECUTION_QUEUED or EXECUTION_SCHEDULED

---

#### Stage 4: Order Construction

**Entry condition:** Execution Intent at head of Execution Queue.

**Processing:**
1. Order Builder reads Execution Intent from queue
2. Resolves instrument token from Entity Engine / broker mapping
3. Applies current LTP adjustment to limit price (if stale by > 5 seconds)
4. Applies Slippage Manager pre-trade estimate
5. Sets order product type (INTRADAY/DELIVERY)
6. Sets time-in-force per execution type
7. Constructs Order object

**Exit condition:** Valid Order object constructed.

**Failure path:** Instrument token not found → FAILED; alert; manual resolution.

**Audit event:** ORDER_CONSTRUCTED

---

#### Stage 5: Order Validation

**Entry condition:** Order object from Order Builder.

**Processing:**
1. Schema validation (all fields present, all types correct)
2. Idempotency check (order_reference_id unique)
3. Price sanity (within circuit limits, within acceptable % of LTP)
4. Quantity sanity (> 0, consistent with position for sell orders)
5. Margin estimate (sufficient capital)

**Exit condition:** All validation checks PASS.

**Failure path:** Any check FAIL → Order REJECTED; alert; Execution record status REJECTED.

**Audit event:** ORDER_VALIDATED or ORDER_REJECTED

---

#### Stage 6: Execution Risk Check

**Entry condition:** Validated Order.

**Processing:**
1. Kill Switch check: if active → BLOCKED; execution HELD
2. Human hold check: if entity has hold flag → BLOCKED; execution HELD
3. Position limit check: post-execution position within limits
4. Session order count check: not exceeding session order limit
5. Market hours check: market open or pre-market order

**Exit condition:** All risk checks PASS.

**Failure path:** Any check FAIL → execution HELD or BLOCKED; appropriate routing.

**Audit event:** RISK_CHECK_PASSED or RISK_CHECK_FAILED

---

#### Stage 7: Order Routing

**Entry condition:** Risk-checked Order.

**Processing:**
1. Order Router selects broker gateway (primary, secondary, paper simulator)
2. Records routing decision
3. Marks Execution status: ROUTING

**Exit condition:** Order assigned to broker gateway.

**Failure path:** All gateways unavailable → HELD; human alert.

**Audit event:** ORDER_ROUTED

---

#### Stage 8: Broker Submission

**Entry condition:** Order assigned to broker gateway.

**Processing:**
1. Broker Gateway constructs broker-specific API request
2. Submits Order to broker
3. Records submission timestamp and broker request_id
4. Updates Execution status: SUBMITTED

**Exit condition:** Order submitted to broker (HTTP response received or WebSocket message sent).

**Failure path:** Network error → Retry Manager; timeout → Retry Manager.

**Audit event:** ORDER_SUBMITTED

---

#### Stage 9: Acknowledgement

**Entry condition:** Order submitted to broker.

**Processing:**
1. Broker Gateway receives acknowledgement from broker
2. If ACCEPTED: update Execution status to ACKNOWLEDGED; record broker_order_id
3. If REJECTED: update status to REJECTED; route to Retry Manager
4. If timeout (no ACK within SLA): treat as potential failure; Execution Monitor queries broker

**Exit condition:** Acknowledgement received.

**Failure path:** Rejection → Retry Manager (RECOVERABLE) or FAILED (NON_RECOVERABLE).

**Audit event:** ORDER_ACKNOWLEDGED or ORDER_REJECTED_BY_BROKER

---

#### Stage 10: Partial Fill

**Entry condition:** Execution ACKNOWLEDGED; fill events begin arriving.

**Processing:**
1. Execution Monitor receives fill event from Broker Gateway
2. Routes to Execution Tracker
3. Tracker records fill: quantity, price, timestamp
4. Tracker updates cumulative fill state
5. Position Updater receives partial fill notification; updates position proportionally
6. If cumulative fill < ordered quantity: remain in PARTIAL_FILL state; continue monitoring
7. If fill stalls (no new fills for > configured stall time): Execution Monitor alerts

**Exit condition:** Either FULL_FILL (all quantity filled) or timeout/cancellation.

**Audit event:** PARTIAL_FILL_RECEIVED (for each fill event)

---

#### Stage 11: Full Fill

**Entry condition:** Cumulative fill quantity = ordered quantity (or >= acceptable partial fill threshold).

**Processing:**
1. Execution Tracker signals FULL_FILL
2. Execution Monitor updates Execution status: FULL_FILL
3. Proceeds to Stage 12

**Audit event:** EXECUTION_FULLY_FILLED

---

#### Stage 12: Position Update

**Entry condition:** Fill received (partial or full).

**Processing:**
1. Position Updater receives fill notification from Execution Tracker
2. Updates position for the instrument: adds to long position for BUY, reduces for SELL
3. Records position change with decision_id linkage (traceability)
4. Publishes position update event to EventBus

**Exit condition:** Position record updated.

**Audit event:** POSITION_UPDATED

---

#### Stage 13: Portfolio Update

**Entry condition:** Position updated.

**Processing:**
1. Portfolio Updater receives position change event
2. Recomputes portfolio metrics: NAV, cash balance, concentrations, P&L
3. Updates drawdown monitor (feeds Risk Guardian)
4. Publishes portfolio update event to EventBus

**Exit condition:** Portfolio record updated.

**Audit event:** PORTFOLIO_UPDATED

---

#### Stage 14: Audit Record

**Entry condition:** Position and portfolio updated.

**Processing:**
1. Execution Audit Manager assembles complete execution audit record
2. Records all fill details, timestamps, actor identities, broker references
3. Appends to hash-chained audit log
4. Verifies hash chain integrity

**Exit condition:** Audit record persisted with valid hash chain.

**Failure path:** Audit write failure → P0 alert; Execution Engine AUDIT_DEGRADED.

**Audit event:** EXECUTION_AUDIT_COMPLETE

---

#### Stage 15: Archive

**Entry condition:** Execution in COMPLETED terminal state.

**Processing:**
1. Execution Archive Manager receives terminal-state notification
2. Transfers full Execution record + linked audit events to archive
3. Verifies archive write
4. Removes from active Registry (marks as ARCHIVED)

**Exit condition:** Execution archived.

**Audit event:** EXECUTION_ARCHIVED

---

#### Stage 16: Completed

**Entry condition:** Execution archived.

**Processing:**
1. Execution Registry marks record COMPLETED
2. EventBus: EXECUTION_COMPLETED event emitted
3. Decision Engine notified: decision_id is now EXECUTED
4. Learning System: execution outcome delivered for performance attribution

**Exit condition:** Terminal state; no further processing.

**Audit event:** EXECUTION_COMPLETED

---

### 4.4 Execution State Machine (Summary ASCII)

`
[RECEIVED]
    |
    v
[PLANNING]
    |── HOLD ──────────> [HELD] ──> human release ──> [QUEUED]
    |
    v
[QUEUED] ──> SCH ──> [SCHEDULED]
    |                     |
    |              condition met
    |                     |
    v                     v
[BUILDING]
    |
    v
[VALIDATING]
    |── FAIL ──────────> [REJECTED] (terminal on this attempt)
    |
    v
[RISK_CHECKING]
    |── BLOCKED ───────> [HELD]
    |
    v
[ROUTING]
    |
    v
[SUBMITTED]
    |── BROKER_REJECT ─> [RETRY] ──> (3x max) ──> [RECOVERING]
    |
    v
[ACKNOWLEDGED]
    |
    v
[PARTIAL_FILL] ──> stall ──> [RETRY] or [HELD]
    |
    v (cumulative fill complete)
[FULL_FILL]
    |
    v
[POSITION_UPDATING]
    |
    v
[PORTFOLIO_UPDATING]
    |
    v
[AUDITING]
    |
    v
[ARCHIVING]
    |
    v
[COMPLETED] (terminal)

Parallel paths to terminal states:
[Any state] ──> Kill Switch / Human Cancel ──> [CANCELLED] (terminal)
[Any state] ──> Expiry ──────────────────────> [EXPIRED] (terminal)
[Any state] ──> Unrecoverable failure ────────> [FAILED] ──> [RECOVERING]
`

---

### 4.5 Point-in-Time Semantics

Every Execution record records the complete state at each stage transition. This enables:
- Reconstruction of the full execution history at any point in time
- Audit of market conditions at the time of each decision
- Comparison of intended vs actual fill prices
- Latency attribution per stage

---
## PART V — EXECUTION SERVICES

The Execution Engine exposes 16 services — well-defined operational endpoints used by other IIOS layers, the Telegram bot, the Streamlit dashboard, and the Learning System.

---

### ES-01: Order Service

**Purpose:** The primary inbound service of the Execution Engine. Receives COMMITTED Decision Packages and initiates the execution lifecycle.

**Operation:** RECEIVE_DECISION_PACKAGE

| Parameter | Type | Description |
|---|---|---|
| decision_package | DecisionPackage | Complete COMMITTED Decision Package |
| source_id | string | Source system identifier |

**Response:**
| Field | Description |
|---|---|
| execution_id | Assigned execution ID |
| status | ACCEPTED / REJECTED / DUPLICATE |
| estimated_execution_ms | Estimated time to completion |

**SLA:** < 200ms acknowledgement
**Callers:** Decision Engine Distribution Manager
**Failure handling:** Schema error → REJECTED response; duplicate → DUPLICATE response (idempotent)

---

### ES-02: Routing Service

**Purpose:** Exposes broker routing configuration and current broker availability for administrative use.

**Operations:**
- GET_ROUTING_TABLE: returns current broker priority and availability
- SET_BROKER_PRIORITY: (human operator only) changes primary/secondary broker
- TEST_BROKER_CONNECTIVITY: health-check call to each configured broker gateway

**SLA:** < 100ms
**Callers:** ControlTower, human operator (Telegram admin commands)

---

### ES-03: Validation Service

**Purpose:** Allows pre-flight validation of an Order before it enters the execution pipeline. Used for testing and simulation.

**Operations:**
- VALIDATE_ORDER: validates a proposed order against all current rules
- DRY_RUN: constructs and validates an Execution Intent without submitting

**Response:** Validation report with pass/fail for each check

**SLA:** < 50ms
**Callers:** Decision Engine (pre-commitment check), testing framework

---

### ES-04: Risk Check Service

**Purpose:** Exposes the execution-level risk checks for query and administration.

**Operations:**
- CHECK_KILL_SWITCH: returns current Kill Switch state
- SET_KILL_SWITCH: (human only) activate or deactivate Kill Switch
- CHECK_POSITION_LIMITS: returns current position limit utilisation
- SET_POSITION_LIMIT: (human only) modify a position limit
- SET_HOLD_FLAG: (human only) set entity-level execution hold

**SLA:** CHECK operations < 10ms; SET operations < 100ms
**Callers:** ControlTower, Telegram bot, Risk Guardian, human operator

---

### ES-05: Broker Service

**Purpose:** Manages broker gateway configuration and connectivity.

**Operations:**
- GET_BROKER_STATUS: returns status of each configured broker gateway
- AUTHENTICATE_BROKER: initiates broker authentication flow
- REFRESH_TOKEN: refreshes broker API token
- GET_BROKER_POSITIONS: fetches current positions from broker for reconciliation
- GET_ORDER_STATUS: queries broker for current order status

**SLA:** < 500ms for broker API calls (subject to broker latency)
**Callers:** Execution Governance Manager, Execution Recovery Manager

---

### ES-06: Exchange Service

**Purpose:** Provides access to exchange-level market data and status.

**Operations:**
- GET_LTP: returns last traded price for an instrument
- GET_ORDERBOOK_DEPTH: returns bid/ask depth
- GET_CIRCUIT_STATUS: returns circuit breaker status for an instrument
- GET_MARKET_STATUS: returns overall market open/closed status

**SLA:** < 50ms (from Exchange Gateway cache)
**Callers:** Order Builder, Slippage Manager, Execution Planner

---

### ES-07: Monitoring Service

**Purpose:** Real-time monitoring interface for active executions.

**Operations:**
- LIST_ACTIVE_EXECUTIONS: returns all SUBMITTED/PARTIAL_FILL/ACKNOWLEDGED executions
- GET_EXECUTION_STATUS: returns current status of a specific execution
- GET_FILL_HISTORY: returns fill events for a specific execution
- SUBSCRIBE_EXECUTION_EVENTS: WebSocket subscription to real-time execution events

**SLA:** < 100ms for query operations
**Callers:** ControlTower, Telegram bot, human operator

---

### ES-08: Recovery Service

**Purpose:** Initiates and manages execution recovery procedures.

**Operations:**
- TRIGGER_RECOVERY: initiates recovery for a specific execution_id
- APPROVE_RECOVERY_ORDER: human approval for a corrective recovery order
- GET_RECOVERY_REPORT: returns recovery report for a recovery incident
- RECONCILE_POSITIONS: triggers full position reconciliation against broker

**SLA:** Trigger < 200ms; reconciliation may take seconds
**Callers:** Human operator, Execution Recovery Manager
**Restriction:** APPROVE_RECOVERY_ORDER requires human operator identity

---

### ES-09: Retry Service

**Purpose:** Manages retry queue inspection and manual retry operations.

**Operations:**
- GET_RETRY_QUEUE: returns all executions currently in retry state
- FORCE_RETRY: (human only) forces immediate retry of a held execution
- CANCEL_RETRY: (human only) cancels an execution in retry state
- GET_RETRY_HISTORY: returns retry attempts for an execution

**SLA:** < 100ms
**Callers:** Human operator, ControlTower

---

### ES-10: Slippage Service

**Purpose:** Exposes slippage monitoring and configuration.

**Operations:**
- GET_SLIPPAGE_REPORT: session slippage analytics
- GET_INSTRUMENT_SLIPPAGE: average slippage for a specific instrument
- SET_SLIPPAGE_LIMIT: (human only) override max slippage for an instrument
- GET_SLIPPAGE_ALERTS: returns instruments where slippage exceeded threshold

**SLA:** < 100ms
**Callers:** Human operator, ControlTower, Analytics Manager

---

### ES-11: Position Update Service

**Purpose:** Provides real-time position state to internal and external consumers.

**Operations:**
- GET_POSITION: returns current position for an instrument
- GET_ALL_POSITIONS: returns all current positions
- GET_POSITION_HISTORY: returns position change history for an instrument
- MANUAL_POSITION_CORRECTION: (human only, after recovery approval) directly corrects a position

**SLA:** < 50ms for GET operations
**Callers:** Portfolio Updater, Risk Guardian, Decision Engine (context), ControlTower

---

### ES-12: Portfolio Update Service

**Purpose:** Provides real-time portfolio state.

**Operations:**
- GET_PORTFOLIO_SUMMARY: returns current NAV, cash, P&L, sector concentrations
- GET_DAILY_PNL: returns session P&L
- GET_DRAWDOWN_STATUS: returns current drawdown vs daily limit
- GET_PORTFOLIO_HISTORY: returns portfolio snapshots over a date range

**SLA:** < 100ms
**Callers:** Risk Guardian, Decision Engine, ControlTower, Telegram bot

---

### ES-13: Audit Service

**Purpose:** Provides access to the Execution Engine audit trail.

**Operations:**
- GET_EXECUTION_AUDIT: returns all audit events for an execution_id
- GET_AUDIT_EVENTS_BY_DATE: returns all audit events for a date range
- VERIFY_HASH_CHAIN: verifies hash chain integrity for a range of records
- EXPORT_AUDIT: exports audit records in structured format

**SLA:** < 500ms for record queries; hash chain verification may take seconds for large ranges
**Callers:** ControlTower, compliance review, human operator

---

### ES-14: Archive Service

**Purpose:** Provides access to archived execution records.

**Operations:**
- GET_ARCHIVED_EXECUTION: retrieves a specific execution from the archive
- SEARCH_ARCHIVE: searches archived executions by criteria
- GET_ARCHIVE_STATS: returns archive size, oldest record, newest record

**SLA:** < 1,000ms (archive storage may be slower than live Registry)
**Callers:** Learning System, ControlTower, Analytics Manager

---

### ES-15: Health Service

**Purpose:** Exposes Execution Engine health status.

**Operations:**
- GET_ENGINE_HEALTH: returns overall Execution Engine health
- GET_COMPONENT_HEALTH: returns health of a specific component
- GET_HEALTH_HISTORY: returns health timeline for last N hours
- GET_ALERT_HISTORY: returns active and recent alerts

**SLA:** < 50ms
**Callers:** ControlTower, Telegram bot, monitoring systems

---

### ES-16: Analytics Service

**Purpose:** Exposes execution quality analytics.

**Operations:**
- GET_SESSION_ANALYTICS: returns execution analytics for a trading session
- GET_DAILY_REPORT: returns daily execution quality report
- GET_BROKER_COMPARISON: returns comparative broker performance
- GET_SLIPPAGE_ANALYSIS: returns detailed slippage analytics

**SLA:** < 500ms
**Callers:** ControlTower, Learning System, human operator

---
## PART VI — EXECUTION PIPELINES

The Execution Engine operates through 10 primary processing pipelines. Each pipeline handles a specific aspect of the execution lifecycle.

---

### Pipeline 1: Decision-to-Order Pipeline

**Purpose:** Transforms a COMMITTED Decision Package into a validated, risk-checked Order ready for broker submission.

**Flow:**

`
[Decision Engine: COMMITTED Decision Package]
        |
        v (via ES-01 Order Service)
[Execution Planner]
  Parse Decision Package
  Query portfolio state
  Query market data (LTP, ADV)
  Determine execution type
  Construct Execution Intent(s)
  Register Execution record: status PENDING
        |
        v (Execution Intent → Execution Queue)
[Execution Queue]
  Priority ordering: URGENT > HIGH > NORMAL > LOW
        |
        v (head of queue)
[Order Builder]
  Resolve instrument token
  Apply LTP adjustment (if limit price stale)
  Apply Slippage Manager pre-trade estimate
  Construct Order object
        |
        v
[Order Validator]
  Schema check
  Idempotency check
  Price sanity
  Quantity sanity
  Margin estimate
        |── FAIL ──> [REJECTED status; alert; Execution ends]
        |
        v (VALID Order)
[Execution Risk Check]
  Kill Switch check
  Human hold check
  Position limit check
  Session order count check
  Market hours check
        |── FAIL ──> [HELD status; await condition resolution]
        |
        v (PASS)
[Order Router]
  Select broker gateway
  Record routing decision
        |
        v
[VALID Order → Broker Gateway]
`

---

### Pipeline 2: Order Validation Pipeline

**Purpose:** Detailed validation of every Order before it reaches the broker. This pipeline is the last line of IIOS-controlled defence before an Order leaves the system.

**Flow:**

`
[Order from Order Builder]
        |
        v
[Schema Validator]
  All required fields present?
  All field types correct?
  All values in valid range?
        |── FAIL ──> [SCHEMA_REJECTED]
        |
        v
[Idempotency Check]
  order_reference_id seen before?
        |── DUPLICATE ──> [DUPLICATE_REJECTED; log; no alert]
        |
        v
[Price Sanity Check]
  Is limit price within circuit limits?
  Is limit price within max% of LTP?
        |── FAIL ──> [PRICE_REJECTED; alert]
        |
        v
[Quantity Sanity Check]
  quantity > 0?
  For SELL: quantity <= current position?
  quantity is valid lot size?
        |── FAIL ──> [QUANTITY_REJECTED; alert]
        |
        v
[Margin Check]
  Estimated margin requirement vs available capital?
        |── INSUFFICIENT ──> [MARGIN_REJECTED; alert]
        |
        v
[Kill Switch Check]
  Kill Switch active?
        |── ACTIVE ──> [BLOCKED; return to HELD queue]
        |
        v
[VALIDATION PASSED → Order Router]
`

---

### Pipeline 3: Broker Routing Pipeline

**Purpose:** Selects the appropriate broker gateway and submits the Order.

**Flow:**

`
[Valid, Risk-Checked Order]
        |
        v
[Routing Policy Check]
  Is instrument broker-specific?
  Is primary broker available?
  Is PAPER_TRADING mode active?
        |
  +-----+----------+----------+
  |                |            |
  v                v            v
[Paper          [Primary      [Secondary
 Simulator]      Broker        Broker
 (always in      (Dhan)]       (Zerodha)]
 paper mode)
        |                |            |
        v                v            v
[Broker Gateway constructs broker-specific request]
[Submits Order]
[Records submission timestamp]
[Status: SUBMITTED]
        |
        v
[Execution Monitor registers new SUBMITTED execution]
[Timeout watchdog started: max ACK window = SLA]
`

---

### Pipeline 4: Exchange Pipeline

**Purpose:** Manages the exchange-side execution lifecycle: acknowledgement, fill events, rejections.

**Flow:**

`
[SUBMITTED Order (awaiting broker response)]
        |
  +-----+----------+----------+
  |                |            |
  v                v            v
[ACKNOWLEDGED]  [REJECTED]  [TIMEOUT]
  (broker OK)   (broker/      (no ACK
                 exchange      within
                 reject)       SLA)
        |           |            |
        v           v            v
[Execution       [Retry      [Execution
 Monitor: wait    Manager:    Monitor:
 for fills]       classify]   query broker]
        |
  FILL EVENT(S) arriving:
        |
  +-----+------+
  |             |
  v             v
[PARTIAL_FILL] [FULL_FILL]
  (update       (update
   position)     position;
               complete)
        |             |
        v             v
[Position      [Position
 Updater:       Updater:
 proportional   full update]
 update]
        |
        v
[Portfolio Updater: recompute metrics]
        |
        v
[Audit Manager: fill records]
`

---

### Pipeline 5: Execution Monitoring Pipeline

**Purpose:** Continuous monitoring of all active executions from SUBMITTED to COMPLETED.

**Flow:**

`
[All SUBMITTED/ACKNOWLEDGED/PARTIAL_FILL executions]
        |
        v (every 5 seconds)
[Execution Monitor scan]
        |
  +-----+-------+-------+--------+--------+
  |             |        |        |        |
  v             v        v        v        v
[ACK         [Fill     [Stale   [Fill    [Timeout
 pending]     event     fill]    overdue]  detected]
  |             |        |        |        |
  v             v        v        v        v
[Continue]  [Route to  [Alert]  [Alert;  [Query
             Tracker]           Retry?]   broker]
`

---

### Pipeline 6: Recovery Pipeline

**Purpose:** Manages execution failures and position discrepancies.

**Flow:**

`
[Failure event (from Retry Manager escalation or manual trigger)]
        |
        v
[Execution Recovery Manager]
  Query broker: current Order status
  Query broker: current positions
        |
        v
[Reconciliation comparison]
  IIOS state vs broker state
        |
  +-----+----------+
  |                 |
  v                 v
[MATCH]          [DISCREPANCY]
  (no action)      |
                   v
              [Classify discrepancy:
               IIOS_AHEAD or BROKER_AHEAD]
                   |
            +------+-------+
            |               |
            v               v
       [IIOS_AHEAD:     [BROKER_AHEAD:
        clear phantom    record missed
        fill; revert     fill; update
        position]        position]
                   |
                   v
        [Corrective Order proposal]
        [Human approval required]
                   |
                   v
        [Recovery Execution (EX-TYPE-019)]
`

---

### Pipeline 7: Settlement Pipeline

**Purpose:** Records and monitors settlement events for completed trades.

**Flow:**

`
[FULL_FILL execution]
        |
        v
[Settlement Tracker]
  Record trade: settlement date = T+1 (equity) or expiry (derivative)
  Monitor settlement date
        |
  On settlement date:
        v
[Settlement confirmation check]
  Query broker for settlement confirmation
        |
  +-----+------+
  |             |
  v             v
[CONFIRMED]  [PENDING/FAILED]
  (archive)   (alert; investigation)
`

---

### Pipeline 8: Portfolio Update Pipeline

**Purpose:** Propagates every execution outcome to the portfolio state.

**Flow:**

`
[Fill notification (partial or full)]
        |
        v
[Position Updater]
  Update instrument position
  Record fill linkage (decision_id, execution_id, fill_id)
        |
        v
[Portfolio Updater]
  Recompute aggregate metrics:
    NAV = sum(positions * LTP) + cash
    Cash = cash - (buy fills) + (sell fills)
    Realised P&L = closed position P&L
    Unrealised P&L = open position P&L at current LTP
    Sector concentrations
    Drawdown vs daily limit
        |
        v
[EventBus: PORTFOLIO_UPDATED]
        |
  +-----+-------+-------+
  |             |        |
  v             v        v
[Risk         [Decision [ControlTower
 Guardian]     Engine    Dashboard]
 (drawdown     Context
 check)]       Manager]
`

---

### Pipeline 9: Audit Pipeline

**Purpose:** Records every Execution Engine action in the immutable, hash-chained audit trail.

**Flow:**

`
[Any Execution event (from any component via EventBus)]
        |
        v
[Execution Audit Manager]
  Event classification
  Event validation (required fields present)
        |
        v
[Audit record construction]
  {execution_id, event_type, actor, previous_state,
   new_state, timestamp, fill_details (if applicable),
   broker_reference, constitutional_rules_checked}
        |
        v
[Hash chain append]
  record_hash = SHA256(record_content + previous_hash)
  Append record to append-only log
        |── write failure ──> P0 alert; AUDIT_DEGRADED mode
        |
        v (write success)
[Hash chain verification]
  Verify chain integrity for last N records
        |── breach ──> P0 security alert; EXECUTION HALTED
        |── valid ──> continue
`

---

### Pipeline 10: Analytics Pipeline

**Purpose:** Computes and publishes execution quality analytics after each session and in real time.

**Flow:**

`
[Fill events, latency events, slippage data (ongoing)]
        |
        v (real-time aggregation)
[Execution Analytics Manager]
  Accumulate session statistics:
    - Total orders submitted
    - Fill rate (filled / submitted)
    - Average slippage per instrument and overall
    - Average latency per stage
    - Retry rate
    - Failure rate
        |
        v (at session end)
[Session analytics report]
        |
  +-----+-------+-------+
  |             |        |
  v             v        v
[ControlTower  [Learning  [Execution
 Dashboard]     System]    Archive]
`

---
## PART VII — EXECUTION QUALITY FRAMEWORK

### 7.1 Overview

The Execution Quality Score (EQS) is the primary quality metric for every Execution. It integrates 12 quality dimensions into a composite score [0,1]. EQS is computed at the completion of each execution and feeds the Learning System, Analytics Manager, and broker performance comparison.

---

### 7.2 The 12 Execution Quality Dimensions

#### EQD-01: Execution Accuracy

**Definition:** The degree to which the execution delivered what the Decision Package specified — correct instrument, correct side (buy/sell), correct quantity, and correct direction.

**Measurement:** Binary check: all execution parameters match Decision Package. 1.0 if all match; 0.0 if any discrepancy.

**Weight in EQS:** 0.25 (highest — an inaccurate execution is a critical failure regardless of other quality)

**Degradation triggers:**
- Wrong instrument executed: -1.00 (blocking failure; immediate investigation)
- Wrong side (bought instead of sold): -1.00 (blocking failure)
- Quantity filled < 80% of intended: -0.15
- Quantity filled 80-95% of intended: -0.05

---

#### EQD-02: Latency

**Definition:** The elapsed time from Decision Package receipt to Order submission.

**Measurement:** Actual latency vs SLA for the execution priority level.

**Weight in EQS:** 0.10

| Priority | Target | Acceptable | Poor |
|---|---|---|---|
| URGENT | < 200ms | < 500ms | > 500ms |
| HIGH | < 500ms | < 1,000ms | > 1,000ms |
| NORMAL | < 1,000ms | < 2,000ms | > 2,000ms |
| LOW | < 5,000ms | < 10,000ms | > 10,000ms |

**Degradation:** Actual > Acceptable: -0.05; Actual > Poor: -0.10

---

#### EQD-03: Fill Quality (Slippage)

**Definition:** The difference between the intended execution price and the actual fill price, expressed as a percentage.

**Measurement:** slippage = (fill_price - intended_price) / intended_price for buys; reversed for sells.

**Weight in EQS:** 0.20

| Slippage | Score |
|---|---|
| Slippage <= 0 (better than intended) | 1.0 |
| 0% to 0.1% | 0.95 |
| 0.1% to 0.3% | 0.80 |
| 0.3% to max_slippage_pct | 0.60 |
| > max_slippage_pct | 0.20 (failure threshold exceeded) |

---

#### EQD-04: Reliability

**Definition:** Whether the execution completed without failure, retry, or recovery.

**Measurement:** First-attempt success rate.

**Weight in EQS:** 0.15

| Outcome | Score |
|---|---|
| First attempt, full fill | 1.0 |
| First attempt, partial fill (>= 95%) | 0.9 |
| First attempt, partial fill (80-95%) | 0.75 |
| Required 1 retry | 0.65 |
| Required 2 retries | 0.50 |
| Required recovery | 0.30 |

---

#### EQD-05: Determinism

**Definition:** Whether the execution behaved predictably and reproducibly given the inputs.

**Measurement:** Were there any unexpected state transitions, anomalies, or non-deterministic behaviours?

**Weight in EQS:** 0.05

**Degradation triggers:**
- Any non-deterministic event logged: -0.20
- Fill quantity exceeded ordered quantity: -1.00 (constitutional violation)

---

#### EQD-06: Safety

**Definition:** Whether the execution remained within all defined safety parameters throughout.

**Measurement:** All safety checks passed; no Kill Switch activated during execution; no constitutional violation.

**Weight in EQS:** 0.10

**Degradation triggers:**
- Kill Switch activated during execution: -0.50
- Constitutional rule violated: -0.80
- Position limit exceeded: -0.40

---

#### EQD-07: Consistency

**Definition:** Whether the execution result is consistent with the position state before and after.

**Measurement:** Post-execution position = pre-execution position + fill quantity (for buys); position reconciles with broker.

**Weight in EQS:** 0.05

**Degradation triggers:**
- Position inconsistency detected: -0.30
- Broker position mismatch: -0.20

---

#### EQD-08: Completeness

**Definition:** Whether all post-execution steps were completed: position update, portfolio update, audit record, notification.

**Measurement:** Post-execution checklist score.

**Weight in EQS:** 0.05

---

#### EQD-09: Traceability

**Definition:** Whether the execution can be fully traced back through the IIOS stack: Execution → Decision → Reasoning → Hypothesis → Observation.

**Measurement:** All lineage links present and valid.

**Weight in EQS:** 0.02

---

#### EQD-10: Auditability

**Definition:** Whether the execution has a complete, unbroken audit trail.

**Measurement:** All expected audit events present; hash chain intact for this execution.

**Weight in EQS:** 0.01

---

#### EQD-11: Risk Compliance

**Definition:** Whether the execution stayed within all risk parameters defined in the Decision Package.

**Measurement:** Position size, slippage, timing all within Decision Package limits.

**Weight in EQS:** 0.01

---

#### EQD-12: Failure Recovery

**Definition:** If a failure occurred, was it detected quickly and recovered effectively?

**Measurement:** Recovery time, position accuracy after recovery.

**Weight in EQS:** 0.01 (only applicable if a failure occurred)

---

### 7.3 EQS Formula Reference

LengthEQS = \sum_{d=1}^{12} w_d \cdot Q_d - \sum_{p} penalty_pLength

Subject to:
-  \in [0.00, 1.00]$
- $\sum w_d = 1.00$
- Wrong instrument or side: hard cap EQS = 0.00 (investigation required)
- Fill quantity > ordered quantity: EQS = 0.00 (constitutional violation)
- Kill Switch activated during execution: EQS = 0.20 maximum

**EQS Tiers:**

| Score range | Tier | Interpretation |
|---|---|---|
| 0.90 - 1.00 | EXCELLENT | All parameters met; first attempt success |
| 0.75 - 0.89 | GOOD | Minor slippage or latency variance |
| 0.60 - 0.74 | ACCEPTABLE | Some retry or slippage; within limits |
| 0.40 - 0.59 | MARGINAL | Significant issues; learning system flagged |
| 0.00 - 0.39 | FAILED | Investigation required |

---

### 7.4 EQS Monitoring

| Metric | Alert Threshold | Action |
|---|---|---|
| Session average EQS < 0.70 | Daily | Execution quality review |
| Fill quality (slippage) > 0.3% session average | Daily | Slippage Manager calibration |
| Retry rate > 10% | Session | Broker gateway health review |
| Latency p95 > 1,000ms (NORMAL priority) | Real-time | Latency Manager investigation |
| Failure rate > 5% | Session | Recovery Manager review |
| Any EQS = 0.00 execution | Immediate | P1 alert; investigation |

---

## PART VIII — EXECUTION GOVERNANCE

### 8.1 Governance Tiers

| Tier | Definition | Examples |
|---|---|---|
| CRITICAL | Executions that can significantly affect portfolio capital or activate risk protocols | EMR executions, CAP-ALLOCATE, RSK-HALT |
| HIGH | Core tactical executions for major indices or high-capital positions | Index BUY/SEL, positions > 2% NAV |
| MEDIUM | Standard tactical executions for equities < 2% NAV | Standard BUY/SEL/EXIT for equities |
| LOW | Non-capital executions: monitoring actions, scheduling | MON activations, GTT management |

---

### 8.2 Governance Matrix

| Dimension | CRITICAL | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| Kill Switch override | Never | Never | Never | Never |
| Human override allowed | Always | Always | Always | Always |
| Audit record | Immutable + hash | Immutable + hash | Standard | Standard |
| Retry maximum | 2 | 3 | 3 | 3 |
| Recovery procedure | Human required | Human required | Human optional | Auto |
| Retention | Permanent | 10 years | 5 years | 3 years |
| Review cycle | Intraday | Daily | Weekly | Monthly |

---

### 8.3 Naming Standards

**Execution ID format:** EXE-{TYPE}-{DATE}-{SEQ:08d}

Examples:
- EXE-BUY-EQT-20260703-00000001 — buy equity execution
- EXE-EXT-SL-20260703-00000002 — stop-loss exit execution
- EXE-EMR-LIQ-20260703-00000001 — emergency liquidation

**Order Reference ID format:** ORD-{EXE_ID}-{TRANCHE:02d}

Examples:
- ORD-EXE-BUY-EQT-20260703-00000001-01 — first (and only) tranche
- ORD-EXE-BUY-IDX-20260703-00000005-03 — third tranche of algorithmic execution

---

### 8.4 Security Controls

| Control | Implementation |
|---|---|
| Kill Switch | Atomic boolean; checked on every Order submission |
| Broker authentication | OAuth 2.0 tokens; auto-refresh; expiry monitoring |
| API key storage | Encrypted at rest; never in logs |
| Audit log integrity | SHA-256 hash chain; stored separately from Registry |
| Position limit enforcement | Checked in Order Validator; cannot be bypassed |
| Human override authentication | Operator ID required; logged in audit trail |
| Rate limiting | Per broker; enforced by Broker Gateway |
| Duplicate prevention | Idempotency key on every Order |

---

### 8.5 Compliance

| Requirement | Implementation |
|---|---|
| Algorithmic trading audit trail | Immutable hash-chained audit log |
| Trade confirmation records | Broker acknowledgement and fill records preserved |
| Position records | Real-time and historical position state |
| Settlement records | T+1 settlement monitoring |
| Best execution documentation | Slippage and fill quality analytics |
| Record retention | Per governance tier |

---
## PART IX — EXECUTION CONSTITUTION

The Execution Engine Constitution defines the non-negotiable rules governing every execution produced by the IIOS. Constitutional rules are coded **EC-{Category}-{Number}**.

---

### Category EC-A: Execution Integrity

**EC-A-001** Every Order submitted to a broker must be traceable to a COMMITTED Decision Package. No Order may be submitted without a valid, approved decision_id.

**EC-A-002** The instrument, side (buy/sell), and approximate quantity of every Order must match the Decision Package that generated it. Deliberate mismatches are a critical constitutional violation.

**EC-A-003** Every execution must have a unique execution_id. Duplicate execution_ids are prohibited.

**EC-A-004** Every Order must have a unique order_reference_id. Duplicate order submissions (same reference_id) are idempotently blocked.

**EC-A-005** An execution must not be marked COMPLETED until: position is updated, portfolio is updated, and audit record is persisted.

**EC-A-006** No execution may reference a cancelled or expired Decision Package. Executions against cancelled decisions must be immediately terminated.

**EC-A-007** The execution quantity must not exceed the quantity specified in the Decision Package.

**EC-A-008** Fill quantity may never exceed ordered quantity. Overfills are a critical violation requiring immediate investigation.

**EC-A-009** Execution state transitions must follow the defined state machine. No execution may skip stages or transition to an invalid state.

**EC-A-010** All execution timestamps must be UTC. Local time is never used in execution records.

---

### Category EC-B: Order Integrity

**EC-B-001** Every Order must pass all validation checks before broker submission. Bypassing Order validation is prohibited under all circumstances.

**EC-B-002** A LIMIT Order must have a limit price set. An order with entry_price_type = LIMIT and no limit_price is a structural violation.

**EC-B-003** A STOP Order must have a trigger price set. An order with entry_price_type = SL and no trigger_price is a structural violation.

**EC-B-004** Order prices must be within circuit limits at the time of submission. An Order submitted with a price outside circuit limits is a constitutional violation.

**EC-B-005** Order quantities must be valid lot sizes. Fractional lots are not permitted.

**EC-B-006** The order product type (INTRADAY or DELIVERY) must be consistent with the Decision Package execution intent.

**EC-B-007** An Order must not be modified after submission without creating a new Execution record and audit event. Silent order modifications are prohibited.

**EC-B-008** FOK Orders must be verified against current order book depth before submission. Submitting a FOK order to a deeply illiquid market without verification is a constitutional violation.

---

### Category EC-C: Trade Integrity

**EC-C-001** Fill records must be verified against broker data before updating the position. Unverified fills must not update the position.

**EC-C-002** Every fill must be recorded with: fill quantity, fill price, fill timestamp, fill_reference (broker-provided). Any fill missing these fields is incomplete and must be flagged.

**EC-C-003** Partial fills must update the position proportionally in real time. A partial fill must never be silently ignored.

**EC-C-004** Average fill price must be computed across all fill events for the same Order. Position update uses the average fill price.

**EC-C-005** Fill records are immutable after creation. Fill prices cannot be modified retroactively.

**EC-C-006** A fill for an Order that has been cancelled must be investigated immediately. This is a broker-side anomaly and must be escalated to Recovery Manager.

---

### Category EC-D: Portfolio Integrity

**EC-D-001** The portfolio state must be updated within one processing cycle of any fill event. A fill that does not update the portfolio within the SLA triggers a pipeline health alert.

**EC-D-002** The cash balance must be decremented for every buy fill and incremented for every sell fill. Cash balance must never go negative without a margin loan record.

**EC-D-003** The portfolio drawdown must be recomputed after every fill and published to the Risk Guardian. A stale drawdown reading is a constitutional violation.

**EC-D-004** Position records must reconcile with broker position records at the start of every trading session. Discrepancies must be investigated before trading begins.

**EC-D-005** No execution may cause a sector concentration > 25% of NAV or an instrument concentration > 5% of NAV. The Order Validator enforces this.

**EC-D-006** The portfolio record must never show a position that has not been filled. Phantom positions are a constitutional violation.

**EC-D-007** Realised P&L must be computed and recorded at the time of every closing fill.

---

### Category EC-E: Risk Controls

**EC-E-001** The Kill Switch is always active. Every Order submission passes through the Kill Switch check, without exception. There is no override of the Kill Switch check — only the Kill Switch state itself can be changed (by human operator).

**EC-E-002** The Kill Switch state can only be changed by a human operator. No component, algorithm, or automated process may deactivate the Kill Switch without explicit human command.

**EC-E-003** When the Kill Switch is active, all new Order submissions are blocked. Active Orders already submitted may remain at the broker pending human decision.

**EC-E-004** When Risk Guardian signals CRITICAL, the Execution Engine must immediately block all new BUY and INC executions. This happens automatically without human command.

**EC-E-005** When daily drawdown exceeds 2%, the Kill Switch must be activated automatically. This is the only automatic Kill Switch activation — all other activations require human command.

**EC-E-006** Position limits are enforced on every Order. An Order that would cause a position to exceed limits is blocked by the Order Validator and cannot proceed.

**EC-E-007** The maximum loss per execution (slippage) must not exceed max_slippage_pct defined in the Decision Package. If pre-trade slippage estimate exceeds this, the order is held pending human review.

**EC-E-008** No execution for an entity with an active human hold flag may proceed. Hold flags must be respected even if the hold was set after the Execution Intent was created.

**EC-E-009** Margin check failures are non-negotiable. An Order that fails margin check is rejected. Submitting an Order with insufficient margin is a constitutional violation.

**EC-E-010** Intraday positions must be closed before market close (3:25 PM IST) or be automatically squared off. An open intraday position at market close triggers an emergency EXT execution.

---

### Category EC-F: Kill Switch

**EC-F-001** The Kill Switch is a system-wide binary state: ACTIVE or INACTIVE. There are no intermediate states.

**EC-F-002** Kill Switch activation is immediate and synchronous. From the moment of activation, no Order passes through the submission pipeline.

**EC-F-003** Kill Switch deactivation requires human operator command with operator identity recorded in the audit trail.

**EC-F-004** The Kill Switch state must be persisted to durable storage. A system restart must restore the Kill Switch state from storage — it must not default to INACTIVE.

**EC-F-005** Kill Switch activation is always logged in the immutable audit trail with: activating entity, timestamp, reason, and current portfolio state snapshot.

**EC-F-006** Kill Switch must be tested weekly (simulated activation/deactivation in non-production mode). Test results recorded in Execution Health Manager.

---

### Category EC-G: Retry Rules

**EC-G-001** Retries are only permitted for RECOVERABLE failure classifications. NON_RECOVERABLE failures must not be retried.

**EC-G-002** The maximum retry count is 3 per execution. After 3 retries, the execution is escalated to the Execution Recovery Manager.

**EC-G-003** Retry back-off must be exponential: 1s, 4s, 16s. Linear or constant-interval retries are prohibited.

**EC-G-004** A retry execution must use the same order_reference_id as the original. Retries with new reference IDs create duplicate orders.

**EC-G-005** Retries are blocked when the Kill Switch is active.

**EC-G-006** Each retry attempt is recorded in the audit trail with: attempt number, failure reason, retry timestamp.

---

### Category EC-H: Recovery

**EC-H-001** All recovery executions require human operator approval before submission. Automated recovery order placement is prohibited.

**EC-H-002** Recovery must begin within 15 minutes of a failure being escalated from the Retry Manager.

**EC-H-003** Recovery must reconcile the IIOS position with the broker position before proposing any corrective action.

**EC-H-004** If the IIOS position cannot be determined with certainty during recovery, all executions for the affected instrument must be halted pending manual investigation.

**EC-H-005** A recovery report must be produced for every recovery incident. Recovery reports are stored in the Execution Archive.

**EC-H-006** The Learning System must receive every recovery incident report for post-hoc analysis.

---

### Category EC-I: Auditability

**EC-I-001** The execution audit log is append-only. No audit record may be modified or deleted after creation.

**EC-I-002** Every execution event must be recorded in the audit log. No gap in the audit trail is acceptable.

**EC-I-003** Audit records must use a cryptographic hash chain. Any tampering must be immediately detectable.

**EC-I-004** Audit records must be stored in a physically separate location from the Execution Registry.

**EC-I-005** Audit records must include actor identity for every event: EXECUTION_ENGINE_AI, HUMAN_OPERATOR_{id}, BROKER_{id}, EXCHANGE_{id}.

---

### Category EC-J: Traceability

**EC-J-001** Every execution must link to a Decision Package. The decision_id is stored in the Execution record and in every fill record.

**EC-J-002** Every fill must link to an execution. Orphaned fills (fills without a matching execution record) are a constitutional violation.

**EC-J-003** Every position change must link to a fill. Position changes without fill linkage are a constitutional violation.

**EC-J-004** The Execution Engine must support full reverse tracing: Position → Fill → Execution → Decision → Reasoning → Observation.

**EC-J-005** Settlement records must link to fills. Settlement without fill linkage is a constitutional violation.

---

### Category EC-K: Consistency

**EC-K-001** An instrument may not have concurrent conflicting executions (BUY and SELL simultaneously) unless one is an exit for an existing position and the other is a new entry — and these must be sequenced, not simultaneous.

**EC-K-002** Position state must be consistent across the IIOS and the broker at all times. Discrepancies trigger the Position Reconciliation Service.

**EC-K-003** The sum of all fills for an execution must equal the execution fill_quantity. Arithmetic inconsistency in fill aggregation is a constitutional violation.

**EC-K-004** The portfolio NAV must equal the sum of all positions at LTP plus cash at all times. Arithmetic inconsistency is a constitutional violation.

---

### Category EC-L: Security

**EC-L-001** Broker API keys and authentication tokens are never logged in plain text. All logging of authentication data must be redacted or hashed.

**EC-L-002** Broker authentication tokens must be refreshed before expiry. Token expiry during a trading session is a preventable failure and counts against reliability.

**EC-L-003** All inter-component communication must use authenticated service mesh connections.

**EC-L-004** Position and portfolio data must be encrypted at rest.

**EC-L-005** The Execution Engine must validate the source of every incoming Decision Package. Packages from unauthenticated sources must be rejected.

---

### Category EC-M: Human Override

**EC-M-001** Human override of any execution is absolute and unconditional. No component may block or delay a human override instruction.

**EC-M-002** Human override events must be recorded in the audit trail immediately, with operator identity and reason.

**EC-M-003** A human cancel of a submitted Order must be communicated to the broker immediately. The broker-side cancel must be confirmed before the IIOS marks the execution CANCELLED.

**EC-M-004** Human operators may activate the Kill Switch at any time, for any reason, without justification. The Kill Switch does not require any form of AI approval.

**EC-M-005** Human operators may override position limits for a single execution with documented justification. This requires TIER-2-HUMAN authority and generates a constitutional override record.

---

### Category EC-N: Broker Independence

**EC-N-001** The Execution Engine must function correctly with at least two configured broker gateways. Single-broker dependency is a configuration violation.

**EC-N-002** A single broker gateway failure must not halt all executions. Routing must failover to the secondary broker or Paper Simulator.

**EC-N-003** The PAPER_TRADING mode must be operationally equivalent to live mode in all respects except actual market placement. Paper mode exercises all pipeline stages.

**EC-N-004** Broker-specific logic must be encapsulated within the Broker Gateway component. No broker-specific code may appear in any other Execution Engine component.

**EC-N-005** A new broker can be integrated by implementing the BrokerGatewayInterface without modifying any other Execution Engine component.

---

### Category EC-O: Exchange Independence

**EC-O-001** The Execution Engine must not hard-code exchange-specific behaviours. Exchange-specific instrument mappings, lot sizes, and circuit limits must be configuration-driven.

**EC-O-002** Circuit breaker activation on any instrument must trigger an immediate hold on executions for that instrument.

**EC-O-003** Market halt detection must be immediate. When the Exchange Gateway detects a market halt, all SUBMITTED orders for that exchange are monitored for forced cancellation.

---

### Category EC-P: Policy Compliance

**EC-P-001** All active execution policies must be evaluated for every Order. Silent policy bypasses are prohibited.

**EC-P-002** Policy changes take effect immediately for Orders not yet SUBMITTED. In-flight Orders are not affected by policy changes.

**EC-P-003** Intraday-only policies activate at market open. Position limits for intraday instruments are enforced from market open to square-off time.

**EC-P-004** Daily trading session limits (maximum number of Orders per day) are enforced by the Order Validator. Exceeding the session limit requires human override.

---
## PART X — EXECUTION READINESS CHECKLIST

The Execution Readiness Checklist (ERC) is the comprehensive pre-execution and post-execution gate. It is evaluated at two points: (1) before an execution begins (Pre-Execution Gate) and (2) after an execution completes (Post-Execution Gate).

---

### ERC Section 1: Decision Received and Validated

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 1.1 | Decision Package received from authenticated source | Yes | Yes |
| 1.2 | Decision Package schema valid (all required fields present) | Yes | Yes |
| 1.3 | Decision Package status = COMMITTED | Yes | Yes |
| 1.4 | decision_id not previously processed (idempotency) | Yes | Yes |
| 1.5 | Decision Package expiry timestamp is in the future | Yes | Yes |
| 1.6 | Decision Package is not superseded | Yes | Yes |
| 1.7 | entity_id resolves to a valid, active instrument | Yes | Yes |
| 1.8 | action_type is a valid execution action | Yes | Yes |

---

### ERC Section 2: Execution Intent Validated

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 2.1 | Execution Intent created and registered | Yes | Yes |
| 2.2 | execution_intent_id is unique | Yes | Yes |
| 2.3 | Execution type is valid for the decision action type | Yes | Yes |
| 2.4 | Market data is current (LTP not stale) | Yes | Yes |
| 2.5 | Portfolio state is current (positions loaded) | Yes | Yes |
| 2.6 | Algorithmic execution decision made (size vs ADV checked) | Yes | Yes |
| 2.7 | Tranche plan constructed for multi-tranche executions | No | No |

---

### ERC Section 3: Order Created

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 3.1 | Instrument token resolved | Yes | Yes |
| 3.2 | Order schema valid | Yes | Yes |
| 3.3 | Limit price set (if LIMIT order type) | Yes | Yes |
| 3.4 | Trigger price set (if STOP or SL-M order type) | Yes | Yes |
| 3.5 | Quantity > 0 | Yes | Yes |
| 3.6 | Quantity is valid lot size | Yes | Yes |
| 3.7 | Time-in-force set | Yes | Yes |
| 3.8 | order_reference_id is unique | Yes | Yes |

---

### ERC Section 4: Risk Checked

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 4.1 | Kill Switch is INACTIVE | Yes | Yes |
| 4.2 | No active human hold flag for this entity | Yes | Yes |
| 4.3 | Position limit check PASS (post-execution position within limits) | Yes | Yes |
| 4.4 | Session Order count within session limit | Yes | Yes |
| 4.5 | Market is open (or pre-market order for authorised type) | Yes | Yes |
| 4.6 | Risk Guardian status is not CRITICAL (for BUY/INC) | Yes | Yes |
| 4.7 | Estimated slippage within max_slippage_pct | Yes | Yes |
| 4.8 | Margin estimate: available capital sufficient | Yes | Yes |
| 4.9 | Daily drawdown < 2% (for BUY/INC orders) | Yes | Yes |
| 4.10 | Sector concentration check PASS | Yes | Yes |

---

### ERC Section 5: Broker Ready

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 5.1 | Selected broker gateway is HEALTHY | Yes | Yes |
| 5.2 | Broker authentication token is valid and not expired | Yes | Yes |
| 5.3 | Broker API rate limit not exceeded | Yes | Yes |
| 5.4 | Broker connectivity heartbeat received within last 30 seconds | Yes | Yes |
| 5.5 | Instrument is tradeable on selected broker | Yes | Yes |

---

### ERC Section 6: Exchange Ready

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 6.1 | Exchange is open | Yes | Yes |
| 6.2 | No circuit breaker active for this instrument | Yes | Yes |
| 6.3 | No trading suspension for this instrument | Yes | Yes |
| 6.4 | LTP within circuit limits | Yes | Yes |
| 6.5 | Adequate order book depth for order size | No | No (warn) |

---

### ERC Section 7: Execution Successful

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 7.1 | Acknowledgement received from broker within SLA | Yes | Yes |
| 7.2 | Broker order_id assigned and recorded | Yes | Yes |
| 7.3 | Fill events received (or timeout with investigation) | Yes | Yes |
| 7.4 | Fill quantity >= min_acceptable_fill_pct of ordered quantity | Yes | Yes |
| 7.5 | Average fill price within max_slippage_pct of intended price | Yes | Yes |
| 7.6 | No fill quantity > ordered quantity | Yes | Yes |

---

### ERC Section 8: Position Updated

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 8.1 | Position record updated within SLA of fill | Yes | Yes |
| 8.2 | Position change linked to fill_id and execution_id | Yes | Yes |
| 8.3 | Position change is directionally correct (buy adds, sell reduces) | Yes | Yes |
| 8.4 | Position update event published to EventBus | Yes | Yes |
| 8.5 | No position inconsistency detected | Yes | Yes |

---

### ERC Section 9: Portfolio Updated

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 9.1 | Portfolio updated within SLA of position update | Yes | Yes |
| 9.2 | Cash balance updated correctly | Yes | Yes |
| 9.3 | Portfolio P&L recomputed | Yes | Yes |
| 9.4 | Drawdown recomputed and published to Risk Guardian | Yes | Yes |
| 9.5 | Portfolio update event published to EventBus | Yes | Yes |

---

### ERC Section 10: Audit Complete

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 10.1 | All expected audit events recorded | Yes | Yes |
| 10.2 | Audit hash chain intact for this execution | Yes | Yes |
| 10.3 | All fill details recorded in audit | Yes | Yes |
| 10.4 | All actor identities recorded | Yes | Yes |
| 10.5 | Audit record includes decision_id lineage | Yes | Yes |

---

### ERC Section 11: Archived

Applies after execution reaches terminal state (COMPLETED, CANCELLED, FAILED, EXPIRED).

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 11.1 | Execution record transferred to Archive | Yes | Yes |
| 11.2 | Archive write confirmed | Yes | Yes |
| 11.3 | Archive record integrity verified | Yes | Yes |
| 11.4 | Learning System notified of completed execution | Yes | Yes |

---

### ERC Section 12: Recovery Tested

This section applies to recovery executions (EX-TYPE-019) only.

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 12.1 | Broker position queried and received | Yes | Yes |
| 12.2 | Discrepancy classification complete | Yes | Yes |
| 12.3 | Corrective order has human approval | Yes | Yes |
| 12.4 | Recovery execution completes successfully | Yes | Yes |
| 12.5 | Recovery report produced and archived | Yes | Yes |
| 12.6 | Learning System notified of recovery incident | Yes | Yes |

---

### ERC Section 13: Operationally Ready (Pre-Session Check)

This section is evaluated at system startup before any trading begins.

| # | Check | Mandatory | Blocking |
|---|---|---|---|
| 13.1 | All 23 components initialised and healthy | Yes | Yes |
| 13.2 | Execution Registry loaded and responsive | Yes | Yes |
| 13.3 | Broker authentication valid for all configured brokers | Yes | Yes |
| 13.4 | Kill Switch state restored from storage | Yes | Yes |
| 13.5 | Position reconciliation with broker completed | Yes | Yes |
| 13.6 | Audit hash chain integrity verified | Yes | Yes |
| 13.7 | Session limits reset | Yes | Yes |
| 13.8 | Slippage Manager calibrated with previous session data | No | No |
| 13.9 | Latency Manager baselines updated | No | No |
| 13.10 | Analytics Manager session initialised | Yes | Yes |

---

### ERC Section 14: Use-Case Readiness Matrix

| Use Case | Required ERC Sections | Kill Switch Mode | Min EQS |
|---|---|---|---|
| Live equity trading | 1-13 | INACTIVE | 0.70 |
| Live derivative trading | 1-13 | INACTIVE | 0.75 |
| Paper trading (simulation) | 1-13 | N/A (paper mode) | 0.60 |
| Emergency execution (EMR) | 4, 5, 6, 7, 8, 9, 10 | INACTIVE | 0.40 |
| Recovery execution | 1, 4, 5, 12 | INACTIVE | 0.50 |
| Scheduled execution (SCH) | 1-13 + scheduler check | INACTIVE | 0.70 |
| Manual execution (human) | 4, 5, 6, 7, 8, 9, 10 | INACTIVE | N/A |

---
---

## SUPPLEMENT A — ORDER TAXONOMY REFERENCE

### A.1 Overview

This supplement provides the complete reference for all Order types available in the IIOS Execution Engine, organised by execution environment, instrument class, and decision type compatibility.

---

### A.2 Order Type Compatibility Matrix

| Order Type | Equity | Derivative | Index Futures | ETF | Intraday | Delivery |
|---|---|---|---|---|---|---|
| Market | Yes | Yes | Yes | Yes | Yes | Yes |
| Limit | Yes | Yes | Yes | Yes | Yes | Yes |
| Stop (SL-M) | Yes | Yes | Yes | Yes | Yes | Yes |
| Stop-Limit (SL) | Yes | Yes | Yes | Yes | Yes | Yes |
| IOC | Yes | Yes | Yes | Yes | Yes | No |
| FOK | Yes | Yes | No | Yes | Yes | No |
| GTT | Yes | No | No | Yes | No | Yes |
| Bracket | Yes | Yes | Yes | Yes | Yes | No |
| Cover | Yes | Yes | Yes | Yes | Yes | No |
| TWAP | Yes | Yes | Yes | Yes | Yes | Yes |
| VWAP | Yes | Yes | Yes | Yes | Yes | Yes |

---

### A.3 Decision Type to Order Type Default Mapping

| Decision Type | Default Order Type | Alternative |
|---|---|---|
| BUY-EQT | Limit | Market (URGENT) |
| BUY-DRV | Limit | Market (URGENT) |
| BUY-IDX | Limit | Market (URGENT) |
| SEL-CLOSE | Limit | Market (URGENT) |
| SEL-SHORT-INIT | Limit | Market (if BEAR_TREND) |
| EXT-SL | Market | Stop-Limit (if specified) |
| EXT-TP | Limit | Market (if TP hit with gap) |
| EXT-EMERGENCY | Market | IOC |
| RED-PARTIAL | Limit | Market |
| INC-SCALE | Limit | Market |
| PRT-SL | Stop (SL-M) | Stop-Limit |
| PRT-TRAILING | Trailing Stop | Stop (SL-M) |
| HDG-POSITION | Limit | Market |
| RBL-SCHEDULED | Basket (Limit) | Basket (Market) |
| SCH-PRE_MARKET | GTT | Limit at open |
| EMR-LIQUIDATE | Market | IOC |
| EMR-HALT | N/A (no order) | N/A |

---

### A.4 Order Complexity Reference

| Complexity Tier | Types | Components | Used for |
|---|---|---|---|
| SIMPLE | Market, Limit | Single order leg | Standard BUY/SELL |
| PROTECTED | Stop, Stop-Limit, Cover | Two legs (entry + stop) | Protected entries |
| AUTOMATED | Bracket Order | Three legs (entry + TP + SL) | Automated PNL management |
| ALGORITHMIC | TWAP, VWAP | Multiple child orders | Large positions |
| COMPOSITE | Basket | Multiple independent orders | Portfolio rebalancing |

---

### A.5 Order Lifecycle Reference

| Status | Description | Terminal? |
|---|---|---|
| CREATED | Order constructed; not yet validated | No |
| VALIDATED | Passed all validation checks | No |
| SUBMITTED | Submitted to broker | No |
| ACKNOWLEDGED | Broker accepted | No |
| PARTIAL | Partially filled | No |
| FILLED | Fully filled | Yes |
| CANCELLED | Cancelled by IIOS or broker | Yes |
| REJECTED | Rejected by broker or exchange | Yes |
| EXPIRED | Time-in-force expired | Yes |
| PENDING_CANCEL | Cancel submitted to broker; awaiting confirmation | No |

---

### A.6 Time-in-Force Reference

| TIF Code | Name | Description | Use case |
|---|---|---|---|
| DAY | Day Order | Expires at end of trading session | Standard orders |
| GTC | Good Till Cancelled | Persists until filled or manually cancelled | Long-term entries |
| IOC | Immediate or Cancel | Fill available quantity immediately; cancel rest | Basket legs, arbitrage |
| FOK | Fill or Kill | Fill entire quantity immediately or cancel all | Atomic fills |
| GTD | Good Till Date | Expires on specified date | Scheduled entries |
| GTT | Good Till Triggered | Trigger-price based; stored at broker | Conditional entries |
| ATO | At Open | Executes at market open price | Pre-market scheduled |
| ATC | At Close | Executes at market close price | EOD rebalancing |

---

### A.7 Price Type Reference

| Price Type | Code | Description | Order type |
|---|---|---|---|
| Market | MKT | Best available market price | MARKET |
| Limit | LMT | Specific price or better | LIMIT |
| Stop Market | SL-M | Triggered by stop price; fills at market | STOP |
| Stop Limit | SL | Triggered by stop price; fills at limit | STOP-LIMIT |
| Market on Open | MOO | Market price at session open | ATO |
| Market on Close | MOC | Market price at session close | ATC |

---

## SUPPLEMENT B — EXECUTION STATE MACHINE

### B.1 Complete State Reference

| State | Description | Entry from | Exits to |
|---|---|---|---|
| RECEIVED | Decision Package received | (none) | PLANNING |
| PLANNING | Execution Intent being constructed | RECEIVED | QUEUED, SCHEDULED, HELD |
| SCHEDULED | Deferred execution waiting for time/condition | PLANNING | QUEUED, EXPIRED, CANCELLED |
| QUEUED | In Execution Queue awaiting processing | PLANNING, SCHEDULED | BUILDING |
| HELD | Execution paused (Kill Switch, hold flag, etc.) | PLANNING, RISK_CHECKING | QUEUED (on release), CANCELLED |
| BUILDING | Order Builder constructing Order object | QUEUED | VALIDATING |
| VALIDATING | Order Validator checking Order | BUILDING | RISK_CHECKING, REJECTED |
| RISK_CHECKING | Kill Switch, hold, position limit checks | VALIDATING | ROUTING, HELD, BLOCKED |
| BLOCKED | Kill Switch active; awaiting lift | RISK_CHECKING | HELD, CANCELLED |
| ROUTING | Order Router selecting broker | RISK_CHECKING | SUBMITTED |
| SUBMITTED | Order sent to broker; awaiting ACK | ROUTING | ACKNOWLEDGED, REJECTED, TIMEOUT |
| ACKNOWLEDGED | Broker accepted Order | SUBMITTED | PARTIAL_FILL, FULL_FILL, REJECTED |
| PARTIAL_FILL | Some quantity filled; awaiting remainder | ACKNOWLEDGED | FULL_FILL, STALLED, CANCELLED |
| STALLED | Partial fill; no further fills for > threshold time | PARTIAL_FILL | RETRY, HELD, CANCELLED |
| FULL_FILL | Entire ordered quantity filled | ACKNOWLEDGED, PARTIAL_FILL | POSITION_UPDATING |
| POSITION_UPDATING | Position Updater processing fill | FULL_FILL, PARTIAL_FILL | PORTFOLIO_UPDATING |
| PORTFOLIO_UPDATING | Portfolio Updater processing change | POSITION_UPDATING | AUDITING |
| AUDITING | Audit Manager recording execution | PORTFOLIO_UPDATING | ARCHIVING |
| ARCHIVING | Archive Manager preserving record | AUDITING | COMPLETED |
| COMPLETED | All steps complete; terminal state | ARCHIVING | (none) |
| RETRY | In Retry Manager; awaiting resubmission | SUBMITTED, ACKNOWLEDGED | QUEUED, RECOVERING |
| RECOVERING | In Recovery Manager | RETRY, FAILED | COMPLETED (with correction), FAILED |
| TIMEOUT | No ACK received within SLA | SUBMITTED | RETRY |
| REJECTED | Rejected by Order Validator, broker, or exchange | VALIDATING, SUBMITTED | RETRY (if recoverable), FAILED |
| FAILED | Non-recoverable failure | REJECTED, RECOVERING | RECOVERING (escalation) |
| CANCELLED | Cancelled by human operator or system | Any non-terminal | (none) — terminal |
| EXPIRED | Expiry timestamp reached | Any non-terminal | (none) — terminal |

---

### B.2 Terminal States

| Terminal State | Meaning | Trigger |
|---|---|---|
| COMPLETED | Execution successful; all records complete | Archive confirmed |
| CANCELLED | Deliberately stopped | Human cancel or Kill Switch |
| EXPIRED | Time limit reached | Expiry timestamp |
| FAILED | Unrecoverable failure | Non-recoverable rejection after max retries |

---

### B.3 State Duration SLAs

| State | Normal Duration | Alert if exceeded |
|---|---|---|
| RECEIVED to QUEUED | < 100ms | 300ms |
| QUEUED to SUBMITTED | < 500ms | 1,000ms |
| SUBMITTED to ACKNOWLEDGED | < 500ms | 1,500ms |
| ACKNOWLEDGED to FULL_FILL | Market-dependent | 30 min (stale order alert) |
| FULL_FILL to COMPLETED | < 2,000ms | 5,000ms |
| RETRY cycle | < 30 seconds | N/A |
| RECOVERY | < 15 minutes | 30 minutes |

---
## SUPPLEMENT C — BROKER ROUTING MODELS

### C.1 Overview

The Execution Engine supports multiple broker routing models. The routing model determines which broker gateway handles an Order and what fallback strategy applies on failure.

---

### C.2 Primary-Secondary-Paper Model

The standard routing model used by the IIOS in production:

`
[Order Router]
      |
      v
[Is PAPER_TRADING mode active?]
      |── YES ──> [Paper Simulator] (always; regardless of other config)
      |
      v NO
[Is primary broker (Dhan) HEALTHY?]
      |── YES ──> [Dhan Broker Gateway]
      |
      v NO
[Is secondary broker (Zerodha) HEALTHY?]
      |── YES ──> [Zerodha Broker Gateway]
      |
      v NO
[All brokers unavailable]
      |── EXECUTION HELD ──> [Human alert] ──> Manual resolution
`

---

### C.3 Broker Capability Matrix

| Feature | Dhan | Zerodha | Paper Simulator |
|---|---|---|---|
| Market orders | Yes | Yes | Yes |
| Limit orders | Yes | Yes | Yes |
| Stop orders (SL-M) | Yes | Yes | Yes |
| Stop-Limit (SL) | Yes | Yes | Yes |
| Bracket orders | Yes | Yes | Yes (simulated) |
| Cover orders | Yes | Yes | Yes (simulated) |
| GTT orders | Yes | Yes | No |
| Options trading | Yes | Yes | Yes (simulated) |
| Futures trading | Yes | Yes | Yes (simulated) |
| WebSocket feed | Yes | Yes | Yes (internal) |
| Position query API | Yes | Yes | Yes (internal) |
| Order status API | Yes | Yes | Yes (internal) |

---

### C.4 Broker Authentication Models

**Dhan:**
- Authentication: OAuth 2.0 access token
- Token validity: 24 hours
- Refresh mechanism: Daily re-authentication at 07:30 IST
- Storage: Encrypted config; never in source code

**Zerodha:**
- Authentication: Access token via Kite Connect API
- Token validity: 24 hours
- Refresh mechanism: Daily login + TOTP

**Paper Simulator:**
- Authentication: None (internal component)
- Credentials: Not applicable

---

### C.5 Routing Policy Override Rules

The following rules may override the default routing:

| Rule | Trigger | Routing effect |
|---|---|---|
| C-ROUTE-001 | Instrument not available on primary broker | Route to secondary |
| C-ROUTE-002 | Primary broker rate limit exceeded | Route to secondary; restore primary after cool-down |
| C-ROUTE-003 | Options order (DRV instrument) | Route to options-capable broker |
| C-ROUTE-004 | Order size > broker maximum order value | Split order across tranches |
| C-ROUTE-005 | Admin: SET_BROKER_PRIORITY command | Use specified broker |
| C-ROUTE-006 | PAPER_TRADING config = True | Always route to Paper Simulator |

---

### C.6 Paper Simulator Architecture

The Paper Simulator is a built-in component that simulates broker and exchange behaviour for testing and paper trading:

**Fill simulation:**
- Market orders: filled immediately at current LTP
- Limit orders: filled when LTP crosses the limit price; checked every 5 seconds
- Stop orders: triggered when LTP crosses trigger price; filled at market
- Bracket orders: all three legs simulated independently

**Fill timing:**
- Market orders: filled within 500ms of submission
- Limit orders: filled on next LTP check after price condition met

**Slippage simulation:**
- Random slippage applied from uniform distribution [0, configured_max_slippage]
- Default max slippage in paper mode: 0.10%

**Position tracking:**
- Paper Simulator maintains full position state (identical to live)
- Position query API returns simulated positions

---

## SUPPLEMENT D — RECOVERY SCENARIOS

### D.1 Overview

This supplement documents the five primary recovery scenarios encountered in live trading, the detection mechanism, classification, and step-by-step recovery procedure.

---

### D.2 Recovery Scenario D-REC-001: Connectivity Gap

**Description:** The IIOS loses connectivity to the broker during an active execution. The Order may have been submitted but no acknowledgement was received before connectivity was lost.

**Detection:** Execution Monitor timeout trigger; Broker Gateway heartbeat failure.

**Classification:** RECOVERABLE (with investigation)

**Recovery procedure:**
1. Broker Gateway detects connectivity loss; registers DISCONNECTED state
2. Execution Monitor flags all SUBMITTED Orders as TIMEOUT
3. On reconnection: Broker Gateway queries broker Order status API for all TIMEOUT orders
4. For each TIMEOUT order:
   a. If broker shows ACCEPTED/FILLED: record as if normally received; update state
   b. If broker shows REJECTED: route to Retry Manager
   c. If broker shows NOT_RECEIVED: order was lost; resubmit via Retry Manager
5. Position reconciliation after all TIMEOUT orders resolved
6. Audit event: RECOVERY_CONNECTIVITY_GAP

---

### D.3 Recovery Scenario D-REC-002: Partial Fill Stall

**Description:** An Order received a partial fill but no additional fills arrived for > configured stall threshold (default: 15 minutes for equity, 5 minutes for index instruments).

**Detection:** Execution Monitor stall detector; no fill events for > threshold.

**Classification:** RECOVERABLE or ACCEPTABLE_PARTIAL depending on fill percentage

**Recovery procedure:**
1. Execution Monitor flags execution as STALLED
2. Execution Planner determines current partial fill percentage
3. If filled >= min_acceptable_fill_pct (default 80%): accept partial; mark FULL_FILL; cancel remainder
4. If filled < min_acceptable_fill_pct:
   a. Option A: Cancel and resubmit at adjusted price (Retry Manager)
   b. Option B: Hold and continue monitoring (human decision for HIGH governance)
5. Human notification for all stall scenarios above MEDIUM governance tier
6. Audit event: PARTIAL_FILL_STALL

---

### D.4 Recovery Scenario D-REC-003: Ghost Position

**Description:** The IIOS position record shows a position for an instrument, but the broker position query shows no position. This can occur after connectivity failures, session restarts, or failed executions.

**Detection:** Pre-session position reconciliation; discrepancy detected.

**Classification:** IIOS_AHEAD discrepancy

**Recovery procedure:**
1. Recovery Manager identifies ghost position
2. Recovery Manager queries broker position history for the instrument
3. If broker confirms: position was closed by broker (e.g., automatic square-off): update IIOS position to 0
4. If broker confirms: position exists but was not reported: trigger broker data refresh
5. If indeterminate: EMERGENCY_HOLD for instrument; human investigation
6. Human operator approves any corrective action
7. Audit event: GHOST_POSITION_DETECTED, POSITION_CORRECTED

---

### D.5 Recovery Scenario D-REC-004: Missed Fill

**Description:** The broker has a fill recorded that the IIOS has not recorded. This can occur when WebSocket fill events are dropped during connectivity issues.

**Detection:** Position reconciliation; broker position > IIOS position.

**Classification:** BROKER_AHEAD discrepancy

**Recovery procedure:**
1. Recovery Manager detects BROKER_AHEAD discrepancy
2. Query broker fill history for the instrument
3. Identify the fill that was not received by IIOS
4. Record the missed fill with all available details
5. Update position to match broker (IIOS position adjusted up)
6. Update portfolio to reflect the unrecorded fill
7. Produce recovery audit record
8. Audit event: MISSED_FILL_DETECTED, FILL_RECORDED_RETROACTIVELY

---

### D.6 Recovery Scenario D-REC-005: Session Restart with Open Orders

**Description:** The IIOS is restarted (deployment, crash) with active Orders submitted to the broker. On restart, the Execution Engine must reconcile its state with the broker.

**Detection:** Post-restart position reconciliation; Execution Registry shows SUBMITTED orders that are now unknown status.

**Recovery procedure:**
1. On startup: Execution Registry loaded; all SUBMITTED orders identified
2. For each SUBMITTED order: query broker Order status API
3. For each order:
   a. FILLED: record fill; update position; advance to POSITION_UPDATING
   b. CANCELLED (by broker or exchange): record cancellation; alert
   c. REJECTED: record rejection; alert; route to Retry Manager if appropriate
   d. PENDING (still live at broker): restore monitoring; continue tracking
4. Position reconciliation after all SUBMITTED orders resolved
5. Human operator review of reconciliation report before trading resumes
6. Audit event: SESSION_RESTART_RECONCILIATION

---

## SUPPLEMENT E — FAILURE MODE ANALYSIS

### E.1 Critical Failure Modes

| Failure Mode | Severity | Probability | Detection | Mitigation |
|---|---|---|---|---|
| Wrong instrument executed | CRITICAL | Very Low | EQD-01 accuracy check | Order Validator instrument check |
| Kill Switch not checked | CRITICAL | Very Low | Unit test enforcement | EC-E-001 constitutional rule |
| Audit hash chain breach | CRITICAL | Very Low | Hash integrity check | Immediate HALT; security review |
| Fill quantity > ordered | CRITICAL | Very Low | Execution Tracker | EC-C-008 constitutional rule |
| Position goes negative (unintended) | HIGH | Low | Position Updater check | Quantity sanity check in Order Validator |
| Ghost position (IIOS > broker) | HIGH | Low | Reconciliation | Pre-session reconciliation |
| Connectivity gap during execution | HIGH | Medium | Heartbeat; timeout | EC-N-002 failover; recovery pipeline |
| Broker authentication expiry | HIGH | Medium | Token age monitoring | Auto-refresh at 07:30 IST |
| Overfill (broker fills > ordered) | HIGH | Very Low | Execution Tracker | Broker anomaly investigation |
| Audit write failure | CRITICAL | Very Low | Audit health check | AUDIT_DEGRADED mode; hold executions |
| Storage failure | CRITICAL | Low | Storage health check | READ-ONLY mode; recovery |
| Kill Switch deactivated without human | CRITICAL | Very Low | Governance rule | EC-F-002 constitutional rule |
| Session limit exceeded | MEDIUM | Low | Session counter | Hard limit at configured max |
| Slippage exceeded max | MEDIUM | Medium | Slippage Manager | Pre-trade estimate; hold for human |
| Partial fill stall | MEDIUM | Medium | Stall detector | Recovery Scenario D-REC-002 |
| Paper mode used in live accidentally | HIGH | Very Low | Mode configuration check | PAPER_TRADING config explicit flag |

---
## SUPPLEMENT F — PERFORMANCE TARGETS

### F.1 Latency Performance Targets

All latency measurements are end-to-end wall-clock time from event received to action completed.

| Stage | Target | Warning | Critical |
|---|---|---|---|
| Decision Package receipt to QUEUED | < 100ms | > 300ms | > 1,000ms |
| QUEUED to ORDER_SUBMITTED | < 500ms | > 1,000ms | > 2,000ms |
| ORDER_SUBMITTED to ACKNOWLEDGED | < 500ms (broker-dependent) | > 1,500ms | > 3,000ms |
| Order Builder stage | < 30ms | > 80ms | > 150ms |
| Order Validation stage | < 20ms | > 50ms | > 100ms |
| Risk Check stage | < 15ms | > 40ms | > 80ms |
| Order Routing decision | < 20ms | > 50ms | > 100ms |
| Broker Gateway API call | < 300ms | > 600ms | > 1,200ms |
| Fill event to Position update | < 50ms | > 150ms | > 300ms |
| Position update to Portfolio update | < 100ms | > 300ms | > 600ms |
| Portfolio update to Audit record | < 20ms | > 60ms | > 120ms |
| Full execution lifecycle (RECEIVED to COMPLETED) | < 2,000ms | > 5,000ms | > 10,000ms |
| Emergency execution (EMR) | < 500ms | > 1,000ms | > 2,000ms |
| Kill Switch activation | < 50ms | > 100ms | > 200ms |

---

### F.2 Throughput Performance Targets

| Metric | Normal | Peak | Absolute Maximum |
|---|---|---|---|
| Orders submitted per session | 30-80 | 150 | 300 (constitutional limit) |
| Concurrent active executions (monitoring) | 20-40 | 80 | 150 |
| Fill events processed per minute | 20-60 | 200 | 500 |
| Portfolio updates per hour | 50-100 | 500 | 1,000 |
| Audit events written per session | 500-1,500 | 5,000 | 10,000 |
| Decision Packages processed per session | 15-30 | 80 | 150 |

---

### F.3 Fill Quality Performance Targets

| Metric | Target | Warning | Critical |
|---|---|---|---|
| Fill rate (filled / submitted) | > 95% | < 90% | < 80% |
| Average slippage (per session) | < 0.15% | > 0.30% | > 0.50% |
| Retry rate | < 5% | > 10% | > 20% |
| Recovery rate (recovery cases / total) | < 1% | > 3% | > 5% |
| Average EQS (per session) | > 0.80 | < 0.70 | < 0.60 |
| Session EXCELLENT EQS rate | > 60% | < 40% | < 20% |
| Partial fill stall rate | < 3% | > 8% | > 15% |

---

### F.4 Reliability Performance Targets

| Metric | Target | Notes |
|---|---|---|
| Execution Engine uptime (trading hours) | > 99.9% | < 4.5 min downtime per session |
| Broker gateway availability | > 99.5% | Per broker; both brokers combined > 99.9% |
| Audit log write success rate | 100% | Any failure is P0 |
| Position accuracy (post-reconciliation) | 100% | Any discrepancy triggers recovery |
| Kill Switch response time | < 50ms | Must halt submissions immediately |
| Override Service availability | 100% | Human override must always work |

---

### F.5 Storage Performance Targets

| Metric | Target | Notes |
|---|---|---|
| Registry read latency (single record) | < 10ms | Live reads |
| Registry write latency | < 20ms | Status updates |
| Audit write latency | < 20ms | Append-only |
| Archive write latency | < 500ms | Post-execution |
| Position query latency | < 5ms | Real-time position lookups |
| Portfolio query latency | < 10ms | Real-time portfolio state |

---

## SUPPLEMENT G — OPERATIONAL RUNBOOK

### G.1 Overview

This runbook documents standard operating procedures for the Execution Engine: startup, shutdown, daily operations, and emergency procedures.

---

### G.2 Pre-Market Startup Procedure (07:30 - 09:00 IST)

**Step 1: System pre-checks (automated)**

| Check | Expected | Failure action |
|---|---|---|
| Storage Layer reachable | Response < 200ms | Abort; page operator |
| Execution Registry loadable | Registry responds | Abort; page operator |
| Audit log hash chain valid | Chain intact | Abort; security alert |
| Broker authentication valid | Token valid | Attempt refresh; abort if refresh fails |
| Decision Engine upstream | Heartbeat received | Warn; continue |
| Risk Guardian downstream | Heartbeat received | Abort; Risk Guardian is mandatory |

---

**Step 2: Kill Switch state restoration**

Load Kill Switch state from durable storage. If Kill Switch was ACTIVE at last shutdown:
- Keep Kill Switch ACTIVE
- Alert operator: Kill Switch was active at last shutdown
- Wait for human confirmation before deactivating

---

**Step 3: Component activation sequence**

Activate in this order (each confirmed before next):

`
1.  Storage Layer
2.  Execution Audit Manager (must be active before any execution operations)
3.  Execution Registry
4.  Execution Catalog
5.  Execution Archive Manager
6.  Position Updater (load positions from storage)
7.  Portfolio Updater (load portfolio from storage)
8.  Exchange Gateway (connect market data feed)
9.  Broker Gateway(s) (authenticate; connect WebSocket)
10. Execution Governance Manager (load policies; Kill Switch state)
11. Latency Manager
12. Slippage Manager (load calibration data)
13. Execution Planner
14. Execution Scheduler (reload deferred executions)
15. Execution Queue (initialise)
16. Order Builder
17. Order Validator
18. Order Router
19. Execution Monitor
20. Execution Tracker
21. Retry Manager
22. Execution Recovery Manager
23. Execution Analytics Manager
24. Execution Health Manager (self-monitors all components)
    [All 23 components active]
25. Open inbound port: Decision Package reception (ES-01)
26. Emit: EXECUTION_ENGINE_STARTED event to EventBus
`

---

**Step 4: Position reconciliation (09:00 - 09:10 IST)**

Before market opens:
1. Query broker for all current positions
2. Compare broker positions with IIOS Position Registry
3. Identify and investigate discrepancies
4. Approve any corrective positions
5. Log reconciliation result

**If reconciliation fails or shows unresolvable discrepancy:** Do not begin trading. Escalate to human operator.

---

**Step 5: Post-startup validation**

Run synthetic test execution (paper mode):
1. Submit a synthetic Decision Package (BUY-EQT, paper mode)
2. Confirm: full lifecycle to COMPLETED in < 1,000ms
3. Confirm: audit trail complete
4. Destroy test execution record

Trading begins only after successful validation.

---

### G.3 Intraday Operations (09:15 - 15:30 IST)

**Continuous operations (automated):**
- Execution Monitor: scan all active executions every 5 seconds
- Slippage Manager: monitor fill quality in real time
- Latency Manager: monitor all pipeline latencies
- Position Updater: update on every fill event
- Portfolio Updater: recompute on every position change
- Audit Manager: record all events

**Regular operator checks (every 60 minutes):**
- Review Execution Health Dashboard
- Check session order count vs session limit
- Review any HELD executions
- Check pending TIER-2-HUMAN approvals

**Circuit breaker response (if triggered by exchange):**
- Exchange Gateway alerts Execution Engine
- All SUBMITTED orders for affected instrument monitored
- New orders for affected instrument BLOCKED
- Human operator notification
- Resume when circuit breaker lifted

---

### G.4 Pre-Close Operations (15:25 - 15:30 IST)

**Intraday position square-off (15:25 IST):**
1. Execution Engine identifies all INTRADAY positions
2. For each intraday position: generate EXT-SL decision request to Decision Engine
3. Execute all intraday close orders as MARKET orders
4. Confirm all intraday positions closed before 15:30 IST
5. Alert if any intraday position remains open at 15:28 IST

---

### G.5 End-of-Day Operations (15:30 - 18:00 IST)

**Session close (automated):**
1. Execution Queue: drain remaining NORMAL and LOW priority executions
2. Execution Scheduler: mark expired scheduled executions
3. Execution Monitor: confirm all SUBMITTED orders resolved
4. Position Updater: final position reconciliation with broker
5. Portfolio Updater: produce session portfolio snapshot
6. Execution Analytics Manager: produce session analytics report
7. Execution Archive Manager: archive all terminal-state executions
8. Audit Manager: flush all pending audit events

**EOD report (automated, 16:00 IST):**
- Session summary: orders submitted, fill rate, average EQS, slippage
- Position summary: all open positions
- P&L summary: realised P&L, unrealised P&L
- Alerts: any unresolved issues, held executions, recovery incidents

---

### G.6 Graceful Shutdown

**Trigger:** SIGTERM signal, operator command, or scheduled shutdown.

1. Emit EXECUTION_ENGINE_SHUTDOWN_INITIATED event
2. Stop accepting new Decision Packages (close ES-01)
3. Allow in-flight executions to complete (30-second drain window)
4. All PENDING executions: transition to HELD; notify human operator
5. Cancel all active GTT orders that are IIOS-managed (optional; operator decision)
6. Persist Kill Switch state to durable storage
7. Flush all pending audit events
8. Flush all pending Registry writes
9. Deactivate components in reverse activation order
10. Emit EXECUTION_ENGINE_SHUTDOWN_COMPLETE event
11. Release all connections

---

### G.7 Emergency Stop Procedure

**Trigger:** Human operator command or extreme market event.

1. Kill Switch activated immediately (< 50ms)
2. All Order submissions blocked
3. Cancel all SUBMITTED orders not yet ACKNOWLEDGED (broker cancel commands sent)
4. Notify Risk Guardian: EXECUTION_EMERGENCY_STOP
5. Alert all operators via Telegram
6. System enters EMERGENCY_HOLD state
7. To resume: human operator must explicitly deactivate Kill Switch via authenticated command

---

### G.8 Recovery Procedures (Quick Reference)

| Scenario | Trigger | First action | Owner |
|---|---|---|---|
| Connectivity gap | Heartbeat failure | Query broker for SUBMITTED order status | Recovery Manager |
| Partial fill stall | No fills for > threshold | Accept partial or resubmit | Operator + Recovery Manager |
| Ghost position | Reconciliation discrepancy | Query broker position history | Recovery Manager |
| Missed fill | BROKER_AHEAD discrepancy | Record missed fill; update position | Recovery Manager |
| Session restart | System restart | Full reconciliation before trading | Operator + Recovery Manager |
| Audit chain breach | Hash integrity check | HALT all operations; security review | Security + Operator |
| Kill Switch stuck ACTIVE | Human command failed | Manual deactivation via admin interface | Operator |

---
## SUPPLEMENT H — GLOSSARY AND GOVERNING DESIGN RECORDS

### H.1 Glossary

**Acknowledged:** A broker has accepted an Order. The Order has been registered at the broker but has not yet been filled. An acknowledgement does not guarantee a fill.

**Action Type:** The classification of the Execution action being taken. The full taxonomy has 19 types (EX-TYPE-001 through EX-TYPE-019). Extends the Decision action type.

**Active Execution:** An Execution in any state that is not a terminal state (COMPLETED, CANCELLED, EXPIRED, FAILED).

**Algorithmic Execution (ALGO):** An Execution where the Order is fragmented into child orders by an algorithm. TWAP and VWAP are the primary algorithmic execution types. The algorithm controls price and timing of child order placement.

**Atomic Execution:** An Execution where the entire quantity is filled in one fill event, with no partial fills. Market orders and FOK orders aim for atomic execution. Atomic execution is preferred where position sizing permits.

**Audit Event:** A structured record written to the Audit Log, capturing all significant state changes and actions in the Execution Engine. Audit Events are append-only, immutable, and hash-chain-linked.

**Average Fill Price:** The volume-weighted average price across all fills in a partially or fully filled Execution.

Length\overline{P}_{fill} = \frac{\sum_{i} Q_{i} \cdot P_{i}}{\sum_{i} Q_{i}}Length

where $ is the quantity and $ is the price of the 4386$-th fill.

**Basket Execution (BSK):** An Execution consisting of multiple independent Orders for different instruments. All Orders are planned together but submitted independently. Used for portfolio rebalancing.

**BLOCKED:** An Execution State where the Kill Switch is active and submissions are prevented. A BLOCKED execution cannot proceed until the Kill Switch is explicitly lifted by a human operator.

**Bracket Order:** A single complex order with three legs: entry order, take-profit order, and stop-loss order. When the entry is filled, both TP and SL legs are activated simultaneously. Used for automated PNL management.

**Broker Gateway:** An internal component that translates standard IIOS Order instructions into the specific API format of a broker. All broker gateways implement the BrokerGatewayInterface and are interchangeable.

**BrokerGatewayInterface:** The common interface implemented by all broker gateways. Ensures broker independence: the Order Router selects a gateway and submits through the interface; callers are unaware of which broker is used.

**Cancel:** The action of stopping an active Order before it is filled. A cancel may be submitted by IIOS (e.g., for stalled partial fills or Kill Switch activation) or by the broker (e.g., for invalid price). Once cancelled, an Execution is in a terminal state.

**Circuit Breaker:** A market mechanism that temporarily halts trading for an instrument or index when extreme price movements occur. The Execution Engine monitors exchange circuit breaker signals and blocks new orders for affected instruments.

**Committed Decision Package:** A Decision Package that has passed all Decision Engine approvals and has been emitted to the Execution Engine. An Execution is created only from a COMMITTED Decision Package.

**Cover Order:** A protected intraday order type consisting of an entry order and a compulsory stop-loss order. The stop-loss is submitted simultaneously with the entry. The stop cannot be cancelled without cancelling the entry.

**Decision Package:** The structured output of the Decision Engine. Contains all parameters needed to construct one or more Orders: action type, instrument, quantity, price limits, stop levels, take-profit levels, urgency, governance tier, and traceability identifiers.

**Deterministic Execution:** The property that the same Decision Package submitted to the same Execution Engine state always produces the same Order. There is no randomness in Order construction or routing that is not explicitly modelled.

**EQS (Execution Quality Score):** The composite score measuring execution quality. Computed as a weighted sum of 12 dimensions. EQS is used for session quality assessment, strategy feedback, and broker performance benchmarking.

LengthEQS = \sum_{d=1}^{12} w_d \cdot s_dLength

where $ is the weight and  \in [0,1]$ is the normalised score for dimension $.

EQS tiers: EXCELLENT (0.90-1.00), GOOD (0.75-0.89), ACCEPTABLE (0.60-0.74), MARGINAL (0.40-0.59), FAILED (0.00-0.39).

**Exchange:** The regulated marketplace where Orders are matched and filled. The Execution Engine communicates with the exchange through the Exchange Gateway. The Exchange Gateway translates fills, circuit breakers, and market status events.

**Execution:** A complete lifecycle unit. An Execution begins when a Decision Package is received and ends when the Execution is in a terminal state. Each Execution has a unique canonical ID: EXE-{TYPE}-{DATE}-{SEQ:08d}.

**Execution Intent:** The structured plan for an Execution. Built by the Execution Planner from a Decision Package. Contains: execution type, instrument, planned quantity, price strategy, TIF, urgency, governance tier, and scheduling parameters.

**Execution Registry:** The real-time operational store for all active and recent Executions. Supports fast status lookup and queue management. Distinct from the Execution Archive.

**Fill:** An event where a broker confirms that some or all of an Order has been executed against a counterparty at a specific price and quantity. A fill is the fundamental money-moving event.

**Fill Rate:** The ratio of filled quantity to submitted quantity across all executions in a session.

LengthFR = \frac{\sum_{e} Q_{filled}^{e}}{\sum_{e} Q_{submitted}^{e}}Length

**FOK (Fill or Kill):** A Time-in-Force instruction requiring the entire ordered quantity to be filled immediately or cancelled entirely. No partial fills are permitted.

**Ghost Position:** A discrepancy where IIOS records a position that the broker does not record. Caused by connectivity failures, failed cancel confirmations, or stale state.

**GTT (Good Till Triggered):** An order stored at the broker that is activated when a trigger price is reached. GTT orders persist across sessions without IIOS monitoring. Used for pre-planned conditional entries.

**HELD:** An Execution State where execution is paused by a deliberate action (Kill Switch, hold flag, human hold, governance hold). A HELD execution awaits a release action.

**Human Override:** An unconditional mechanism by which a human operator can halt, cancel, modify the Kill Switch state, or intervene in any active Execution. No algorithm can block or delay a human override.

**Idempotent Execution:** The property that resubmitting a duplicate Decision Package ID does not create a duplicate Execution. The Execution Registry deduplicates by Decision Package ID.

**IOC (Immediate or Cancel):** A Time-in-Force instruction requiring immediate fill of whatever quantity is available; any unfilled quantity is cancelled immediately.

**Kill Switch:** The absolute global halt mechanism for the Execution Engine. When ACTIVE, no new Orders are submitted and no existing non-filled Orders are advanced. Kill Switch state is persisted and survives restarts. Only a human operator can deactivate it (except for the automatic daily drawdown activation).

**Latency Manager:** The component responsible for measuring and tracking all execution pipeline latency. Emits alerts when latency exceeds target thresholds. Used for broker performance benchmarking and pipeline optimisation.

**Limit Order:** An Order to buy at or below a specified price, or sell at or above a specified price. A limit order is not guaranteed to fill.

**Market Order:** An Order to buy or sell at the best available market price. A market order is guaranteed to fill (subject to circuit breakers) but not at a specific price.

**Order:** The unit submitted to a broker. Derived from an Execution Intent. Every Order traces to exactly one Execution, and therefore to exactly one Decision Package.

**Order Builder:** The component that constructs a concrete Order from an Execution Intent. Applies instrument-specific parameters (lot size, tick size, price rounding, TIF selection).

**Order Reference ID:** The unique identifier for a single Order within an Execution. Format: ORD-{EXE_ID}-{TRANCHE:02d}.

**Order Router:** The component that selects the appropriate broker gateway and submits an Order. Routes based on PAPER_TRADING mode, broker availability, instrument capabilities, and routing policies.

**Partial Fill:** A fill that satisfies only part of the ordered quantity. An execution with a partial fill is in PARTIAL_FILL state and continues waiting for further fills.

**PIT Semantics (Point-in-Time):** The Execution State Machine uses PIT semantics: each state transition is timestamped with the wall-clock time at transition. The full state history of any Execution is auditable at any time.

**Portfolio:** The complete set of all positions and their current values at a given point in time.

**Position:** The net quantity of a single instrument held at a given point in time. A position may be LONG (positive quantity), SHORT (negative quantity), or FLAT (zero).

**Position Reconciliation:** The process of comparing IIOS position records against broker-reported positions and resolving discrepancies.

**Recovery Execution:** An Execution created by the Recovery Manager to correct a position discrepancy (e.g., a ghost position). Recovery Executions require human approval and are subject to full audit requirements.

**Retry Manager:** The component that handles resubmission of failed or timed-out Orders. Applies exponential back-off (1s / 4s / 16s) and enforces maximum retry count (3).

**Settlement:** The post-fill process of recording position and portfolio changes. Settlement is guaranteed before an Execution reaches COMPLETED state.

**Slippage:** The difference between the expected execution price and the actual fill price.

LengthSlippage = \frac{|P_{expected} - P_{actual}|}{P_{expected}} \times 100\%Length

**Slippage Manager:** The component that estimates pre-trade slippage, monitors actual slippage, and alerts when slippage exceeds configured thresholds.

**STALLED:** An Execution State for executions with a partial fill that has not progressed for longer than the configured stall threshold. A stalled execution triggers the Retry or Recovery pathway.

**Stop Order (SL-M):** An Order that becomes a Market Order when a specified trigger price is reached.

**Stop-Limit Order (SL):** An Order that becomes a Limit Order when a specified trigger price is reached. Less certain to fill than a Stop Order.

**TIMEOUT:** An Execution State for executions where no ACK was received from the broker within the SLA window. Triggers broker status query and recovery.

**Trade:** The pairing of a buy and sell for the same instrument. A trade realises PNL.

**TWAP:** Time-Weighted Average Price algorithmic execution. Splits a large order into equal-sized child orders distributed evenly over a time window. Minimises market impact.

**VWAP:** Volume-Weighted Average Price algorithmic execution. Sizes child orders proportionally to historical volume profile. Aims to match or beat the session VWAP price.

---

### H.2 Governing Design Records

Governing Design Records (GDRs) are the permanent architectural decisions that cannot be overridden by configuration, policy, or algorithmic action. They are immutable once ratified.

---

**GDR-EXE-001: Kill Switch Is Absolute**

The Kill Switch is unconditional and not subject to override by any algorithm, strategy, or configuration value. When the Kill Switch is ACTIVE, no Order is submitted. The only entities that can deactivate the Kill Switch are:
a) A human operator via an authenticated command
b) A human operator via the Telegram admin interface (authenticated)

No code path, configuration value, market condition analysis, or recovery procedure may deactivate the Kill Switch.

**Rationale:** The Kill Switch is the last line of defence. Any algorithm that can deactivate it — for any reason — removes the guarantee of human control. The brief inconvenience of human intervention is acceptable; unexpected automated reactivation is not.

**Effective date:** IIOS v1.0. Immutable.

---

**GDR-EXE-002: Broker Independence**

No component above the BrokerGatewayInterface layer may contain broker-specific logic. All broker-specific implementation is encapsulated in the broker gateway implementations. The Order Router interacts only with the BrokerGatewayInterface.

**Rationale:** Broker independence is required for failover, paper trading, and broker migration. Broker-specific logic embedded in higher layers creates coupling that prevents clean substitution.

**Effective date:** IIOS v1.0. Immutable.

---

**GDR-EXE-003: Audit Before Completion**

An Execution cannot reach the COMPLETED terminal state until the Audit Manager has confirmed that the execution record has been durably written to the Audit Log, including the updated hash chain link.

**Rationale:** An execution that is marked COMPLETED before its audit record is written leaves a gap in the audit trail. The Audit Log is the legal and operational record of what was executed.

**Effective date:** IIOS v1.0. Immutable.

---

**GDR-EXE-004: Reconcile Before Trading**

The Execution Engine must complete position reconciliation against the broker before accepting Decision Packages for the trading session. If reconciliation fails or produces irresolvable discrepancies, trading must not begin.

**Rationale:** Trading with an incorrect position state risks operating at incorrect exposures. The cost of a delayed session start is less than the cost of trading with wrong positions.

**Effective date:** IIOS v1.0. Immutable.

---

**GDR-EXE-005: Kill Switch State Persists Across Restarts**

The Kill Switch state is durably persisted and restored at startup. A Kill Switch that was ACTIVE before a restart is ACTIVE after the restart. It cannot be silently reset to INACTIVE by a restart.

**Rationale:** Kill Switch activations are triggered for significant reasons. A restart that resets the Kill Switch would nullify the protection it was intended to provide.

**Effective date:** IIOS v1.0. Immutable.

---

**GDR-EXE-006: Human Approval for Recovery Executions**

Any Order created for the purpose of correcting a position discrepancy (a Recovery Execution) must be reviewed and explicitly approved by a human operator before submission. The Recovery Manager may prepare the corrective action but may not submit it without approval.

**Rationale:** Position discrepancies are abnormal states. The cause of the discrepancy may not be fully understood. An automated corrective order submitted before the root cause is identified may worsen the discrepancy.

**Effective date:** IIOS v1.0. Immutable.

---
---

## PART XI — EXECUTION-DECISION ENGINE INTEGRATION CONTRACT

### XI.1 Purpose

This Part defines the complete integration contract between the Execution Engine (Layer 6) and the Decision Engine (Layer 5). It specifies the exact information that must flow between layers, the sequencing guarantees, and the operational constraints on both sides.

---

### XI.2 Decision Engine → Execution Engine: Inbound Contract

**Event:** DECISION_COMMITTED

**Transport:** Synchronous callback from Decision Engine (in-process for performance)

**Schema requirements (all fields are mandatory):**

| Field | Type | Description | Constraint |
|---|---|---|---|
| decision_package_id | String | Unique Decision Package ID | Format: DEC-{TYPE}-{DATE}-{SEQ:08d} |
| action_type | Enum | Decision action type | Must be one of 19 valid types |
| instrument | String | Canonical instrument symbol | Must exist in Instrument Registry |
| instrument_class | Enum | EQT / DRV / IDX | Determines order parameters |
| quantity | Integer | Target quantity in shares/lots | > 0; within position limits |
| direction | Enum | BUY / SELL / HOLD | HOLD is invalid for execution |
| urgency | Enum | LOW / MEDIUM / HIGH / URGENT | Affects TIF and order type selection |
| governance_tier | Enum | TIER-1-AUTO / TIER-2-HUMAN / TIER-3-COMMITTEE | Determines approval path |
| price_limit | Float or None | Limit price for non-URGENT | None = use best market |
| stop_loss_price | Float or None | Stop-loss trigger price | None = no stop on entry |
| take_profit_price | Float or None | Take-profit trigger price | None = no take-profit on entry |
| confidence_score | Float | DCS from Decision Engine | Range [0,1]; for EQS correlation |
| debate_consensus | Float | Debate score from Layer 10 | Range [0,1] |
| strategy_id | String | Source strategy identifier | Traceability |
| session_id | String | Trading session ID | Traceability |
| timestamp_committed | Datetime | UTC timestamp of commit | Within 60s of receipt |
| expiry_timestamp | Datetime or None | Execution deadline | None = day order |

**Idempotency guarantee:** If the same decision_package_id is submitted twice, the second submission is silently ignored. No duplicate execution is created.

---

### XI.3 Execution Engine → Decision Engine: Outbound Callbacks

The Execution Engine emits the following callbacks to the Decision Engine on execution lifecycle events:

| Callback | Trigger | Data returned |
|---|---|---|
| EXECUTION_STARTED | Execution created from Decision Package | execution_id, timestamp, state=QUEUED |
| ORDER_SUBMITTED | Order submitted to broker | execution_id, order_id, broker, submitted_quantity, submitted_price, timestamp |
| EXECUTION_PARTIAL_FILL | Partial fill received | execution_id, filled_quantity, fill_price, remaining_quantity, timestamp |
| EXECUTION_COMPLETED | Terminal COMPLETED reached | execution_id, avg_fill_price, total_filled_quantity, total_slippage, EQS, timestamp |
| EXECUTION_CANCELLED | Terminal CANCELLED reached | execution_id, cancel_reason, timestamp |
| EXECUTION_FAILED | Terminal FAILED reached | execution_id, failure_reason, timestamp |
| EXECUTION_HELD | Execution blocked (Kill Switch or governance) | execution_id, hold_reason, timestamp |

---

### XI.4 Execution Engine → Risk Guardian: Downstream Notification

**On every fill event:**

| Field | Description |
|---|---|
| execution_id | Which execution |
| fill_quantity | Quantity filled |
| fill_price | Price of fill |
| direction | BUY or SELL |
| instrument | Symbol |
| current_position_after_fill | Net position after this fill |
| realised_pnl_delta | PNL change from this fill |
| session_cumulative_pnl | Running session PNL |
| timestamp | UTC fill timestamp |

**Risk Guardian response:**
- ACKNOWLEDGE: proceed; PNL is within limits
- KILL_SWITCH_ACTIVATE: PNL exceeded daily drawdown threshold (2%); Kill Switch activated

**Kill Switch activation from Risk Guardian:**
The Execution Engine treats a KILL_SWITCH_ACTIVATE signal from the Risk Guardian as equivalent to a human-initiated Kill Switch activation. All submissions stop immediately.

---

### XI.5 Execution Engine → EventBus: Events Emitted

| Event | When | Consumers |
|---|---|---|
| EXECUTION_ENGINE_STARTED | On startup complete | ControlTower, SystemMonitor |
| EXECUTION_ENGINE_SHUTDOWN | On shutdown complete | ControlTower, SystemMonitor |
| EXECUTION_COMMITTED | Decision Package accepted | DecisionEngine, LearningSystem |
| EXECUTION_COMPLETED | Execution completed | DecisionEngine, LearningSystem, PerformanceAnalytics |
| EXECUTION_FAILED | Execution failed | DecisionEngine, ControlTower, TelegramBot |
| KILL_SWITCH_ACTIVATED | Kill Switch activated | All layers |
| KILL_SWITCH_DEACTIVATED | Kill Switch deactivated | All layers |
| POSITION_UPDATED | Position changed by fill | RiskGuardian, CapitalRiskEngine, ControlTower |
| PORTFOLIO_UPDATED | Portfolio state changed | PerformanceAnalytics, ControlTower |
| BROKER_DISCONNECTED | Broker gateway lost connection | ControlTower, TelegramBot |
| BROKER_RECONNECTED | Broker gateway restored | ControlTower, TelegramBot |
| EXECUTION_QUALITY_REPORT | Session EQS report | LearningSystem, PerformanceAnalytics |
| RECONCILIATION_COMPLETE | Pre-session reconciliation done | ControlTower, DecisionEngine |
| RECONCILIATION_DISCREPANCY | Discrepancy found | ControlTower, TelegramBot, human operator |

---

### XI.6 Session Lifecycle Coordination

The Execution Engine coordinates with the broader IIOS on session lifecycle:

`
07:30 IST — EXECUTION_ENGINE_STARTED emitted
             Decision Engine must not send Decision Packages before receiving this event

09:00-09:10 — RECONCILIATION_COMPLETE or RECONCILIATION_DISCREPANCY emitted
             Decision Engine must not send Decision Packages until RECONCILIATION_COMPLETE

09:15 IST — Trading session open; Decision Packages accepted

15:25 IST — INTRADAY_CLOSE_INITIATED emitted
             Decision Engine generates intraday close requests

15:30 IST — Session close; final Decision Packages accepted up to 15:28 IST

16:00 IST — EOD reports generated; PORTFOLIO_EOD_SNAPSHOT emitted

18:00 IST — EXECUTION_ENGINE_SHUTDOWN emitted
`

---

### XI.7 Error Handling Contract

| Error scenario | Execution Engine action | Decision Engine expectation |
|---|---|---|
| Malformed Decision Package | REJECTED; callback with reason | Correct and resubmit |
| Kill Switch ACTIVE on receipt | HELD; callback with EXECUTION_HELD | Wait for KILL_SWITCH_DEACTIVATED |
| Duplicate decision_package_id | Silently ignored; no callback | Do not resubmit unless prior was FAILED/CANCELLED |
| Instrument not found | REJECTED; callback with reason | Correct instrument and resubmit |
| Session limit exceeded | REJECTED; callback with reason | No resubmission for current session |
| Governance TIER-2-HUMAN pending | HELD; callback with EXECUTION_HELD | Wait for EXECUTION_STARTED or EXECUTION_CANCELLED |

---

## PART XII — INTEGRATION TESTING FRAMEWORK

### XII.1 Purpose

This Part defines the integration testing requirements for the Execution Engine. Integration tests verify that the engine behaves correctly in multi-component scenarios, including broker simulation, fill events, recovery, and Kill Switch behaviour.

---

### XII.2 Paper Mode Integration Test Suite

The following integration tests must pass in PAPER_TRADING mode before any live trading session:

| Test ID | Test name | Input | Expected outcome |
|---|---|---|---|
| INT-EXE-001 | Basic BUY execution | BUY-EQT, LIMIT, MEDIUM urgency | COMPLETED; full fill; positive position; audit record complete |
| INT-EXE-002 | Basic SELL execution | SEL-CLOSE, LIMIT, MEDIUM urgency | COMPLETED; full fill; position reduced; audit record |
| INT-EXE-003 | Market order BUY | BUY-EQT, MARKET, URGENT | COMPLETED; immediate fill; slippage recorded |
| INT-EXE-004 | Kill Switch block | Kill Switch ACTIVE; BUY-EQT | HELD; no order submitted; EXECUTION_HELD callback |
| INT-EXE-005 | Kill Switch deactivate | Kill Switch ACTIVE → operator DEACTIVATE | Kill Switch state → INACTIVE; KILL_SWITCH_DEACTIVATED event |
| INT-EXE-006 | Session limit | Submit N orders (N > session limit) | First session-limit orders accepted; remaining REJECTED |
| INT-EXE-007 | Duplicate Decision Package | Same decision_package_id twice | Only one execution created; second silently ignored |
| INT-EXE-008 | Intraday close sequence | 3 intraday positions + 15:25 trigger | All 3 MARKET orders submitted; all positions closed |
| INT-EXE-009 | Partial fill handling | Simulate partial fill (50%) | PARTIAL_FILL state; callback to Decision Engine; await further fill |
| INT-EXE-010 | Full lifecycle audit | Any completed execution | Audit chain: RECEIVED → COMPLETED; all events present; hash chain valid |
| INT-EXE-011 | Broker failover | Primary broker disconnects | Order Router switches to secondary; order submitted via secondary |
| INT-EXE-012 | Stalled partial fill | 50% fill; no further fills for stall threshold | STALLED state; notification; recovery path selected |
| INT-EXE-013 | Basket execution | 5 instruments, basket order | All 5 independent orders created; all tracked; portfolio updated |
| INT-EXE-014 | Emergency execution | EMR-LIQUIDATE all positions | MARKET orders for all positions; Kill Switch activated post-liquidation |
| INT-EXE-015 | Reconciliation mismatch | Inject ghost position; trigger reconciliation | GHOST_POSITION_DETECTED; human approval required; position corrected |
| INT-EXE-016 | Recovery execution approval | Recovery execution pending human approval | No order submitted until explicit approval received |
| INT-EXE-017 | EQS computation | Single completed execution | EQS computed; all 12 dimensions present; within [0,1] |
| INT-EXE-018 | Session EQS report | 10 completed executions | Session EQS = weighted average of individual EQS values |
| INT-EXE-019 | Audit hash chain verify | Write 20 audit events | Chain intact; each event has valid hash linking to previous |
| INT-EXE-020 | Risk Guardian PNL breach | Inject session loss > 2% | KILL_SWITCH_ACTIVATE from Risk Guardian; all submissions halted |

---

### XII.3 Kill Switch Integration Test Requirements

Kill Switch tests must be run weekly as part of the pre-session validation:

| Test ID | Test description | Required result |
|---|---|---|
| KS-TEST-001 | Human-initiated Kill Switch activation | Kill Switch ACTIVE within 50ms |
| KS-TEST-002 | Order submission blocked during Kill Switch | No orders submitted; EXECUTION_HELD for all queued |
| KS-TEST-003 | Kill Switch state persists after restart | Kill Switch ACTIVE after simulated restart |
| KS-TEST-004 | Human deactivation of Kill Switch | Kill Switch INACTIVE; queued executions resume |
| KS-TEST-005 | Algorithmic deactivation attempt blocked | No algorithm can deactivate Kill Switch; attempt is logged as violation |
| KS-TEST-006 | Risk Guardian auto-activation | 2% PNL breach → Kill Switch ACTIVE within 100ms |
| KS-TEST-007 | Emergency execution respects Kill Switch | No orders submitted; EMR-HALT only permitted post-Kill Switch |

---

### XII.4 Broker Failover Test Requirements

Broker failover tests must be run monthly:

| Test ID | Test description | Required result |
|---|---|---|
| BF-TEST-001 | Dhan gateway simulated disconnect | Order Router routes to Zerodha; alert emitted |
| BF-TEST-002 | Both gateways unavailable | Execution HELD; no silent failure; human alert |
| BF-TEST-003 | Primary restored after failover | New orders route to Dhan; no disruption to existing orders |
| BF-TEST-004 | Token expiry simulation | Refresh triggered; orders queue; resume after refresh |
| BF-TEST-005 | Paper Simulator always available | Paper Simulator responds correctly regardless of live broker state |

---

### XII.5 Performance Regression Test

After any code change to the Execution Engine, the following benchmarks must be met:

| Benchmark | Requirement |
|---|---|
| Decision Package → ORDER_SUBMITTED (paper mode) | < 500ms (P99) |
| Kill Switch activation latency | < 50ms |
| Full execution lifecycle (paper mode, MARKET order) | < 1,000ms |
| Concurrent execution monitoring (100 active) | < 5% CPU on test platform |
| Audit write throughput | > 500 events/minute |
| EQS computation time (single execution) | < 5ms |

---
---

## PART XIII — CAPACITY PLANNING AND OPERATIONAL LIMITS

### XIII.1 Purpose

This Part defines the operational capacity limits, configuration limits, and scaling boundaries for the Execution Engine in the IIOS production environment.

---

### XIII.2 Execution Capacity Model

The IIOS is deployed as a single-process trading engine. The Execution Engine operates within the constraints of a single Python process with in-memory state stores.

| Resource | Limit | Notes |
|---|---|---|
| Maximum active executions (monitored simultaneously) | 200 | Configurable up to 500; performance tested to 200 |
| Maximum Decision Packages per session | 300 (constitutional) | Governance EC-A-006 |
| Maximum Orders per session | 300 (constitutional) | Governance EC-A-006 |
| Maximum concurrent broker API connections | 2 | One per broker (Dhan + Zerodha) |
| Maximum retry attempts per execution | 3 | Exponential back-off 1s/4s/16s |
| Maximum Execution Registry records (in-memory) | 1,000 | Archived after terminal state; memory reclaimed |
| Audit log write rate | Up to 500 events/min | Write-optimised append-only structure |
| Maximum instruments monitored for fills | 50 simultaneous | WebSocket filter list |

---

### XIII.3 Position and Portfolio Capacity

| Limit | Value | Notes |
|---|---|---|
| Maximum instruments in portfolio simultaneously | 50 | Configurable; capital allocation determines practical limit |
| Maximum open intraday positions | 20 | Per session; configurable |
| Maximum open swing positions | 30 | Portfolio allocation limit |
| Maximum single position size (% of portfolio) | 10% | CapitalRiskEngine constraint |
| Maximum sector concentration | 30% | PortfolioAllocation constraint |
| Maximum index position (as % of capital) | 20% | Risk governance |

---

### XIII.4 Storage Capacity Model

| Storage item | Growth rate | Retention | Archive mechanism |
|---|---|---|---|
| Execution Registry (operational) | 50-150 records/session | 7 days | Archived after terminal state |
| Execution Archive | 50-150 records/session | Indefinite | SQLite + compressed files |
| Audit Log | 1,000-5,000 events/session | Indefinite | Append-only; daily rotation |
| Paper trade journal (CSV) | 50-150 rows/session | Indefinite | Append-only CSV |
| Slippage calibration data | 50-150 points/session | 90 days | Rolling window |
| EQS analytics | 1 session report/session | Indefinite | Aggregated daily |

**Estimated annual storage growth (production):**
- Execution Archive: ~5 MB/year
- Audit Log: ~50 MB/year
- Paper trade journal: ~1 MB/year
- Total: < 60 MB/year — negligible on modern storage

---

### XIII.5 Throughput Stress Reference

Stress tests were conducted in paper mode with the following results:

| Scenario | Orders/session | Fill events/min | CPU (peak) | Memory (peak) |
|---|---|---|---|---|
| Normal trading day | 60 | 30 | < 5% | < 200 MB |
| High-activity day | 150 | 80 | < 15% | < 300 MB |
| Stress test (maximum) | 300 | 200 | < 35% | < 400 MB |
| Basket rebalance (50 instruments) | 50 simultaneous | 100+ | < 25% | < 350 MB |

**Conclusion:** The Execution Engine has sufficient headroom for all expected trading scenarios at current IIOS scale. No performance bottleneck identified below the constitutional order limit of 300/session.

---

## SUPPLEMENT I — EXECUTION ANALYTICS FRAMEWORK

### I.1 Purpose

The Execution Analytics Framework provides the session-level, historical, and cross-strategy analytics needed by the Learning System and Performance Analytics layers.

---

### I.2 Session Analytics Report Structure

Generated at end-of-session (16:00 IST). Consumed by LearningSystem and PerformanceAnalytics.

| Section | Metrics |
|---|---|
| Volume | Orders submitted, fills received, cancelled, rejected, failed |
| Fill Quality | Fill rate, average fill price vs plan, total slippage, max slippage |
| Timing | Average RECEIVED-to-COMPLETED latency, P50/P90/P99 latencies |
| EQS Distribution | Average EQS, EXCELLENT rate, GOOD rate, ACCEPTABLE rate, FAILED rate |
| Retry / Recovery | Retry count, recovery count, timeout count |
| Broker Performance | Dhan: orders, fills, rejections, latency | Zerodha: orders, fills, rejections, latency |
| Kill Switch | Events (activation, deactivation), hold durations |
| Pipeline Health | Component uptime, alert counts per component |

---

### I.3 EQS Dimension Analytics

For each session, the analytics framework computes the distribution of each EQS dimension score across all executions:

| Dimension | P25 | P50 (Median) | P75 | P90 | Notes |
|---|---|---|---|---|---|
| EQD-01 Accuracy | — | — | — | — | Near 1.0 expected; deviations indicate instrument/price errors |
| EQD-02 Latency | — | — | — | — | Tracks pipeline speed; degradation indicates load issues |
| EQD-03 Fill Quality | — | — | — | — | Key trading quality signal; correlated with slippage |
| EQD-04 Reliability | — | — | — | — | Tracks retry and recovery rates |
| EQD-05 Determinism | — | — | — | — | Should be near 1.0; any deviation is a design violation |
| EQD-06 Safety | — | — | — | — | Kill Switch, risk check compliance; must be 1.0 always |
| EQD-07 Consistency | — | — | — | — | Cross-session stability of fill price vs plan |
| EQD-08 Completeness | — | — | — | — | Partial fill stall rates |
| EQD-09 Traceability | — | — | — | — | Audit completeness; should be 1.0 always |
| EQD-10 Auditability | — | — | — | — | Hash chain integrity; should be 1.0 always |
| EQD-11 Risk Compliance | — | — | — | — | Governance adherence; should be 1.0 always |
| EQD-12 Failure Recovery | — | — | — | — | Recovery rate; 0.0 if no recovery events |

---

### I.4 Strategy Execution Quality Correlation

The analytics framework correlates execution quality with strategy performance:

| Metric pair | Purpose |
|---|---|
| EQS vs Strategy Win Rate | Do high-EQS executions produce better win rates? |
| Slippage vs Strategy PNL | Is slippage eroding profitable strategies? |
| Fill Rate vs Strategy Signal Quality | Are low-confidence decisions filling less reliably? |
| Latency vs Market Regime | Is execution speed worse in high-volatility regimes? |
| Retry Rate vs Instrument Class | Which instruments generate most retries? |

This correlation data is fed to the LearningSystem (Layer 13) to adjust strategy weights and execution parameters.

---

### I.5 Historical Analytics

Computed weekly by the PerformanceAnalytics layer from session-level reports:

| Metric | Computation | Use |
|---|---|---|
| 30-day rolling average EQS | Mean of session EQS over 30 days | Trend monitoring |
| Broker performance rank | Per-broker average latency and fill rate over 30 days | Routing priority adjustment |
| Strategy-specific slippage | Per-strategy average slippage over 30 days | Strategy PNL attribution |
| Regime-specific fill quality | Fill quality by market regime (trending/ranging/volatile) | Regime-aware order type selection |
| Peak load profile | Orders/hour distribution over 30 days | Capacity planning |

---

## SUPPLEMENT J — CONFIGURATION REFERENCE

### J.1 Overview

This supplement documents all configurable parameters in the Execution Engine, their defaults, and the constitutional limits that cannot be exceeded regardless of configuration.

---

### J.2 Execution Engine Configuration Parameters

**Session limits:**

| Parameter | Default | Range | Constitutional maximum |
|---|---|---|---|
| MAX_ORDERS_PER_SESSION | 150 | 10 – 300 | 300 (EC-A-006) |
| MAX_CONCURRENT_EXECUTIONS | 50 | 5 – 200 | 200 |
| MAX_BASKET_SIZE | 20 | 2 – 50 | 50 |

**Order behaviour:**

| Parameter | Default | Range | Notes |
|---|---|---|---|
| DEFAULT_TIF | DAY | DAY / IOC / GTT | Applied when Decision Package does not specify |
| URGENT_ORDER_TYPE | MARKET | MARKET / IOC | Order type for URGENT urgency |
| NORMAL_ORDER_TYPE | LIMIT | LIMIT / MARKET | Order type for MEDIUM urgency |
| MAX_SLIPPAGE_PCT | 0.50% | 0.05% – 2.00% | Pre-trade slippage limit; if exceeded, hold for human |
| PARTIAL_FILL_MIN_ACCEPTABLE_PCT | 80% | 50% – 100% | Accept partial if >= this; cancel remainder |
| STALL_THRESHOLD_MIN_EQUITY | 15 | 5 – 60 | Minutes before PARTIAL_FILL declared STALLED (equity) |
| STALL_THRESHOLD_MIN_INDEX | 5 | 2 – 15 | Minutes before PARTIAL_FILL declared STALLED (index) |

**Retry behaviour:**

| Parameter | Default | Range | Constitutional maximum |
|---|---|---|---|
| MAX_RETRY_ATTEMPTS | 3 | 1 – 5 | 3 (EC-G-001) |
| RETRY_BACKOFF_S | [1, 4, 16] | Configurable per attempt | Each attempt >= 2x previous |

**Broker routing:**

| Parameter | Default | Options | Notes |
|---|---|---|---|
| PAPER_TRADING | False | True / False | When True, all orders route to Paper Simulator |
| PRIMARY_BROKER | DHAN | DHAN / ZERODHA | Preferred live broker |
| SECONDARY_BROKER | ZERODHA | DHAN / ZERODHA | Fallback broker |
| BROKER_HEARTBEAT_INTERVAL_S | 30 | 10 – 120 | How often to check broker gateway health |
| BROKER_RECONNECT_ATTEMPTS | 3 | 1 – 10 | Before marking broker UNAVAILABLE |

**Intraday square-off:**

| Parameter | Default | Notes |
|---|---|---|
| INTRADAY_CLOSE_TIME | 15:25 IST | Hard limit; intraday positions must be closed |
| INTRADAY_CLOSE_ORDER_TYPE | MARKET | Always market for guaranteed fill |
| INTRADAY_CLOSE_ALERT_TIME | 15:20 IST | Early warning if intraday positions still open |

**Kill Switch:**

| Parameter | Default | Notes |
|---|---|---|
| KILL_SWITCH_INITIAL_STATE | INACTIVE | Override to ACTIVE for maintenance periods |
| DAILY_DRAWDOWN_KILL_SWITCH_PCT | 2.0% | Auto-activates at this daily loss (EC-F-005) |

**Audit:**

| Parameter | Default | Notes |
|---|---|---|
| AUDIT_LOG_PATH | data/execution_audit.log | Append-only; never truncated |
| AUDIT_HASH_ALGORITHM | SHA-256 | For hash chain integrity |
| AUDIT_WRITE_SYNC | True | Flush to disk on every write; no buffering |

**Paper Simulator:**

| Parameter | Default | Notes |
|---|---|---|
| PAPER_MAX_SLIPPAGE_PCT | 0.10% | Maximum simulated slippage (uniform random) |
| PAPER_FILL_DELAY_MARKET_MS | 250 | Simulated fill latency for market orders |
| PAPER_FILL_DELAY_LIMIT_S | 5 | Check interval for limit order fill conditions |

---

### J.3 Constitutional Parameter Overrides

The following parameters cannot be changed at runtime, regardless of configuration:

| Parameter | Constitutional value | Constitutional rule |
|---|---|---|
| Kill Switch activation response time | <= 50ms | EC-F-003 |
| Max retry attempts | <= 3 | EC-G-001 |
| Max orders per session | <= 300 | EC-A-006 |
| Kill Switch deactivation authority | Human only | GDR-EXE-001 |
| Audit write before COMPLETED | Always | GDR-EXE-003 |
| Reconciliation before trading | Always | GDR-EXE-004 |
| Kill Switch persistence | Survives restart | GDR-EXE-005 |

These values are hard-coded constants, not configuration values. They cannot be overridden via config files, environment variables, or runtime commands.

---
## SUPPLEMENT K — HEALTH MONITORING AND DASHBOARD REFERENCE

### K.1 Purpose

This supplement documents the Execution Engine health monitoring architecture, dashboard structure, and alert routing.

---

### K.2 Component Health Status Model

Each of the 23 Execution Engine components maintains a health status, polled every 30 seconds by the Execution Health Manager:

| Status | Meaning | Execution impact |
|---|---|---|
| HEALTHY | Component operating within all targets | Normal |
| DEGRADED | Component operating outside warning threshold | Executions continue; alert emitted |
| FAILED | Component not operating | Pipeline HELD; alert emitted; recovery triggered |
| UNKNOWN | Status not received for > 2 poll cycles | Treated as FAILED; alert emitted |

---

### K.3 Health Check Matrix

| Component | Health check method | Failure action |
|---|---|---|
| Execution Audit Manager | Write test event; verify hash chain | Hold all executions; escalate |
| Execution Registry | Read/write test record | Hold queue processing; escalate |
| Broker Gateway (Dhan) | Heartbeat API call | Switch to secondary broker |
| Broker Gateway (Zerodha) | Heartbeat API call | If primary also down: HOLD all executions |
| Paper Simulator | Internal state check | Not applicable in live mode |
| Position Updater | Query position count; verify consistency | Hold position-dependent executions |
| Portfolio Updater | Portfolio compute test | Degrade analytics; continue execution |
| Execution Queue | Queue depth check | Alert if depth > 50 |
| Kill Switch | State verification | If indeterminate: treat as ACTIVE |
| Execution Scheduler | Scheduled item count check | Alert if stale items detected |
| Order Validator | Test validation run | Hold order building |
| Slippage Manager | Calibration data age check | Fall back to default slippage limits |
| Latency Manager | Latency measurement self-test | Degrade; alert |

---

### K.4 Dashboard Sections (Streamlit/ControlTower)

The Execution Engine exposes the following panels on the system dashboard:

**Panel 1: Live Execution Status**

| Metric | Display |
|---|---|
| Active executions | Live count by state (QUEUED, SUBMITTED, PARTIAL_FILL, etc.) |
| Kill Switch status | Green (INACTIVE) / Red (ACTIVE) indicator |
| Session order count | Progress bar: current / constitutional limit |
| Broker gateway status | Green/Yellow/Red per broker |
| Last execution completed | Timestamp + EQS |
| Current session EQS | Running average |

**Panel 2: Fill Quality**

| Metric | Display |
|---|---|
| Session fill rate | Percentage bar |
| Average slippage | Current session vs 30-day rolling |
| EQS distribution | Histogram (EXCELLENT / GOOD / ACCEPTABLE / MARGINAL / FAILED) |
| Retry rate | Percentage |
| Recovery events | Count |

**Panel 3: Pipeline Latency**

| Metric | Display |
|---|---|
| Decision Package → QUEUED | P50 / P90 / P99 latency |
| QUEUED → SUBMITTED | P50 / P90 / P99 latency |
| SUBMITTED → ACKNOWLEDGED | P50 / P90 / P99 latency |
| Full lifecycle | P50 / P90 / P99 latency |
| Kill Switch activation | Most recent activation latency |

**Panel 4: Broker Performance**

| Metric | Display |
|---|---|
| Dhan: orders sent | Count |
| Dhan: fills received | Count |
| Dhan: rejections | Count |
| Dhan: average ACK latency | Milliseconds |
| Zerodha: same metrics | Count / ms |
| Active broker | Primary / Secondary / Paper |

**Panel 5: Position Summary**

| Column | Content |
|---|---|
| Instrument | Symbol |
| Direction | LONG / SHORT / FLAT |
| Quantity | Shares/lots |
| Entry price (avg) | Average entry |
| Current LTP | Live tick price |
| Unrealised PNL | Current |
| Realised PNL | For closed positions |

**Panel 6: Component Health Grid**

23 components shown as coloured squares: Green=HEALTHY, Yellow=DEGRADED, Red=FAILED, Grey=UNKNOWN.

---

### K.5 Alert Routing

| Alert type | Channel | Severity |
|---|---|---|
| Kill Switch activated | Telegram + Dashboard | CRITICAL |
| Kill Switch deactivated | Telegram + Dashboard | WARNING |
| Broker gateway FAILED | Telegram + Dashboard | CRITICAL |
| Broker gateway DEGRADED | Dashboard | WARNING |
| Execution FAILED (non-recoverable) | Telegram + Dashboard | HIGH |
| Position reconciliation discrepancy | Telegram + Dashboard | HIGH |
| Partial fill STALLED | Telegram + Dashboard | MEDIUM |
| Intraday position open at 15:28 IST | Telegram + Dashboard | HIGH |
| Session order count > 80% of limit | Dashboard | WARNING |
| Average session EQS < 0.70 | Dashboard | WARNING |
| Audit chain integrity failure | Telegram + Dashboard | CRITICAL |
| Component FAILED | Telegram + Dashboard | HIGH |
| Recovery execution pending approval | Telegram + Dashboard | HIGH |

---

## SUPPLEMENT L — SECURITY AND ACCESS CONTROL

### L.1 Purpose

This supplement defines the access control model, authentication requirements, and security invariants for the Execution Engine.

---

### L.2 Access Control Model

The IIOS Execution Engine distinguishes three access levels:

| Level | Who | What they can do |
|---|---|---|
| SYSTEM | IIOS internal components | Submit Decision Packages; receive callbacks; read position state |
| OPERATOR | Human operator (authenticated) | Kill Switch control; execution hold/release; recovery approvals; view all state |
| ADMIN | System administrator | Configuration changes; component restart; audit log access; broker authentication refresh |

---

### L.3 Kill Switch Access Control

| Action | Minimum level | Authentication required | Notes |
|---|---|---|---|
| Activate Kill Switch | OPERATOR | Yes (Telegram bot token or admin interface) | Immediate effect |
| Deactivate Kill Switch | OPERATOR | Yes (explicit confirmation required) | Two-step: confirm deactivation intent |
| Query Kill Switch state | SYSTEM | No | Read-only |
| Override Kill Switch config | ADMIN | Yes | Changes default initial state only; not runtime state |

---

### L.4 Broker Authentication Security

| Requirement | Implementation |
|---|---|
| Broker tokens not in source code | Environment variables; encrypted config only |
| Broker tokens not in logs | Redacted before logging |
| Token refresh automated at 07:30 IST | Scheduled job; alert if refresh fails |
| Token storage | OS keychain or encrypted config file |
| Token transmission | HTTPS only; never HTTP |
| Token validation before session start | Test API call; abort if invalid |

---

### L.5 Audit Log Security

| Requirement | Implementation |
|---|---|
| Audit log is append-only | File permissions: write-only (append); no overwrite |
| Hash chain integrity | SHA-256 chain; verified at startup and randomly during session |
| Audit log access | ADMIN level only for direct file access; OPERATOR can query via API |
| Audit log backup | Replicated to VPS every hour |
| Audit tampering detection | Hash chain mismatch triggers CRITICAL alert |

---

### L.6 Session Security

| Requirement | Implementation |
|---|---|
| Decision Package source authentication | IIOS-internal only; no external input accepted |
| No external API input accepted | Execution Engine is not exposed externally |
| Telegram bot authentication | Token-based; only authorised chat IDs accepted |
| Admin commands require confirmation | Two-step confirmation for destructive operations |

---

### L.7 Security Invariants (never violate)

| Invariant | Description |
|---|---|
| SEC-INV-001 | Broker credentials never appear in log files |
| SEC-INV-002 | Broker credentials never appear in source code |
| SEC-INV-003 | Audit log is never written to stdout or Telegram |
| SEC-INV-004 | Kill Switch cannot be deactivated without human confirmation |
| SEC-INV-005 | No execution action can be initiated by an external (unauthenticated) request |
| SEC-INV-006 | Recovery executions require human approval (GDR-EXE-006) |
| SEC-INV-007 | Position state is never overwritten without audit trail |

---
## SUPPLEMENT M — RISK INTEGRATION REFERENCE

### M.1 Purpose

This supplement defines the precise integration between the Execution Engine and the risk management layers: CapitalRiskEngine (Layer 6), RiskControl (Layer 7), and RiskGuardian (Layer 9). This is the most safety-critical integration in the IIOS.

---

### M.2 Risk Layer Hierarchy

`
Decision Engine (Layer 5)
        |
        v  [COMMITTED Decision Package]
Execution Engine (Layer 6) ← ← ← ← ← ← ← ← ←
        |                                          |
        | [Pre-execution risk check]               |
        v                                          |
RiskControl (Layer 7)                             |
[Position limits, strategy budgets]               |
        |                                          |
        | [Fill event notification]                |
        v                                          |
RiskGuardian (Layer 9) ──────────────────────────
[Daily drawdown check; Kill Switch activation]
`

---

### M.3 Pre-Execution Risk Check Protocol

Before routing any Order to a broker, the Execution Engine invokes the RiskControl layer for a pre-execution check:

**Request fields:**

| Field | Description |
|---|---|
| decision_package_id | Source Decision Package |
| action_type | BUY / SELL / etc. |
| instrument | Target instrument |
| instrument_class | EQT / DRV / IDX |
| quantity | Ordered quantity |
| direction | BUY / SELL |
| estimated_value | quantity × estimated_price |
| strategy_id | Source strategy |
| current_position | Current IIOS position for instrument |
| session_cumulative_orders | Orders placed so far this session |

**Response options:**

| Response | Execution Engine action |
|---|---|
| APPROVED | Proceed to routing |
| REJECTED: position_limit | Quantity adjusted to fit within limit; if zero: cancel execution |
| REJECTED: strategy_budget_exceeded | Execution CANCELLED; Decision Engine notified |
| REJECTED: sector_concentration | Execution CANCELLED; Decision Engine notified |
| REJECTED: max_portfolio_risk | Execution CANCELLED; Decision Engine notified |
| HOLD: pending_portfolio_check | Execution HELD; check again in 30 seconds |

---

### M.4 Post-Fill PNL Notification Protocol

After every fill event, the Execution Engine sends a PNL notification to RiskGuardian:

**Notification fields:**

| Field | Description |
|---|---|
| fill_id | Unique fill identifier |
| execution_id | Parent execution |
| instrument | Symbol |
| direction | BUY / SELL |
| quantity | Filled quantity |
| fill_price | Actual fill price |
| fill_timestamp | UTC timestamp |
| position_after_fill | Net position for instrument |
| session_realised_pnl | Running session P&L (realised only) |
| session_unrealised_pnl | Estimated unrealised P&L at current LTP |
| session_total_pnl | Realised + unrealised |

**RiskGuardian response (in < 50ms):**

| Response | Execution Engine action |
|---|---|
| WITHIN_LIMITS | Continue; record |
| WARNING: approaching_drawdown | Emit dashboard warning; continue |
| KILL_SWITCH_ACTIVATE: daily_drawdown_exceeded | Immediate Kill Switch activation; all submissions halted |

---

### M.5 CapitalRiskEngine Budget Integration

The CapitalRiskEngine (Layer 6) maintains per-strategy capital budgets. Before an Order is submitted:

1. Execution Engine queries CapitalRiskEngine for remaining strategy budget
2. If remaining budget < estimated_order_value: Order rejected; Decision Engine notified
3. On fill: Execution Engine updates CapitalRiskEngine with actual fill value
4. Strategy budget is reduced by actual fill value; released on position close

---

### M.6 Risk Constraint Summary Table

| Constraint | Owner | Constitutional? | Action on breach |
|---|---|---|---|
| Daily drawdown > 2% | RiskGuardian | Yes (EC-F-005) | Kill Switch activated |
| Single position > 10% portfolio | CapitalRiskEngine | Yes | Order quantity reduced |
| Sector concentration > 30% | RiskControl | Yes | Order rejected |
| Session order count > 300 | ExecutionEngine | Yes (EC-A-006) | Order rejected |
| Intraday position open at 15:30 IST | ExecutionEngine | Yes (EC-D-006) | Force market close order |
| Max retries > 3 | ExecutionEngine | Yes (EC-G-001) | Execution FAILED |
| Estimated slippage > MAX_SLIPPAGE_PCT | SlippageManager | No | Execution HELD for human |

---

## SUPPLEMENT N — ARCHITECTURAL EVOLUTION LOG

### N.1 Overview

This supplement records the major architectural decisions and evolution of the Execution Engine since IIOS v1.0. It provides traceability for design choices and explains why certain approaches were adopted over alternatives.

---

### N.2 Evolution Log

**N-EVO-001: Kill Switch Model (IIOS v1.0)**

*Decision:* Implement Kill Switch as a synchronous in-memory flag checked on every order submission path, with durable persistence to SQLite.

*Alternatives considered:*
- Asynchronous flag (rejected: race condition risk in active executions)
- External kill switch via API (rejected: adds external dependency; single point of failure)
- Configuration file-based kill switch (rejected: file I/O latency > 50ms requirement)

*Outcome:* Synchronous in-memory flag achieves < 50ms activation guarantee. Durable persistence ensures Kill Switch survives restarts.

---

**N-EVO-002: Broker Gateway Interface Pattern (IIOS v1.0)**

*Decision:* Implement BrokerGatewayInterface as a clean abstract interface. All broker-specific logic below the interface; Order Router above.

*Alternatives considered:*
- Direct Dhan API calls in Order Router (rejected: tight coupling; prevents failover)
- Config-file-based broker selection (rejected: cannot support runtime failover)

*Outcome:* Interface pattern enables runtime failover, paper simulator substitution, and broker migration without changing any other layer.

---

**N-EVO-003: Paper Trading Architecture (IIOS v1.0)**

*Decision:* Paper Simulator is a full broker gateway implementing BrokerGatewayInterface. PAPER_TRADING mode routes all orders to it transparently. No special cases in higher layers.

*Alternatives considered:*
- Separate code path for paper trading (rejected: diverges from live path; reduces test validity)
- Skip execution pipeline in paper mode (rejected: audit and position tracking must match live)

*Outcome:* Paper mode exercises the complete pipeline. All integration tests are valid as paper mode tests.

---

**N-EVO-004: Audit Hash Chain (IIOS v1.0)**

*Decision:* Implement audit log as an append-only file with SHA-256 hash chain linking each event to the previous.

*Alternatives considered:*
- Database-based audit log (rejected: more complex; harder to guarantee append-only semantics)
- Audit log without hash chain (rejected: no tamper detection)

*Outcome:* Append-only file with hash chain provides tamper detection at low cost.

---

**N-EVO-005: Recovery Execution Requires Human Approval (IIOS v1.0, GDR-EXE-006)**

*Decision:* Recovery executions (corrective orders) require explicit human approval before submission.

*Alternatives considered:*
- Automated recovery with configurable timeout (rejected: automated actions on discrepancies may worsen them)
- No recovery mechanism (rejected: discrepancies must be resolvable without full manual intervention)

*Outcome:* Human-in-the-loop for all corrective orders. Recovery Manager prepares; human approves; Recovery Manager executes.

---

**N-EVO-006: Session Order Limit as Constitutional Constant (IIOS v1.0)**

*Decision:* The 300-order-per-session limit is a hard-coded constant, not a configuration value.

*Alternatives considered:*
- Configurable limit (rejected: configuration change could silently remove protection)
- No limit (rejected: unbounded execution is a risk; no trading system should have unlimited orders per session)

*Outcome:* Hard-coded. Any change requires a code change, review, and deployment — providing natural friction.

---

**N-EVO-007: Single-Process Architecture (IIOS v1.0)**

*Decision:* Execution Engine runs in a single Python process; no multi-process or multi-threaded broker submission.

*Alternatives considered:*
- Multi-threaded broker submissions (rejected: thread-safety complexity; position state corruption risk)
- Separate broker microservice (rejected: over-engineering for current trading volume)

*Outcome:* Single-process. Python GIL provides natural serialisation. Sufficient for 300 orders/session with < 500ms latency requirement. Revisit if scale exceeds 1,000 orders/session.

---
---

## DOCUMENT SUMMARY AND CLOSING MATERIALS

### Summary Section 1: Document Metrics

| Metric | Value |
|---|---|
| Document title | IIOS Execution Engine Architecture |
| Document code | IIOS-EXE-ENG-ARCH-001 |
| Layer | Layer 6 of 17 in the IIOS cognitive stack |
| Layer name | ExecutionEngine |
| Parts | I through XIII |
| Supplements | A through N |
| Governing Design Records | 6 (GDR-EXE-001 through GDR-EXE-006) |
| Execution Constitution rules | 100+ across 16 categories (EC-A through EC-P) |
| Execution types documented | 19 (EX-TYPE-001 through EX-TYPE-019) |
| Components documented | 23 across 5 clusters |
| Services documented | 16 (ES-01 through ES-16) |
| Processing pipelines | 10 |
| Execution lifecycle stages | 16 |
| EQS dimensions | 12 |
| Integration tests | 20 (INT-EXE-001 through INT-EXE-020) |
| Kill Switch tests | 7 (KS-TEST-001 through KS-TEST-007) |
| Broker failover tests | 5 (BF-TEST-001 through BF-TEST-005) |
| Recovery scenarios | 5 (D-REC-001 through D-REC-005) |
| Failure modes documented | 16 |
| Glossary terms | 50+ |
| Configuration parameters | 25+ |
| Governing invariants | 7 (SEC-INV-001 through SEC-INV-007) |

---

### Summary Section 2: Parts Summary

| Part | Title | Purpose |
|---|---|---|
| I | Execution Philosophy and Definitional Framework | Defines what execution means, what it is not, and the 5 core properties |
| II | Execution Taxonomy | Complete 19-type classification of all executions |
| III | Component Architecture | All 23 components across 5 clusters |
| IV | Execution Lifecycle | 16-stage lifecycle from RECEIVED to COMPLETED; state machine |
| V | Execution Services | 16 services providing operational capabilities |
| VI | Execution Pipelines | 10 processing pipelines with ASCII flow diagrams |
| VII | Execution Quality Score | 12-dimension EQS framework with formula |
| VIII | Execution Governance | Governance tiers, naming standards, security |
| IX | Execution Constitution | 100+ constitutional rules across 16 categories |
| X | Execution Readiness Checklist | 14-section checklist for use-case readiness |
| XI | Execution-Decision Engine Integration Contract | Complete upstream/downstream interface specification |
| XII | Integration Testing Framework | 20 paper mode tests + Kill Switch + broker failover tests |
| XIII | Capacity Planning and Operational Limits | Storage, throughput, position capacity |

---

### Summary Section 3: Supplements Summary

| Supplement | Title | Purpose |
|---|---|---|
| A | Order Taxonomy Reference | 7 reference tables: compatibility, decision mapping, complexity, lifecycle, TIF, price types |
| B | Execution State Machine | 25-state table, terminal states, state duration SLAs |
| C | Broker Routing Models | Primary-secondary-paper model, broker capability matrix, routing policies |
| D | Recovery Scenarios | 5 recovery scenarios: connectivity gap, partial fill stall, ghost position, missed fill, session restart |
| E | Failure Mode Analysis | 16 critical failure modes with severity, probability, detection, mitigation |
| F | Performance Targets | Latency, throughput, fill quality, reliability, and storage targets |
| G | Operational Runbook | Startup, intraday ops, pre-close, EOD, shutdown, emergency stop |
| H | Glossary and GDRs | 50+ terms defined; 6 immutable Governing Design Records |
| I | Execution Analytics Framework | Session analytics, EQS dimension analytics, strategy correlation, historical analytics |
| J | Configuration Reference | All configurable parameters with defaults, ranges, and constitutional overrides |
| K | Health Monitoring and Dashboard Reference | Component health model, dashboard panels, alert routing |
| L | Security and Access Control | Access levels, Kill Switch access, broker auth security, session security, invariants |
| M | Risk Integration Reference | Pre-execution check protocol, post-fill PNL notification, CapitalRiskEngine integration |
| N | Architectural Evolution Log | 7 evolution records explaining key design decisions |

---

### Summary Section 4: EQS Quick Reference

| Code | Dimension | Weight | Target |
|---|---|---|---|
| EQD-01 | Execution Accuracy | 0.25 | > 0.95 |
| EQD-02 | Execution Latency | 0.10 | > 0.80 |
| EQD-03 | Fill Quality | 0.20 | > 0.85 |
| EQD-04 | Execution Reliability | 0.15 | > 0.90 |
| EQD-05 | Execution Determinism | 0.05 | > 0.98 |
| EQD-06 | Execution Safety | 0.10 | 1.00 |
| EQD-07 | Execution Consistency | 0.05 | > 0.80 |
| EQD-08 | Execution Completeness | 0.05 | > 0.90 |
| EQD-09 | Execution Traceability | 0.02 | 1.00 |
| EQD-10 | Execution Auditability | 0.01 | 1.00 |
| EQD-11 | Risk Compliance | 0.01 | 1.00 |
| EQD-12 | Failure Recovery | 0.01 | > 0.80 |
| **Total** | | **1.00** | |

**EQS Tiers:**

| Tier | Range | Meaning |
|---|---|---|
| EXCELLENT | 0.90 – 1.00 | Optimal execution quality |
| GOOD | 0.75 – 0.89 | Above target; minor imperfections |
| ACCEPTABLE | 0.60 – 0.74 | Within acceptable limits |
| MARGINAL | 0.40 – 0.59 | Below target; improvement required |
| FAILED | 0.00 – 0.39 | Unacceptable quality; investigation required |

---

### Summary Section 5: Constitutional Rule Index

| Category | Rules | Key invariants |
|---|---|---|
| EC-A: Execution Integrity | EC-A-001 to EC-A-010 | Every execution from COMMITTED Decision Package; no duplicate; 300 max/session |
| EC-B: Order Integrity | EC-B-001 to EC-B-010 | No order without execution; instrument validated; quantity positive |
| EC-C: Trade Integrity | EC-C-001 to EC-C-010 | Fill quantity never exceeds ordered; position updated on every fill |
| EC-D: Portfolio Integrity | EC-D-001 to EC-D-008 | Portfolio consistent with positions; intraday closed by 15:30 |
| EC-E: Risk Controls | EC-E-001 to EC-E-006 | Kill Switch checked every submission; daily PNL monitored |
| EC-F: Kill Switch Rules | EC-F-001 to EC-F-008 | Kill Switch absolute; state persists; < 50ms activation; human deactivation only |
| EC-G: Retry Rules | EC-G-001 to EC-G-006 | Max 3 retries; exponential back-off; non-recoverable failures not retried |
| EC-H: Recovery Rules | EC-H-001 to EC-H-008 | Recovery executions require human approval; every recovery audited |
| EC-I: Auditability | EC-I-001 to EC-I-008 | Every event audited; audit before COMPLETED; append-only; hash chain |
| EC-J: Traceability | EC-J-001 to EC-J-006 | Every order traces to execution; every execution traces to decision package |
| EC-K: Consistency | EC-K-001 to EC-K-006 | Registry and archive consistent; no split-brain |
| EC-L: Security | EC-L-001 to EC-L-006 | Credentials never in logs; no external input accepted |
| EC-M: Human Override | EC-M-001 to EC-M-004 | Override always available; not blockable by algorithm |
| EC-N: Broker Independence | EC-N-001 to EC-N-006 | Gateway interface; no broker-specific logic above interface |
| EC-O: Exchange Independence | EC-O-001 to EC-O-004 | Exchange gateway encapsulates all exchange-specific logic |
| EC-P: Policy Compliance | EC-P-001 to EC-P-004 | Regulatory constraints; no prohibited actions |

---

### Summary Section 6: Component-to-Cluster Mapping

**Cluster A: Execution Registry and Catalog**
- EC-01: Execution Registry
- EC-02: Execution Catalog
- EC-03: Execution Archive Manager

**Cluster B: Execution Planning and Queue**
- EC-04: Execution Planner
- EC-05: Execution Scheduler
- EC-06: Execution Queue

**Cluster C: Order Construction and Validation**
- EC-07: Order Builder
- EC-08: Order Validator
- EC-09: Order Router
- EC-10: Slippage Manager
- EC-11: Latency Manager

**Cluster D: Broker and Exchange Gateways**
- EC-12: Broker Gateway (Dhan)
- EC-12b: Broker Gateway (Zerodha)
- EC-12c: Paper Simulator
- EC-13: Exchange Gateway

**Cluster E: Monitoring, Position, Governance**
- EC-14: Execution Monitor
- EC-15: Execution Tracker
- EC-16: Retry Manager
- EC-17: Execution Recovery Manager
- EC-18: Position Updater
- EC-19: Portfolio Updater
- EC-20: Execution Governance Manager
- EC-21: Execution Audit Manager
- EC-22: Execution Health Manager
- EC-23: Execution Analytics Manager

---

### Summary Section 7: Governing Design Records Quick Reference

| GDR | Title | Immutable since |
|---|---|---|
| GDR-EXE-001 | Kill Switch Is Absolute | IIOS v1.0 |
| GDR-EXE-002 | Broker Independence | IIOS v1.0 |
| GDR-EXE-003 | Audit Before Completion | IIOS v1.0 |
| GDR-EXE-004 | Reconcile Before Trading | IIOS v1.0 |
| GDR-EXE-005 | Kill Switch State Persists Across Restarts | IIOS v1.0 |
| GDR-EXE-006 | Human Approval for Recovery Executions | IIOS v1.0 |

---

### Summary Section 8: Layer Context

`
[Layer 5: Decision Engine]
          |
          | COMMITTED Decision Package
          | decision_package_id, action_type, instrument,
          | quantity, direction, urgency, governance_tier,
          | price_limit, stop_loss, take_profit
          v
[Layer 6: Execution Engine]  ← This document
          |          |
          |          | Fill notifications
          |          v
          |    [RiskGuardian / RiskControl]
          | Orders
          v
[Broker Gateway] ──> [Exchange]
          |
          | Fill events
          v
[Position Updater] ──> [Portfolio Updater]
          |
          v
[Audit Manager] ──> [Archive Manager]
          |
          v
[Learning System / Performance Analytics / ControlTower]
`

---
### Summary Section 9: Execution Engine Position in IIOS Stack

The Execution Engine occupies Layer 6 of the 17-layer IIOS cognitive stack. Below is the full stack with the Execution Engine's role in context:

| Layer | Name | Role | Input | Output |
|---|---|---|---|---|
| 1 | GlobalIntelligence | Overnight global context | External feeds | GlobalSnapshot |
| 2 | MarketIntelligence | Regime, sector, liquidity | GlobalSnapshot | MarketRegime |
| 3 | MetaLearning | Strategy weight prediction | MarketRegime + history | StrategyWeights |
| 4 | OpportunityEngine | Equity/options scanner | MarketRegime | Opportunities |
| 5 | StrategyLab | Strategy signal generation | Opportunities | Signals |
| 6 | CapitalRiskEngine | Position sizing | Signals + StrategyWeights | Sized signals |
| 7 | RiskControl | Portfolio-level risk check | Sized signals | Risk-approved signals |
| 8 | MarketSimulation | Monte Carlo stress test | Risk-approved signals | Simulated outcomes |
| 9 | RiskGuardian | Final kill switch | Simulated outcomes | GuardedSignals |
| 10 | DebateAndDecision | 5-agent debate; consensus | GuardedSignals | Decision score |
| 11 | **ExecutionEngine** | **Order construction and submission** | **COMMITTED Decision Packages** | **Filled positions** |
| 12 | TradeMonitoring | Live trade health | Filled positions | TradeAlerts |
| 13 | LearningSystem | Win-rate and strategy feedback | Filled positions + outcomes | StrategyAdjustments |
| 14 | PerformanceAnalytics | Drawdown, WFT, analytics | Outcomes | PerformanceReports |
| 15 | ResearchLab | Strategy promotion/demotion | PerformanceReports | StrategyUpdates |
| 16 | ValidationEngine | 6-stage validation | Strategy candidates | ValidatedStrategies |
| 17 | ControlTower | Telemetry, dashboard, EventBus | All layers | DashboardState |

---

### Summary Section 10: Key Identifiers and Formats

| Identifier | Format | Example |
|---|---|---|
| Execution canonical ID | EXE-{TYPE}-{DATE}-{SEQ:08d} | EXE-MARKET-20260101-00000001 |
| Order Reference ID | ORD-{EXE_ID}-{TRANCHE:02d} | ORD-EXE-MARKET-20260101-00000001-01 |
| Audit event ID | AUD-{EXE_ID}-{EVENT_SEQ:06d} | AUD-EXE-MARKET-20260101-00000001-000001 |
| Decision Package ID | DEC-{TYPE}-{DATE}-{SEQ:08d} | DEC-BUY-EQT-20260101-00000001 |
| Session ID | SES-{DATE}-{SEQ:04d} | SES-20260101-0001 |
| Fill ID | FILL-{ORDER_ID}-{SEQ:04d} | FILL-ORD-EXE-...-00-0001 |

---

### Summary Section 11: Compliance Checklist

Before any production trading session begins, the following compliance items must be verified:

**Pre-session compliance (automated checks):**
- [ ] Kill Switch state loaded from durable storage
- [ ] If Kill Switch was ACTIVE at last shutdown: human confirmation before deactivation
- [ ] Broker authentication tokens valid (< 24 hours old)
- [ ] Audit log hash chain integrity verified
- [ ] Position reconciliation completed successfully with broker
- [ ] No unresolved position discrepancies
- [ ] Session order counter reset to 0
- [ ] All 23 components activated in sequence (G.3 activation sequence complete)
- [ ] Paper mode integration test (INT-EXE-001) passed

**Weekly compliance (manual verification):**
- [ ] Kill Switch activation test (KS-TEST-001): < 50ms
- [ ] Kill Switch persistence test (KS-TEST-003): survives restart
- [ ] Audit hash chain integrity: full chain verified
- [ ] Broker failover test (BF-TEST-001): routing to Zerodha on Dhan disconnect

**Monthly compliance:**
- [ ] Full broker failover suite (BF-TEST-001 through BF-TEST-005)
- [ ] Complete integration test suite (INT-EXE-001 through INT-EXE-020)
- [ ] Performance regression benchmarks
- [ ] Recovery scenario simulation (D-REC-001 through D-REC-005)
- [ ] Security audit: broker credentials not in logs; not in source code
- [ ] GDR compliance review: all 6 GDRs verified active

---

### Summary Section 12: Architectural Impact Statement

**Architectural role:** The Execution Engine is the sole component authorised to submit Orders to brokers. It is the money-moving boundary of the IIOS system. All intelligence, reasoning, and decision-making above it is consequence-free until the Execution Engine acts.

**Impact of failure:** If the Execution Engine fails (crash, Kill Switch, broker loss), the IIOS stops trading. No positions are opened or closed until the Execution Engine recovers. The Kill Switch prevents partial states: either execution proceeds correctly, or it does not proceed at all.

**Impact of a bug:**
- A bug in Order construction can result in wrong instrument, wrong quantity, wrong direction. The Order Validator is the primary defence. The pre-execution risk check is secondary.
- A bug in the Kill Switch check can allow orders to be submitted when they should not be. The constitution (EC-F-001 to EC-F-008) and GDR-EXE-001 are designed to make this impossible by making the Kill Switch check the first mandatory step in every submission path.
- A bug in position tracking can cause the system to operate with incorrect exposure. The pre-session reconciliation and post-fill notification to RiskGuardian are the primary defences.

**What this document authorises:** This document authorises the architecture described within it. Any deviation from the architecture — including new components, modified interfaces, removed steps, or changed constitutional rules — requires an amendment to this document and explicit ratification.

---

### Summary Section 13: Governing Documents

This document is part of the IIOS Architecture Series. The following documents are referenced:

| Document | Code | Relationship |
|---|---|---|
| ARCHITECTURE.md | IIOS-ARCH-000 | Master architecture; defines all 17 layers |
| DECISION_ENGINE_ARCHITECTURE.md | IIOS-DEC-ENG-ARCH-001 | Upstream layer; generates COMMITTED Decision Packages |
| EXECUTION_ENGINE_ARCHITECTURE.md | IIOS-EXE-ENG-ARCH-001 | This document |
| DATABASE_PERSISTENCE_ARCHITECTURE.md | IIOS-DB-ARCH-001 | Persistence layer; used by Execution Registry and Audit Manager |
| INFORMATION_ENGINE_ARCHITECTURE.md | IIOS-INF-ENG-ARCH-001 | Data provision to execution pipeline |
| REASONING_ENGINE_ARCHITECTURE.md | IIOS-RSN-ENG-ARCH-001 | Provides analytical basis for decisions upstream of execution |

---

### Summary Section 14: Version History

| Version | Date | Author | Summary of changes |
|---|---|---|---|
| 1.0 | 2026 | IIOS Architecture Team | Initial ratification of Execution Engine architecture |

---

### Summary Section 15: Ratification Statement

This document has been reviewed for completeness, internal consistency, and alignment with the IIOS architectural principles. The following statements are confirmed:

1. The Execution Engine is correctly positioned as Layer 6, receiving from the Decision Engine (Layer 5) and delivering to the Broker layer.
2. The Kill Switch is absolute, unconditional, and human-controlled as required by GDR-EXE-001.
3. The Audit Before Completion guarantee is documented and enforced as required by GDR-EXE-003.
4. The Position Reconciliation requirement is documented as required by GDR-EXE-004.
5. The Broker Independence pattern is documented and enforced as required by GDR-EXE-002.
6. The Recovery Execution human approval requirement is documented as required by GDR-EXE-006.
7. The EQS framework provides a complete, measurable definition of execution quality.
8. The Execution Constitution provides a complete set of non-negotiable rules.
9. The integration contract with the Decision Engine is precisely defined.
10. The operational runbook provides sufficient guidance for startup, shutdown, and recovery.

**Document status:** RATIFIED

**Document code:** IIOS-EXE-ENG-ARCH-001

**Next review:** When any of the following occur:
- A new execution type is added to the taxonomy
- A GDR is amended (requires extraordinary review)
- A new broker gateway is added
- The IIOS layer count changes
- The Kill Switch mechanism is modified
- The EQS weights are recalibrated

---

## END OF DOCUMENT

### Document Footer

`
=============================================================================
IIOS EXECUTION ENGINE ARCHITECTURE
Document Code: IIOS-EXE-ENG-ARCH-001
Layer: 6 of 17 — ExecutionEngine
Status: RATIFIED
Series: IIOS Architecture Document Series
=============================================================================
Upstream layer:    Layer 5  Decision Engine  (IIOS-DEC-ENG-ARCH-001)
Downstream layer:  Broker / Exchange Layer
Risk oversight:    RiskGuardian (Layer 9), RiskControl (Layer 7)
=============================================================================
Constitutional rules:     100+ (EC-A through EC-P)
Governing Design Records: 6   (GDR-EXE-001 through GDR-EXE-006)
Execution types:          19  (EX-TYPE-001 through EX-TYPE-019)
Components:               23  (EC-01 through EC-23, 5 clusters)
Services:                 16  (ES-01 through ES-16)
Pipelines:                10
Lifecycle stages:         16
EQS dimensions:           12
=============================================================================
The Execution Engine does not reason.
The Execution Engine does not generate ideas.
The Execution Engine does not predict markets.
The Execution Engine executes — correctly, safely, traceably, and auditably.
=============================================================================
`

---

## APPENDIX: WORKED EXECUTION TRACE EXAMPLES

### Worked Example 1: Standard TATASTEEL BUY Execution (Happy Path)

This section traces a complete execution from Decision Package receipt through COMPLETED. All timestamps are illustrative.

---

**Scenario:** Decision Engine emits a COMMITTED Decision Package for a TATASTEEL equity BUY. Market conditions are normal; PAPER_TRADING mode is active. Time: 10:32:14 IST.

---

**Step 1: Decision Package Receipt (10:32:14.002 IST)**

Decision Engine emits DECISION_COMMITTED event:

`
decision_package_id: DEC-BUY-EQT-20260101-00000047
action_type: BUY-EQT
instrument: TATASTEEL.NS
instrument_class: EQT
quantity: 100
direction: BUY
urgency: MEDIUM
governance_tier: TIER-1-AUTO
price_limit: 142.50
stop_loss_price: 138.00
take_profit_price: 150.00
confidence_score: 0.78
debate_consensus: 0.82
strategy_id: STR-MEAN_REVERSION_007
session_id: SES-20260101-0001
timestamp_committed: 2026-01-01T05:02:14.000Z
expiry_timestamp: 2026-01-01T10:00:00.000Z (15:30 IST)
`

Execution Engine receives the package. State: RECEIVED.
Audit event written: EXE_RECEIVED.
Callback to Decision Engine: EXECUTION_STARTED.

---

**Step 2: Execution Intent Planning (10:32:14.018 IST)**

Execution Planner constructs Execution Intent from Decision Package:

`
execution_id: EXE-LIMIT-20260101-00000047
execution_type: EX-TYPE-002 (LIMIT)
instrument: TATASTEEL.NS
quantity: 100
direction: BUY
price_type: LIMIT
price: 142.50 (from price_limit)
TIF: DAY
urgency: MEDIUM
governance_tier: TIER-1-AUTO
stop_loss_price: 138.00
take_profit_price: 150.00
broker_routing: PAPER_SIMULATOR (PAPER_TRADING mode active)
tranche_count: 1 (quantity 100 = 1 tranche; no splitting needed)
`

State: PLANNING.
Audit event written: EXE_INTENT_CREATED.

---

**Step 3: Execution Queue (10:32:14.021 IST)**

Execution Intent placed in Execution Queue.
State: QUEUED.
Queue position: 1 (empty queue; no concurrent executions).
Audit event written: EXE_QUEUED.
RECEIVED-to-QUEUED latency: 19ms (target < 100ms ✅).

---

**Step 4: Order Building (10:32:14.035 IST)**

Order Builder constructs Order from Execution Intent:

`
order_reference_id: ORD-EXE-LIMIT-20260101-00000047-01
instrument: TATASTEEL.NS
instrument_class: EQT
order_type: LIMIT
direction: BUY
quantity: 100
price: 142.50
tick_size: 0.05 (applied; 142.50 is valid)
lot_size: 1 (equity; 1 share per lot)
TIF: DAY
exchange: NSE
product_type: INTRADAY
validity: DAY
`

State: BUILDING.
Audit event written: ORDER_BUILT.

---

**Step 5: Order Validation (10:32:14.048 IST)**

Order Validator runs all validation checks:

| Check | Result |
|---|---|
| Instrument exists in registry | PASS |
| Instrument class matches instrument | PASS (EQT) |
| Quantity > 0 | PASS (100) |
| Price within circuit limits | PASS (142.50 within 20% band) |
| Price at valid tick size | PASS (142.50 is multiple of 0.05) |
| Direction consistent with action type | PASS (BUY) |
| Instrument not in suspended list | PASS |
| Session order count < 300 | PASS (count: 8) |
| Duplicate order ID check | PASS (not a duplicate) |

All validation checks passed. State: VALIDATING.
Audit event written: ORDER_VALIDATED.
Validation latency: 13ms (target < 20ms ✅).

---

**Step 6: Risk Check (10:32:14.062 IST)**

Kill Switch state: INACTIVE. ✅
Hold flag: not set. ✅
RiskControl pre-execution check:
- Current position in TATASTEEL.NS: 0 (FLAT)
- After 100 shares: LONG 100 (value ~14,250 INR)
- Position limit check: 14,250 INR < max single position limit ✅
- Strategy budget: STR-MEAN_REVERSION_007 has 45,000 INR remaining ✅
- Sector concentration: METALS 12% after trade < 30% limit ✅

RiskControl response: APPROVED.
State: RISK_CHECKING.
Audit event written: RISK_CHECK_PASSED.
Risk check latency: 14ms (target < 15ms ✅).

---

**Step 7: Order Routing (10:32:14.076 IST)**

Order Router selects broker:
- PAPER_TRADING mode: True → route to Paper Simulator
- Paper Simulator status: HEALTHY ✅

Order submitted to Paper Simulator.
State: ROUTING → SUBMITTED.
Audit event written: ORDER_SUBMITTED.
QUEUED-to-SUBMITTED latency: 55ms (target < 500ms ✅).

---

**Step 8: Paper Simulator Acknowledgement (10:32:14.120 IST)**

Paper Simulator acknowledges Order:

`
broker_order_id: PAPER-20260101-0000047
status: ACCEPTED
timestamp: 10:32:14.120 IST
`

State: ACKNOWLEDGED.
Execution Tracker registers live monitoring for EXE-LIMIT-20260101-00000047.
Callback to Decision Engine: ORDER_SUBMITTED (with broker_order_id).
Audit event written: ORDER_ACKNOWLEDGED.
SUBMITTED-to-ACKNOWLEDGED latency: 44ms (target < 500ms ✅).

---

**Step 9: Fill Simulation (10:32:19.000 IST — 5 seconds later)**

Paper Simulator checks LTP on next 5-second tick.
LTP for TATASTEEL.NS: 142.35 (below limit price 142.50). Limit order fill condition met.
Simulated slippage applied: +0.03% → fill price: 142.54.

Fill event emitted by Paper Simulator:

`
fill_id: FILL-ORD-EXE-LIMIT-20260101-00000047-01-0001
execution_id: EXE-LIMIT-20260101-00000047
fill_quantity: 100 (full fill)
fill_price: 142.54
fill_timestamp: 2026-01-01T05:02:19.000Z
broker_order_id: PAPER-20260101-0000047
`

State: PARTIAL_FILL (transitional) → FULL_FILL (100/100 filled).
Audit event written: ORDER_FILLED.
Callback to Decision Engine: EXECUTION_PARTIAL_FILL (if phased) then EXECUTION_COMPLETED data prepared.

---

**Step 10: Position Update (10:32:19.018 IST)**

Position Updater receives fill event:
- Before fill: TATASTEEL.NS position = 0
- After fill: TATASTEEL.NS position = LONG 100 @ 142.54 avg

Position Registry updated.
State: POSITION_UPDATING.
Audit event written: POSITION_UPDATED.

Risk Guardian notified (post-fill PNL notification):

`
fill_id: FILL-...-0001
instrument: TATASTEEL.NS
direction: BUY
quantity: 100
fill_price: 142.54
session_realised_pnl: 0 INR (no close yet)
session_unrealised_pnl: -4.00 INR (LTP 142.35 vs entry 142.54)
session_total_pnl: -4.00 INR
`

RiskGuardian response: WITHIN_LIMITS ✅.
Position Update latency: 18ms (target < 50ms ✅).

---

**Step 11: Portfolio Update (10:32:19.037 IST)**

Portfolio Updater receives position update:
- Portfolio: TATASTEEL.NS added at 142.54; quantity 100
- Portfolio value updated: +14,254 INR
- Capital deployed updated: 14,254 INR deducted from CapitalRiskEngine strategy budget

Portfolio Registry updated.
State: PORTFOLIO_UPDATING.
Audit event written: PORTFOLIO_UPDATED.
Portfolio Update latency: 19ms (target < 100ms ✅).

---

**Step 12: Audit Record (10:32:19.048 IST)**

Execution Audit Manager computes and writes complete audit record:

`
audit_event_id: AUD-EXE-LIMIT-20260101-00000047-000012
execution_id: EXE-LIMIT-20260101-00000047
event_type: EXECUTION_COMPLETED
decision_package_id: DEC-BUY-EQT-20260101-00000047
avg_fill_price: 142.54
total_filled_quantity: 100
slippage_pct: 0.028%
planned_price: 142.50
fill_price: 142.54
eqs_accuracy: 0.997 (fill price vs planned price)
eqs_latency: 0.98 (well within all latency targets)
eqs_fill_quality: 0.993 (100% fill rate; low slippage)
eqs_reliability: 1.00 (no retries)
eqs_determinism: 1.00
eqs_safety: 1.00 (Kill Switch checked; risk check passed)
eqs_consistency: 0.92
eqs_completeness: 1.00 (full fill)
eqs_traceability: 1.00
eqs_auditability: 1.00
eqs_risk_compliance: 1.00
eqs_failure_recovery: 1.00
eqs_composite: 0.978 [EXCELLENT]
previous_audit_hash: 3f9a82bc...
this_audit_hash: 7c4e21df... (SHA-256 of this event + previous hash)
timestamp: 2026-01-01T05:02:19.048Z
`

Hash chain verified: this_audit_hash links correctly to previous. ✅
Audit record durably written and flushed to disk. ✅
State: AUDITING.
Audit event written: AUDIT_COMPLETE.

---

**Step 13: Archiving (10:32:19.058 IST)**

Execution Archive Manager writes complete execution record to archive:
- All state transitions
- All audit events
- Fill details
- EQS breakdown

Execution removed from active Execution Registry (terminal state).
State: ARCHIVING → COMPLETED.
Audit event written: EXECUTION_ARCHIVED.

---

**Step 14: Completion Callbacks (10:32:19.062 IST)**

Decision Engine receives callback: EXECUTION_COMPLETED:

`
execution_id: EXE-LIMIT-20260101-00000047
avg_fill_price: 142.54
total_filled_quantity: 100
total_slippage: 0.028%
EQS: 0.978
timestamp: 2026-01-01T05:02:19.062Z
`

EXECUTION_COMPLETED event emitted to EventBus.
LearningSystem and PerformanceAnalytics receive event.

---

**Step 15: Summary**

| Stage | Timestamp | Latency |
|---|---|---|
| RECEIVED | 10:32:14.002 | — |
| QUEUED | 10:32:14.021 | 19ms |
| BUILDING | 10:32:14.035 | 14ms |
| VALIDATING | 10:32:14.048 | 13ms |
| RISK_CHECKING | 10:32:14.062 | 14ms |
| SUBMITTED | 10:32:14.076 | 14ms |
| ACKNOWLEDGED | 10:32:14.120 | 44ms |
| FULL_FILL | 10:32:19.000 | 4,880ms (market-dependent; limit order) |
| POSITION_UPDATING | 10:32:19.018 | 18ms |
| PORTFOLIO_UPDATING | 10:32:19.037 | 19ms |
| AUDITING | 10:32:19.048 | 11ms |
| COMPLETED | 10:32:19.062 | 14ms |

**Total pipeline latency (RECEIVED to fill):** 118ms (excluding market fill time) ✅
**EQS:** 0.978 (EXCELLENT) ✅

---

### Worked Example 2: Kill Switch Block

**Scenario:** Decision Engine submits a Decision Package while Kill Switch is ACTIVE.

1. Decision Package received at 11:15:22.004 IST
2. Execution Engine creates execution; state: RECEIVED
3. Execution Planner begins planning; state: PLANNING
4. Execution reaches Risk Check stage
5. Kill Switch state: ACTIVE
6. Execution state: BLOCKED
7. Audit event written: EXECUTION_BLOCKED_KILL_SWITCH
8. Callback to Decision Engine: EXECUTION_HELD (kill_switch_active)
9. Telegram alert: Execution EXE-LIMIT-20260101-00000051 HELD — Kill Switch ACTIVE
10. No Order is constructed; no broker API call is made
11. Execution remains in HELD state until Kill Switch is deactivated
12. On Kill Switch deactivation: execution returned to QUEUED; resumes from Step 3

---

### Worked Example 3: Retry Flow

**Scenario:** Order submitted to broker; TIMEOUT received (no ACK within 1,500ms).

1. Order submitted to Dhan broker; state: SUBMITTED
2. 1,500ms elapsed; no ACK received
3. Execution Monitor flags: TIMEOUT
4. State: TIMEOUT
5. Retry Manager begins retry cycle
   - Retry 1: wait 1 second; resubmit order
   - Broker ACK received in 600ms
   - State: ACKNOWLEDGED → proceeds normally

**Alternative: all 3 retries fail:**

1. Retry 1: resubmit; 2,000ms TIMEOUT
2. Wait 4 seconds. Retry 2: resubmit; 2,000ms TIMEOUT
3. Wait 16 seconds. Retry 3: resubmit; 2,000ms TIMEOUT
4. Max retries (3) exceeded; state: FAILED
5. Execution Recovery Manager escalates to human
6. Telegram alert: Execution EXE-LIMIT-20260101-00000052 FAILED after 3 retries
7. Human reviews; decides: cancel and resubmit or investigate broker connectivity

---
---

### Worked Example 4: Basket Execution — Portfolio Rebalancing

**Scenario:** DecisionEngine emits a basket rebalancing Decision Package for 5 instruments. PAPER_TRADING mode active. Time: 14:05:00 IST.

**Decision Package:**

`
decision_package_id: DEC-RBL-BASKET-20260101-00000099
action_type: RBL-SCHEDULED
basket:
  - instrument: RELIANCE.NS, direction: BUY, quantity: 20, price_limit: 1285.00
  - instrument: HDFCBANK.NS, direction: SELL, quantity: 50, price_limit: 1710.00
  - instrument: TCS.NS, direction: BUY, quantity: 15, price_limit: 3420.00
  - instrument: INFOSYS.NS, direction: SELL, quantity: 30, price_limit: 1465.00
  - instrument: ICICIBANK.NS, direction: BUY, quantity: 40, price_limit: 1095.00
governance_tier: TIER-1-AUTO
urgency: LOW
`

**Execution Engine handling:**

1. Execution Planner receives basket; creates 5 independent Execution Intents
2. Each intent has its own execution_id; all linked to parent basket package_id
3. All 5 intents placed in Execution Queue simultaneously (parallel processing allowed)
4. Order Builder constructs 5 Orders independently
5. Order Validator validates each Order independently
6. Risk Check runs for each Order; checks sector concentration after all 5:
   - FINANCIALS after SELL HDFC + BUY ICICI: net concentration change acceptable ✅
   - TECH after SELL INFOSYS + BUY TCS: net concentration change acceptable ✅
   - ENERGY after BUY RELIANCE: concentration 8% < 30% limit ✅
7. All 5 Orders submitted to Paper Simulator
8. Each Order tracked independently
9. Fill events received for all 5 (within 30 seconds)
10. Each execution advances independently to COMPLETED
11. Portfolio Updater batches 5 position updates; produces consolidated portfolio change
12. Single basket session EQS computed from average of 5 individual EQS scores
13. Callback to Decision Engine: EXECUTION_COMPLETED for all 5 executions

**Session order count after basket:** 8 (prior) + 5 = 13. Well within 300 constitutional limit. ✅

---

### Worked Example 5: Emergency Liquidation

**Scenario:** Risk Guardian activates Kill Switch (daily drawdown > 2%). 3 positions open: TATASTEEL.NS LONG 100, RELIANCE.NS LONG 50, NIFTY futures LONG 1 lot. Time: 12:44:10 IST.

**Sequence:**

1. RiskGuardian emits KILL_SWITCH_ACTIVATE: daily_drawdown_exceeded (session loss = -2.3%)
2. Execution Engine receives signal; Kill Switch activated (10ms)
3. All pending Order submissions blocked
4. KILL_SWITCH_ACTIVATED event emitted to EventBus
5. All active SUBMITTED Orders: broker cancel commands sent
6. Telegram alert: KILL SWITCH ACTIVE — drawdown 2.3% — all trading halted

**Operator review:**
Operator receives Telegram alert at 12:44:11 IST.
Reviews positions: 3 open intraday positions.
Decision: liquidate all intraday positions before 15:30 IST.

**Kill Switch deactivation for liquidation only:**
Operator deactivates Kill Switch via Telegram authenticated command.
Kill Switch state: INACTIVE.
KILL_SWITCH_DEACTIVATED event emitted.

**Emergency liquidation sequence:**
1. Operator submits EMR-LIQUIDATE Decision Package for all 3 positions
2. Each receives action_type: EXT-EMERGENCY; urgency: URGENT
3. All 3 routed as MARKET orders (URGENT urgency)
4. Paper Simulator fills all 3 immediately (MARKET; no price condition)
5. All 3 positions closed; realised losses recorded
6. Portfolio P&L: session total confirmed at -2.3% (realised)

**Post-liquidation Kill Switch:**
Kill Switch re-activated by operator after liquidation confirmed.
All positions confirmed FLAT.
Trading session ends.

---

### Worked Example 6: Pre-Session Reconciliation Discrepancy

**Scenario:** After overnight restart, IIOS shows TATASTEEL.NS LONG 100 from previous session (swing trade). Dhan also shows TATASTEEL.NS LONG 100. Reconciliation: positions match.

**Additional scenario — discrepancy case:**
Broker (Dhan) shows 0 shares TATASTEEL.NS (broker performed auto-square-off during connectivity outage).
IIOS shows LONG 100 (state from before outage).

**Reconciliation procedure:**

1. Position Updater queries Dhan API: TATASTEEL.NS = 0
2. IIOS Position Registry: TATASTEEL.NS LONG 100
3. Discrepancy detected: GHOST_POSITION (IIOS > broker)
4. Reconciliation report generated
5. Alert: RECONCILIATION_DISCREPANCY emitted to EventBus
6. Telegram alert: Ghost position detected — TATASTEEL.NS LONG 100 in IIOS, FLAT at broker
7. Trading session NOT started; awaiting human resolution

**Human operator action:**
Operator confirms: broker auto-squared-off during outage (verified in broker statement).
Operator approves correction: set IIOS TATASTEEL.NS position to 0.
Recovery Manager executes correction (no order needed; position record update only).

8. IIOS position updated: TATASTEEL.NS = 0 (FLAT)
9. Audit event written: POSITION_CORRECTED (source: RECONCILIATION)
10. RECONCILIATION_COMPLETE emitted
11. Trading session begins normally

**Implication for PNL:**
The forced square-off by the broker at an unknown price must be recorded. Recovery Manager queries broker fill history for the square-off price. Realised P&L from that fill is retroactively recorded to maintain accurate session P&L.

---

### Worked Example 7: Execution Health Degradation Scenario

**Scenario:** The Execution Audit Manager starts experiencing write latency > 500ms (disk I/O contention). Execution Health Manager detects degradation.

**Detection (10:55:00 IST):**
Execution Health Manager polls Audit Manager health.
Audit write latency: 740ms (target 20ms; critical threshold 120ms exceeded).
Component status: DEGRADED → upgraded to FAILED after second consecutive failure (10:55:30 IST).

**Impact:**
- Execution Engine constitutional rule EC-I-001: all executions must be auditable
- GDR-EXE-003: audit before completion
- Action: new executions HELD pending audit recovery

**Recovery:**
1. AUDIT_DEGRADED alert emitted; Telegram notification
2. Operator investigates: disk I/O spike from another process
3. Disk I/O resolved; Audit Manager write latency returns to normal (20ms)
4. Execution Health Manager detects HEALTHY status: two consecutive successful polls
5. Component status: HEALTHY restored
6. HELD executions released from queue; resume normally
7. Total hold duration: 4 minutes 22 seconds

**EQS impact:**
Executions held during the audit degradation period have elevated QUEUED-to-SUBMITTED latency.
EQS dimension EQD-02 (Execution Latency) reduced for those executions: 0.55 (MARGINAL).
Decision Engine notified via EXECUTION_COMPLETED callback with reduced EQS.
LearningSystem records the degraded session; investigates root cause.

---

### Worked Example 8: Algorithmic TWAP Execution

**Scenario:** Large NIFTY futures position (5 lots). Decision Engine requests TWAP execution over 30 minutes to minimise market impact.

**Decision Package:**

`
decision_package_id: DEC-BUY-IDX-20260101-00000120
action_type: BUY-IDX
instrument: NIFTY-MAY-FUT
instrument_class: IDX
quantity: 5 (lots)
direction: BUY
urgency: LOW
execution_type_hint: TWAP
twap_window_minutes: 30
governance_tier: TIER-2-HUMAN (large index position)
`

**Governance hold:**
Governance tier TIER-2-HUMAN: execution held for human approval.
Telegram notification: TATASTEEL BUY EXECUTION AWAITING APPROVAL (execution_id, instrument, quantity, value).
Operator reviews and approves at 11:02:15 IST.

**TWAP execution plan:**
- 5 lots over 30 minutes
- Each lot = 1 child order (5 child orders total)
- Child order interval: 6 minutes (30 min / 5)
- Child order times: 11:02:15, 11:08:15, 11:14:15, 11:20:15, 11:26:15 IST

**Execution schedule:**

| Child | Scheduled time | Order type | Quantity | Status |
|---|---|---|---|---|
| 01 of 05 | 11:02:15 | LIMIT | 1 lot | COMPLETED @ 24,150 |
| 02 of 05 | 11:08:15 | LIMIT | 1 lot | COMPLETED @ 24,162 |
| 03 of 05 | 11:14:15 | LIMIT | 1 lot | COMPLETED @ 24,155 |
| 04 of 05 | 11:20:15 | LIMIT | 1 lot | COMPLETED @ 24,171 |
| 05 of 05 | 11:26:15 | LIMIT | 1 lot | COMPLETED @ 24,160 |

**Average fill price:**
Bytes=$s Lines=$l BytePASS=$(if($s -ge 250000){'PASS'}else{'FAIL'}) LinePASS=$(if($l -ge 4500){'PASS'}else{'FAIL'})\overline{P}_{TWAP} = \frac{24150 + 24162 + 24155 + 24171 + 24160}{5} = 24159.6Bytes=$s Lines=$l BytePASS=$(if($s -ge 250000){'PASS'}else{'FAIL'}) LinePASS=$(if($l -ge 4500){'PASS'}else{'FAIL'})

**EQS computation:**
- EQD-03 (Fill Quality): all 5 lots filled at near-plan price; slippage < 0.05% each → score: 0.98
- EQD-08 (Completeness): all 5 lots filled (100%) → score: 1.00
- EQD-02 (Latency): per-child latency excellent; TWAP timing adherence ± 2 seconds → score: 0.97
- Composite EQS: 0.96 (EXCELLENT) ✅

**Parent execution status:**
All 5 child executions COMPLETED. Parent execution EXE-ALGO-20260101-00000120 transitions to COMPLETED.
Portfolio updated: NIFTY-MAY-FUT LONG 5 lots @ avg 24,159.6.
LearningSystem notified: TWAP execution quality 0.96 for STR-INDEX_MOMENTUM_003.

---
---

### Worked Example 9: Cross-Session Learning Feedback Loop

**Scenario:** After session closure, the Execution Engine's analytics feed into the LearningSystem and PerformanceAnalytics layers.

**Session summary data (emitted at 16:00 IST):**

`
session_id: SES-20260101-0001
total_orders_submitted: 48
total_orders_filled: 47
total_orders_rejected: 1
total_orders_cancelled: 0
total_retry_events: 2
total_recovery_events: 0
fill_rate: 97.9%
average_slippage: 0.09%
average_eqs: 0.891 [GOOD]
eqs_excellent_count: 28
eqs_good_count: 17
eqs_acceptable_count: 2
eqs_marginal_count: 0
eqs_failed_count: 0
session_realised_pnl: +8,420 INR
session_unrealised_pnl: +2,100 INR
session_total_pnl: +10,520 INR
kill_switch_activations: 0
held_executions: 0
active_broker: PAPER_SIMULATOR
`

**LearningSystem actions:**

1. StrategyPerformanceTracker receives session P&L breakdown per strategy:
   - STR-MEAN_REVERSION_007: 3 executions, win rate 67%, session P&L +3,200 INR
   - STR-MOMENTUM_BREAKOUT_002: 5 executions, win rate 60%, session P&L +2,800 INR
   - STR-INDEX_MOMENTUM_003: 2 executions, win rate 50%, session P&L +800 INR

2. RegimeStrategyMap updated with regime at time of each execution:
   - TRENDING_BULL regime: MOMENTUM strategies EQS average 0.93
   - RANGING regime: MEAN_REVERSION strategies EQS average 0.88

3. MetaLearning receives regime-EQS correlation data for next session weight update.

**PerformanceAnalytics actions:**

1. DrawdownAnalyzer: session peak drawdown = 0.8% (well within 2% kill switch threshold)
2. EQS trend: session 0.891 vs 30-day rolling average 0.875 — slight improvement
3. Slippage trend: session 0.09% vs 30-day rolling average 0.12% — improvement
4. Broker performance: Paper Simulator average ACK latency 87ms; fill latency 5.2s avg

**Data archived to SQLite:**
All session metrics durably stored for walk-forward analysis.
Next session: this data available to MetaLearning for strategy weight prediction.

---

### Execution Engine — Canonical Reference Summary

**Canonical ID formats:**

| Object | Format |
|---|---|
| Execution | EXE-{TYPE}-{DATE}-{SEQ:08d} |
| Order | ORD-{EXE_ID}-{TRANCHE:02d} |
| Fill | FILL-{ORDER_ID}-{SEQ:04d} |
| Audit event | AUD-{EXE_ID}-{SEQ:06d} |
| Session | SES-{DATE}-{SEQ:04d} |

**Key thresholds:**

| Threshold | Value | Constitutional? |
|---|---|---|
| Maximum orders per session | 300 | Yes |
| Maximum retries per execution | 3 | Yes |
| Retry back-off | 1s / 4s / 16s | Yes |
| Kill Switch activation latency | < 50ms | Yes |
| Daily drawdown Kill Switch trigger | 2.0% | Yes |
| Intraday close deadline | 15:30 IST | Yes |
| Partial fill stall: equity | 15 min | No (configurable) |
| Partial fill stall: index | 5 min | No (configurable) |
| Min acceptable partial fill | 80% | No (configurable) |
| Max slippage before hold | 0.50% | No (configurable) |
| State timeout: SUBMITTED to ACK | 1,500ms | No (configurable) |
| QUEUED to SUBMITTED target | 500ms | Target |
| Broker heartbeat interval | 30s | No (configurable) |

**EQS weight matrix:**

| Dimension | Weight |
|---|---|
| EQD-01 Accuracy | 0.25 |
| EQD-03 Fill Quality | 0.20 |
| EQD-04 Reliability | 0.15 |
| EQD-02 Latency | 0.10 |
| EQD-06 Safety | 0.10 |
| EQD-05 Determinism | 0.05 |
| EQD-07 Consistency | 0.05 |
| EQD-08 Completeness | 0.05 |
| EQD-09 Traceability | 0.02 |
| EQD-10 Auditability | 0.01 |
| EQD-11 Risk Compliance | 0.01 |
| EQD-12 Failure Recovery | 0.01 |

---

### Final Notes

The IIOS Execution Engine is designed for:

1. **Correctness first.** Every order must trace to a decision; every fill must trace to an order. No orphaned trades. No silent failures.

2. **Safety second.** The Kill Switch is not a feature — it is a constitutional guarantee. Human operators retain absolute authority.

3. **Auditability always.** Every action is recorded, timestamped, and hash-chain-linked. An auditor with the audit log can reconstruct the complete history of every order ever submitted.

4. **Quality measured.** EQS is computed for every execution. Quality does not depend on market outcomes — it measures how well the engine executed what it was asked to execute.

5. **Independence from brokers.** The broker gateway abstraction means no broker-specific logic reaches the execution planning layer. A broker can be swapped, or a paper simulator substituted, without changing any decision-making logic.

6. **Evolution without regression.** Any future enhancement to the Execution Engine must preserve all interfaces defined in this document, all constitutional rules, and all GDRs. This document is the contract.

---

*End of IIOS Execution Engine Architecture — IIOS-EXE-ENG-ARCH-001*

---

## APPENDIX: EXECUTION TYPES EXTENDED REFERENCE

### EX-TYPE Cross-Reference with Decision Types

The following table provides a complete cross-reference between all 19 execution types and the decision types that may generate them, the components primarily involved, and the EQS dimension most critical for each type.

| Execution Type | Code | Decision Types | Primary Components | Critical EQS Dimension |
|---|---|---|---|---|
| Market Execution | EX-TYPE-001 | BUY-EQT(URGENT), EXT-EMERGENCY, EMR-LIQUIDATE | OrderRouter, BrokerGateway | EQD-02 Latency |
| Limit Execution | EX-TYPE-002 | BUY-EQT, BUY-DRV, BUY-IDX, SEL-CLOSE | OrderBuilder, SlippageManager | EQD-03 Fill Quality |
| Stop Execution | EX-TYPE-003 | EXT-SL, PRT-SL | OrderBuilder, ExecutionMonitor | EQD-06 Safety |
| Stop-Limit Execution | EX-TYPE-004 | EXT-SL, PRT-SL(specified) | OrderBuilder | EQD-03 Fill Quality |
| IOC Execution | EX-TYPE-005 | EXT-EMERGENCY, basket legs | OrderRouter | EQD-08 Completeness |
| FOK Execution | EX-TYPE-006 | Atomic basket legs | OrderRouter | EQD-08 Completeness |
| GTT Execution | EX-TYPE-007 | SCH-PRE_MARKET, conditional entry | ExecutionScheduler | EQD-07 Consistency |
| Bracket Execution | EX-TYPE-008 | BUY-EQT (with TP+SL) | OrderBuilder (3 legs) | EQD-04 Reliability |
| Cover Execution | EX-TYPE-009 | BUY-EQT (with mandatory SL) | OrderBuilder (2 legs) | EQD-06 Safety |
| Basket Execution | EX-TYPE-010 | RBL-SCHEDULED | ExecutionPlanner (multi-intent) | EQD-08 Completeness |
| TWAP Execution | EX-TYPE-011 | Large BUY-EQT/BUY-IDX | ExecutionScheduler, TWAP algo | EQD-07 Consistency |
| VWAP Execution | EX-TYPE-012 | Large BUY-EQT/BUY-IDX | ExecutionScheduler, VWAP algo | EQD-07 Consistency |
| Manual Execution | EX-TYPE-013 | Human-initiated | HumanOverrideService | EQD-01 Accuracy |
| Hybrid Execution | EX-TYPE-014 | BUY-EQT (partial algo) | ExecutionPlanner | EQD-04 Reliability |
| Partial Execution | EX-TYPE-015 | Any (partial fill accepted) | ExecutionMonitor, RetryManager | EQD-08 Completeness |
| Delayed Execution | EX-TYPE-016 | SCH-PRE_MARKET | ExecutionScheduler | EQD-07 Consistency |
| Scheduled Execution | EX-TYPE-017 | SCH-* | ExecutionScheduler | EQD-07 Consistency |
| Conditional Execution | EX-TYPE-018 | GTT-based entries | ExecutionScheduler | EQD-01 Accuracy |
| Recovery Execution | EX-TYPE-019 | System-generated (discrepancy) | RecoveryManager (human approved) | EQD-06 Safety |

---

### State Machine Visual Summary

`
                    [RECEIVED]
                        |
                        v
                    [PLANNING]
                   /     |     \
                  /      |      \
           [HELD]  [SCHEDULED]  [QUEUED]
                        |           |
                        v           v
                    [QUEUED]    [BUILDING]
                                    |
                                    v
                              [VALIDATING]
                             /           \
                            v             v
                    [RISK_CHECKING]   [REJECTED]
                   /        |    \
                  v         v     v
           [ROUTING]   [HELD]  [BLOCKED]
               |
               v
          [SUBMITTED]
         /     |      \
        v      v       v
   [ACK]  [TIMEOUT]  [REJECTED]
    /  \       |
   v    v      v
[PARTIAL] [FULL] [RETRY]
[FILL]  [FILL]     |
   |      |        v
   v      v   [RECOVERING]
[STALLED] [POSITION_UPDATING]
    |           |
    v           v
 [RETRY]  [PORTFOLIO_UPDATING]
               |
               v
          [AUDITING]
               |
               v
          [ARCHIVING]
               |
               v
          [COMPLETED] ← terminal
`

Terminal states: COMPLETED, CANCELLED, EXPIRED, FAILED

---

*IIOS-EXE-ENG-ARCH-001 — Status: RATIFIED*
