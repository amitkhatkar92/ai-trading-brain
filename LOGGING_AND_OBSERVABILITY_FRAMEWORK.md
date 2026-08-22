# LOGGING AND OBSERVABILITY FRAMEWORK
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-LOG-OBS-001
**Version:** 1.0.0
**Status:** AUTHORITATIVE
**Classification:** Architecture Engineering Specification
**Owner:** Architecture Council
**Date:** 2026-07-04

---

## DOCUMENT PURPOSE

This document defines the complete Logging and Observability Framework for the
Investment Intelligence Operating System (IIOS). The framework is the engineering
specification governing all logging, monitoring, tracing, metrics collection,
diagnostics, auditing, health reporting, and operational observability throughout
the IIOS system lifecycle.

The framework makes every engine, workflow, AI agent, service, and infrastructure
component observable — providing the visibility needed to operate, debug, optimize,
and audit the system with confidence.

This document defines architecture exclusively. It contains no source code, no
logging configuration values, and no database schemas.

---

## SCOPE

| In Scope | Out of Scope |
|----------|-------------|
| Observability architecture and design | Log configuration values |
| Component specifications | Source code implementation |
| Governance framework | API endpoint definitions |
| Lifecycle design | Dashboard UI designs |
| Quality standards | Alerting rule values |
| Constitutional rules | Infrastructure setup scripts |
| Readiness certification | Database schema definitions |

---

## TABLE OF CONTENTS

- Part I — Logging and Observability Philosophy
- Part II — Logging Taxonomy
- Part III — Framework Architecture
- Part IV — Log Hierarchy
- Part V — Logging Lifecycle
- Part VI — Observability Services
- Part VII — Logging Quality Framework
- Part VIII — Logging Governance
- Part IX — Logging Constitution
- Part X — Logging Readiness Checklist
- Supplement A — Logging Taxonomy Reference
- Supplement B — Severity Catalog
- Supplement C — Metrics Catalog
- Supplement D — Tracing Reference
- Supplement E — Governance Decision Records
- Supplement F — Logging Anti-Patterns
- Supplement G — Operational Runbook
- Supplement H — Comprehensive Glossary

---

# PART I — LOGGING AND OBSERVABILITY PHILOSOPHY

## 1.1 What Is Logging?

Logging is the systematic, structured recording of system events as they occur.
A log record is an immutable statement of fact: something happened at a specific
time, in a specific context, with specific attributes. Logs are the primary narrative
of a system's operational history.

In IIOS, logging captures the execution narrative of a trading intelligence system
making real financial decisions. Every decision made, every order placed, every risk
check performed, every learning update processed is a log event. The aggregate of
all log events tells the complete story of the system's behavior.

Logging in IIOS serves four foundational purposes:
1. **Operational visibility** — operators know what the system is doing right now.
2. **Diagnostic capability** — engineers can reconstruct what happened and why.
3. **Audit compliance** — the complete record is available for regulatory inspection.
4. **Safety evidence** — every safety check (kill switch, risk guardian) is logged
   and the record cannot be altered.

A log is NOT:
- A real-time monitoring alert (logs are recorded; alerts are triggered).
- A metric (logs are events; metrics are aggregated measurements).
- A configuration value (logs describe what happened; configuration governs behavior).
- A notification to a human (logs are machine-readable records; notifications are
  human-targeted communications).

---

## 1.2 What Is Observability?

Observability is the property of a system that allows its internal state to be inferred
from its external outputs. A system is observable if an engineer can understand what
is happening inside it — and why — solely by examining the data the system produces.

The three classical pillars of observability are:
- **Logs:** Discrete events recording what happened.
- **Metrics:** Continuous numerical measurements of system state.
- **Traces:** Records of the path a request or computation took through the system.

IIOS extends this with:
- **Health scores:** The OHS (Operational Health Score) providing a synthesized view
  of component health.
- **Audit trails:** Immutable records of governance-relevant events.
- **Telemetry:** Structured operational data collected for analytics and reporting.

Observability is not merely having lots of data. A system with abundant unstructured
logs and no way to search or correlate them is not observable. IIOS observability is
designed to answer specific operational questions quickly:
- Is the system trading correctly right now?
- Why did the system not enter a specific trade?
- What was the kill switch state during a specific market event?
- Which engine is degrading the cycle latency?
- Is a strategy's win rate trending down?

---

## 1.3 Logging vs Monitoring

Logging and monitoring are complementary but distinct. Understanding their relationship
is essential to designing both correctly.

**Logging:**
- Records what happened (historical).
- Produces discrete records (events).
- Is always-on: every significant event is logged.
- Is not inherently time-sensitive: a log event can be written asynchronously.
- Is the foundation for monitoring (monitoring aggregates and analyzes log data).
- Audience: forensic investigators, compliance officers, engineers debugging issues.

**Monitoring:**
- Observes what is happening (real-time).
- Produces alerts and dashboards (continuous).
- Is threshold-driven: only alerts when something is anomalous.
- Is time-sensitive: monitoring alerts must arrive before damage is done.
- Builds on logging but adds real-time analysis.
- Audience: operators watching dashboards, on-call engineers receiving alerts.

The relationship: monitoring is the real-time lens on the log stream. Monitoring
reads the stream of events and metrics, applies rules, and produces alerts when
conditions warrant. Logging continues whether monitoring is watching or not.

In IIOS, the Log Router feeds both the Log Storage Manager (for persistence) and
the Monitoring Manager (for real-time analysis) from the same log event stream.

---

## 1.4 Logging vs Metrics

**Logging** records individual events: "Order TATASTEEL SHORT placed at 11:43:17,
quantity 100, price 892.45."

**Metrics** record continuous measurements: "Current open positions: 3. Cycle latency
(last 60s): 172ms average. Win rate (last 30 days): 58.3%."

Key differences:

| Aspect | Logging | Metrics |
|--------|---------|---------|
| Granularity | Per event | Aggregated |
| Volume | High (millions/day) | Medium (thousands/day) |
| Precision | Exact (event-level) | Statistical (averaged) |
| Time model | Discrete timestamps | Continuous series |
| Query model | Search and filter | Aggregate and compare |
| Retention | Long (years) | Medium (months) |
| Use case | "What happened?" | "How is it performing?" |

IIOS uses both. Log events are the atoms; metrics are the aggregated molecules.
The Metrics Manager consumes log events (among other sources) to compute metrics.

---

## 1.5 Logging vs Tracing

**Logging** records individual events without explicit connection to the broader
execution context.

**Tracing** records the complete causal chain of a computation — tracking how a
request or process flows through multiple components, preserving the parent-child
relationships between operations.

In IIOS, a trace of a full decision cycle would show:
`
[TRACE: cycle-2026-07-04-09:30:00]
  |--> global_intelligence.fetch() — 17ms
  |--> market_intelligence.classify() — 19ms
  |--> meta_learning.predict_weights() — 8ms
  |--> opportunity_engine.scan() — 35ms
       |--> opportunity_engine.score_candidate("TATASTEEL") — 12ms
       |--> opportunity_engine.score_candidate("HDFC") — 11ms
  |--> strategy_lab.generate_signals() — 22ms
  |--> ... (continuing through all 17 layers)
`

A trace shows not just what happened but how the components interacted, what called
what, and how long each step took. Traces are essential for diagnosing latency issues
and for understanding why a specific decision was made (which engine's output influenced
which downstream engine's decision).

IIOS traces the full decision cycle for every cycle execution during market hours.

---

## 1.6 Logging vs Auditing

**Logging** records operational events for diagnostic and operational purposes.
Logs may be rotated, compressed, and eventually deleted (per retention policy).

**Auditing** records governance-relevant events for compliance and accountability.
Audit records are immutable, tamper-evident, and retained for extended periods
(minimum 5 years for trading-affecting events).

The distinction is one of purpose and permanence:

| Aspect | Logging | Auditing |
|--------|---------|---------|
| Purpose | Operational diagnosis | Compliance and accountability |
| Mutability | May be rotated/deleted | Immutable forever |
| Tamper evidence | Not required | Required (hash chain) |
| Retention | 30-90 days (operational) | 5+ years |
| Coverage | All significant events | Governance-relevant events only |
| Audience | Engineers, operators | Compliance, regulators, auditors |

In IIOS, ALL of the following are audit events, not merely log events:
- Kill switch activations and deactivations.
- Order placements and fills.
- Risk limit exceptions.
- Configuration changes affecting trading.
- Strategy promotions and demotions.
- Emergency override activations.

Audit events are also log events (they appear in the log stream) but are additionally
written to the immutable audit store with hash-chain tamper evidence.

---

## 1.7 Logging vs Diagnostics

**Logging** is the standard narrative record of system operation.

**Diagnostics** are targeted, often verbose records produced specifically to assist
in debugging a problem. Diagnostic logging typically includes:
- Internal state dumps.
- Variable values at decision points.
- Execution path details not normally logged.
- Timing breakdowns within a single operation.

Diagnostic logging is typically enabled on demand (not always-on) because its
verbosity would be excessive in normal operation. In IIOS, diagnostic mode is enabled
per-engine when a problem is being investigated.

The key property of diagnostic logging: it produces far more detail than operational
logging, targeted at the specific problem being investigated. After the investigation,
diagnostic mode is disabled.

---

## 1.8 Logging vs Telemetry

**Logging** captures discrete events.

**Telemetry** is the continuous, structured collection of operational data for
analytics, performance tracking, and trend analysis. Telemetry is:
- Always-on, like logging.
- Structured for machine processing, like logging.
- But optimized for analytics rather than forensic diagnosis.
- Written to a time-series or structured data store optimized for aggregation.
- Retained and analyzed to understand system trends over weeks, months, years.

In IIOS, telemetry captures: per-cycle execution metrics, per-strategy performance
data, per-engine health scores, per-agent debate quality scores, data feed latency
trends, and decision quality metrics. Telemetry is the operational intelligence that
drives continuous improvement.

The Telemetry Manager is distinct from the Log Storage Manager because their
storage backends, query patterns, and retention policies differ.

---

## 1.9 Logging vs Events

**Logging** produces records consumed primarily by operators and engineers for
diagnosis and monitoring.

**Events** are structured messages published by components to notify other components
of state changes. Events flow through the Event Bus and trigger reactions from
subscribing components.

Logging and events are related but distinct:
- A log record is written to storage and never acknowledged.
- An event is published on a bus and consumed by subscribers who react to it.
- A single system occurrence may produce both a log record AND an event.

In IIOS: when the Risk Guardian triggers the kill switch, it logs the event (to the
audit log and the operational log) AND publishes a KillSwitchTriggeredEvent on the
Event Bus (consumed by Execution Engine, Trade Monitoring, and Control Tower).

---

## 1.10 Logging vs Alerts

**Logging** passively records. No human is necessarily notified.

**Alerts** actively notify humans when conditions warrant. Alerts are:
- Threshold-driven (generated when a metric or condition crosses a threshold).
- Time-sensitive (intended to prompt immediate human response).
- Targeted (sent to specific recipients via Telegram, email, dashboard).
- Actionable (an alert that requires no action is noise).

In IIOS, alerts are generated by the Alert Manager, which continuously evaluates
log streams and metrics against alert rules. Not every log event produces an alert.
Only events that cross defined thresholds and require human awareness generate alerts.

The relationship: logs → monitoring analysis → alert rules → alerts → notifications.

---

## 1.11 Logging vs Notifications

**Alerts** are system-to-operator messages indicating something requires attention.

**Notifications** are a broader category including:
- Trade execution notifications (a trade was placed, filled, or closed).
- Daily summary notifications (end-of-day P&L, strategy performance).
- System status notifications (system started, stopped, health changed).
- Custom notifications configured by users.

Notifications are delivered via the Telegram bot and are designed to be informative
rather than urgent. An alert requires response; a notification provides information.

In IIOS, the Telegram bot handles both alert delivery (for operational alerts) and
notification delivery (for trade confirmations and daily summaries).

---

## 1.12 Logging Lifecycle

The complete lifecycle of a log event:

`
ORIGINATION
    |
    v
GENERATION -----> Component creates log event with structured fields
    |
    v
ENRICHMENT -----> Correlation ID, engine context, session ID added
    |
    v
VALIDATION -----> Format, required fields, sensitivity check
    |
    v
CLASSIFICATION -----> Level, category, retention tier assigned
    |
    v
ROUTING -----> To appropriate sinks: operational log, audit log,
    |           telemetry store, alert evaluator, trace collector
    v
STORAGE -----> Written to persistent storage
    |
    v
AGGREGATION -----> Combined with related events for analysis
    |
    v
ANALYSIS -----> Pattern detection, anomaly detection, alerting
    |
    v
ARCHIVING -----> Compressed to long-term storage at retention boundary
    |
    v
DELETION -----> Deleted at end of retention period (operational only;
                audit records are never deleted)
`

---

## 1.13 Log Ownership

Every log category in IIOS has an owner. Ownership governs:
- Which team is responsible for log quality in that category.
- Who reviews logs for anomalies.
- Who is alerted when log patterns indicate a problem.
- Who manages the retention policy for that category.

### Ownership Tiers for Logging

**Architecture Council:** System logs, audit logs, security logs, governance logs.
**Engine Owners:** All engine-specific logs, workflow logs, agent logs.
**Operations Team:** Infrastructure logs, deployment logs, monitoring logs, health logs.
**Compliance Officer:** Compliance logs (read access; Audit Manager owns the records).

---

## 1.14 Observability Principles

The IIOS observability design is governed by nine principles:

**Principle 1 — Observable by Default.** No engine, agent, or service is deployed
without producing observable output. Unobserved components are disallowed.

**Principle 2 — Structured Over Unstructured.** All log events are structured
(key-value pairs or JSON). Free-text messages are supplementary to structured fields,
not the primary record.

**Principle 3 — Context Propagation.** Every log event carries its operational
context: which engine, which cycle, which session, which correlation ID. Context
is never stripped for brevity.

**Principle 4 — Separation of Concerns.** Operational logs, audit logs, and telemetry
are written to separate stores with separate retention policies. They serve different
purposes and must not be conflated.

**Principle 5 — Sanitization Before Storage.** No sensitive value (credentials,
tokens, PII) appears in any log record. The Log Sanitizer runs before any log event
is written to any sink.

**Principle 6 — Immutability of Audit.** Audit log records are never modified or
deleted. The audit store is append-only. Attempts to modify audit records are themselves
audit events.

**Principle 7 — Proportional Verbosity.** Log volume is proportional to operational
significance. DEBUG-level events are not written in production by default. Emergency
and critical events are written to multiple sinks redundantly.

**Principle 8 — Recovery Capability.** The logging system itself must be resilient.
If the primary log sink is unavailable, events are buffered and written when the sink
recovers. Critical events (kill switch, order placement) are written synchronously
and never dropped.

**Principle 9 — Queryable History.** The complete operational history of the system
must be queryable. "What was the system doing at time T?" must be answerable from
the log store.

---

## 1.15 Operational Transparency

Operational transparency is the organizational commitment to making system behavior
visible to all stakeholders: operators see the trading activity, architects see the
health trends, compliance sees the audit trail, and the team collectively sees any
degradation before it becomes a crisis.

In IIOS, operational transparency is implemented through:
- The Streamlit real-time dashboard (live health, positions, P&L, cycle metrics).
- The Telegram bot (trade notifications, health alerts, daily summaries).
- The Configuration Catalog (current configuration visible to authorized parties).
- The Audit Manager (complete change history visible to Architecture Council).
- The Analytics Service (trend reports reviewed at regular governance meetings).

No aspect of IIOS's operation is invisible to the team. Every engine's health, every
strategy's performance, every decision's rationale, and every risk event is documented
and accessible.

---

*End of Part I*

---

# PART II — LOGGING TAXONOMY

## 2.1 Taxonomy Overview

The IIOS logging taxonomy organizes all log events into 24 categories. Each category
has a defined namespace, ownership tier, severity profile, retention policy, and
routing rules. The taxonomy is exhaustive — every log event produced by IIOS belongs
to exactly one primary category.

---

## 2.2 Category 1 — System Logs (SYSTEM)

**Namespace:** SYSTEM
**Owner:** Architecture Council
**Severity Profile:** INFO to CRITICAL
**Retention:** 90 days operational, 1 year archive
**Routing:** Operational log, dashboard, Telegram (CRITICAL only)

System logs record the lifecycle events of the IIOS platform itself: startup,
shutdown, mode changes, scheduler events, and cross-cutting system state changes.

**Sub-categories:**

SYSTEM.STARTUP — System initialization events: each phase of startup, the time
taken, and whether initialization succeeded or failed. Includes: configuration loaded,
engines registered, scheduler started, health monitor started.

SYSTEM.SHUTDOWN — Graceful shutdown events: scheduler stopped, engines deactivated,
positions reconciled, final state persisted.

SYSTEM.MODE_CHANGE — Events when the operating mode changes (development → paper,
paper → production). Mode changes are also written to the audit log.

SYSTEM.SCHEDULER — Scheduler events: cycle triggers, job execution, job failures,
next scheduled run times.

SYSTEM.HEALTH — System-wide health status changes: OHS transitions (OPTIMAL →
NOMINAL, NOMINAL → DEGRADED, etc.).

SYSTEM.ERROR — Unhandled system-level errors that affect the entire platform,
not specific to any engine.

---

## 2.3 Category 2 — Engine Logs (ENGINE.[name])

**Namespace:** ENGINE.[engine_name]
**Owner:** Engine Owner
**Severity Profile:** DEBUG to CRITICAL
**Retention:** 30 days operational, 90 days archive
**Routing:** Operational log, engine-specific log file, dashboard

Engine logs record the operational narrative of each of the 18 IIOS engines.

**Sub-categories:**

ENGINE.[name].LIFECYCLE — Engine initialization, activation, deactivation.

ENGINE.[name].EXECUTION — Per-execution events: inputs received, computation
started, outputs produced, execution time.

ENGINE.[name].DECISION — Decision points within the engine: which path was taken,
which filters applied, why certain candidates were rejected.

ENGINE.[name].PERFORMANCE — Latency measurements, resource usage, cache statistics.

ENGINE.[name].ERROR — Engine-level errors: dependency unavailable, computation
failed, output validation failed.

ENGINE.[name].HEALTH — Engine health score changes and OHS tier transitions.

ENGINE.[name].CACHE — Cache hit/miss events, cache invalidation, cache refresh.

ENGINE.[name].INTEGRATION — Events related to external system integration: data
feed queries, broker API calls, database reads/writes.

---

## 2.4 Category 3 — Workflow Logs (WORKFLOW.[name])

**Namespace:** WORKFLOW.[workflow_name]
**Owner:** Engine Owner of owning engine
**Severity Profile:** DEBUG to ERROR
**Retention:** 30 days operational
**Routing:** Operational log, engine log

Workflow logs record the execution of named multi-step processes.

**Sub-categories:**

WORKFLOW.[name].START — Workflow initiated: input parameters, triggering condition.

WORKFLOW.[name].STEP — Each step of the workflow: step name, input state, output
state, execution time.

WORKFLOW.[name].BRANCH — Conditional branching events: which branch was taken and why.

WORKFLOW.[name].ERROR — Step failures: which step failed, what input produced
the failure, what retry action was taken.

WORKFLOW.[name].COMPLETE — Workflow completed: final output, total execution time.

---

## 2.5 Category 4 — AI Agent Logs (AGENT.[id])

**Namespace:** AGENT.[agent_id]
**Owner:** Engine Owner of Debate and Decision engine
**Severity Profile:** DEBUG to WARNING
**Retention:** 30 days operational, 90 days archive (for learning analysis)
**Routing:** Operational log, decision log, analytics

AI Agent logs record the behavior of the five debate agents in the Debate and
Decision engine.

**Sub-categories:**

AGENT.[id].ARGUMENT — The argument formulated by the agent: stance, evidence,
confidence score, reasoning summary.

AGENT.[id].REBUTTAL — Agent's response to other agents' arguments.

AGENT.[id].SCORE — The score assigned by the agent to the proposed trade:
numeric score, weighting factors, justification.

AGENT.[id].POSITION_CHANGE — Events where an agent changes its stance during
the debate.

AGENT.[id].QUALITY — Agent quality metrics: argument diversity, prediction
accuracy over time.

---

## 2.6 Category 5 — Decision Logs (DECISION)

**Namespace:** DECISION
**Owner:** Debate and Decision Engine Owner
**Severity Profile:** INFO to WARNING
**Retention:** 1 year operational, 5 years archive (regulatory requirement)
**Routing:** Operational log, audit log, decision database, analytics

Decision logs record every trade decision made by the system. These are among the
most important logs in IIOS from a compliance perspective.

**Sub-categories:**

DECISION.PROPOSAL — A trade proposal entering the decision engine: symbol, direction,
proposed size, proposing strategy, trigger conditions.

DECISION.DEBATE_SUMMARY — The complete debate summary: all five agent scores,
debate quality score, final synthesized score.

DECISION.APPROVE — An approved decision: final score (>= 6.5), position details,
expiry time, rationale.

DECISION.REJECT — A rejected decision: final score (< 6.5), primary rejection
reason, agent vote breakdown.

DECISION.EXPIRE — A decision that expired before execution: original approval time,
expiry time, reason for non-execution.

DECISION.COOLDOWN — A decision blocked by the cooldown manager: symbol, last
decision time, cooldown remaining.

---

## 2.7 Category 6 — Prediction Logs (PREDICTION)

**Namespace:** PREDICTION
**Owner:** Meta Learning and Research Lab Engine Owners
**Severity Profile:** DEBUG to WARNING
**Retention:** 30 days operational, 1 year archive
**Routing:** Operational log, telemetry

Prediction logs record the outputs of IIOS prediction models: regime predictions,
return forecasts, volatility forecasts.

**Sub-categories:**

PREDICTION.REGIME — Regime prediction: predicted regime, confidence, alternative
regime probabilities, prediction horizon.

PREDICTION.RETURN — Return forecast: symbol, horizon, expected return, confidence
interval.

PREDICTION.STRATEGY_WEIGHT — Strategy weight predictions from Meta Learning:
per-regime weights, k-NN confidence score.

PREDICTION.CALIBRATION — Prediction calibration events: whether predictions are
being calibrated, calibration error metrics.

PREDICTION.STALENESS — Events when predictions are considered stale and refreshed.

---

## 2.8 Category 7 — Portfolio Logs (PORTFOLIO)

**Namespace:** PORTFOLIO
**Owner:** Execution Engine Owner (positions) and Capital Risk Engine Owner (allocation)
**Severity Profile:** INFO to CRITICAL
**Retention:** 1 year operational, 5 years archive
**Routing:** Operational log, audit log (position changes), analytics

Portfolio logs record the state of the investment portfolio: positions opened,
closed, modified, and the overall portfolio composition.

**Sub-categories:**

PORTFOLIO.POSITION_OPEN — A new position is opened: symbol, direction, quantity,
entry price, entry time, strategy, decision reference.

PORTFOLIO.POSITION_CLOSE — A position is closed: symbol, exit price, P&L, hold
duration, close reason (stop, target, signal, force-close).

PORTFOLIO.POSITION_MODIFY — A position is modified: old and new stop/target levels.

PORTFOLIO.ALLOCATION — Capital allocation decisions: strategy budgets, position
size calculations.

PORTFOLIO.EXPOSURE — Portfolio exposure events: current gross/net exposure, sector
concentration, symbol concentration.

PORTFOLIO.PNL — P&L events: unrealized P&L updates, realized P&L on close,
daily P&L milestones.

---

## 2.9 Category 8 — Risk Logs (RISK)

**Namespace:** RISK
**Owner:** Risk Guardian Engine Owner (constitutional risk) and Risk Control Engine Owner
**Severity Profile:** INFO to CRITICAL
**Retention:** 1 year operational, 5 years archive (regulatory)
**Routing:** Operational log, audit log (all CRITICAL), Telegram (CRITICAL), analytics

Risk logs record all risk management activity. Risk logs at CRITICAL severity are
written synchronously and to multiple sinks.

**Sub-categories:**

RISK.PRE_TRADE_CHECK — Results of pre-trade risk checks: check type, result
(PASS/FAIL), check details.

RISK.KILL_SWITCH_CHECK — Each VIX and portfolio loss check by the Risk Guardian:
current VIX, threshold, daily P&L, result.

RISK.KILL_SWITCH_TRIGGER — Kill switch activated: trigger condition, portfolio
state at trigger, positions affected.

RISK.KILL_SWITCH_LIFT — Kill switch lifted: condition resolved, system returning
to normal operation.

RISK.POSITION_LIMIT_CHECK — Position limit checks: current count, limit, result.

RISK.EXPOSURE_LIMIT_CHECK — Exposure limit checks: current exposure, limit, result.

RISK.STRESS_TEST — Pre-trade stress test results: scenarios run, worst-case loss,
pass/fail.

RISK.DRAWDOWN_WARNING — Strategy drawdown approaching threshold: current drawdown,
threshold, strategy.

---

## 2.10 Category 9 — Learning Logs (LEARNING)

**Namespace:** LEARNING
**Owner:** Learning System Engine Owner
**Severity Profile:** DEBUG to WARNING
**Retention:** 30 days operational, 1 year archive
**Routing:** Operational log, telemetry, analytics

Learning logs record the IIOS learning system's activity: strategy performance
tracking, win rate updates, strategy auto-disable events.

**Sub-categories:**

LEARNING.PERFORMANCE_UPDATE — Strategy performance updated after a closed trade:
trade outcome, updated win rate, updated Sharpe, trade count.

LEARNING.STRATEGY_DISABLE — Strategy auto-disabled due to poor performance:
strategy ID, trigger condition, current metrics.

LEARNING.STRATEGY_ENABLE — Strategy re-enabled after recovery: metrics at
re-enable, conditions met.

LEARNING.REGIME_MAP_UPDATE — Regime-strategy map updated: which regime, which
strategies updated, weight changes.

LEARNING.KNOWLEDGE_DECAY — Historical performance records decayed: decay factor
applied, affected strategies.

---

## 2.11 Category 10 — Simulation Logs (SIMULATION)

**Namespace:** SIMULATION
**Owner:** Market Simulation Engine Owner
**Severity Profile:** DEBUG to WARNING
**Retention:** 30 days operational
**Routing:** Operational log

Simulation logs record Monte Carlo simulation runs, scenario analysis, and stress
testing activity.

**Sub-categories:**

SIMULATION.MONTE_CARLO — Monte Carlo run: scenario count, random seed, variance
model, run duration, results summary.

SIMULATION.SCENARIO — Per-scenario results: scenario name, severity, simulated P&L,
pass/fail against threshold.

SIMULATION.STRESS_TEST — Stress test summary: which stress scenarios were applied,
worst case, pass/fail decision.

SIMULATION.BACKTEST — Backtesting run: strategy, date range, trade count, performance
metrics.

---

## 2.12 Category 11 — Strategy Logs (STRATEGY)

**Namespace:** STRATEGY
**Owner:** Strategy Lab Engine Owner
**Severity Profile:** DEBUG to WARNING
**Retention:** 30 days operational, 90 days archive
**Routing:** Operational log, analytics

Strategy logs record the behavior of trading strategies: signal generation, entry
and exit logic, parameter changes.

**Sub-categories:**

STRATEGY.SIGNAL — A trading signal generated: strategy ID, symbol, signal type,
signal strength, timestamp.

STRATEGY.ENTRY_FILTER — Entry filter results: which candidates were filtered and why.

STRATEGY.NO_SIGNAL — A strategy ran but produced no signal: conditions checked,
reason no signal.

STRATEGY.PARAMETER_CHANGE — Strategy parameters changed (configuration event
also recorded in config audit): old and new parameters, reason.

STRATEGY.EVOLUTION — Strategy evolution events in Research Lab: parent strategy,
mutation applied, initial fitness.

STRATEGY.PROMOTION — Strategy promoted from lab to active: promotion gate scores
(win rate, Sharpe, drawdown).

STRATEGY.DEMOTION — Strategy demoted from active to lab: performance metrics at
demotion, reason.

---

## 2.13 Category 12 — Governance Logs (GOVERNANCE)

**Namespace:** GOVERNANCE
**Owner:** Architecture Council
**Severity Profile:** INFO to CRITICAL
**Retention:** 5 years operational, permanent archive
**Routing:** Operational log, audit log, Telegram (Architecture Council)

Governance logs record system governance events: configuration changes, strategy
promotions/demotions, emergency overrides, architecture decisions.

**Sub-categories:**

GOVERNANCE.CONFIG_CHANGE — A configuration change was applied (also in config
audit): namespace, key, old value, new value, approver.

GOVERNANCE.EMERGENCY_OVERRIDE — Emergency override activated: what was overridden,
by whom, authorization reference.

GOVERNANCE.ARCHITECTURE_DECISION — A significant architectural decision was made:
decision summary, alternatives considered, decision record reference.

GOVERNANCE.POLICY_CHANGE — A policy (risk policy, decision policy) was changed:
policy name, old definition, new definition, approver.

---

## 2.14 Category 13 — Security Logs (SECURITY)

**Namespace:** SECURITY
**Owner:** Architecture Council
**Severity Profile:** INFO to CRITICAL
**Retention:** 1 year operational, 5 years archive
**Routing:** Operational log, security audit log, Architecture Council alerts

Security logs record security-relevant events: access control decisions, secret
rotation, suspicious activity, authentication events.

**Sub-categories:**

SECURITY.ACCESS — Access control decisions: who requested access, to what, result.

SECURITY.AUTH — Authentication events: successful logins, failed login attempts.

SECURITY.SECRET_ROTATION — Secret rotation events: which secret was rotated,
rotation outcome.

SECURITY.VIOLATION — Security violations: unauthorized access attempt, secret
exposure detected, configuration injection attempt.

SECURITY.SCAN — Security scan results: secret scanner, configuration validator,
dependency vulnerability scan.

---

## 2.15 Category 14 — Audit Logs (AUDIT)

**Namespace:** AUDIT
**Owner:** Architecture Council (for governance audits); Engine Owner (for engine audits)
**Severity Profile:** INFO to CRITICAL (all are treated as CRITICAL for retention)
**Retention:** Permanent (never deleted)
**Routing:** Immutable audit store (separate from operational log)

Audit logs are the tamper-evident, permanent record of governance-significant events.

**Sub-categories:**

AUDIT.ORDER — Every order placed, modified, or cancelled: complete order details,
decision reference, market conditions at placement.

AUDIT.KILL_SWITCH — Every kill switch event: trigger, portfolio state, response,
resolution. Permanent record.

AUDIT.CONFIG_CHANGE — Every configuration change: complete record per the audit
format defined in the Configuration Framework.

AUDIT.STRATEGY_GOVERNANCE — Strategy promotion and demotion decisions.

AUDIT.EMERGENCY — Emergency override events: full details of each emergency action.

AUDIT.COMPLIANCE — Compliance-relevant events: surveillance triggers, regulatory
reporting events.

AUDIT.ACCESS — All access to sensitive systems by human operators.

---

## 2.16 Category 15 — Performance Logs (PERFORMANCE)

**Namespace:** PERFORMANCE
**Owner:** Operations Team
**Severity Profile:** DEBUG to WARNING
**Retention:** 30 days operational, 90 days archive
**Routing:** Operational log, telemetry, monitoring (for latency alerts)

Performance logs record latency measurements, throughput metrics, and resource
utilization.

**Sub-categories:**

PERFORMANCE.LATENCY — Per-operation latency measurements: operation, latency,
threshold, WARN/CRIT status.

PERFORMANCE.CYCLE — Per-cycle performance: total cycle time, per-layer breakdown.

PERFORMANCE.THROUGHPUT — Data throughput metrics: messages processed, events published.

PERFORMANCE.RESOURCE — Resource utilization: CPU, memory, file descriptors,
thread counts.

PERFORMANCE.CACHE — Cache performance: hit rates, miss rates, eviction rates.

---

## 2.17 Category 16 — Infrastructure Logs (INFRA)

**Namespace:** INFRA
**Owner:** Operations Team
**Severity Profile:** INFO to CRITICAL
**Retention:** 30 days operational, 90 days archive
**Routing:** Operational log, operations team alerts

Infrastructure logs record events from the underlying infrastructure: Docker containers,
OS, network, storage.

**Sub-categories:**

INFRA.CONTAINER — Container lifecycle events: started, stopped, restarted, OOM killed.

INFRA.NETWORK — Network events: connectivity, DNS resolution, VPN status.

INFRA.STORAGE — Disk events: usage thresholds, I/O errors, backup events.

INFRA.OS — Operating system events: resource exhaustion, system calls.

---

## 2.18 Category 17 — Deployment Logs (DEPLOY)

**Namespace:** DEPLOY
**Owner:** Operations Team
**Severity Profile:** INFO to CRITICAL
**Retention:** 30 days operational, 6 months archive
**Routing:** Operational log, operations team notifications

Deployment logs record system deployment events: image builds, container deployments,
health checks post-deployment.

**Sub-categories:**

DEPLOY.BUILD — Docker image build events: version built, build duration, build result.

DEPLOY.DEPLOY — Deployment events: which version deployed, to which environment,
deployment result.

DEPLOY.HEALTH_CHECK — Post-deployment health checks: both containers healthy/unhealthy.

DEPLOY.ROLLBACK — Deployment rollback events: which version restored, reason.

---

## 2.19 Category 18 — Diagnostic Logs (DIAG)

**Namespace:** DIAG
**Owner:** Engine Owner (for engine diagnostics); Operations (for system diagnostics)
**Severity Profile:** DEBUG only (never written in production by default)
**Retention:** 7 days operational (no archive)
**Routing:** Diagnostic log only (not operational log, not telemetry)

Diagnostic logs record verbose debug information enabled on demand for troubleshooting.

**Sub-categories:**

DIAG.STATE_DUMP — Complete internal state of an engine at a diagnostic checkpoint.

DIAG.VARIABLE_TRACE — Values of specific variables at computation points.

DIAG.CALL_TRACE — Complete call stack at a point of interest.

DIAG.TIMING_BREAKDOWN — Sub-millisecond timing of operations within a single
function call.

---

## 2.20 Category 19 — Exception Logs (EXCEPTION)

**Namespace:** EXCEPTION
**Owner:** Engine Owner for engine exceptions; Architecture Council for system exceptions
**Severity Profile:** WARNING to CRITICAL
**Retention:** 90 days operational, 1 year archive
**Routing:** Operational log, exception tracking system, monitoring alerts

Exception logs record all exceptions caught during system operation.

**Sub-categories:**

EXCEPTION.HANDLED — A caught and handled exception: exception type, message, stack
trace, recovery action taken.

EXCEPTION.UNHANDLED — An unhandled exception that propagated: exception type,
message, stack trace, system impact.

EXCEPTION.DATA_FEED — Data feed exceptions: feed type, failure mode, fallback activated.

EXCEPTION.BROKER — Broker API exceptions: operation attempted, failure mode, retry status.

EXCEPTION.TIMEOUT — Timeout exceptions: operation that timed out, timeout value,
retry or abort decision.

---

## 2.21 Category 20 — Recovery Logs (RECOVERY)

**Namespace:** RECOVERY
**Owner:** Operations Team
**Severity Profile:** WARNING to CRITICAL
**Retention:** 90 days operational, 1 year archive
**Routing:** Operational log, operations team alerts, audit log (for serious recoveries)

Recovery logs record system recovery events: component restarts, state reconstruction,
fallback activations.

**Sub-categories:**

RECOVERY.COMPONENT_RESTART — A component was restarted: component, restart count,
trigger condition.

RECOVERY.STATE_RECONSTRUCTION — State was reconstructed from checkpoint or database:
what was reconstructed, data coverage.

RECOVERY.FALLBACK_ACTIVATION — A fallback was activated: primary failure, fallback
used, data quality with fallback.

RECOVERY.FULL_SYSTEM_RECOVERY — A full system recovery was performed: duration,
recovery path, data integrity assessment.

---

## 2.22 Category 21 — Monitoring Logs (MONITOR)

**Namespace:** MONITOR
**Owner:** Operations Team
**Severity Profile:** INFO to WARNING
**Retention:** 30 days operational
**Routing:** Monitoring log (separate from operational log to prevent feedback loops)

Monitoring logs record the activity of the monitoring system itself.

**Sub-categories:**

MONITOR.CHECK_RESULT — Result of a scheduled monitoring check.

MONITOR.ALERT_TRIGGERED — An alert was triggered: alert rule, trigger condition.

MONITOR.ALERT_RESOLVED — An alert was resolved: original trigger time, resolution.

MONITOR.DRIFT_DETECTED — Configuration drift detected: affected namespace.

---

## 2.23 Category 22 — Health Logs (HEALTH)

**Namespace:** HEALTH
**Owner:** Operations Team (system health); Engine Owners (engine health)
**Severity Profile:** INFO to CRITICAL
**Retention:** 30 days operational, 90 days archive
**Routing:** Operational log, telemetry, dashboard, Telegram (CRITICAL)

Health logs record OHS score changes and health check results.

**Sub-categories:**

HEALTH.OHS_UPDATE — OHS score updated: component, previous score, new score,
contributing factors.

HEALTH.TIER_TRANSITION — OHS tier changed: component, from tier, to tier, timestamp.

HEALTH.CHECK_RESULT — Result of a scheduled health check: check type, result.

HEALTH.DEGRADATION — Component health degrading: component, degradation trend.

---

## 2.24 Category 23 — Telemetry Logs (TELEMETRY)

**Namespace:** TELEMETRY
**Owner:** Architecture Council (framework); Engine Owners (engine telemetry)
**Severity Profile:** INFO only
**Retention:** 90 days operational, 1 year archive
**Routing:** Telemetry store (separate from operational log)

Telemetry logs are structured records written to the telemetry database for analytics.

**Sub-categories:**

TELEMETRY.CYCLE — Per-cycle telemetry: cycle ID, layers executed, total time,
decisions made, orders placed.

TELEMETRY.STRATEGY — Per-strategy performance telemetry: win rate trend,
Sharpe trend, drawdown.

TELEMETRY.AGENT_QUALITY — Debate agent quality telemetry: argument diversity,
score distribution, prediction accuracy.

TELEMETRY.FEED — Data feed telemetry: feed used, latency, staleness.

---

## 2.25 Category 24 — Compliance Logs (COMPLIANCE)

**Namespace:** COMPLIANCE
**Owner:** Architecture Council (framework); Compliance Officer (access and reporting)
**Severity Profile:** INFO to CRITICAL
**Retention:** 5 years operational, permanent archive
**Routing:** Compliance log (separate store), audit log, Architecture Council notifications

Compliance logs record events relevant to regulatory compliance.

**Sub-categories:**

COMPLIANCE.ORDER_AUDIT — Complete order audit record per regulatory requirements.

COMPLIANCE.POSITION_REPORT — Position reporting events for threshold positions.

COMPLIANCE.SURVEILLANCE — Surveillance check results: wash trade check, spoofing
check, order-to-trade ratio.

COMPLIANCE.REGULATORY_EVENT — Reportable events to regulatory authorities.

---

*End of Part II*

---# PART III — FRAMEWORK ARCHITECTURE

## 3.1 Architecture Overview

The Logging and Observability Framework Architecture defines 19 components that
collectively provide complete observability for IIOS. These components manage the
complete journey of observability data from generation to archival.

`
FRAMEWORK ARCHITECTURE — COMPONENT MAP

[Log Sources: Engines, Agents, Workflows, Infrastructure]
         |
         v
[Log Collector] -----> [Log Validator / Sanitizer]
         |
         v
[Log Router] -------> [Log Storage Manager]
    |                        |
    |                 [Log Aggregator]
    |                        |
    +-------> [Metrics Manager] <---- [Telemetry Manager]
    |
    +-------> [Tracing Manager]
    |
    +-------> [Alert Manager] -----> [Notifications]
    |
    +-------> [Audit Manager]
    |
    +-------> [Monitoring Manager] <---- [Health Manager]
    |                                         |
    +-------> [Dashboard Manager] <----------+
    |
[Analytics Manager]
         |
[Retention Manager] -----> [Archive Manager] -----> [Recovery Manager]

[Logging Registry] <----> [Logging Catalog]
[Logging Manager] (orchestrates all components)
`

---

## 3.2 Component 1 — Logging Registry

### Purpose
The Logging Registry is the central catalog of all defined log event types, their
schemas, classification rules, routing rules, and retention policies. It is the
reference that makes logging consistent across all IIOS components.

### Responsibilities
- Maintain the authoritative list of all log event types and their metadata.
- Store schema definitions for each log event type (required fields, field types,
  validation rules).
- Store classification rules (category, severity, sensitivity).
- Store routing rules (which sinks receive which event types).
- Store retention policies (operational retention, archive retention).
- Detect unregistered log event types (events emitted by code but not in the Registry).
- Serve as the reference for documentation and training materials.

### Inputs
- Registration requests from engines at startup.
- Schema definition files from docs/logging/ directory.
- Existing Registry state on system restart.

### Outputs
- Complete event type catalog (for documentation).
- Schema reference (for validation).
- Routing reference (for the Log Router).
- Retention reference (for the Retention Manager).
- Unregistered event type alerts.

### Dependencies
- Schema definition files (must exist before Registry initializes).
- No runtime dependencies on other logging components.

### Interactions
- Log Validator queries Registry for schema validation.
- Log Router queries Registry for routing rules.
- Retention Manager queries Registry for retention policies.
- Logging Catalog reads Registry for catalog generation.

### Failure Modes
- **Schema parse error:** Registry initialization fails. System startup is blocked
  until the schema error is fixed.
- **Registration conflict:** Two components attempt to register the same event type
  differently. The conflict is logged, second registration is rejected, and a startup
  warning is raised.
- **Missing schema:** Specific component's event types are unregistered. The component
  is warned at startup.

### Recovery Strategy
- Parse error: Fix the schema file and restart.
- Registration conflict: Trace the two registrations, resolve naming conflict, restart.
- Missing schema: Register the schema and restart (or continue with unvalidated events
  at DEGRADED health status).

### Monitoring
- Registry initialization time: target < 1,000ms.
- Registered event type count: tracked over time.
- Unregistered event type rate: target 0.

### Engineering Notes
- The Registry is initialized before all other logging components. It is the
  first component in the startup sequence.
- The Registry is read-heavy and write-once after initialization.
- The Registry is the source for auto-generated logging documentation.

---

## 3.3 Component 2 — Logging Catalog

### Purpose
The Logging Catalog provides a human-readable, searchable, and documented view of
all log event types and their current production volumes, patterns, and statistics.

### Responsibilities
- Generate documentation for every registered log event type.
- Provide search capability by namespace, event type, severity, and keyword.
- Display event type documentation alongside example log records.
- Generate volume statistics per event type (events per hour, per day).
- Produce log coverage reports (which system components are producing logs).
- Identify log silence (expected events not appearing).

### Outputs
- Documentation (Markdown) for the docs/ system.
- Volume statistics reports.
- Coverage reports.
- Log silence alerts.

### Engineering Notes
- The Catalog is generated periodically (on CI run, on schema change, daily).
- Log volume statistics are read from the Log Storage Manager's metadata.

---

## 3.4 Component 3 — Logging Manager

### Purpose
The Logging Manager is the central orchestrator of the logging framework. It
coordinates all logging components, enforces logging governance, and provides
the runtime management interface for the logging system.

### Responsibilities
- Coordinate startup and shutdown of all logging components.
- Enforce logging governance rules: log level settings, sink configurations.
- Manage logging component health (if a sink fails, manage the fallback).
- Provide the administrative interface for logging system management.
- Apply global log sampling rules (for very high-volume debug events).
- Manage log context propagation (correlation ID injection).
- Monitor the logging system's own performance.
- Handle log level overrides (e.g., temporarily increase verbosity for an engine).

### Inputs
- Configuration (from the Configuration Framework).
- Component health reports (from all logging components).
- Administrative commands (from operators via CLI).
- Log context (from the request/cycle context propagation system).

### Outputs
- Runtime logging configuration applied to all components.
- Component health aggregate.
- Administrative responses.
- Log system performance metrics.

### Dependencies
- Configuration Framework (for logging configuration).
- All logging components (coordinates them).

### Failure Modes
- **Manager crash:** Logging continues using the last known configuration. Components
  operate independently without central coordination. An alert is raised.
- **Configuration load failure:** The Manager uses the last known configuration.
  Any dynamic configuration changes are queued and applied when configuration
  is restored.

---

## 3.5 Component 4 — Log Collector

### Purpose
The Log Collector is the ingestion point for all log events from all IIOS components.
It receives log records from engine loggers, validates their format, and hands them
to the Log Router.

### Responsibilities
- Receive log events from all engines, agents, workflows, and infrastructure.
- Buffer incoming events to handle burst traffic without dropping records.
- Apply the Sanitizer (remove sensitive values before any further processing).
- Validate log event format (required fields present, field types correct).
- Assign missing automatic fields (timestamp, correlation ID if absent).
- Enqueue validated events for routing.
- Enforce backpressure on high-volume sources to prevent memory overflow.

### Inputs
- Log events from all IIOS components via logging libraries.
- Direct log entries from infrastructure components.
- Container stdout/stderr (captured and structured).

### Outputs
- Sanitized, validated, enriched log events to the Log Router queue.

### Buffer Strategy
The Log Collector maintains an in-memory buffer with the following properties:
- Maximum size: configurable (default 50,000 events).
- Overflow strategy: Oldest events are dropped (FIFO eviction), with a counter of
  dropped events logged at WARNING level.
- Flush interval: 100ms (events are not held longer than 100ms in the buffer).
- Critical event bypass: Events at CRITICAL severity bypass the buffer and are
  processed immediately, synchronously.

### Failure Modes
- **Buffer overflow:** Non-critical events are dropped. A counter of dropped events
  is maintained and reported. Critical and audit events are never dropped.
- **Sanitizer failure:** The event is dropped (not written unsanitized). An error
  is logged to the diagnostic channel.
- **Validation failure:** The event is written to a quarantine log with the validation
  errors noted. It is not routed to operational sinks.

### Monitoring
- Buffer utilization percentage (alert if > 80%).
- Dropped event count (alert if > 0 per 5 minutes for non-DEBUG events).
- Ingest rate (events per second, tracked for capacity planning).

---

## 3.6 Component 5 — Log Router

### Purpose
The Log Router determines which storage sinks each log event is written to, based
on the event's category, severity, and routing rules from the Logging Registry.

### Responsibilities
- Route each event to the appropriate set of sinks.
- Apply routing rules from the Logging Registry.
- Handle sink failures gracefully (route to fallback sinks).
- Apply per-sink filtering (e.g., send only WARN+ to the alert evaluator).
- Route audit events to the audit-specific storage path.
- Route telemetry events to the telemetry store.
- Apply fan-out for events that must go to multiple sinks simultaneously.

### Routing Rules Reference

| Event Category | Operational Log | Audit Store | Telemetry Store | Alert Evaluator | Dashboard |
|---------------|-----------------|-------------|-----------------|-----------------|-----------|
| SYSTEM.* | Yes | CRITICAL only | OHS events | ERROR+ | Yes |
| ENGINE.* | Yes | No | PERFORMANCE | ERROR+ | Yes |
| DECISION.* | Yes | APPROVE/REJECT | All | REJECT anomalies | Yes |
| RISK.* | Yes | KILL_SWITCH | All | CRITICAL | Yes |
| AUDIT.* | Yes | Always | No | Always | CRITICAL only |
| SECURITY.* | Yes | VIOLATION | No | VIOLATION | CRITICAL |
| COMPLIANCE.* | Yes | Always | No | CRITICAL | No |
| TELEMETRY.* | No | No | Always | No | Charts |
| DIAG.* | Diag log only | No | No | No | No |

### Failure Modes
- **Primary sink unavailable:** Events are routed to the fallback sink and the
  primary sink issue is alerted. Critical events are retried to the primary.
- **All sinks for a category unavailable:** Events are buffered in the Collector
  buffer. An immediate CRITICAL alert is raised.

### Engineering Notes
- The Router is the highest-throughput component. It must process events in
  microseconds to avoid becoming the system bottleneck.
- Routing rules are loaded at startup and cached. Dynamic routing rule changes
  require a routing rule reload (non-disruptive).

---

## 3.7 Component 6 — Log Aggregator

### Purpose
The Log Aggregator groups related log events to provide higher-level views of
system activity. It transforms the raw event stream into aggregated summaries
that are more useful for monitoring and analysis.

### Responsibilities
- Correlate log events from multiple components into a single logical unit
  (e.g., all events from one decision cycle, all events from one trade lifecycle).
- Compute per-cycle summaries: decisions made, orders placed, latencies.
- Detect log event sequences indicating specific patterns (success, failure,
  anomaly).
- Generate aggregate log views for the dashboard and analytics.
- Support log search by aggregation key (find all events from a specific cycle,
  all events related to a specific trade).

### Aggregation Keys
- cycle_id — Groups all events from one decision cycle.
- 	rade_id — Groups all events from one trade lifecycle (decision to close).
- session_id — Groups all events from one trading session.
- strategy_id — Groups all events related to one strategy.
- correlation_id — Groups all events from one request or operation.

---

## 3.8 Component 7 — Log Storage Manager

### Purpose
The Log Storage Manager persists log events to durable storage, managing multiple
storage tiers with different retention policies and access patterns.

### Responsibilities
- Write log events to the appropriate storage tier.
- Manage the transition from hot storage (recent, fast access) to warm storage
  (recent weeks, moderate access) to cold archive storage (historical, slow access).
- Enforce retention policies: delete expired events per category policy.
- Provide search and query capability over stored logs.
- Monitor storage utilization and alert before capacity is exceeded.
- Manage log file rotation and compression.

### Storage Tiers

**Hot storage:** Recent 7 days of operational logs. In-memory index for fast search.
Uncompressed. Target query latency: < 100ms.

**Warm storage:** 7–90 days of operational logs. On-disk with index. Compressed
(gzip). Target query latency: < 5 seconds.

**Cold archive:** 90 days to retention limit. Compressed and archived. No index.
Restored to warm tier on demand. Target query latency: minutes.

**Audit store:** Separate from operational tiers. Append-only, encrypted, hash-chained.
All retention periods are permanent for audit events.

### Log File Organization

`
logs/
|-- operational/
|   |-- app/
|   |   |-- app-YYYY-MM-DD.log       [current day]
|   |   |-- app-YYYY-MM-DD.log.gz    [compressed previous days]
|   |-- engine/
|   |   |-- [engine_name]-YYYY-MM-DD.log
|   |-- decisions/
|   |   |-- decisions-YYYY-MM-DD.log
|   |-- risk/
|   |   |-- risk-YYYY-MM-DD.log
|   |-- exceptions/
|       |-- exceptions-YYYY-MM-DD.log
|-- audit/
|   |-- audit-YYYY-MM-DD.log         [immutable, encrypted]
|   |-- audit-chain.index            [hash chain index]
|-- telemetry/
|   |-- telemetry.db                 [SQLite telemetry database]
|-- diagnostic/
|   |-- [engine]-diag-YYYY-MM-DD.log [only written when diag mode active]
|-- archive/
    |-- [year]/[month]/              [archived compressed logs]
`

### Failure Modes
- **Write failure (non-critical event):** Event is buffered for retry. Alert raised
  if write fails persist beyond 60 seconds.
- **Write failure (critical/audit event):** System writes to secondary storage
  immediately. A CRITICAL alert is raised. The failing primary storage is investigated.
- **Storage full:** Monitoring alerts at 80% and 90% capacity. At 95%, non-audit,
  non-compliance events beyond their retention period are immediately purged.

### Monitoring
- Storage utilization per tier (alert at 80%, CRITICAL at 90%).
- Write latency (target: < 5ms for hot tier writes).
- Failed write count (target: 0 for CRITICAL/AUDIT events).
- Rotation success rate (target: 100%).

---

## 3.9 Component 8 — Metrics Manager

### Purpose
The Metrics Manager collects, aggregates, and stores numerical measurements of
system performance and operational health. It produces the time-series data used
by dashboards, alerts, and analytics.

### Responsibilities
- Collect metrics from all IIOS components on defined collection intervals.
- Aggregate metrics from the log event stream (count events, compute latency
  percentiles from latency log events).
- Store metrics in a time-series format optimized for range queries.
- Provide metrics to the Dashboard Manager for visualization.
- Provide metrics to the Alert Manager for threshold evaluation.
- Expose a metrics query interface for analytics.
- Manage metrics retention (shorter than log retention — metrics are summaries).

### Metric Types

**Counters:** Monotonically increasing values. Examples: total cycles run, total
orders placed, total decisions approved, total kill switch triggers.

**Gauges:** Point-in-time values. Examples: current open positions, current daily
P&L, current VIX value, current memory usage.

**Histograms:** Distribution of values. Examples: cycle latency distribution, decision
score distribution, trade P&L distribution.

**Rates:** Derived from counters over time. Examples: decisions per hour, orders per
session, exceptions per day.

### Key IIOS Metrics (see Supplement C for complete catalog)

**System metrics:**
- iios.system.health_score — Current system OHS (0.0–1.0).
- iios.system.cycle_duration_ms — Last cycle execution time.
- iios.system.active_since_days — Days since last system restart.

**Trading metrics:**
- iios.trading.open_positions — Current open position count.
- iios.trading.daily_pnl_pct — Current day P&L as portfolio percentage.
- iios.trading.daily_decisions — Decisions made today.
- iios.trading.daily_orders — Orders placed today.

**Risk metrics:**
- iios.risk.vix_current — Current India VIX value.
- iios.risk.kill_switch_active — Boolean: is kill switch currently active.
- iios.risk.daily_loss_pct — Current daily loss as portfolio percentage.

**Engine metrics:**
- iios.engine.[name].health_score — Per-engine OHS.
- iios.engine.[name].last_execution_ms — Last execution latency.
- iios.engine.[name].error_count_1h — Errors in last hour.

**Strategy metrics:**
- iios.strategy.[id].win_rate — Strategy win rate (rolling 30 days).
- iios.strategy.[id].sharpe — Strategy Sharpe ratio.
- iios.strategy.[id].active — Boolean: strategy is active.

### Monitoring
- Metrics collection success rate (target: 100% for critical metrics).
- Metrics store write latency.
- Metrics query latency (dashboard impact).

---

## 3.10 Component 9 — Tracing Manager

### Purpose
The Tracing Manager captures distributed traces of computation across the multi-engine
IIOS pipeline, providing end-to-end visibility into how requests and cycles flow
through the system.

### Responsibilities
- Initiate traces for full decision cycles.
- Propagate trace context (trace ID, span ID) across engine boundaries.
- Record spans for each engine's contribution to the trace.
- Store completed traces in the trace store.
- Provide trace search and visualization data.
- Compute trace statistics: end-to-end latency, per-span latency, slow span detection.
- Identify bottleneck engines from trace data.

### Trace Anatomy

A trace is a collection of spans. Each span represents one operation in the trace.

`
TRACE: cycle-20260704-093000-001 [FULL DECISION CYCLE]

Span: global_intelligence_fetch [17ms]
  |--> Sub-span: cache_check [1ms] HIT
  |--> Sub-span: return_cached [0ms]

Span: market_intelligence_classify [19ms]
  |--> Sub-span: regime_classify [12ms]
  |--> Sub-span: sector_analyze [7ms]

Span: meta_learning_predict [8ms]
Span: opportunity_scan [35ms]
  |--> Sub-span: equity_scan [20ms]
  |--> Sub-span: score_candidates [15ms] (8 candidates)

Span: strategy_signals [22ms]
Span: capital_allocation [11ms]
Span: risk_control [14ms]
Span: market_simulation [28ms] (14 scenarios)
Span: risk_guardian_check [3ms] ALLOW
Span: debate_and_decision [45ms]
  |--> Sub-span: agent_signal_analysis [8ms]
  |--> Sub-span: agent_contrarian [9ms]
  |--> Sub-span: agent_risk [8ms]
  |--> Sub-span: agent_opportunity [9ms]
  |--> Sub-span: agent_synthesis [11ms]

Span: execution_engine [4ms] ORDER_PLACED
Span: trade_monitoring_register [2ms]
Span: learning_update [1ms]
Span: control_tower_telemetry [1ms]

TOTAL TRACE DURATION: 172ms [HEALTHY]
`

### Trace Sampling Strategy
- Full cycles during market hours: 100% sampled (every cycle is traced).
- Pre-market cycles: 100% sampled.
- EOD learning cycles: 100% sampled.
- Duplicate (no-signal) cycles: 10% sampled.
- Error paths: 100% sampled (always trace errors).

### Engineering Notes
- Trace context is propagated through the event bus and direct method calls.
- The trace ID is also included in every log event for correlation.

---

## 3.11 Component 10 — Health Manager

### Purpose
The Health Manager computes and tracks the Operational Health Score (OHS) for
every component and the system as a whole, implementing the OHS framework as
defined in the IIOS architecture.

### Responsibilities
- Run health checks for each engine and system component on a defined interval.
- Compute the OHS score (0.0 to 1.0) for each component.
- Classify each component's OHS into a tier (OPTIMAL, NOMINAL, DEGRADED,
  CRITICAL, FAILED).
- Compute the system-wide aggregate OHS.
- Publish health events to the Event Bus.
- Provide health history for trend analysis.
- Alert the Alert Manager when a component crosses a tier boundary downward.

### OHS Constitutional Tiers

These tier boundaries are constitutional (cannot be changed without Architecture
Council unanimous vote):

| Tier | OHS Range | Color | Response Required |
|------|-----------|-------|-------------------|
| OPTIMAL | 0.95 ≤ OHS ≤ 1.00 | Green | None |
| NOMINAL | 0.80 ≤ OHS < 0.95 | Yellow | Monitor |
| DEGRADED | 0.60 ≤ OHS < 0.80 | Orange | Investigate |
| CRITICAL | 0.35 ≤ OHS < 0.60 | Red | Immediate action |
| FAILED | OHS < 0.35 | Black | Emergency response |

### OHS Score Computation

Each component's OHS is computed from weighted sub-scores:

`
ENGINE OHS COMPUTATION

Sub-score 1: Error rate in last 5 minutes
  0 errors → 1.0, 1 error → 0.9, 2 errors → 0.8, 5+ errors → 0.0
  Weight: 30%

Sub-score 2: Last execution latency vs threshold
  < WARN threshold → 1.0
  WARN to CRIT → linear interpolation 0.7 to 0.4
  > CRIT threshold → 0.0
  Weight: 30%

Sub-score 3: Output validity (last output valid) → 1.0 or 0.0
  Weight: 20%

Sub-score 4: Dependency health (average OHS of dependencies)
  Weight: 20%

ENGINE OHS = 0.30*(error_score) + 0.30*(latency_score)
           + 0.20*(output_score) + 0.20*(dependency_score)
`

### Special Engine Health Rules

**Risk Guardian:** If the Risk Guardian fails to complete a kill switch check,
its OHS immediately drops to FAILED (0.0) regardless of other sub-scores.
A failed Risk Guardian is a system-level CRITICAL emergency.

**Execution Engine:** If the Execution Engine cannot reach the broker (paper or live),
its OHS drops to DEGRADED (0.70). If it cannot place orders due to an internal error,
it drops to CRITICAL.

### Monitoring
- Health check interval compliance (checks must run on schedule).
- Health manager OHS (the health manager itself has an OHS — meta-health).
- Tier transition frequency (frequent oscillations indicate instability).

---

## 3.12 Component 11 — Alert Manager

### Purpose
The Alert Manager is the rule-based evaluation engine that transforms the log and
metrics stream into actionable human notifications. It is the bridge between the
observability system and the human operators.

### Responsibilities
- Evaluate alert rules against the real-time log and metrics stream.
- Apply alert thresholds and conditions to detect alert situations.
- Apply deduplication: do not re-alert for the same condition within the
  deduplication window.
- Apply grouping: combine multiple related alerts into a single notification.
- Manage alert severity: CRITICAL, ERROR, WARNING, INFO alert levels.
- Route alerts to appropriate recipients via the notification channels.
- Track alert resolution: an alert is active until its condition resolves.
- Maintain alert history for pattern analysis.

### Alert Rule Structure

Each alert rule defines:
- **Condition:** What condition triggers the alert (threshold, pattern, absence).
- **Severity:** CRITICAL, ERROR, WARNING, INFO.
- **Channel:** Where to send the alert (Telegram, dashboard, email).
- **Deduplication window:** How long before the same alert can fire again.
- **Resolution condition:** What condition closes the alert.
- **Message template:** What to send to the operator.

### IIOS Alert Categories

**CRITICAL alerts (immediate human response required):**
- Kill switch triggered.
- System OHS enters CRITICAL or FAILED tier.
- Any engine OHS enters FAILED tier.
- Risk Guardian OHS drops below 0.5.
- Execution Engine cannot place orders.
- Daily loss exceeds 1.5% (pre-kill-switch warning).
- Audit chain integrity failure.
- Backup overdue by > 4 hours.

**ERROR alerts (response required within 1 hour):**
- Any engine OHS enters CRITICAL tier.
- Data feed primary failure (fallback activated).
- Decision cycle duration > 5,000ms.
- Exception rate > 10 per hour for any engine.
- Configuration drift detected.

**WARNING alerts (response required within 1 day):**
- Any engine OHS enters DEGRADED tier.
- Strategy win rate below 40% (approaching auto-disable threshold).
- Log storage utilization > 80%.
- Memory usage > 80%.
- Any strategy drawdown > 10% (approaching 15% threshold).

**INFO alerts (no action required — informational):**
- System startup complete.
- Kill switch lifted.
- Strategy promoted to active.
- Daily P&L summary.

### Deduplication and Rate Limiting
- CRITICAL alerts: no deduplication (every occurrence is reported).
- ERROR alerts: 15-minute deduplication window.
- WARNING alerts: 60-minute deduplication window.
- INFO alerts: 4-hour deduplication window.
- Maximum alerts per hour: 20 (prevents alert storms from overwhelming operators).

---

## 3.13 Component 12 — Monitoring Manager

### Purpose
The Monitoring Manager provides the continuous oversight layer that watches the
running IIOS system and ensures proactive problem detection before issues become
incidents.

### Responsibilities
- Run scheduled monitoring checks (latency, health, resource usage, data freshness).
- Detect anomalies in the log and metrics stream.
- Correlate events across multiple components to detect cross-cutting issues.
- Monitor the monitoring system itself (meta-monitoring).
- Produce monitoring reports for the daily health review.
- Manage the monitoring schedule: some checks run every 30 seconds, others every 5 minutes.

### Monitoring Check Schedule

| Check Category | Interval | Trigger Condition |
|---------------|----------|-------------------|
| Engine latency | Every cycle | > WARN threshold |
| OHS scores | Every 30s | Tier change |
| Data feed health | Every 60s | Feed unavailable |
| Kill switch conditions | Every 60s | VIX > 40 or daily loss > 1.5% |
| Log storage utilization | Every 5m | > 80% |
| Audit chain integrity | Daily | Chain break |
| Backup freshness | Every hour | Backup > 25h old |
| Configuration drift | Every 5m | Hash mismatch |
| Open alert count | Every 15m | > 5 active alerts |

### Anomaly Detection

The Monitoring Manager implements pattern-based anomaly detection:

**Latency anomaly:** Cycle latency suddenly increases by > 50% vs 5-minute moving
average. Indicates a component degradation.

**Error rate anomaly:** Error rate for any engine increases by > 200% vs 1-hour
baseline. Indicates a new problem.

**Decision silence:** No decisions (approve or reject) produced for 30+ minutes
during market hours. Indicates pipeline blockage.

**Log silence:** An expected log source produces no events for 10+ minutes.
Indicates the component may have stopped operating.

**Data staleness:** Global Intelligence cache not refreshed for > 10 minutes.
Indicates data feed issue.

---

## 3.14 Component 13 — Audit Manager

### Purpose
The Audit Manager provides the immutable, tamper-evident record of all
governance-significant events in IIOS. It is the single most important component
for compliance and accountability.

### Responsibilities
- Receive audit events from all governance-relevant components.
- Write audit records to the append-only audit store with hash-chain linking.
- Enforce audit store immutability (no delete, no modify operations exist).
- Maintain the hash chain: each record contains the hash of the previous record.
- Verify chain integrity on demand and on scheduled checks.
- Provide audit query capability (who did what, when, with what effect).
- Generate compliance reports from audit data.
- Detect tampering: any hash chain break is immediately alerted.

### Audit Record Schema (conceptual)

Each audit record contains:

| Field | Purpose |
|-------|---------|
| record_id | Unique sequential identifier |
| timestamp | ISO 8601 UTC with millisecond precision |
| event_category | AUDIT sub-category (ORDER, KILL_SWITCH, CONFIG, etc.) |
| actor | Who or what caused the event |
| operation | What was done |
| subject | What was affected |
| details | Complete structured details of the event |
| system_state | Snapshot of key system metrics at event time |
| previous_hash | SHA-256 of the previous audit record |
| record_hash | SHA-256 of this record (computed after writing) |

### Tamper Evidence Design

The hash chain works as follows:
- Record N's hash is computed from all its fields including previous_hash.
- Record N+1's previous_hash field contains Record N's ecord_hash.
- If any record is modified or deleted, Record N+1's previous_hash will not match
  the recomputed hash of Record N. The chain is broken.
- Chain integrity is verified daily and on audit export.

### Audit Store Access Control

- Write: Audit Manager only (no other component can write to the audit store).
- Read: Architecture Council members, Compliance Officer, designated auditors.
- No delete: No mechanism exists to delete audit records. The audit store is
  physically read-only for everyone except the Audit Manager's append operation.

### Failure Modes
- **Audit store write failure:** This is a blocking failure for governance-relevant
  operations. A configuration change or order placement cannot proceed without a
  successful audit record. An immediate CRITICAL alert is raised.
- **Hash chain corruption:** Detected during integrity check. This is a security
  incident. All suspected records are quarantined. Incident response is initiated.

---

## 3.15 Component 14 — Telemetry Manager

### Purpose
The Telemetry Manager collects, stores, and provides access to the structured
operational data that drives IIOS continuous improvement and performance analytics.

### Responsibilities
- Collect per-cycle telemetry records.
- Collect per-strategy performance telemetry.
- Collect per-agent debate quality telemetry.
- Collect data feed quality telemetry.
- Store telemetry in the SQLite telemetry database.
- Provide a query interface for analytics and reporting.
- Aggregate telemetry into daily, weekly, and monthly summaries.
- Detect telemetry gaps (missing records indicating system failures).

### Telemetry Schema (conceptual, not defined here)

The telemetry database (at data/databases/telemetry.db) contains tables for:
- cycle_telemetry: Per-cycle execution records.
- strategy_telemetry: Per-strategy performance records.
- gent_telemetry: Per-agent debate quality records.
- engine_health_telemetry: Per-engine OHS history.
- eed_telemetry: Data feed quality records.
- decision_telemetry: Per-decision outcome records.

### Key Telemetry Events

**Cycle telemetry (every cycle):** cycle_id, timestamp, total_duration_ms,
per_layer_duration_ms, decisions_count, orders_count, regime, vix.

**Decision telemetry (every decision):** decision_id, timestamp, symbol,
direction, score, agent_scores, outcome, strategy_id.

**Strategy telemetry (every closed trade):** trade_id, strategy_id, symbol,
entry/exit timestamps, P&L, hold_duration, regime at entry.

**Engine health telemetry (every 5 minutes):** timestamp, engine_name, ohs_score,
ohs_tier, error_count, latency_p50, latency_p95.

---

## 3.16 Component 15 — Dashboard Manager

### Purpose
The Dashboard Manager serves the real-time operational visibility interface (Streamlit
dashboard) and provides the data layer behind it.

### Responsibilities
- Serve the Streamlit dashboard on the configured port.
- Aggregate real-time data from Metrics Manager, Health Manager, and Telemetry Manager.
- Provide the dashboard with live positions, P&L, cycle metrics, strategy performance.
- Manage dashboard refresh intervals.
- Implement dashboard access control (who can view the dashboard).
- Produce dashboard snapshots for reporting.

### Dashboard Panels (architectural reference)

**System Health Panel:** System OHS, all engine OHS scores, current tier indicators.

**Trading Activity Panel:** Current open positions, today's closed trades, daily P&L,
decision count, order count.

**Cycle Performance Panel:** Last cycle latency, cycle history chart, per-layer
latency breakdown.

**Strategy Performance Panel:** Active strategies, win rate, Sharpe, drawdown per
strategy.

**Risk Panel:** Current VIX, daily loss %, kill switch status, active risk alerts.

**Data Feed Panel:** Primary feed status, fallback status, data freshness.

**Alert Panel:** Active alerts, recent alert history.

---

## 3.17 Component 16 — Analytics Manager

### Purpose
The Analytics Manager provides quantitative analysis of the IIOS operational history,
transforming telemetry and log data into actionable intelligence for system improvement.

### Responsibilities
- Generate daily, weekly, and monthly performance reports.
- Analyze decision quality trends (score distributions, approve rate, post-decision
  accuracy).
- Analyze strategy performance trends.
- Analyze system latency trends.
- Correlate system events with market events.
- Identify degradation patterns before they become incidents.
- Produce analytics reports for Architecture Council reviews.

### Key Analytics Products

**Daily Operations Report:** Cycle count, decision count, order count, P&L, health
score trend, top errors.

**Strategy Health Report:** Per-strategy: win rate trend (rolling 7, 14, 30 days),
Sharpe trend, drawdown, trade count, activity status.

**Decision Quality Report:** Score distribution, approve rate, score calibration
(predicted scores vs realized outcomes).

**Latency Report:** Cycle latency percentiles (p50, p95, p99), per-engine contribution,
latency trend, anomalies.

**Risk Event Report:** All kill switch events, near-miss events (VIX > 40 without
triggering), risk check failure counts.

---

## 3.18 Component 17 — Retention Manager

### Purpose
The Retention Manager enforces log retention policies — deleting expired operational
logs and archiving logs approaching their archival deadline.

### Responsibilities
- Enforce retention policies for each log category.
- Identify logs approaching their retention boundary and initiate archiving.
- Delete logs that have exceeded their retention period (operational logs only;
  audit logs are never deleted).
- Verify that no logs required by compliance are being deleted prematurely.
- Report retention status: how much data is retained per category, oldest record age.

### Retention Policy Reference

| Category | Operational Retention | Archive Retention | Total |
|---------|----------------------|-------------------|-------|
| SYSTEM | 90 days | 1 year | 14 months |
| ENGINE | 30 days | 90 days | 4 months |
| DECISION | 1 year | 5 years | 6 years |
| RISK | 1 year | 5 years | 6 years |
| AUDIT | Never deleted | Permanent | Permanent |
| SECURITY | 1 year | 5 years | 6 years |
| COMPLIANCE | 5 years | Permanent | Permanent |
| TELEMETRY | 90 days | 1 year | 14 months |
| INFRA | 30 days | 90 days | 4 months |
| DIAG | 7 days | No archive | 7 days |
| EXCEPTION | 90 days | 1 year | 14 months |
| PERFORMANCE | 30 days | 90 days | 4 months |

### Failure Modes
- **Accidental audit deletion attempt:** The Retention Manager's delete operation
  checks the category. Audit and compliance logs are excluded from deletion logic
  at the code level. An attempt to delete an audit log is an error condition.
- **Storage full before retention boundary:** Emergency compression is applied.
  Operational logs are compressed to free space. If still insufficient, the oldest
  non-audit, non-compliance logs are purged early (with a warning).

---

## 3.19 Component 18 — Archive Manager

### Purpose
The Archive Manager manages the long-term storage of logs beyond their operational
retention period, ensuring they remain accessible for compliance and forensic purposes.

### Responsibilities
- Receive logs from the Retention Manager for archiving.
- Compress logs for efficient long-term storage.
- Write to archive storage.
- Maintain archive index (what is archived, covering what time period).
- Provide archive retrieval (restore archived logs to warm storage for query).
- Verify archive integrity.
- Manage archive storage utilization.

### Archive Storage Organization

Archives are organized by year and month:
`
archive/
|-- 2026/
|   |-- 01/ [January 2026]
|   |   |-- SYSTEM-2026-01.tar.gz
|   |   |-- ENGINE-2026-01.tar.gz
|   |   |-- DECISION-2026-01.tar.gz
|   |-- 02/ ...
|-- 2027/ ...
`

---

## 3.20 Component 19 — Recovery Manager

### Purpose
The Recovery Manager coordinates the recovery of the logging and observability
system from failures, ensuring observability is restored quickly after any incident.

### Responsibilities
- Detect logging system failures.
- Coordinate recovery sequencing (which components to restore in which order).
- Execute recovery procedures per defined recovery scenarios.
- Validate the logging system after recovery.
- Ensure no logs are permanently lost during recovery.
- Document the recovery in the audit log.

### Recovery Scenarios

**Scenario 1 — Log Storage write failure:**
Cause: Disk full, file system error.
Recovery: Free disk space, retry writes. Buffered events are flushed.

**Scenario 2 — Audit store corruption:**
Cause: Storage failure, disk error.
Recovery: Restore audit store from backup. Reconstruct recent records from
the operations log. Treat as security incident (investigate root cause).

**Scenario 3 — Full observability system failure:**
Cause: Multiple component failures.
Recovery: Restore Log Collector first (to prevent event loss). Then restore
Storage Manager, then Router, then other components.

**Recovery priority order:**
1. Log Collector (stops event loss).
2. Audit Manager (restores compliance record).
3. Log Storage Manager (restores persistence).
4. Alert Manager (restores human notification).
5. Metrics Manager (restores performance visibility).
6. Health Manager (restores OHS).
7. Dashboard Manager (restores operator visibility).
8. Analytics Manager (restores trend analysis).

---

*End of Part III*

---

# PART IV — LOG HIERARCHY

## 4.1 Hierarchy Overview

The IIOS Log Hierarchy defines the 15 contextual levels at which log events are
generated. The hierarchy reflects the operational structure of the system: from
the widest (system-wide) to the narrowest (individual exception). Each level in
the hierarchy provides context to the events at that level.

`
LOG HIERARCHY — CONTEXTUAL LEVELS

Level 1:  SYSTEM           Widest scope — entire IIOS platform
    |
Level 2:  ENVIRONMENT      Deployment environment (production/paper/dev)
    |
Level 3:  ENGINE           Individual engine (global_intelligence, risk_guardian, etc.)
    |
Level 4:  WORKFLOW         Named multi-step process within an engine
    |
Level 5:  SERVICE          Individual service class within an engine
    |
Level 6:  AGENT            Individual AI agent (debate agents)
    |
Level 7:  SESSION          One trading session (09:15–15:30 IST)
    |
Level 8:  REQUEST/CYCLE    One decision cycle
    |
Level 9:  OPERATION        One discrete operation within a cycle
    |
Level 10: EVENT            A specific occurrence within an operation
    |
Level 11: DIAGNOSTIC       Verbose debugging information (on-demand only)
    |
Level 12: EXCEPTION        An error or anomalous condition
    |
Level 13: AUDIT            Governance-relevant events (separate path)
    |
Level 14: SECURITY         Security-relevant events (separate path)
    |
Level 15: RECOVERY         System recovery events (highest priority path)
`

---

## 4.2 Level 1 — System

**Scope:** The entire IIOS platform.
**Context fields required:** 	imestamp, system_version, environment, instance_id
**Example events:**
- System startup complete: version, startup duration, mode.
- System shutdown initiated: reason, shutdown mode (graceful/emergency).
- System mode change: from mode, to mode, reason.
- System OHS tier transition: from tier, to tier, aggregate score.

**Log format principle:** System-level events are always at INFO or above.
DEBUG-level logging does not apply at the system level.

---

## 4.3 Level 2 — Environment

**Scope:** The deployment environment configuration.
**Context fields required:** environment_name, environment_version, deployment_id
**Example events:**
- Environment configuration loaded: source files, override count.
- Environment health check: all expected services reachable.
- Environment drift detected: which components have drifted.

---

## 4.4 Level 3 — Engine

**Scope:** A single IIOS engine instance.
**Context fields required:** engine_name, engine_version, engine_start_time
**Example events:**
- Engine initialized: initialization time, dependency check results.
- Engine execution started: input summary, trigger reason.
- Engine execution completed: output summary, execution time.
- Engine OHS change: previous score, new score, contributing factors.
- Engine error: error type, impact, recovery action.

---

## 4.5 Level 4 — Workflow

**Scope:** A named workflow execution within an engine.
**Context fields required:** workflow_name, workflow_id, parent_engine, step_count
**Example events:**
- Workflow started: input parameters.
- Workflow step completed: step name, output, duration.
- Workflow step failed: step name, error, retry decision.
- Workflow completed: final output, total duration.

---

## 4.6 Level 5 — Service

**Scope:** A service class within an engine (e.g., KillSwitchService).
**Context fields required:** service_class, parent_engine, call_context
**Example events:**
- Service method called: method name, input summary.
- Service method returned: output summary, duration.
- Service cache hit/miss: cache key, hit or miss.

---

## 4.7 Level 6 — Agent

**Scope:** An individual AI agent's activity.
**Context fields required:** gent_id, gent_role, debate_session_id
**Example events:**
- Agent argument formulated: stance, confidence, key evidence.
- Agent score assigned: score value, weighting factors.
- Agent position changed: original stance, new stance, reason.
- Agent quality score: prediction accuracy for this session.

---

## 4.8 Level 7 — Session

**Scope:** One trading session (market hours period).
**Context fields required:** session_id, session_date, session_type
**Example events:**
- Session started: market open time, initial regime, initial VIX.
- Session cycle count: cycles completed, cycle rate.
- Session closed: session stats (cycles, decisions, orders, P&L).

---

## 4.9 Level 8 — Request/Cycle

**Scope:** One complete decision cycle execution.
**Context fields required:** cycle_id, session_id, cycle_timestamp, cycle_trigger
**Example events:**
- Cycle started: trigger condition, input context summary.
- Cycle layer completed: layer name, duration, output.
- Cycle completed: total duration, decisions made, orders placed.
- Cycle aborted: abort reason, cycle stage at abort.

---

## 4.10 Level 9 — Operation

**Scope:** A single discrete operation within a cycle (e.g., one VIX check).
**Context fields required:** operation_id, cycle_id, operation_type
**Example events:**
- VIX check performed: current VIX, threshold, result.
- Order submitted: symbol, quantity, direction, broker response.
- Cache lookup: key, result, latency.

---

## 4.11 Level 10 — Event

**Scope:** A specific occurrence at the operation level.
**Context fields required:** event_id, operation_id, event_type
**Example events:**
- Signal threshold crossed: signal name, value, threshold.
- Filter condition met/not met: filter name, input, result.
- Score computed: score type, inputs, result.

---

## 4.12 Level 11 — Diagnostic

**Scope:** Verbose debugging information, enabled on demand only.
**Context fields required:** diag_session_id, engine_name, diag_level
**Example events (not written in production by default):**
- Variable state at checkpoint.
- Sub-function entry and exit with argument values.
- Loop iteration details.

---

## 4.13 Level 12 — Exception

**Scope:** Error conditions.
**Context fields required:** exception_id, exception_type, stack_trace_id, ecovery_action
**Example events:**
- Network timeout on data feed request.
- Parse error on configuration file.
- Database connection failure.
- Unexpected null value in computation.

---

## 4.14 Level 13 — Audit

**Scope:** Governance-relevant events — separate path from operational logs.
**Context fields required:** udit_record_id, ctor, operation, subject, previous_hash
**Example events:**
- Kill switch triggered.
- Order placed.
- Configuration changed.
- Strategy promoted.

---

## 4.15 Level 14 — Security

**Scope:** Security-relevant events — separate path.
**Context fields required:** security_event_id, ctor, esource, decision
**Example events:**
- Unauthorized access attempt.
- Secret rotation performed.
- Configuration injection attempt detected.

---

## 4.16 Level 15 — Recovery

**Scope:** System recovery events — highest priority path.
**Context fields required:** ecovery_id, ailure_type, ecovery_action, ecovery_result
**Example events:**
- Component restarted after failure.
- State reconstructed from checkpoint.
- Fallback data feed activated.

---

## 4.17 Hierarchy Diagram — Context Propagation

`
CONTEXT PROPAGATION THROUGH HIERARCHY

When a decision cycle executes:

System context:
  instance_id: iios-prod-001
  environment: production
  version: 2.1.0

  Session context (propagated):
    session_id: session-20260704
    session_date: 2026-07-04

    Cycle context (propagated):
      cycle_id: cycle-20260704-093000-001
      cycle_trigger: SCHEDULER

      Engine context (propagated into each engine):
        engine_name: risk_guardian
        parent_cycle_id: cycle-20260704-093000-001

        Operation context:
          operation_id: op-vix-check-001
          operation_type: KILL_SWITCH_CHECK

          Event:
            Event: VIX check result
            vix_value: 18.4
            threshold: 45
            result: ALLOW
            latency_ms: 3

Every log event at every level carries all parent context fields.
`

---

*End of Part IV*

---
# PART V — LOGGING LIFECYCLE

## 5.1 Lifecycle Overview

Every log event in IIOS travels through a 12-stage lifecycle from the moment it
is generated by a component to the moment it is archived or deleted. The lifecycle
ensures that events are properly validated, enriched, routed, stored, analyzed,
and retired according to their category and retention policy.

`
LOGGING LIFECYCLE — 12 STAGES

Stage 1:  GENERATION     Event occurs in an engine/component; logger emits record
    |
Stage 2:  VALIDATION     Schema is validated, required fields checked
    |
Stage 3:  SANITIZATION   Sensitive values identified and redacted
    |
Stage 4:  ENRICHMENT     Context fields automatically added (cycle_id, trace_id)
    |
Stage 5:  CLASSIFICATION Category, severity, sensitivity tags assigned
    |
Stage 6:  ROUTING        Router determines which sinks receive the event
    |
Stage 7:  STORAGE        Event written to appropriate storage sinks
    |
Stage 8:  AGGREGATION    Related events grouped into traces and summaries
    |
Stage 9:  ANALYSIS       Events evaluated for alerts, anomalies, metrics
    |
Stage 10: ALERTING       Alert rules evaluated; notifications dispatched if needed
    |
Stage 11: ARCHIVING      Events past operational period archived to cold storage
    |
Stage 12: RETENTION/DELETION   Events past retention period permanently deleted
                                (except audit and compliance — never deleted)
`

---

## 5.2 Stage 1 — Generation

**Actor:** Engine or component code (using the IIOS logger library).
**Input:** Raw event data (what happened, where, context).
**Output:** Unvalidated log record with event data.

**Engineering rules for Generation:**
- Log events must be generated at the point of occurrence — not buffered and
  generated later from memory.
- Exception events must include stack trace references (not raw stack traces;
  a stack trace ID that maps to a stored stack trace record).
- Log messages must not contain sensitive values (API keys, tokens, passwords,
  account numbers). Sanitization is a backup — generation-time discipline is primary.
- Log messages must be in English (the operational language of IIOS).
- Log events must not be generated in tight loops without rate limiting
  (maximum 100 identical events per second from a single source).

**Log Event Anatomy at Generation:**

`
Raw log event (before pipeline):
{
  "timestamp": "2026-07-04T09:30:00.123Z",
  "level": "INFO",
  "source": "risk_guardian.kill_switch_service",
  "message": "Kill switch check completed — VIX within threshold",
  "vix_value": 18.4,
  "threshold": 45.0,
  "result": "ALLOW",
  "duration_ms": 3
}
`

**Fields added by the logger library automatically:**
- 	hread_id: thread executing the log call.
- process_id: process ID.
- host: hostname of the running instance.

---

## 5.3 Stage 2 — Validation

**Actor:** Log Collector (Validator sub-component).
**Input:** Raw log record.
**Output:** Validated log record, or quarantine notification with validation errors.

**Validation checks:**
1. All required fields are present (timestamp, level, source, message).
2. Timestamp is a valid ISO 8601 UTC datetime.
3. Level is a recognized value (DEBUG, INFO, WARNING, ERROR, CRITICAL).
4. Source matches a registered component pattern.
5. Message is a non-empty string.
6. No field values exceed maximum length limits.
7. Numeric fields are valid numbers (not NaN, not infinity).
8. Enum fields contain only defined values.

**Validation failure handling:**
- The event is written to logs/quarantine/YYYY-MM-DD.log with validation errors.
- An error counter is incremented.
- If more than 100 events per hour fail validation from a single source, a WARNING
  alert is raised (indicates a code change broke log format).
- Quarantine events are reviewed by the operator; they are not automatically deleted.

---

## 5.4 Stage 3 — Sanitization

**Actor:** Log Collector (Sanitizer sub-component).
**Input:** Validated log record.
**Output:** Sanitized log record (sensitive values replaced with markers).

**Sanitization philosophy:**
Sanitization is non-optional. Every log event passes through the Sanitizer before
any storage or routing occurs. The Sanitizer is the security boundary between
internal computation (which may briefly touch sensitive values) and the observability
store (which must never contain sensitive values).

**Sensitive value detection — patterns:**
- Strings matching ccess_token, pi_key, secret, password, credential
  in field names: replaced with [REDACTED:field_name].
- Strings in message text matching token patterns (alphanumeric, 40+ chars):
  replaced with [POSSIBLE_TOKEN:REDACTED].
- Phone numbers: replaced with [PHONE:REDACTED].
- Account numbers (PAN format, account number format): replaced with
  [ACCOUNT:REDACTED].
- Private key material (begins with "-----BEGIN"): replaced with
  [PRIVATE_KEY:REDACTED].

**Sanitization audit:**
When the Sanitizer redacts a value, it writes a separate sanitization event to the
security log (SECURITY category) with the field name that was redacted, the
detection pattern that matched, and the log event source. The redacted value itself
is never stored anywhere.

**Sanitization failure:**
If the Sanitizer cannot process an event (e.g., crash), the event is dropped
(not stored unsanitized). This is a hard rule with no exceptions.

---

## 5.5 Stage 4 — Enrichment

**Actor:** Log Collector (Enricher sub-component).
**Input:** Sanitized log record.
**Output:** Enriched log record with context fields.

**Automatic enrichment (always applied):**
- cycle_id: Current decision cycle ID from the thread-local context.
- session_id: Current trading session ID from the thread-local context.
- 	race_id: Current trace ID from the tracing context.
- span_id: Current span ID from the tracing context.
- correlation_id: Cross-component correlation ID.
- environment: Deployment environment name.
- service_version: Version of the IIOS service.
- instance_id: Unique identifier for this running instance.

**Conditional enrichment:**
- 	rade_id: If a trade context is active (injected by Order Manager during
  trade lifecycle events).
- strategy_id: If a strategy context is active.
- egime: Current market regime from the most recent Market Intelligence output.

**Enrichment principle:** Context fields added during enrichment are never fabricated.
If the context field is not available (e.g., no active cycle during startup), the
field is omitted rather than assigned a placeholder value.

---

## 5.6 Stage 5 — Classification

**Actor:** Log Collector (Classifier sub-component).
**Input:** Enriched log record.
**Output:** Classified log record with category, severity, and sensitivity tags.

**Category assignment:** The category is determined from the source field:
- isk_guardian.* source → RISK.KILL_SWITCH or RISK.GUARDIAN category.
- execution_engine.* source → ENGINE.EXECUTION category.
- *audit* source → AUDIT category.
And so on per the routing rules in the Logging Registry.

**Severity assignment:**
The log level field is mapped to a severity:
- DEBUG → severity 1 (lowest)
- INFO → severity 2
- WARNING → severity 3
- ERROR → severity 4
- CRITICAL → severity 5 (highest)

**Sensitivity assignment:**
Based on the event category and content scan:
- AUDIT, SECURITY, COMPLIANCE → HIGH sensitivity.
- RISK.KILL_SWITCH, DECISION.* → HIGH sensitivity.
- ENGINE.*, SYSTEM.* → MEDIUM sensitivity.
- DIAG.* → LOW sensitivity.
- Sensitivity HIGH events are encrypted at rest in the audit store.

---

## 5.7 Stage 6 — Routing

**Actor:** Log Router.
**Input:** Classified, enriched, sanitized log record.
**Output:** Event dispatched to appropriate storage sinks (multiple sinks for fan-out).

**Routing logic (simplified):**
1. Look up the event category in the routing table.
2. For each configured sink for this category:
   a. Apply sink-level filter (e.g., only WARN+ for alert evaluator).
   b. If the event passes the filter, enqueue it for that sink.
3. For AUDIT events: always route to audit store (no filtering possible).
4. For CRITICAL events: apply synchronous write to primary sink, asynchronous
   write to secondary sink.

**Fan-out example (RISK.KILL_SWITCH event at CRITICAL severity):**
- Primary operational log sink: YES
- Risk-specific log file: YES
- Alert evaluator: YES (triggers CRITICAL alert)
- Audit store: YES (governance record)
- Telemetry store: YES (risk metrics)
- Dashboard: YES (kill switch panel)
- Total sinks: 6

---

## 5.8 Stage 7 — Storage

**Actor:** Log Storage Manager.
**Input:** Routed log events.
**Output:** Persisted log records in the appropriate storage tier.

**Write procedure:**
1. Write to hot storage (current day log file).
2. Update in-memory index (for fast search).
3. Increment per-category event counter (for metrics).
4. If the event is for the audit store: write with hash computation, update chain.
5. Acknowledge to the Router that the event is stored.

**Durability requirements:**
- CRITICAL and AUDIT events: synchronous write (acknowledged only after fsync).
- ERROR events: synchronous write.
- WARNING and INFO events: asynchronous write (buffered, fsync every 5 seconds).
- DEBUG events: asynchronous write (fsync every 60 seconds).

---

## 5.9 Stage 8 — Aggregation

**Actor:** Log Aggregator.
**Input:** Stream of stored log events.
**Output:** Aggregated cycle summaries, trade timelines, session summaries.

**Aggregation is non-blocking:** It runs asynchronously against the stored event
stream. It does not delay any event's progression through earlier stages.

**Cycle aggregation result:**
- A complete CycleSummary record: all events from a cycle identified by
  cycle_id, in sequence, with per-layer latencies.

**Trade aggregation result:**
- A complete TradeTimeline record: all events from a trade identified by
  	rade_id, from signal to close.

---

## 5.10 Stage 9 — Analysis

**Actor:** Analytics Manager and Monitoring Manager.
**Input:** Stored and aggregated log events.
**Output:** Anomalies detected, metrics updated, trend analyses produced.

**Analysis operations:**
- Error rate computation (events per minute for each severity).
- Latency extraction (cycle and engine durations extracted from log events).
- Pattern detection (are the expected log sequences appearing?).
- Anomaly detection (sudden changes in rates, latencies, patterns).

---

## 5.11 Stage 10 — Alerting

**Actor:** Alert Manager.
**Input:** Analysis results, metric updates, raw CRITICAL events (immediate path).
**Output:** Alert notifications dispatched to configured channels.

**Alert dispatch path:**
For CRITICAL severity events, there is a short circuit:
The event enters the alert evaluator directly without waiting for aggregation
or analysis. The alert is evaluated and dispatched within 1 second of the
event being stored.

**Notification channels:**
- Telegram bot (primary channel for human operators).
- Dashboard alert panel (secondary, visual).
- Log file (always — every alert is logged).

---

## 5.12 Stage 11 — Archiving

**Actor:** Retention Manager (triggers) + Archive Manager (executes).
**Input:** Operational log files approaching their archival age.
**Output:** Compressed, archived log files in cold storage.

**Archiving trigger:** When an operational log file's age exceeds the configured
operational retention period for its category (see retention table in Component 17).

**Archiving process:**
1. The Retention Manager identifies files ready for archiving.
2. The Archive Manager compresses the files.
3. The compressed archive is written to the archive directory.
4. The Archive Manager verifies the compressed file is readable.
5. The original operational file is deleted.
6. The archive is added to the archive index.

---

## 5.13 Stage 12 — Retention/Deletion

**Actor:** Retention Manager.
**Input:** Archived log files older than their total retention period.
**Output:** Permanent deletion of expired archived log files.

**Deletion rules:**
- Operational retention + archive retention period must both be exceeded.
- Compliance check: verify the category is not under any hold (legal hold, active
  investigation, scheduled audit).
- Audit logs: no deletion code path. Audit records are permanent by architecture.
- Compliance logs: no deletion before the compliance retention period.

**Deletion verification:**
After deletion, the Retention Manager records what was deleted (date range, category,
event count, total size freed) in the telemetry store. This is not an audit log entry
(the deleted content is gone) but a housekeeping record.

---

## 5.14 Lifecycle State Machine

`
LOG EVENT STATE MACHINE

[Generated] --[validate]--> [Validated]
                                |
                           [Invalid] --> [Quarantined]
                                |
                        [sanitized] --> [Sanitized]
                                |
                        [enriched] --> [Enriched]
                                |
                      [classified] --> [Classified]
                                |
                         [routed] --> [Routed]
                                |
                        [stored] --> [Stored/Hot]
                                |
                     [aggregate] --> [Aggregated]
                                |
                    [time passes]
                                |
                    [archive trigger] --> [Archived]
                                |
                 [retention exceeded] --> [Deleted]
                   (except AUDIT/COMPLIANCE --> [Permanent])
`

---

*End of Part V*

---

# PART VI — OBSERVABILITY SERVICES

## 6.1 Services Overview

IIOS Observability Services are the runtime interfaces that operational teams use
to access the information produced by the Logging and Observability Framework.
There are 12 defined observability services.

| # | Service | Primary User | Access Method |
|---|---------|-------------|---------------|
| 1 | Logging Service | All components | Python logger |
| 2 | Metrics Service | Dashboards, alerts | Metrics API |
| 3 | Tracing Service | Debug, analytics | Trace viewer |
| 4 | Monitoring Service | Operations | Dashboard, alerts |
| 5 | Health Service | Operations | OHS dashboard |
| 6 | Alert Service | Operations | Telegram, dashboard |
| 7 | Analytics Service | Architecture Council | Reports |
| 8 | Dashboard Service | Operations | Streamlit UI |
| 9 | Audit Service | Compliance, Council | Audit query |
| 10 | Retention Service | Operations | Automated |
| 11 | Archive Service | Compliance | Archive retrieval |
| 12 | Recovery Service | Operations | Recovery CLI |

---

## 6.2 Service 1 — Logging Service

### Purpose
The Logging Service provides the programmatic interface for all IIOS components
to emit log events. It is the entry point for the entire logging pipeline.

### Interface (conceptual, not final code)

`python
class IIOSLogger:
    def debug(self, message: str, **context) -> None: ...
    def info(self, message: str, **context) -> None: ...
    def warning(self, message: str, **context) -> None: ...
    def error(self, message: str, exc_info: bool = False, **context) -> None: ...
    def critical(self, message: str, exc_info: bool = False, **context) -> None: ...
    def audit(self, event_type: str, actor: str, subject: str, **details) -> None: ...
    def security(self, event_type: str, **details) -> None: ...
    def telemetry(self, event_type: str, **metrics) -> None: ...
    def set_context(self, **context_fields) -> ContextManager: ...

def get_logger(component: str) -> IIOSLogger: ...
`

### Usage Pattern

`python
# Standard usage
logger = get_logger("risk_guardian.kill_switch_service")
logger.info("Kill switch check completed", vix_value=18.4, result="ALLOW", duration_ms=3)

# With context manager (adds context fields to all events in block)
with logger.set_context(cycle_id="cycle-001", trade_id="trade-042"):
    logger.info("Processing trade", symbol="RELIANCE")
    logger.info("Signal computed", signal_strength=0.83)
    # All events in this block have cycle_id and trade_id automatically

# Audit logging
logger.audit(
    event_type="ORDER_PLACED",
    actor="DECISION_ENGINE",
    subject="RELIANCE",
    direction="BUY",
    quantity=10,
    order_id="ord-001"
)

# Exception logging
try:
    result = compute_signal()
except Exception as exc:
    logger.error("Signal computation failed", exc_info=True, recovery_action="USE_CACHED")
`

### Rate Limiting
- DEBUG events from a single source: maximum 100 per second.
- INFO events from a single source: maximum 50 per second.
- WARNING and above: no rate limiting.
- Rate limit violations: excess events are dropped with a counter.

### Thread Safety
The IIOS Logger is fully thread-safe. Context managers use thread-local storage.

---

## 6.3 Service 2 — Metrics Service

### Purpose
The Metrics Service provides access to IIOS time-series metrics. It serves
dashboards, alert rules, and analytics queries.

### Interface (conceptual)

`python
class MetricsService:
    def get_metric(
        self, name: str, start: datetime, end: datetime,
        resolution: str = "1m"
    ) -> List[MetricPoint]: ...

    def get_current(self, name: str) -> Optional[float]: ...

    def get_summary(
        self, name: str, window: timedelta
    ) -> MetricSummary: ...  # min, max, mean, p50, p95, p99

    def list_metrics(self, prefix: str = "") -> List[str]: ...

    def record(self, name: str, value: float, **labels) -> None: ...
    def increment(self, name: str, amount: float = 1.0, **labels) -> None: ...
    def set_gauge(self, name: str, value: float, **labels) -> None: ...
`

### Metrics Naming Convention

All IIOS metrics follow a hierarchical dotted naming convention:
iios.[domain].[sub_domain].[metric_name]

Examples:
- iios.system.health_score
- iios.engine.risk_guardian.health_score
- iios.trading.open_positions
- iios.risk.vix_current
- iios.strategy.STRAT_001.win_rate

---

## 6.4 Service 3 — Tracing Service

### Purpose
The Tracing Service provides access to distributed traces, enabling operators and
developers to understand the full execution path of any decision cycle.

### Interface (conceptual)

`python
class TracingService:
    def get_trace(self, trace_id: str) -> Optional[Trace]: ...

    def get_cycle_trace(self, cycle_id: str) -> Optional[Trace]: ...

    def get_recent_traces(
        self, limit: int = 20,
        min_duration_ms: Optional[int] = None
    ) -> List[TraceSummary]: ...

    def get_slow_traces(
        self, threshold_ms: int = 3000, window: timedelta = timedelta(hours=1)
    ) -> List[TraceSummary]: ...

    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> Span: ...
    def end_span(self, span: Span, **result) -> None: ...
`

### Trace Visualization

The Dashboard provides a trace visualization panel. It renders:
- A Gantt chart of span durations for the cycle.
- Annotations indicating which spans exceeded their latency warning threshold.
- A summary table: span name, duration, percentage of total.

---

## 6.5 Service 4 — Monitoring Service

### Purpose
The Monitoring Service provides a programmatic interface to the monitoring state
of IIOS. It is the primary way operators and the Health Manager check the system.

### Interface (conceptual)

`python
class MonitoringService:
    def get_system_health(self) -> SystemHealthReport: ...
    def get_engine_health(self, engine_name: str) -> EngineHealthReport: ...
    def get_all_engine_health(self) -> Dict[str, EngineHealthReport]: ...
    def get_active_alerts(self) -> List[Alert]: ...
    def get_alert_history(
        self, window: timedelta = timedelta(hours=24)
    ) -> List[Alert]: ...
    def get_monitoring_checks(self) -> List[MonitoringCheckStatus]: ...
    def run_monitoring_check(self, check_name: str) -> MonitoringCheckResult: ...
`

### SystemHealthReport Fields

`
SystemHealthReport {
  timestamp: datetime
  system_ohs: float              [0.0 - 1.0]
  system_tier: str               [OPTIMAL/NOMINAL/DEGRADED/CRITICAL/FAILED]
  engines: Dict[str, EngineHealthReport]
  active_alerts_count: int
  kill_switch_active: bool
  vix_current: float
  daily_pnl_pct: float
  uptime_hours: float
  last_cycle_duration_ms: int
}
`

---

## 6.6 Service 5 — Health Service

### Purpose
The Health Service provides the Operational Health Score (OHS) interface —
both the current health state and the history of health score changes.

### Interface (conceptual)

`python
class HealthService:
    def get_ohs(self, component: str = "system") -> float: ...
    def get_ohs_tier(self, component: str = "system") -> OHSTier: ...
    def get_ohs_history(
        self, component: str, window: timedelta
    ) -> List[OHSDataPoint]: ...
    def get_ohs_breakdown(self, component: str) -> OHSBreakdown: ...
    def register_health_check(
        self, component: str, check_fn: Callable
    ) -> None: ...
    def run_health_checks(self) -> Dict[str, HealthCheckResult]: ...
`

### OHS Tier Transitions and Notifications

When a component's OHS crosses a tier boundary downward:
- OPTIMAL → NOMINAL: Dashboard indicator color change. No alert.
- NOMINAL → DEGRADED: WARNING alert to Telegram. Dashboard orange indicator.
- DEGRADED → CRITICAL: ERROR alert to Telegram. Dashboard red indicator.
- CRITICAL → FAILED: CRITICAL alert to Telegram. Dashboard black indicator.
  Operator action required immediately.

When a component's OHS crosses a tier boundary upward (recovering):
- FAILED → CRITICAL: INFO notification.
- CRITICAL → DEGRADED: INFO notification.
- DEGRADED → NOMINAL: INFO notification.
- NOMINAL → OPTIMAL: INFO notification (system returning to normal).

---

## 6.7 Service 6 — Alert Service

### Purpose
The Alert Service provides the interface for creating, querying, and managing
alerts within the IIOS system.

### Interface (conceptual)

`python
class AlertService:
    def get_active_alerts(self) -> List[Alert]: ...
    def get_alert_history(
        self, window: timedelta, severity: Optional[str] = None
    ) -> List[Alert]: ...
    def acknowledge_alert(self, alert_id: str, operator: str) -> None: ...
    def resolve_alert(self, alert_id: str, resolution_note: str) -> None: ...
    def register_rule(self, rule: AlertRule) -> None: ...
    def test_rule(self, rule: AlertRule, test_data: dict) -> AlertRuleTestResult: ...
    def get_alert_statistics(self, window: timedelta) -> AlertStatistics: ...
`

### Alert Lifecycle

`
[Rule evaluates] --> [Alert created] --> [Dispatched to channels]
                                               |
                            [Operator acknowledges] --> [Acknowledged]
                                               |
                            [Condition resolves] --> [Auto-resolved]
                                               |
                            [Operator closes] --> [Manually resolved]
`

An alert stays ACTIVE until either the triggering condition resolves automatically
(e.g., VIX drops below the threshold) or an operator manually resolves it with
a note.

---

## 6.8 Service 7 — Analytics Service

### Purpose
The Analytics Service provides access to the quantitative analysis products generated
from IIOS operational history.

### Interface (conceptual)

`python
class AnalyticsService:
    def get_daily_report(self, date: date) -> DailyOperationsReport: ...
    def get_strategy_health_report(
        self, strategy_id: str, window: timedelta
    ) -> StrategyHealthReport: ...
    def get_decision_quality_report(self, window: timedelta) -> DecisionQualityReport: ...
    def get_latency_report(self, window: timedelta) -> LatencyReport: ...
    def get_risk_event_report(self, window: timedelta) -> RiskEventReport: ...
    def run_custom_query(self, query: AnalyticsQuery) -> AnalyticsResult: ...
`

### Analytics Query Capabilities

The Analytics Service supports querying the log and telemetry store for custom
analysis. Queries are expressed as structured query objects (not raw SQL) to
prevent injection and enforce access controls.

Example query: find all cycles where the Risk Guardian latency exceeded 10ms,
return the cycle_id, timestamp, and risk guardian span duration.

---

## 6.9 Service 8 — Dashboard Service

### Purpose
The Dashboard Service powers the Streamlit operational dashboard and provides
the data layer for all real-time visualizations.

### Dashboard Access

The dashboard is accessible at the configured port (default: port 8501) on the
VPS. Access is restricted to authenticated operators.

### Dashboard Refresh Strategy

Different panels refresh at different intervals to balance freshness with
resource consumption:

| Panel | Refresh Interval |
|-------|-----------------|
| System Health (OHS) | 30 seconds |
| Active Alerts | 15 seconds |
| Kill Switch Status | 15 seconds |
| Open Positions | 30 seconds |
| Daily P&L | 60 seconds |
| Cycle Latency (last) | Every cycle |
| Strategy Performance | 5 minutes |
| Log feed | 60 seconds |
| Risk Metrics | 30 seconds |

### Dashboard Snapshots

The Dashboard Service generates a daily dashboard snapshot (PNG or PDF) at
market close (15:30 IST). This snapshot is archived and attached to the daily
operations report.

---

## 6.10 Service 9 — Audit Service

### Purpose
The Audit Service provides controlled access to the audit store for compliance
queries, governance reviews, and forensic analysis.

### Interface (conceptual)

`python
class AuditService:
    def query_audit(
        self, start: datetime, end: datetime,
        event_types: Optional[List[str]] = None,
        actor: Optional[str] = None,
        subject: Optional[str] = None
    ) -> List[AuditRecord]: ...

    def get_audit_record(self, record_id: str) -> Optional[AuditRecord]: ...

    def verify_chain_integrity(
        self, start_record: str, end_record: str
    ) -> ChainIntegrityReport: ...

    def export_audit_report(
        self, window: DateRange, format: str = "json"
    ) -> AuditReport: ...
`

### Audit Query Access Control

Access to audit data requires explicit authorization:
- Unfiltered audit access: Architecture Council members, Compliance Officer only.
- Filtered audit access (own component's events): Engine owners.
- External auditor access: Temporary grants, time-bounded, specific date range only.

All audit query executions are themselves logged (who queried, what range, what filters).

---

## 6.11 Service 10 — Retention Service

### Purpose
The Retention Service provides visibility into log retention state and controls
for retention policy management.

### Interface (conceptual)

`python
class RetentionService:
    def get_retention_status(self) -> RetentionStatusReport: ...
    def get_category_retention(self, category: str) -> CategoryRetentionInfo: ...
    def schedule_purge(self, category: str, before_date: date) -> PurgeSchedule: ...
    def cancel_purge(self, purge_id: str) -> None: ...
    def get_purge_history(self, window: timedelta) -> List[PurgeRecord]: ...
    def set_hold(self, category: str, reason: str, until: date) -> HoldRecord: ...
    def release_hold(self, hold_id: str, release_reason: str) -> None: ...
`

### Legal Hold Support

The Retention Service supports legal holds: a category with an active hold cannot
have any events deleted. Holds are set when there is an active investigation, audit,
or legal requirement to preserve data. Holds must be explicitly released with a
stated reason.

---

## 6.12 Service 11 — Archive Service

### Purpose
The Archive Service manages access to the long-term archive store.

### Interface (conceptual)

`python
class ArchiveService:
    def list_archives(
        self, category: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[ArchiveEntry]: ...

    def restore_archive(
        self, archive_id: str, target_tier: str = "warm"
    ) -> RestoreJob: ...

    def get_restore_status(self, job_id: str) -> RestoreJobStatus: ...

    def verify_archive_integrity(self, archive_id: str) -> IntegrityReport: ...

    def get_archive_statistics(self) -> ArchiveStatistics: ...
`

### Archive Restoration SLA

When an archive is requested for restoration:
- Request to availability (warm tier): maximum 30 minutes for files < 1GB.
- Request to availability (warm tier): maximum 2 hours for files 1–10GB.
- Files > 10GB: coordinate with operations team.

---

## 6.13 Service 12 — Recovery Service

### Purpose
The Recovery Service provides the operational interface for recovering the logging
system from failures.

### Interface (conceptual)

`python
class RecoveryService:
    def get_recovery_status(self) -> RecoverySystemStatus: ...
    def list_recovery_scenarios(self) -> List[RecoveryScenario]: ...
    def initiate_recovery(
        self, scenario_id: str, operator: str
    ) -> RecoveryRun: ...
    def get_recovery_run_status(self, run_id: str) -> RecoveryRunStatus: ...
    def validate_recovery(self, run_id: str) -> RecoveryValidationReport: ...
    def abort_recovery(self, run_id: str, reason: str) -> None: ...
`

### Recovery Execution Principles

- Recovery is always initiated by a human operator (not automated).
- Every recovery run is logged in the audit store.
- Recovery validation is mandatory after every recovery run.
- A recovery run that fails validation is escalated to the Architecture Council.

---

*End of Part VI*

---
# PART VII — LOGGING QUALITY FRAMEWORK

## 7.1 Quality Framework Purpose

The Logging Quality Framework defines the 12 dimensions of log quality that IIOS
must achieve and maintain. These dimensions are measurable, and the system tracks
quality scores for each dimension over time. A Logging Quality Score (LQS) is
computed for the logging system, analogous to the OHS for operational engines.

---

## 7.2 Dimension 1 — Accuracy

**Definition:** Log events accurately represent the actual state and events in
the system. A log record must not contain false information.

**Measurement:** Spot-check audit process where log events are compared against
known ground truth (e.g., order logs vs broker confirmation records).

**Quality indicators:**
- No discrepancy between log-reported order quantities and broker confirmations.
- No discrepancy between log-reported decision scores and recomputed scores.
- No log events reporting actions that did not actually occur.

**Constitutional link:** Accuracy violations are audit incidents. Any component
that systematically produces inaccurate log events is under investigation.

**Quality target:** 100% accuracy for DECISION, AUDIT, RISK log events.
99.9% for operational logs (rare timing/race conditions acceptable).

---

## 7.3 Dimension 2 — Completeness

**Definition:** All governance-relevant and operationally significant events are
logged. No significant event goes unrecorded.

**Measurement:** Coverage analysis: for each defined event type in the Logging
Registry, are events of that type being produced at the expected rate?

**Quality indicators:**
- Every kill switch trigger has a corresponding audit record.
- Every order placement has a corresponding order audit record.
- Every cycle produces a cycle completion log event.
- Every strategy has weekly performance log events.

**Constitutional link:** Completeness violations are governance incidents.

**Quality target:** 100% for AUDIT, COMPLIANCE, RISK log events.
99.5% for operational logs (brief outages may cause minor gaps).

---

## 7.4 Dimension 3 — Consistency

**Definition:** Log events from the same source follow the same schema and format
consistently over time. A field present in an event type today must be present
tomorrow.

**Measurement:** Schema consistency validation: compare today's log samples against
the registered schema in the Logging Registry.

**Quality indicators:**
- No schema drift (fields disappearing from events without a schema change).
- Consistent timestamp format across all components.
- Consistent severity usage (WARNING not used where ERROR is warranted).

**Quality target:** 100% schema consistency enforced by the Log Collector Validator.

---

## 7.5 Dimension 4 — Timeliness

**Definition:** Log events are written within a bounded delay from the occurrence
they record. A log event recording something that happened 5 minutes ago is not
timely and reduces the value of real-time monitoring.

**Measurement:** Timestamp gap: time between the event occurrence (timestamp in
the event) and the time it appears in the stored log.

**Quality targets:**
- CRITICAL events: stored within 1 second of occurrence.
- ERROR events: stored within 5 seconds of occurrence.
- WARNING, INFO events: stored within 30 seconds.
- DEBUG events: stored within 120 seconds.
- AUDIT events: stored within 1 second (synchronous write path).

**Constitutional link:** Any monitoring system that cannot deliver CRITICAL events
within 1 second is architecturally broken.

---

## 7.6 Dimension 5 — Traceability

**Definition:** Every log event can be traced to its origin: which component emitted
it, in response to which input, as part of which cycle. Given any outcome, the full
chain of events that led to it can be reconstructed.

**Measurement:** Correlation completeness: what percentage of log events have a
valid cycle_id, 	race_id, and correlation_id.

**Quality target:** 100% of log events during decision cycles have trace context.
95% of all log events (startup, EOD, maintenance events may lack cycle context).

**Constitutional link:** Without full traceability, governance is impossible.
Missing correlation context is a logging infrastructure deficiency.

---

## 7.7 Dimension 6 — Integrity

**Definition:** Log events are not modified after being written. The log record
accurately represents the event at the time it was written. Historical logs are
tamper-free.

**Measurement:**
- Audit store hash chain integrity verification (daily).
- File hash checks on archived logs (on archive and on restore).

**Quality target:** 100%. Any integrity violation is a security incident.

**Constitutional link:** Log integrity is constitutional. Rule LOG-CONST-006 states
that no written log record may ever be modified.

---

## 7.8 Dimension 7 — Availability

**Definition:** Log data is available for query when needed. Historical logs can
be retrieved. The logging system does not become unavailable during operational
hours.

**Measurement:**
- Logging system uptime: percentage of market hours during which logs are being
  written.
- Hot tier query availability: percentage of time the search index is functional.
- Archive retrieval success rate.

**Quality target:**
- Log write availability: 99.9% during market hours.
- Hot tier query availability: 99.5%.
- Archive retrieval: 100% success rate (may be slow but never fails permanently).

---

## 7.9 Dimension 8 — Security

**Definition:** Log data does not expose sensitive information. Access to log data
is controlled. Log data is protected from unauthorized access.

**Measurement:**
- Sanitization effectiveness: spot-check scan of stored logs for sensitive patterns.
- Access control compliance: all log queries tracked with authorization verification.
- Audit store encryption verification.

**Quality target:** 100%. Any sensitive data found in a stored log is a security
incident regardless of whether it was accessed.

**Constitutional link:** Rule LOG-CONST-007: sensitive values must be sanitized
before any log record is persisted or transmitted.

---

## 7.10 Dimension 9 — Scalability

**Definition:** The logging system handles the current and projected event volume
without degradation.

**Current baseline volume:**
- Decision cycles: ~50 per market day.
- Log events per cycle: ~200 (estimate across all layers).
- Daily log event volume: ~10,000 operational events.
- Peak rate: ~50 events per second during busy cycles.

**Quality targets:**
- System must handle 10x the current baseline without degradation.
- Buffer utilization during peak: < 50%.
- Write latency must not increase at 5x current volume.

**Headroom principle:** The logging system is always designed for 10x current
volume. This ensures it never becomes a bottleneck before the system grows
significantly.

---

## 7.11 Dimension 10 — Maintainability

**Definition:** The logging system is easy to understand, diagnose, and improve.
Adding a new log event type requires no significant effort. The log schema registry
is up to date and accurate.

**Measurement:**
- Schema documentation coverage: percentage of registered event types with
  complete documentation.
- Unregistered event type rate: events arriving without a schema registration.
- Logging review frequency: cadence of logging system reviews.

**Quality targets:**
- Schema documentation coverage: 100%.
- Unregistered event type rate: 0%.
- Logging review: at least quarterly.

---

## 7.12 Dimension 11 — Auditability

**Definition:** The logging system itself is auditable. The logging governance
framework is documented and reviewable. All changes to logging configuration are
recorded.

**Measurement:**
- Configuration change audit coverage: percentage of logging config changes that
  have audit records.
- Logging policy documentation currency: when was the logging policy last reviewed.

**Quality target:** 100% of logging configuration changes have audit records.
Logging policy reviewed at least annually.

---

## 7.13 Dimension 12 — Operational Reliability

**Definition:** The logging system does not cause failures in the components it
serves. Log emission must not slow down the engines. The logging system must fail
gracefully without affecting the trading system.

**Measurement:**
- Logging overhead: latency added to engine execution by logging calls.
- Logging system failure impact: has a logging failure ever affected trading?

**Quality target:**
- Logging overhead: < 1ms per engine execution.
- Logging system failure impact: 0 trading decisions affected by logging failures.

**Design principle:** If the logging system fails, the trading system continues.
A degraded logging state is acceptable. A logging failure that stops trading is
not acceptable.

---

## 7.14 Logging Quality Score (LQS) Computation

The LQS is a composite score (0.0 to 1.0) computed from weighted quality dimension
scores.

Dimension weights:
- Accuracy: 12%
- Completeness: 12%
- Consistency: 10%
- Timeliness: 8%
- Traceability: 10%
- Integrity: 15%
- Availability: 8%
- Security: 15%
- Scalability: 5%
- Maintainability: 5%
- Auditability: 5%
- Operational Reliability: 5%

LQS tier classification uses the OHS tier boundaries.

---

*End of Part VII*

---

# PART VIII — LOGGING GOVERNANCE

## 8.1 Governance Overview

Logging Governance defines who owns logging decisions, how logging evolves over
time, what standards must be maintained, and how compliance is verified. Good
logging governance means the logging system remains accurate, complete, and
trustworthy despite changes in the underlying system.

---

## 8.2 Ownership Tiers

**Tier 1 — Architecture Council:**
Owns the logging constitution (Part IX), the governance framework (this part),
the 12 quality dimensions, and the retention policy framework. Changes at Tier 1
require unanimous Architecture Council vote.

**Tier 2 — Chief Observability Officer (COO):**
Owns the Logging Registry (schema definitions, routing rules), the quality
measurement processes, and the audit store access policy. The COO reports to
the Architecture Council. Changes at Tier 2 require COO sign-off.

**Tier 3 — Engine Owners:**
Own the log event types emitted by their engine (schema, severity choices, context
fields). Engine owners must register new event types in the Logging Registry.
Changes at Tier 3 require Engine Owner approval.

**Tier 4 — Logging Infrastructure Team:**
Owns the operational configuration of logging components (sink configurations,
rotation schedules, storage utilization management). Changes at Tier 4 are
operational and can be made by the team without escalation (within policy bounds).

---

## 8.3 Logging Naming Standards

### Log Category Naming

Log categories follow a hierarchical dot-separated naming convention:
- SYSTEM — top-level system events.
- ENGINE.[name] — engine-specific events. Example: ENGINE.RISK_GUARDIAN.
- WORKFLOW.[name] — workflow-specific events. Example: WORKFLOW.DECISION_CYCLE.
- AGENT.[id] — agent-specific events. Example: AGENT.CONTRARIAN.

Rules:
- Category names use UPPER_SNAKE_CASE.
- Engine names match the IIOS engine name exactly (as defined in the architecture).
- A maximum of 3 hierarchy levels are permitted.
- Abbreviations are not permitted (use full names).

### Log Event Type Naming

Event types within a category use UPPER_SNAKE_CASE:
[CATEGORY].[EVENT_TYPE]

Examples:
- SYSTEM.STARTUP_COMPLETE
- ENGINE.RISK_GUARDIAN.KILL_SWITCH_TRIGGERED
- DECISION.APPROVED
- AUDIT.ORDER_PLACED

### Log Field Naming

Log event fields use snake_case:
- 	imestamp, level, source, message — reserved standard fields.
- cycle_id, 	race_id, session_id — reserved context fields.
- Custom fields: snake_case, descriptive, no abbreviations.

Prohibited field names: data, info, al, x, 	mp, stuff, 	hing.
These convey no information.

---

## 8.4 Log Classification Standards

### Severity Classification Rules

**CRITICAL:** Use for events that require immediate human intervention.
Examples: kill switch trigger, system OHS entering FAILED tier, audit chain
corruption, logging system failure.

**ERROR:** Use for events representing a failure that requires investigation
within hours. The system continues operating but in a degraded state.
Examples: engine OHS entering CRITICAL tier, data feed primary failure,
exception in a core computation.

**WARNING:** Use for events that indicate potential problems or approaching
thresholds. No immediate action required but worth monitoring.
Examples: latency exceeding WARN threshold, strategy win rate declining,
storage utilization above 80%.

**INFO:** Use for significant operational events that are expected and normal.
Examples: system startup, cycle completion, strategy decision (approve/reject),
session open/close.

**DEBUG:** Use for detailed technical information useful for development and
diagnosis. Never write to production operational logs by default.
Examples: variable values, function entry/exit, loop iterations.

**Severity misclassification** (using a lower severity than warranted) is a
quality defect. Engine owners are responsible for correct severity classification.

### Sensitivity Classification Rules

**HIGH sensitivity:** Events containing governance decisions, risk events,
compliance events, or events that could be sensitive if disclosed.
All HIGH sensitivity events are encrypted in the audit store.

**MEDIUM sensitivity:** Events containing operational data that is not public
but is not governance-critical.

**LOW sensitivity:** Events containing only operational metrics, latencies,
and non-sensitive state.

---

## 8.5 Log Retention Policy Governance

**Retention policies are set at the category level.** They cannot be overridden
for individual events within a category.

**Policy change process:**
1. Retention policy changes require written justification.
2. Changes that shorten retention require Compliance Officer review.
3. Changes that affect AUDIT or COMPLIANCE categories require Architecture
   Council approval.
4. All policy changes are recorded in the governance audit trail.

**Retention Policy Review Calendar:**
- Full retention policy review: annually (Q4 of each calendar year).
- Emergency retention review: within 5 business days of any regulatory requirement
  change.

**Minimum retention floors (constitutional — cannot be shortened):**
- AUDIT: Permanent (no deletion ever).
- COMPLIANCE: 5 years minimum.
- RISK.KILL_SWITCH: 1 year minimum.
- DECISION: 1 year minimum.

---

## 8.6 Access Control Governance

### Log Access Levels

**Level 0 — No access:** Default. Components can only read logs through the defined
service interfaces. No direct file system access to log files.

**Level 1 — Operational read:** Access to current operational logs (hot tier).
Assigned to: operators, engine owners (for their own engine's logs).

**Level 2 — Historical read:** Access to warm and cold archive tiers.
Assigned to: senior operators, Architecture Council members.

**Level 3 — Audit read:** Access to the audit store (read only, filtered).
Assigned to: Compliance Officer, Architecture Council members.

**Level 4 — Full audit read:** Unfiltered access to the entire audit store.
Assigned to: Architecture Council Chair, Compliance Officer.

**Level 5 — Admin:** Access to logging configuration and management.
Assigned to: Logging Infrastructure Team, COO.

### Access Control Review

Access grants are reviewed:
- On each Architecture Council monthly meeting.
- Immediately when a team member's role changes.
- Annually (full access audit).

---

## 8.7 Logging Change Management

### Change Categories

**Category A — Schema change (new event type, new field):**
- Owner: Engine owner (for their engine's events), COO (for cross-cutting events).
- Process: Register in Logging Registry, update documentation, test schema
  validation, deploy.
- Review: COO reviews all new schemas before deployment.

**Category B — Routing rule change:**
- Owner: COO.
- Process: Document the change rationale, test in non-production, deploy.
- Review: COO approval required.

**Category C — Retention policy change:**
- Owner: COO + Compliance Officer.
- Process: Formal proposal, impact analysis, approval, deploy.
- Review: Architecture Council approval for AUDIT/COMPLIANCE categories.

**Category D — Quality dimension change:**
- Owner: Architecture Council.
- Process: Architecture Council formal proposal and vote.
- Review: Unanimous vote required.

**Category E — Logging infrastructure configuration change:**
- Owner: Logging Infrastructure Team.
- Process: Operational change management process.
- Review: Team lead approval.

### Change Deployment Rules

- No logging change is deployed without being tested in a non-production environment.
- Schema changes are backward-compatible (new fields are optional, not required
  on existing events; existing fields are not removed without a deprecation cycle).
- Deprecation cycle: a field is marked deprecated for at least 30 days before removal.
- Emergency changes (security incidents): can skip the review queue with
  post-deployment retrospective required within 24 hours.

---

## 8.8 Logging System Security Governance

### Sensitive Value Policy

The following categories of information must never appear in any log event:
- Authentication credentials (passwords, PINs, tokens, API keys).
- Private key material.
- Account numbers, PAN numbers, tax IDs.
- Session tokens, OAuth tokens, JWT tokens.
- Any value explicitly documented as "do not log" by the data owner.

The Sanitizer is the technical enforcement mechanism. The policy is the governance
mechanism. Both are required.

### Log Tampering Detection

Daily automated hash chain integrity checks. Weekly manual spot-check review
of chain verification results. Any detected tampering triggers a security
incident procedure.

### Log Access Logging

Every access to the audit store is itself logged. This is the meta-audit:
who is reading the audit records and when. This cannot be disabled.

---

## 8.9 Governance Review Calendar

| Review | Frequency | Owner | Output |
|--------|-----------|-------|--------|
| Logging quality score review | Weekly | COO | LQS report |
| Alert rule effectiveness review | Monthly | COO | Alert quality report |
| Schema documentation completeness | Monthly | COO | Documentation status |
| Access control audit | Monthly | Architecture Council | Access report |
| Retention compliance check | Quarterly | Compliance Officer | Compliance report |
| Full logging governance review | Annually | Architecture Council | Governance report |
| Audit store integrity verification | Daily (automated) | Audit Manager | Integrity report |
| Storage utilization review | Weekly | Infra Team | Capacity report |

---

## 8.10 Continuous Improvement Process

The logging system participates in the IIOS continuous improvement cycle:

**Trigger for improvement initiatives:**
- LQS below 0.85 for any dimension.
- More than 5 unregistered event types per week.
- Alert false positive rate above 10%.
- Log query latency degrading over 4 weeks.
- Any logging-related incident.

**Improvement cycle:**
1. Identify the quality gap or incident.
2. Analyze root cause.
3. Propose improvement (schema, routing, infrastructure, governance).
4. Review and approve per change management process.
5. Implement and deploy.
6. Measure improvement.
7. Document the improvement in the governance record.

---

*End of Part VIII*

---

# PART IX — LOGGING CONSTITUTION

## 9.1 Constitution Overview

The Logging Constitution is a set of 110 inviolable rules governing the logging
and observability system. These rules are not guidelines or best practices — they
are architectural laws. Any violation is an incident requiring investigation and
remediation.

Rules are organized into 14 categories:
- **Identity rules (LOG-ID):** Rules governing log event identity and uniqueness.
- **Schema rules (LOG-SCH):** Rules governing log event structure.
- **Sanitization rules (LOG-SAN):** Rules governing sensitive data protection.
- **Severity rules (LOG-SEV):** Rules governing severity classification.
- **Routing rules (LOG-RTE):** Rules governing log routing.
- **Storage rules (LOG-STR):** Rules governing log persistence.
- **Audit rules (LOG-AUD):** Rules governing the audit store.
- **Retention rules (LOG-RET):** Rules governing data retention.
- **Access rules (LOG-ACC):** Rules governing log access.
- **Security rules (LOG-SEC):** Rules governing logging system security.
- **Quality rules (LOG-QLT):** Rules governing log quality.
- **Traceability rules (LOG-TRC):** Rules governing observability tracing.
- **Governance rules (LOG-GOV):** Rules governing logging governance process.
- **Infrastructure rules (LOG-INF):** Rules governing logging infrastructure.

---

## 9.2 Identity Rules (LOG-ID)

**LOG-ID-001:** Every log event must have a unique event_id. Two distinct log events
must never share an event_id.

**LOG-ID-002:** Every log event must have a timestamp in ISO 8601 UTC format with
at least millisecond precision.

**LOG-ID-003:** Timestamps in log events must reflect the actual time the event
occurred, not the time it was buffered or written to storage. A buffered event
must carry the occurrence timestamp.

**LOG-ID-004:** The source field must identify the IIOS component that generated
the event, using the fully qualified component path
(e.g., isk_guardian.kill_switch_service).

**LOG-ID-005:** Log events must not be retroactively created. It is forbidden to
generate log events for past events that were not captured at the time they occurred.
(Exception: recovery reconstruction events are explicitly labeled as reconstructed.)

**LOG-ID-006:** Log events must not be deduplicated in the storage layer. If two
identical events occurred, two records must exist.

**LOG-ID-007:** The event_id must be a UUID or globally unique deterministic
identifier. Sequential integers are not permitted (they do not survive distributed
or restarted environments).

**LOG-ID-008:** The log event schema version must be included in every event.
Schema changes result in a new version number.

---

## 9.3 Schema Rules (LOG-SCH)

**LOG-SCH-001:** All log event types must be registered in the Logging Registry
before they are emitted in production. Unregistered event types are a violation.

**LOG-SCH-002:** Registered schemas are authoritative. An event that does not
conform to its registered schema is a validation failure and goes to quarantine.

**LOG-SCH-003:** Schema changes must be backward-compatible during the deprecation
cycle. New required fields are forbidden (new fields must be optional).

**LOG-SCH-004:** Field names must be in snake_case. Field names must be descriptive.
Single-character field names are prohibited except for reserved fields.

**LOG-SCH-005:** Field types must be explicit and consistent. A field that contains
an integer in one event must not contain a string in another event of the same type.

**LOG-SCH-006:** Null values are permitted only in explicitly nullable fields.
Required fields may not be null.

**LOG-SCH-007:** Log messages (the message field) must be human-readable English
sentences. They must not be machine codes, numeric IDs, or unformatted data.

**LOG-SCH-008:** Log messages must not exceed 1,000 characters. Larger payloads
must be structured as additional fields, not embedded in the message text.

**LOG-SCH-009:** Nested objects in log events must be documented in the schema.
Arbitrary nested structures are not permitted.

**LOG-SCH-010:** Array fields in log events must be bounded (maximum element count
specified in the schema).

---

## 9.4 Sanitization Rules (LOG-SAN)

**LOG-SAN-001:** All log events must pass through the Sanitizer before being written
to any storage sink or transmitted to any external system.

**LOG-SAN-002:** If the Sanitizer fails to process an event, the event must be
dropped. An unsanitized event must never be written to storage.

**LOG-SAN-003:** Sanitization redactions must replace the sensitive value with
a descriptive marker (e.g., [REDACTED:api_token]). Empty strings or nulls
are not acceptable redaction markers.

**LOG-SAN-004:** The fact that a redaction occurred must be recorded in the
security log. The redacted value itself must not be recorded anywhere.

**LOG-SAN-005:** Application code must not log sensitive values. Sanitization is
a defense-in-depth measure, not a primary control. Code review must include
checks for sensitive value logging.

**LOG-SAN-006:** The Sanitizer pattern list must be reviewed and updated when new
sensitive data types are introduced into the system.

**LOG-SAN-007:** Sanitization must be deterministic: the same input always produces
the same output. Non-deterministic sanitization (e.g., using a random salt per
event) breaks audit log integrity.

**LOG-SAN-008:** Sanitization must not corrupt the semantic meaning of a log event.
If redaction makes an event uninterpretable, the event must be redesigned to not
require sensitive values.

---

## 9.5 Severity Rules (LOG-SEV)

**LOG-SEV-001:** CRITICAL severity is reserved for events requiring immediate human
intervention. It must not be used for routine errors.

**LOG-SEV-002:** ERROR severity is for failures that require investigation within
hours. It must not be used for expected failures that are handled by retry logic.

**LOG-SEV-003:** WARNING severity is for approaching thresholds and conditions worth
monitoring. It must not be used for expected operational fluctuations.

**LOG-SEV-004:** INFO severity is for significant normal operational events. It must
not be used for every minor computational step.

**LOG-SEV-005:** DEBUG severity must not be written to production operational logs
by default. It is available on demand only.

**LOG-SEV-006:** Severity must not be inflated to get operator attention. A WARNING
event with high urgency must be either properly classified as ERROR or CRITICAL, or
the alert rules must be adjusted.

**LOG-SEV-007:** Severity levels must not be customized or renamed. The 5-level
hierarchy (DEBUG, INFO, WARNING, ERROR, CRITICAL) is constitutional.

**LOG-SEV-008:** Severity downgrades are forbidden after an event is written. A
written CRITICAL event cannot be retroactively reclassified as WARNING.

---

## 9.6 Routing Rules (LOG-RTE)

**LOG-RTE-001:** All routing decisions must be based on rules registered in the
Logging Registry. Ad-hoc routing outside the registry is forbidden.

**LOG-RTE-002:** AUDIT events must always be routed to the audit store. No routing
rule can exclude AUDIT events from the audit store.

**LOG-RTE-003:** CRITICAL severity events must always trigger an alert evaluation.
No routing rule can exclude CRITICAL events from the alert evaluator.

**LOG-RTE-004:** Routing rules must not be changed at runtime without following
the change management process.

**LOG-RTE-005:** If a routing destination (sink) is unavailable, events must be
buffered for retry. Events must not be silently discarded when a sink is unavailable.

**LOG-RTE-006:** AUDIT events must be routed synchronously. The routing call for
an audit event must not return until the event is acknowledged by the audit store.

**LOG-RTE-007:** Routing must be category-based, not source-based. The routing
table maps categories (not individual source components) to sinks.

**LOG-RTE-008:** Each routing rule must have a documented rationale. Undocumented
routing rules are not permitted in the Logging Registry.

---

## 9.7 Storage Rules (LOG-STR)

**LOG-STR-001:** Log events must be persisted to durable storage. In-memory-only
logging is not acceptable for any production event category.

**LOG-STR-002:** CRITICAL and AUDIT events must be written with synchronous durability
(fsync before acknowledging). Asynchronous writes for these categories are prohibited.

**LOG-STR-003:** Log files must be rotated daily. Log files larger than 500MB must
be rotated regardless of time.

**LOG-STR-004:** Rotated log files must be compressed within 24 hours of rotation.

**LOG-STR-005:** Log storage utilization must be monitored. An alert must fire
before storage reaches 90% capacity.

**LOG-STR-006:** Log writes must not cause I/O contention with the trading system.
Log storage must be on a separate volume from the trading system's data storage
where architecturally possible.

**LOG-STR-007:** A log storage write failure for CRITICAL or AUDIT events is a
system-level emergency. It must not be silently swallowed.

**LOG-STR-008:** The log storage path must be configurable. Hardcoded log paths
are forbidden (except as defaults that can be overridden).

**LOG-STR-009:** Log file permissions must be restrictive. Log files must not be
world-readable.

**LOG-STR-010:** Archived logs must be verified for integrity (checksum) after
archiving and before deletion of the original.

---

## 9.8 Audit Rules (LOG-AUD)

**LOG-AUD-001:** The audit store is append-only. No mechanism for deleting or
modifying audit records may exist in the system.

**LOG-AUD-002:** Every audit record must contain a hash of the previous audit record
(hash chain). A gap in the chain is a tampering incident.

**LOG-AUD-003:** Audit records must be verified for chain integrity daily.
Integrity verification cannot be disabled.

**LOG-AUD-004:** Audit records must be encrypted at rest using approved encryption.

**LOG-AUD-005:** The following events must always produce an audit record:
kill switch trigger, kill switch lift, order placement, strategy promotion,
strategy demotion, configuration change (any), system mode change, access grant,
access revocation, architecture council decision.

**LOG-AUD-006:** Audit record creation must be synchronous. An operation that
requires an audit record must not complete until the audit record is successfully
written.

**LOG-AUD-007:** Access to the audit store must itself be logged. Audit access
logs are stored in a separate access log (not the audit store itself).

**LOG-AUD-008:** Audit records must be retained permanently. There is no audit
retention expiry.

**LOG-AUD-009:** No component other than the Audit Manager may write to the audit
store. Direct audit store writes from other components are prohibited.

**LOG-AUD-010:** Audit export must produce a verifiable export — the exported data
must include the chain hashes so the export can be independently verified.

---

## 9.9 Retention Rules (LOG-RET)

**LOG-RET-001:** Every log event category must have a defined retention policy.
Categories without a retention policy are a governance violation.

**LOG-RET-002:** Retention policies may only be shortened with Compliance Officer
review and written justification.

**LOG-RET-003:** The following categories may never have their retention shortened
below the constitutional minimums: AUDIT (permanent), COMPLIANCE (5 years),
RISK.KILL_SWITCH (1 year), DECISION (1 year).

**LOG-RET-004:** Retention policy changes must be logged in the governance audit trail.

**LOG-RET-005:** Legal holds override retention policies. Events under legal hold
are never deleted regardless of age.

**LOG-RET-006:** Deletion of expired events must be logged (category, date range,
count, size freed). The deletion log itself is retained for 1 year.

**LOG-RET-007:** Retention policies must be documented and accessible to all
operators. Undocumented retention policies are not permitted.

**LOG-RET-008:** Events cannot be selectively retained or deleted within a category.
Retention is applied at the category + date boundary level.

---

## 9.10 Access Rules (LOG-ACC)

**LOG-ACC-001:** Access to log data requires explicit authorization per the defined
access levels (0–5).

**LOG-ACC-002:** Default access is Level 0 (no access). Access must be explicitly
granted — never implicitly assumed.

**LOG-ACC-003:** Access grants must be documented, time-bounded where possible,
and reviewed at least annually.

**LOG-ACC-004:** All access to the audit store must be logged (meta-audit).

**LOG-ACC-005:** Shared accounts must not be used for log access. Each access must
be attributable to a specific individual.

**LOG-ACC-006:** Access grants cannot be self-approved. A person cannot grant
themselves elevated access.

**LOG-ACC-007:** Read-only access to logs must not permit any write or delete
operations, enforced at the storage layer, not only at the application layer.

---

## 9.11 Security Rules (LOG-SEC)

**LOG-SEC-001:** Sensitive values must never appear in any stored log record.
See LOG-SAN rules for enforcement.

**LOG-SEC-002:** The logging system must not be a vector for log injection. All
log messages from external sources (data from brokers, user input) must be
sanitized before logging to prevent log forgery.

**LOG-SEC-003:** The logging system must not expose confidential trading strategy
information in logs accessible to unauthorized parties.

**LOG-SEC-004:** The audit store encryption key must be stored in the secrets
management system, not in configuration files.

**LOG-SEC-005:** Any detected tampering of the audit chain is a security incident
and must be responded to within 4 hours.

**LOG-SEC-006:** The logging system must not be used as a covert communication
channel. Log events are not message queues.

**LOG-SEC-007:** Network transmission of log events to external sinks must use
encrypted transport.

**LOG-SEC-008:** Logging configuration changes must be authorized (cannot be made
by any unauthenticated actor).

---

## 9.12 Quality Rules (LOG-QLT)

**LOG-QLT-001:** The Logging Quality Score (LQS) must be computed and reported
weekly.

**LOG-QLT-002:** An LQS below 0.85 for any dimension for two consecutive weeks
triggers a mandatory improvement initiative.

**LOG-QLT-003:** Log quarantine events (events failing validation) must be reviewed
weekly and resolved.

**LOG-QLT-004:** Unregistered event types must be registered or suppressed within
5 business days of detection.

**LOG-QLT-005:** Alert false positive rate must not exceed 10% of total alerts.
High false positive rates must be addressed by refining alert rules.

**LOG-QLT-006:** Alert silence (no alerts for an extended period that should have
had alerts) must be investigated. Silence is not necessarily health.

**LOG-QLT-007:** Log format changes must not silently break existing queries or
dashboards. Breaking changes require a migration plan.

---

## 9.13 Traceability Rules (LOG-TRC)

**LOG-TRC-001:** Every decision cycle must be traceable from start to finish via
the cycle_id correlation key.

**LOG-TRC-002:** Every trade must be traceable from signal to close via the trade_id
correlation key.

**LOG-TRC-003:** Every audit event must reference the cycle or operation that
triggered it.

**LOG-TRC-004:** If a trace cannot be completed (a span was not captured), the
reason for the gap must be investigated. Trace gaps are quality defects.

**LOG-TRC-005:** Trace context (trace_id, span_id) must be propagated across all
engine boundaries. An engine that receives a trace context must include it in all
events it emits.

**LOG-TRC-006:** The correlation_id must be consistent within a single logical
operation. A mid-operation change of correlation_id is a quality defect.

---

## 9.14 Governance Rules (LOG-GOV)

**LOG-GOV-001:** The Logging Constitution cannot be amended without Architecture
Council unanimous vote.

**LOG-GOV-002:** The Logging Governance Review must be held at minimum annually.
Skipping the annual review is a governance violation.

**LOG-GOV-003:** All logging governance decisions must be recorded in the governance
audit trail.

**LOG-GOV-004:** No logging component may be modified without following the change
management process defined in Section 8.7.

**LOG-GOV-005:** The Chief Observability Officer role may not be left vacant for
more than 30 days. An acting COO must be appointed if the role is temporarily
unfilled.

**LOG-GOV-006:** Logging governance records must be retained for the duration of
the system's operational life.

**LOG-GOV-007:** An exception to any constitution rule requires Architecture Council
approval, must be time-bounded, and must be reviewed at each Architecture Council
meeting until it expires.

---

## 9.15 Infrastructure Rules (LOG-INF)

**LOG-INF-001:** The logging infrastructure must be monitored independently of
the logging system itself. Infrastructure health must not be invisible if the
logging system fails.

**LOG-INF-002:** The logging system must have a defined startup and shutdown sequence.
Startup must complete successfully before the trading system accepts its first cycle.

**LOG-INF-003:** The logging system must fail gracefully. A logging component failure
must not propagate to the trading system.

**LOG-INF-004:** Logging component restart must be automatic for recoverable failures.
The logging system must not require manual intervention for transient failures.

**LOG-INF-005:** Log storage volumes must have adequate free space headroom at all
times. Emergency purge procedures exist but must not be the routine operating mode.

**LOG-INF-006:** The logging system configuration must be under version control.
Configuration changes are tracked in the same manner as code changes.

**LOG-INF-007:** Backup of the audit store must occur at least daily. The backup
must be verified (restored and hash-checked) at least weekly.

**LOG-INF-008:** The logging infrastructure must support rolling restarts. The
logging system must remain operational while individual components are restarted.

---

*End of Part IX*

---
# PART X — LOGGING READINESS CHECKLIST AND CERTIFICATION MATRIX

## 10.1 Readiness Checklist Overview

The Logging Readiness Checklist defines the criteria that must be satisfied before
IIOS is considered observability-ready for production operation. The checklist is
organized into 11 readiness domains. Each domain has a set of checks classified
as HARD (must pass — launch blocker) or SOFT (should pass — improvement opportunity).

---

## 10.2 Domain 1 — Logging Infrastructure Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-INF-01 | Log Collector is initialized and receiving events | HARD | Event flow confirmed |
| LR-INF-02 | Log Router is initialized and routing events | HARD | All sinks receiving events |
| LR-INF-03 | Log Storage Manager is writing to hot tier | HARD | Files being created |
| LR-INF-04 | Log file rotation is configured | HARD | Daily rotation enabled |
| LR-INF-05 | Log compression is configured | HARD | Compression rules active |
| LR-INF-06 | Log storage volume has > 20% free space | HARD | Space check passes |
| LR-INF-07 | Sanitizer is active and processing events | HARD | Test event sanitized |
| LR-INF-08 | Buffer is configured with overflow limits | HARD | Buffer config verified |
| LR-INF-09 | Log directory structure matches specification | SOFT | Directory audit passes |
| LR-INF-10 | Log file permissions are restrictive | HARD | Permissions audit passes |

**Domain 1 certification:** HARD-only: 9/9 required. SOFT: 1/1 recommended.

---

## 10.3 Domain 2 — Logging Registry Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-REG-01 | Logging Registry initializes without errors | HARD | Zero errors on startup |
| LR-REG-02 | All engine event types are registered | HARD | Count matches engine inventory |
| LR-REG-03 | All routing rules are defined | HARD | Each category has routing entry |
| LR-REG-04 | All retention policies are defined | HARD | Each category has retention entry |
| LR-REG-05 | Schema documentation is complete | SOFT | 100% schemas documented |
| LR-REG-06 | No duplicate event type registrations | HARD | Uniqueness check passes |
| LR-REG-07 | Registry loads within 1,000ms | SOFT | Startup timing measured |

**Domain 2 certification:** HARD-only: 5/5 required. SOFT: 2/2 recommended.

---

## 10.4 Domain 3 — Audit System Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-AUD-01 | Audit Manager is initialized | HARD | No startup errors |
| LR-AUD-02 | Audit store is writable | HARD | Test audit record written |
| LR-AUD-03 | Hash chain is initialized | HARD | Genesis record exists |
| LR-AUD-04 | Audit store is encrypted | HARD | Encryption verified |
| LR-AUD-05 | Audit write is synchronous | HARD | Latency test: < 100ms |
| LR-AUD-06 | No delete operation exists for audit records | HARD | Code audit confirms |
| LR-AUD-07 | Audit access is restricted | HARD | Access control test passes |
| LR-AUD-08 | Audit chain integrity check can be run | HARD | Integrity check succeeds |
| LR-AUD-09 | Audit store backup procedure is tested | SOFT | Restore test passes |
| LR-AUD-10 | Audit access logging (meta-audit) is active | HARD | Access log written |

**Domain 3 certification:** HARD-only: 9/9 required. SOFT: 1/1 recommended.

---

## 10.5 Domain 4 — Metrics System Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-MET-01 | Metrics Manager is initialized | HARD | No startup errors |
| LR-MET-02 | System OHS metric is being computed | HARD | iios.system.health_score present |
| LR-MET-03 | All engine OHS metrics are populated | HARD | 18 engine metrics present |
| LR-MET-04 | VIX metric is being refreshed | HARD | iios.risk.vix_current updating |
| LR-MET-05 | Daily P&L metric is functional | HARD | iios.trading.daily_pnl_pct present |
| LR-MET-06 | Kill switch active metric is functional | HARD | Boolean metric initialized |
| LR-MET-07 | Metrics query interface is accessible | HARD | Test query succeeds |
| LR-MET-08 | Metrics retention is configured | SOFT | Retention policy set |
| LR-MET-09 | All critical metrics have alert rules | HARD | Alert rule coverage verified |
| LR-MET-10 | Cycle latency metric is captured per cycle | HARD | Metric updates after test cycle |

**Domain 4 certification:** HARD-only: 9/9 required. SOFT: 1/1 recommended.

---

## 10.6 Domain 5 — Tracing System Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-TRC-01 | Tracing Manager is initialized | HARD | No startup errors |
| LR-TRC-02 | Test cycle produces a complete trace | HARD | All 17 layers captured |
| LR-TRC-03 | Trace context propagates across engines | HARD | Trace IDs consistent |
| LR-TRC-04 | Trace store retains completed traces | HARD | Query returns test trace |
| LR-TRC-05 | Slow span detection is functional | SOFT | Test slow span detected |
| LR-TRC-06 | Cycle-to-trace lookup works | HARD | cycle_id maps to trace_id |

**Domain 5 certification:** HARD-only: 5/5 required. SOFT: 1/1 recommended.

---

## 10.7 Domain 6 — Monitoring System Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-MON-01 | Monitoring Manager is initialized | HARD | No startup errors |
| LR-MON-02 | Health checks are executing on schedule | HARD | Check history confirms |
| LR-MON-03 | OHS scores are computed for all engines | HARD | 18 engine scores present |
| LR-MON-04 | OHS tier transitions trigger notifications | HARD | Test transition sends alert |
| LR-MON-05 | Kill switch condition monitoring is active | HARD | VIX check scheduled |
| LR-MON-06 | Anomaly detection is running | SOFT | Test anomaly detected |
| LR-MON-07 | Log silence detection is active | SOFT | Test silence detected |
| LR-MON-08 | Data freshness monitoring is active | HARD | Staleness check running |

**Domain 6 certification:** HARD-only: 6/6 required. SOFT: 2/2 recommended.

---

## 10.8 Domain 7 — Alert System Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-ALT-01 | Alert Manager is initialized | HARD | No startup errors |
| LR-ALT-02 | Telegram notification channel is functional | HARD | Test alert delivered |
| LR-ALT-03 | Dashboard alert panel is functional | HARD | Test alert visible |
| LR-ALT-04 | All CRITICAL alert rules are loaded | HARD | Rule count verified |
| LR-ALT-05 | Kill switch alert fires within 1 second | HARD | Latency test passes |
| LR-ALT-06 | Deduplication is working | HARD | Duplicate test suppressed |
| LR-ALT-07 | Alert resolution tracking works | SOFT | Resolve test passes |
| LR-ALT-08 | Alert history is retained | SOFT | Query returns history |
| LR-ALT-09 | Rate limiting (max 20/hour) is active | HARD | Rate limit test passes |
| LR-ALT-10 | No alert storms at system startup | HARD | Startup alert count = 0 |

**Domain 7 certification:** HARD-only: 8/8 required. SOFT: 2/2 recommended.

---

## 10.9 Domain 8 — Security and Sanitization Approved

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-SEC-01 | Sanitizer is active on all event paths | HARD | No unsanitized path exists |
| LR-SEC-02 | Test credential is redacted in logs | HARD | Redaction test passes |
| LR-SEC-03 | Audit store encryption is verified | HARD | Encryption test passes |
| LR-SEC-04 | Audit store access requires authorization | HARD | Auth check passes |
| LR-SEC-05 | Log files are not world-readable | HARD | Permission check passes |
| LR-SEC-06 | Log injection protection is in place | HARD | Injection test blocked |
| LR-SEC-07 | No sensitive fields in any stored test log | HARD | Scan of test logs clean |
| LR-SEC-08 | Encryption key stored in secrets manager | HARD | Key source verified |
| LR-SEC-09 | Log network transmission is encrypted | SOFT | TLS verified on all channels |
| LR-SEC-10 | Security event log is operational | HARD | Test security event recorded |

**Domain 8 certification:** HARD-only: 9/9 required. SOFT: 1/1 recommended.

---

## 10.10 Domain 9 — Recovery Verified

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-RCV-01 | Recovery Manager is initialized | HARD | No startup errors |
| LR-RCV-02 | Recovery Scenario 1 (storage failure) is documented | SOFT | Runbook exists |
| LR-RCV-03 | Recovery Scenario 2 (audit corruption) is documented | SOFT | Runbook exists |
| LR-RCV-04 | Recovery Scenario 3 (full failure) is documented | SOFT | Runbook exists |
| LR-RCV-05 | Audit store backup can be restored | HARD | Restore test passes |
| LR-RCV-06 | Log Collector buffer survives brief storage failure | HARD | Resilience test passes |
| LR-RCV-07 | Recovery priority order is implemented | HARD | Recovery sequence verified |

**Domain 9 certification:** HARD-only: 4/4 required. SOFT: 3/3 recommended.

---

## 10.11 Domain 10 — Documentation Complete

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-DOC-01 | Logging and Observability Framework document is complete | HARD | This document |
| LR-DOC-02 | Log event schema documentation is published | HARD | All schemas documented |
| LR-DOC-03 | Logging governance policy is published | HARD | Policy document exists |
| LR-DOC-04 | Operations runbook for logging is published | SOFT | Runbook exists (Supplement G) |
| LR-DOC-05 | Alert rule documentation is published | SOFT | Alert rules documented |
| LR-DOC-06 | Retention policy documentation is published | HARD | Policy document exists |
| LR-DOC-07 | Audit query guide is available | SOFT | Query guide exists |

**Domain 10 certification:** HARD-only: 4/4 required. SOFT: 3/3 recommended.

---

## 10.12 Domain 11 — Operationally Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| LR-OPS-01 | Dashboard is accessible and refreshing | HARD | Dashboard loads |
| LR-OPS-02 | All 18 engine OHS scores visible on dashboard | HARD | Visual verification |
| LR-OPS-03 | Kill switch status visible on dashboard | HARD | Kill switch panel present |
| LR-OPS-04 | Alert panel shows current alert state | HARD | Panel functional |
| LR-OPS-05 | Daily P&L is visible on dashboard | HARD | P&L panel present |
| LR-OPS-06 | Cycle latency chart is updating | HARD | Chart refreshes on cycle |
| LR-OPS-07 | Logging system health is visible | SOFT | LQS shown on dashboard |
| LR-OPS-08 | Operator logging runbook is reviewed | SOFT | Review confirmed |

**Domain 11 certification:** HARD-only: 6/6 required. SOFT: 2/2 recommended.

---

## 10.13 Certification Matrix

`
LOGGING READINESS CERTIFICATION MATRIX

Domain                              HARD  SOFT  Status
----------------------------------------------------------
D1 — Logging Infrastructure Ready    9/9   1/1   [ ]
D2 — Logging Registry Ready          5/5   2/2   [ ]
D3 — Audit System Ready              9/9   1/1   [ ]
D4 — Metrics System Ready            9/9   1/1   [ ]
D5 — Tracing System Ready            5/5   1/1   [ ]
D6 — Monitoring System Ready         6/6   2/2   [ ]
D7 — Alert System Ready              8/8   2/2   [ ]
D8 — Security and Sanitization       9/9   1/1   [ ]
D9 — Recovery Verified               4/4   3/3   [ ]
D10 — Documentation Complete         4/4   3/3   [ ]
D11 — Operationally Ready            6/6   2/2   [ ]
----------------------------------------------------------
TOTAL                               74/74  19/19
----------------------------------------------------------

HARD pass: All 74 HARD checks must pass.
SOFT pass: At least 15/19 SOFT checks recommended.

CERTIFICATION STATEMENT:
"I certify that all 74 HARD logging readiness checks pass and
that the IIOS logging and observability system meets the standards
defined in IIOS-LOG-OBS-001."

Certified by: _____________________ Date: _________________
Role:         Chief Observability Officer
`

---

*End of Part X*

---

# SUPPLEMENT A — LOG TAXONOMY REFERENCE

## A.1 Complete Log Category Hierarchy

All 24 defined log categories with their namespace, description, and primary engine:

| Namespace | Category | Primary Engine | Audit Required |
|-----------|---------|----------------|----------------|
| SYSTEM | System-level events | All | Major events |
| ENGINE.GLOBAL_INTELLIGENCE | Global data events | GlobalIntelligence | No |
| ENGINE.MARKET_INTELLIGENCE | Market analysis | MarketIntelligence | No |
| ENGINE.META_LEARNING | Meta learning events | MetaLearning | No |
| ENGINE.OPPORTUNITY | Opportunity scan | OpportunityEngine | No |
| ENGINE.STRATEGY_LAB | Strategy events | StrategyLab | Promotions |
| ENGINE.CAPITAL_RISK | Capital allocation | CapitalRiskEngine | No |
| ENGINE.RISK_CONTROL | Risk management | RiskControl | CRITICAL events |
| ENGINE.MARKET_SIMULATION | Simulation | MarketSimulation | No |
| ENGINE.RISK_GUARDIAN | Kill switch | RiskGuardian | All triggers |
| ENGINE.DEBATE_DECISION | Decision cycle | DebateAndDecision | All decisions |
| ENGINE.EXECUTION | Order management | ExecutionEngine | All orders |
| ENGINE.TRADE_MONITORING | Trade tracking | TradeMonitoring | No |
| ENGINE.LEARNING | Learning updates | LearningSystem | No |
| ENGINE.PERFORMANCE | Analytics | PerformanceAnalytics | No |
| ENGINE.RESEARCH_LAB | Research | ResearchLab | Promotions |
| ENGINE.VALIDATION | Validation | ValidationEngine | All gates |
| ENGINE.CONTROL_TOWER | Orchestration | ControlTower | Mode changes |
| WORKFLOW | Workflow events | Various | No |
| AGENT | AI agent events | DebateAndDecision | No |
| DECISION | Decision records | DebateAndDecision | All |
| PREDICTION | Prediction records | MetaLearning | No |
| PORTFOLIO | Portfolio state | CapitalRiskEngine | No |
| RISK | Risk events | RiskGuardian, RiskControl | CRITICAL |
| LEARNING | Learning records | LearningSystem | No |
| SIMULATION | Simulation records | MarketSimulation | No |
| STRATEGY | Strategy events | StrategyLab | Promotions/demotions |
| GOVERNANCE | Governance events | ControlTower | All |
| SECURITY | Security events | All | All violations |
| AUDIT | Audit records | All | All (by definition) |
| PERFORMANCE | Performance metrics | All | No |
| INFRA | Infrastructure events | Infrastructure | No |
| DEPLOY | Deployment events | CI/CD | All |
| DIAG | Diagnostic events | All | No |
| EXCEPTION | Error events | All | CRITICAL |
| RECOVERY | Recovery events | All | All |
| MONITOR | Monitoring events | MonitoringManager | No |
| HEALTH | Health events | HealthManager | Tier CRITICAL |
| TELEMETRY | Telemetry records | TelemetryManager | No |
| COMPLIANCE | Compliance records | ControlTower | All |

---

# SUPPLEMENT B — SEVERITY AND SENSITIVITY CATALOG

## B.1 Severity Decision Reference

**Use CRITICAL when any of these are true:**
- A kill switch has been triggered or a threshold was crossed that required
  automated intervention.
- A system component has entered FAILED OHS tier.
- An audit chain integrity failure is detected.
- The trading system has been automatically halted.
- A security violation has been detected (unauthorized access, tampering).
- Data loss has occurred or is imminent.

**Use ERROR when any of these are true:**
- An expected operation failed and the failure degrades the system's capability.
- A component entered CRITICAL OHS tier.
- A fallback has been activated because the primary service failed.
- An exception propagated to the cycle runner (affecting cycle completion).
- A required external service (data feed, broker) is unreachable.

**Use WARNING when any of these are true:**
- A metric is approaching (but has not crossed) a critical threshold.
- A component entered DEGRADED OHS tier.
- Performance is below target but within operating limits.
- A non-critical operation failed and will be retried.
- A configuration anomaly is detected (non-breaking).

**Use INFO when any of these are true:**
- A normal lifecycle event occurred (startup, shutdown, session open/close).
- A significant decision was made (approve/reject, strategy promoted).
- A cycle completed successfully.
- An important state change occurred (mode change, regime change).

**Use DEBUG when any of these are true:**
- Detailed computation state is being captured for diagnosis.
- Function entry/exit tracing is active.
- Cache behavior is being traced.
- Variable state at a checkpoint is being recorded.

---

## B.2 Sensitivity Classification Guide

| Scenario | Sensitivity | Reason |
|----------|-------------|--------|
| Kill switch trigger record | HIGH | Governance-critical |
| Order placement record | HIGH | Financial transaction |
| Configuration change record | HIGH | Governance-critical |
| Decision score breakdown | HIGH | Strategy-sensitive |
| VIX check result | MEDIUM | Operational |
| Engine latency measurement | LOW | Non-sensitive performance data |
| Cycle completion summary | MEDIUM | Operational |
| Exception stack trace | MEDIUM | Could reveal system internals |
| Data feed error | LOW | Expected operational condition |
| System startup event | LOW | Non-sensitive |
| Audit store access | HIGH | Security-critical |

---

# SUPPLEMENT C — METRICS CATALOG

## C.1 Complete IIOS Metrics Reference

### System Metrics

| Metric Name | Type | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| iios.system.health_score | Gauge | System OHS (0.0–1.0) | < 0.60 (CRITICAL) |
| iios.system.cycle_duration_ms | Gauge | Last full cycle time | > 5,000ms (CRIT) |
| iios.system.uptime_hours | Counter | Hours since start | — |
| iios.system.kill_switch_count | Counter | Kill switch activations | > 0 (INFO) |
| iios.system.mode | Gauge | 0=paper, 1=live | Mode change |

### Trading Metrics

| Metric Name | Type | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| iios.trading.open_positions | Gauge | Current open count | > configured max |
| iios.trading.daily_pnl_pct | Gauge | Daily P&L % | < -1.5% (WARNING) / < -2.0% (CRIT) |
| iios.trading.daily_decisions | Counter | Decisions today | — |
| iios.trading.daily_orders | Counter | Orders today | — |
| iios.trading.session_cycles | Counter | Cycles in session | — |

### Risk Metrics

| Metric Name | Type | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| iios.risk.vix_current | Gauge | Current India VIX | > 40 (WARNING) / > 45 (CRITICAL) |
| iios.risk.kill_switch_active | Gauge | 1 if active, 0 if not | 1 (CRITICAL) |
| iios.risk.daily_loss_pct | Gauge | Current day loss % | > 1.5% (WARNING) / > 2.0% (CRIT) |
| iios.risk.max_drawdown_pct | Gauge | Current max drawdown | > 12% (WARNING) / > 15% (CRIT) |

### Engine Metrics (per engine, 18 total)

| Metric Name | Type | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| iios.engine.[name].health_score | Gauge | Engine OHS | < 0.60 (CRITICAL) |
| iios.engine.[name].last_exec_ms | Gauge | Last execution latency | > WARN_THRESHOLD |
| iios.engine.[name].error_count_1h | Counter | Errors in last hour | > 5 (ERROR) |
| iios.engine.[name].exec_count | Counter | Total executions | — |

### Strategy Metrics (per strategy)

| Metric Name | Type | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| iios.strategy.[id].win_rate | Gauge | Win rate (rolling 30d) | < 40% (WARNING) |
| iios.strategy.[id].sharpe | Gauge | Sharpe ratio | < 0.5 (WARNING) |
| iios.strategy.[id].max_drawdown | Gauge | Maximum drawdown | > 12% (WARNING) |
| iios.strategy.[id].active | Gauge | 1 if active, 0 if disabled | Transition |

### Logging System Metrics

| Metric Name | Type | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| iios.logging.ingest_rate | Gauge | Events per second | — |
| iios.logging.buffer_utilization | Gauge | Buffer fill % | > 80% (WARNING) |
| iios.logging.dropped_events | Counter | Dropped non-critical events | > 0 (WARNING) |
| iios.logging.storage_utilization | Gauge | Log storage % used | > 80% (WARNING) |
| iios.logging.lqs | Gauge | Logging Quality Score | < 0.85 (WARNING) |
| iios.logging.audit_chain_age_hours | Gauge | Hours since last integrity check | > 25 (WARNING) |

---

# SUPPLEMENT D — TRACING REFERENCE

## D.1 Standard Span Names

All spans in IIOS traces use the following standard names:

| Span Name | Engine | Typical Duration |
|-----------|--------|-----------------|
| global_intelligence_fetch | GlobalIntelligence | 17ms (cached) |
| market_intelligence_classify | MarketIntelligence | 19ms |
| meta_learning_predict | MetaLearning | 8ms |
| opportunity_scan | OpportunityEngine | 35ms |
| strategy_signals | StrategyLab | 22ms |
| capital_allocation | CapitalRiskEngine | 11ms |
| risk_control_check | RiskControl | 14ms |
| market_simulation | MarketSimulation | 28ms |
| risk_guardian_check | RiskGuardian | 3ms |
| debate_and_decision | DebateAndDecision | 45ms |
| execution_engine | ExecutionEngine | 4ms |
| trade_monitoring_register | TradeMonitoring | 2ms |
| learning_update | LearningSystem | 1ms |
| performance_record | PerformanceAnalytics | 1ms |
| control_tower_telemetry | ControlTower | 1ms |

## D.2 Trace Performance Baselines

**Full decision cycle baseline (current production):**
- Total duration: 172ms (HEALTHY).
- Latency WARN threshold: 2,000ms (default), 5,000ms (GlobalIntelligence).
- Latency CRIT threshold: 5,000ms (default), 12,000ms (GlobalIntelligence).

**Trace latency budget allocation (172ms total):**
- GlobalIntelligence: 17ms (10%)
- MarketIntelligence: 19ms (11%)
- StrategyLab: 22ms (13%)
- DebateAndDecision: 45ms (26%)
- OpportunityEngine: 35ms (20%)
- MarketSimulation: 28ms (16%)
- All other layers: 6ms (4%)

---

# SUPPLEMENT E — GOVERNANCE DECISION RECORDS

## E.1 Governance Decision Log

All significant logging governance decisions are recorded here. This supplement is
updated at each Architecture Council review.

| Record ID | Date | Decision | Rationale | Approved By |
|-----------|------|----------|-----------|-------------|
| LOG-GOV-001 | System inception | Establish 12-stage lifecycle | Completeness and traceability | Architecture Council |
| LOG-GOV-002 | System inception | Audit store is permanently retained | Compliance and accountability | Architecture Council |
| LOG-GOV-003 | System inception | CRITICAL events are synchronously written | Guarantee delivery | Architecture Council |
| LOG-GOV-004 | System inception | Sanitization is mandatory for all events | Security requirement | Architecture Council |
| LOG-GOV-005 | System inception | Hash chain for audit tamper evidence | Integrity assurance | Architecture Council |
| LOG-GOV-006 | System inception | LQS uses same tier system as OHS | Consistency | Architecture Council |
| LOG-GOV-007 | System inception | DEBUG not written in production by default | Performance and log volume | Architecture Council |

---

# SUPPLEMENT F — LOGGING ANTI-PATTERNS

## F.1 Anti-Patterns Reference

### Anti-Pattern 1 — "Log Everything"

**Description:** Logging every variable, every function entry/exit, every minor
computation step at INFO level.

**Problem:** Produces enormous log volumes (terabytes per day), making the logs
unusable for operational purposes. Real signals drown in noise. Storage and
performance costs are prohibitive.

**Correct approach:** Log significant events at INFO. Log debug detail at DEBUG
(off by default). Use metrics for numerical state rather than logging it at high
frequency.

---

### Anti-Pattern 2 — "Log Nothing"

**Description:** Insufficient logging — no logging of significant events because
the developer assumes the system will work.

**Problem:** When something goes wrong, there is no information to diagnose it.
Governance requirements are violated (kill switch triggers, order placements, config
changes must be audited).

**Correct approach:** Follow the event coverage requirements in the Logging Registry.
Every governance-relevant event must be logged. When in doubt, log it at WARNING or
above.

---

### Anti-Pattern 3 — "Log Sensitive Data"

**Description:** Logging API tokens, passwords, account numbers, or strategy
parameters that are confidential.

**Problem:** Log files are wider-distributed than production secrets. Logs may be
accessed by monitoring tools, shared with support, or inadvertently exposed. A
credential in a log is a credential leak.

**Correct approach:** Never log sensitive values. Use sanitization as a safety net
(LOG-SAN rules). Design log events to convey operational meaning without including
the sensitive values themselves.

---

### Anti-Pattern 4 — "Vague Messages"

**Description:** Log messages like "Error occurred", "Something went wrong",
"Process completed", or "Step done".

**Problem:** These messages contain no actionable information. When an operator sees
"Error occurred", they cannot diagnose the problem without reading source code.

**Correct approach:** Log messages must answer: what happened, where, with what
inputs, with what outcome. "Kill switch check failed: VIX fetch returned null — using
cached VIX 18.4 — check is ALLOW" is an excellent message.

---

### Anti-Pattern 5 — "Severity Inflation"

**Description:** Using CRITICAL for everything to ensure the operator sees it.
Using ERROR for expected, handled failures.

**Problem:** When everything is CRITICAL, nothing is CRITICAL. Alert fatigue sets
in and real critical events are missed.

**Correct approach:** Follow the severity classification rules in Section 8.4
and LOG-SEV rules in Part IX. Reserve CRITICAL for genuine emergencies.

---

### Anti-Pattern 6 — "Log Without Context"

**Description:** Log events without cycle_id, trade_id, or any correlation keys.

**Problem:** Cannot reconstruct the sequence of events that led to an outcome.
Cannot answer "what else happened during this cycle?" Cannot correlate the audit
record with the operational log.

**Correct approach:** Always use the context manager (logger.set_context) when
inside a cycle or trade scope. The enricher will add trace context automatically
in all enriched events.

---

### Anti-Pattern 7 — "Synchronous Log Writes on Hot Paths"

**Description:** Forcing synchronous log writes (waiting for fsync) on every
log event in a hot path.

**Problem:** Log writes become a bottleneck. The system's cycle latency increases.
The trading system is slowed by its own observability layer.

**Correct approach:** Only CRITICAL and AUDIT events require synchronous writes.
All other events use asynchronous writes. The LOG-STR rules define the durability
requirements per severity.

---

### Anti-Pattern 8 — "Undocumented Event Types"

**Description:** Adding new log event types to source code without registering them
in the Logging Registry.

**Problem:** The event is not validated, not properly routed, and not documented.
It becomes invisible noise. Completeness audits report it as a gap. Schema drift
happens silently.

**Correct approach:** Register every new event type in the Logging Registry before
deploying the code that emits it. The registration is part of the code change.

---

# SUPPLEMENT G — OPERATIONAL RUNBOOK

## G.1 Daily Operations Checklist

The following checks are recommended daily by operators:

1. Review the dashboard: confirm all 18 engine OHS scores are NOMINAL or OPTIMAL.
2. Review active alerts: any open alerts must have investigation notes.
3. Review daily P&L summary: confirm within expected range.
4. Review kill switch status: should be inactive on normal market days.
5. Review log storage utilization: confirm < 80%.
6. Review audit chain integrity report: confirm chain is intact.
7. Review exception log: any new exception types require investigation.

## G.2 Weekly Checklist

1. Review LQS report: confirm all dimensions > 0.85.
2. Review alert false positive rate: refine rules if > 10%.
3. Review unregistered event type report: register or suppress all.
4. Review quarantine events: resolve validation failures.
5. Review log volume trends: identify unusual volume changes.
6. Review archive jobs: confirm all archiving is completing.
7. Review storage capacity forecast: project when intervention is needed.

## G.3 Incident Response — Logging System Failure

When the logging system reports a failure:

**Step 1 — Assess impact on trading:**
Is the trading system still operating? Logging failures must not stop trading.
If trading is affected, escalate immediately.

**Step 2 — Identify the failing component:**
Check the monitoring dashboard for which logging component has a FAILED OHS.

**Step 3 — Apply recovery procedure:**
Follow the recovery scenario appropriate to the failure (Scenarios 1–3 in the
Recovery Manager, Section 3.20).

**Step 4 — Validate recovery:**
After applying recovery, run the domain readiness checks for the recovered
component. All HARD checks must pass before marking the incident resolved.

**Step 5 — Document:**
Write a post-incident report within 24 hours. Log the incident in the governance
audit trail.

---

# SUPPLEMENT H — COMPREHENSIVE GLOSSARY

| Term | Definition |
|------|-----------|
| Aggregation | The process of combining related log events into summaries (cycle summaries, trade timelines). |
| Alert Manager | The component that evaluates alert rules and dispatches notifications to operators. |
| Archive Manager | The component managing long-term log storage beyond operational retention. |
| Audit Chain | A sequence of audit records linked by hash references providing tamper evidence. |
| Audit Manager | The component providing the immutable, append-only audit store. |
| Audit Record | A log event in the audit store recording a governance-relevant occurrence. |
| Buffer | An in-memory queue holding events temporarily before routing and storage. |
| Category | A hierarchical classification of a log event (e.g., ENGINE.RISK_GUARDIAN). |
| Chief Observability Officer | The person responsible for logging registry, quality measurements, and audit access policy. |
| Compliance Log | A log event required for regulatory or policy compliance purposes. |
| Context Propagation | The automatic inclusion of cycle_id, trace_id, and other context fields in every log event. |
| Correlation ID | A unique identifier linking log events from the same logical operation. |
| Dashboard Manager | The component serving the Streamlit operational dashboard. |
| Enrichment | The automatic addition of context fields (cycle_id, trace_id) to log events. |
| Event Type | A specific type of log event with a defined schema (e.g., DECISION.APPROVED). |
| Hash Chain | See Audit Chain. |
| Health Manager | The component computing and tracking OHS scores for all system components. |
| Hot Storage | The storage tier holding recent log files (last 7 days), indexed for fast search. |
| Legal Hold | A directive preventing deletion of log events, overriding retention policies. |
| Log Aggregator | The component grouping related events by cycle_id, trade_id, or other key. |
| Log Catalog | The human-readable, searchable view of all registered log event types. |
| Log Collector | The ingestion point for all log events; buffers, validates, and sanitizes. |
| Log Router | The component dispatching events to the appropriate storage sinks. |
| Logging Constitution | The 110 inviolable rules governing the logging system. |
| Logging Quality Score | A 0.0–1.0 composite score measuring log quality across 12 dimensions. |
| Logging Registry | The central catalog of all defined log event types, schemas, and routing rules. |
| Metrics Manager | The component collecting, aggregating, and serving time-series metrics. |
| Monitoring Manager | The component providing continuous oversight via scheduled checks. |
| OHS | Operational Health Score — a 0.0–1.0 score for an IIOS component. |
| Quarantine | Storage for log events that failed validation — separate from operational logs. |
| Recovery Manager | The component coordinating observability system recovery from failures. |
| Retention Manager | The component enforcing log retention policies. |
| Sanitization | The process of removing or redacting sensitive values from log events. |
| Sanitizer | The sub-component of the Log Collector performing sanitization. |
| Severity | The urgency classification of a log event (DEBUG, INFO, WARNING, ERROR, CRITICAL). |
| Sensitivity | The confidentiality classification of a log event (LOW, MEDIUM, HIGH). |
| Span | A single operation within a distributed trace. |
| Telemetry | Structured operational data used for performance analysis and continuous improvement. |
| Telemetry Manager | The component collecting and storing telemetry events in the SQLite database. |
| Trace | A collection of spans representing a complete distributed operation (e.g., one cycle). |
| Tracing Manager | The component capturing, storing, and providing access to distributed traces. |
| Warm Storage | Log files 7–90 days old, compressed, with disk-based index. |

---

# DOCUMENT METRICS

| Attribute | Value |
|-----------|-------|
| Document Code | IIOS-LOG-OBS-001 |
| Framework Version | 1.0.0 |
| Document Status | Active |
| Total Parts | 10 |
| Total Supplements | 8 (A through H) |
| Total Constitution Rules | 110 |
| Total Readiness Checks | 74 HARD + 19 SOFT = 93 total |
| Total Components Defined | 19 |
| Total Services Defined | 12 |
| Total Quality Dimensions | 12 |
| Total Log Categories | 39 |
| Total Engine Scopes | 18 |
| Total Governance Domains | 4 ownership tiers |
| Total Alert Categories | 4 (CRITICAL, ERROR, WARNING, INFO) |
| Total Metrics Defined | 47+ across 6 domains |
| Total Hierarchy Levels | 15 |
| Total Lifecycle Stages | 12 |
| Total Anti-Patterns | 8 |
| Total Glossary Entries | 38 |

---

# AMENDMENT HISTORY

| Version | Date | Author | Change Description |
|---------|------|--------|-------------------|
| 1.0.0 | 2026-07-04 | Architecture Council | Initial publication |

---

# CLOSING STATEMENT

This document — the Logging and Observability Framework for the Investment
Intelligence Operating System (IIOS), bearing document code IIOS-LOG-OBS-001 —
is the complete, authoritative specification for how all logging, monitoring,
tracing, metrics collection, auditing, health reporting, and operational observability
are governed throughout IIOS.

The framework defined here is not aspirational. It represents the current
architectural intent: every component, service, rule, and quality dimension in
this document is either already implemented or is on the active development roadmap.
Any deviation from this framework is a known exception that must be documented,
time-bounded, and approved by the Architecture Council.

The Logging Constitution (Part IX) is law. The 74 HARD readiness checks
(Part X) are the bar for production readiness. The 12 quality dimensions (Part VII)
are the ongoing health criteria for the observability system.

Good observability is not an afterthought. It is the infrastructure that makes
everything else in IIOS trustworthy, accountable, and improvable. The framework
defined here ensures that IIOS can be operated, diagnosed, audited, and improved
with confidence — from the first day of paper trading through years of live operation.

---

*IIOS-LOG-OBS-001 / Version 1.0.0 / Status: Active*
*Logging and Observability Framework — Investment Intelligence Operating System*
*Architecture Council Approved*
