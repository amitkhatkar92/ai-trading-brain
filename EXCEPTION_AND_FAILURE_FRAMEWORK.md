# EXCEPTION AND FAILURE MANAGEMENT FRAMEWORK
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-EXC-FLR-001
**Version:** 1.0.0
**Status:** Active
**Classification:** Architecture Reference — Engineering Specification
**Scope:** All IIOS engines, agents, workflows, services, and infrastructure

---

## Document Purpose

This document defines the complete Exception and Failure Management Framework
for the Investment Intelligence Operating System (IIOS). It specifies how every
error, exception, fault, failure, degradation, timeout, interruption, dependency
issue, infrastructure problem, AI anomaly, data inconsistency, security incident,
and recovery process shall be handled throughout the entire system.

This is an engineering architecture specification. It defines structure, behaviour,
responsibilities, policies, and governance. It does not define source code,
implementation language, API contracts, or database schemas.

---

## Scope

This framework applies to:
- All 18 IIOS engines (GlobalIntelligence through ControlTower).
- All AI agents operating within the Debate and Decision engine.
- All data feed integrations (primary and fallback).
- All broker integrations (paper and live).
- All infrastructure components (containers, volumes, networking).
- All logging, monitoring, and observability components.
- All scheduled and event-driven workflows.
- All human-initiated operations (operator commands, configuration changes).

---

## Table of Contents

- Part I: Exception Philosophy
- Part II: Exception Taxonomy (35 categories)
- Part III: Framework Architecture (20 components)
- Part IV: Exception Hierarchy (14 levels)
- Part V: Failure Lifecycle (12 stages)
- Part VI: Recovery Strategies (16 patterns)
- Part VII: Reliability Framework (12 dimensions)
- Part VIII: Exception Governance
- Part IX: Engineering Constitution (110 rules)
- Part X: Readiness Checklist (11 domains)
- Supplement A: Exception Taxonomy Reference
- Supplement B: Severity Catalog
- Supplement C: Recovery Catalog
- Supplement D: Incident Response Matrix
- Supplement E: Failure Pattern Reference
- Supplement F: Engineering Decision Records
- Supplement G: Common Anti-Patterns
- Supplement H: Operational Runbook
- Supplement I: Comprehensive Glossary

---

# PART I — EXCEPTION PHILOSOPHY

## 1.1 What is an Exception?

An exception is a condition that deviates from the expected, normal flow of
operation in a system. It is a signal that something has occurred which the
normal execution path was not designed to handle without explicit intervention.
Exceptions are not inherently failures — they are notifications that a boundary
condition, unexpected state, or resource limit has been encountered.

In the context of IIOS, an exception is any condition detected at runtime that
the executing component cannot resolve by continuing its normal execution path.
Exceptions range in severity from minor (a cache miss that requires a remote
fetch) to critical (a kill switch trigger that halts all trading).

Exceptions are categorised, classified, and handled systematically. An exception
that is properly handled degrades gracefully. An exception that is not handled
propagates upward until it either reaches a handler or terminates the operation.

The goal of exception management is not to prevent exceptions — in a complex system
operating in uncertain environments (live financial markets, external APIs, network
links), exceptions are inevitable. The goal is to handle every exception correctly,
recover wherever possible, and escalate wherever recovery is not possible.

---

## 1.2 What is a Failure?

A failure is the condition in which a component, service, or system is no longer
able to perform its defined function to the required standard. A failure is the
observable result of one or more exceptions that were not recovered.

Key distinction: an exception is the detection of a problem; a failure is the
consequence of a problem that was not resolved. An exception that is handled
successfully does not become a failure. An exception that is not handled or that
exceeds recovery limits becomes a failure.

In IIOS, failures are classified by scope:
- **Component failure:** A single service or sub-component stops functioning.
- **Engine failure:** An entire IIOS engine cannot execute its responsibilities.
- **Layer failure:** An entire layer of the processing pipeline is unavailable.
- **System failure:** IIOS cannot execute decision cycles or manage positions.
- **Infrastructure failure:** Underlying compute, storage, or networking is unavailable.

Failures are never ignored. Every failure triggers a defined response that is
proportional to its severity and scope.

---

## 1.3 Failure vs Error

These terms are often conflated but represent distinct conditions in the IIOS
architecture:

**Error:** A detected deviation from the expected state or result within an operation.
An error is a signal. It may or may not indicate a failure. An error that is caught
and handled by the local component does not propagate and does not become a failure.

**Failure:** The inability to complete a required function. A failure is a consequence.
It represents the end state after an error was not recoverable by the local component.

**Example:** A network timeout connecting to the data feed is an error. If the retry
logic resolves the connection, no failure occurred — only an error was experienced.
If all retries exhaust without connection, the data feed has failed — a failure state.

**Engineering implication:** Error handling is local (within the component). Failure
management is systemic (coordinated across components). The Framework Architecture
defines both layers.

---

## 1.4 Fault vs Defect

**Fault:** An incorrect state in the running system — a condition that, if encountered
by execution, will produce incorrect or unexpected behaviour. A fault is latent until
it is activated by the execution path that encounters it.

**Defect:** An error in the design or implementation that creates a fault when the
system is built and deployed. Defects are the cause; faults are the manifestation.

**Relationship:** A defect in a data feed parser (wrong field mapping) creates a fault
in the running system (the parsed data is incorrect). The fault activates when the
execution reaches the code path that uses the incorrect mapping. The resulting
observable problem is an error or failure.

**IIOS implication:** The Exception Framework handles faults at runtime. The
development process (code review, testing, validation) prevents defects. The
framework cannot fix defects, but it must detect faults caused by defects and
contain their impact.

---

## 1.5 Incident vs Exception

**Exception:** A single detected anomaly within the operation of a component. It
is handled by the component's exception handler or propagated to the next handler
in the chain. Its scope is the operation in which it occurs.

**Incident:** A broader condition affecting one or more system functions, requiring
coordinated response, investigation, and remediation. An incident may be triggered
by a single exception (a kill switch trigger is both an exception and an incident)
or by a pattern of exceptions across multiple components.

**Escalation path:** Exception → unhandled → component failure → incident declared
→ Incident Manager engaged → coordinated response.

An incident has a defined lifecycle: detection, declaration, triage, response,
resolution, post-incident review. An exception has a simpler lifecycle: detection,
classification, handling, audit.

---

## 1.6 Expected vs Unexpected Exception

**Expected exception:** An exception that the system is explicitly designed to handle.
The component knows this condition can occur, has a handler for it, and handles it
without escalation. Network timeouts, cache misses, data validation failures, and
temporary broker unavailability are expected exceptions in IIOS.

**Unexpected exception:** An exception that the component was not designed to handle.
It may represent a bug, an untested code path, a previously unknown environmental
condition, or a violation of an assumed invariant. Unexpected exceptions are
higher-severity because their impact is unknown.

**Design principle:** The set of expected exceptions for each component is defined
in its exception specification. When an unexpected exception occurs (one not in the
specification), it is classified as UNEXPECTED and handled by the default exception
handler, which logs it at ERROR, attempts isolation, and escalates.

The goal over time is to convert unexpected exceptions into expected exceptions:
observe the unexpected exception, add it to the component's exception specification,
and add explicit handling for it.

---

## 1.7 Recoverable vs Non-Recoverable Exception

**Recoverable exception:** An exception from which the system can return to normal
or degraded-but-functional operation without human intervention. The exception is
detected, handled, the affected operation may be retried or replaced by a fallback,
and the system continues.

**Non-recoverable exception:** An exception from which the system cannot return to
acceptable operation automatically. Human intervention is required. Examples: audit
store corruption, broker authentication total failure, infrastructure storage exhaustion.

**Classification criteria:**
- Can the state before the exception be restored or reconstructed? → Recoverable.
- Can the operation be safely retried without side effects? → Recoverable.
- Is there a fallback that provides equivalent or degraded service? → Recoverable.
- Is data integrity at risk if the system continues? → Non-recoverable (escalate).
- Does recovery require human judgment? → Non-recoverable (escalate).

**IIOS trading implication:** Non-recoverable exceptions in the trading path trigger
the kill switch or position halt as a safety measure. It is architecturally safer
to stop trading than to continue with an unrecovered exception in the risk or
execution path.

---

## 1.8 Transient vs Permanent Failure

**Transient failure:** A failure that is temporary in nature. The underlying cause
will resolve (or has already resolved) without intervention. Network packet loss,
brief API rate limit hits, temporary database connection pool exhaustion, and
momentary VIX data feed interruption are transient failures.

**Permanent failure:** A failure that will not resolve without explicit intervention.
A corrupted file, a hardware disk failure, a revoked API key, an expired certificate,
or a code defect that always triggers the same exception are permanent failures.

**Handling strategy difference:**
- Transient failures: Retry with backoff. Most retries succeed within seconds.
- Permanent failures: Retry will not help. Trigger fallback, alert operator,
  do not waste cycles on infinite retry.

**Detection heuristic:** If the same failure recurs 3+ times within 60 seconds,
reclassify from transient to permanent candidate. Alert the operator. Switch to
fallback. Cease retry until the underlying cause is investigated.

---

## 1.9 Graceful Degradation

Graceful degradation is the ability of a system to maintain partial functionality
when components fail, rather than failing completely. In a gracefully degrading
system, failures are contained: they affect the minimum necessary scope, and the
system continues to operate at reduced capability while the failure is active.

**IIOS graceful degradation examples:**
- Primary data feed unavailable → Auto-switch to yfinance fallback. Trading continues.
  Decision quality may decrease slightly (lower data freshness) but the system
  operates.
- MetaLearning engine OHS in DEGRADED tier → Strategy weights use cached/default
  values. Decisions are made but without adaptive weighting.
- Telegram notification channel unavailable → Alerts written to the dashboard and
  log only. Operations continue; human notification is delayed but system is safe.
- One debate agent timeout → Decision made with 4/5 agents. Score computed on
  reduced confidence. Threshold raised by 0.5 points.

**Design principle:** Every IIOS engine must define its graceful degradation mode:
what it provides when operating at reduced capability, what it requires to degrade
gracefully rather than fail completely, and what triggers escalation from degradation
to failure.

---

## 1.10 Fault Tolerance

Fault tolerance is the property of a system that allows it to continue operating
correctly in the presence of one or more faults. A fault-tolerant system does not
merely degrade gracefully — it continues to meet its functional and safety
requirements even when components are faulty.

**IIOS fault tolerance mechanisms:**
- **Redundant data feeds:** Multiple feeds (Dhan, yfinance) for the same data.
  A fault in one feed does not affect data availability.
- **Multi-agent decisions:** 5 debate agents. A fault in one agent does not
  prevent a decision.
- **Kill switch independence:** The Risk Guardian kill switch operates independently
  of other engines. A fault in the decision engine does not prevent kill switch
  activation.
- **Audit store separation:** The audit store is isolated from operational storage.
  A fault in operational logging does not corrupt the audit record.
- **State checkpointing:** Critical state (open positions, trade records) is
  persisted to the database. A fault that restarts the process does not lose position
  state.

**Constitutional requirement:** The kill switch path (detection of VIX > 45 or
daily loss > 2%) must be fault-tolerant with respect to all other engines. No
fault in any other engine may prevent the kill switch from triggering when conditions
are met.

---

## 1.11 Resilience

Resilience is the broader capability of a system to absorb disruption, adapt to
changed conditions, and recover quickly to normal operation. Resilience encompasses
fault tolerance (continuing despite faults) and recovery (returning to normal from
failure) and adds adaptation (the system learns from disruptions to become more
robust against future ones).

**IIOS resilience dimensions:**
- **Absorb:** Buffered logging prevents event loss during brief storage failures.
  The decision cycle has latency headroom before the kill switch threshold.
- **Adapt:** The Learning System adjusts strategy weights based on performance.
  The MetaLearning regime-strategy map adapts to changing market conditions.
  Alert thresholds can be adjusted based on observed false positive rates.
- **Recover:** Defined recovery scenarios for every identified failure type.
  Automatic fallback to secondary data sources. Operator runbooks for manual
  recovery.

**Resilience is measurable:** Mean Time to Detect (MTTD), Mean Time to Recover
(MTTR), and Mean Time Between Failures (MTBF) are tracked per component and
reported in the Analytics service.

---

## 1.12 Reliability

Reliability is the probability that a system performs its required function
correctly over a specified time period under specified conditions. A reliable system
is one that consistently does what it is supposed to do.

**IIOS reliability requirements:**
- Decision cycle completion rate: > 99% of scheduled cycles during market hours.
- Kill switch accuracy: 100% (must trigger exactly when conditions are met, must
  not trigger when conditions are not met).
- Order placement accuracy: > 99.9% (orders must reflect decisions exactly).
- Data feed availability: > 99.5% (accounting for planned fallback events).
- Audit record completeness: 100% (every auditable event must have an audit record).

**Reliability vs availability:** Availability measures whether the system is running.
Reliability measures whether it is running correctly. A system can be available but
unreliable (running but producing wrong outputs). IIOS must be both available and
reliable.

---

## 1.13 Self-Healing

Self-healing is the capability of a system to automatically detect and correct
problems without human intervention. Self-healing does not require the problem to
be anticipated in advance — it requires sufficient monitoring to detect the problem
and sufficient recovery automation to fix it.

**IIOS self-healing capabilities:**
- **Automatic data feed switch:** Detects primary feed failure and switches to
  fallback without human intervention.
- **Automatic engine restart:** A failed engine is restarted automatically up to
  3 times before escalating to human intervention.
- **Automatic strategy disable:** A strategy that exceeds its max drawdown threshold
  (15%) or falls below its win rate threshold (< 50% for 30 days) is automatically
  disabled without human intervention.
- **Circuit breaker reset:** Circuit breakers reset automatically after the cooldown
  period when the underlying service recovers.
- **Buffer self-management:** The log buffer manages its own overflow, evicting old
  events and maintaining headroom.

**Self-healing limits:** Self-healing is appropriate for known failure modes with
defined recovery paths. For unknown failure modes or failures affecting financial
integrity (incorrect positions, audit corruption), human intervention is required.
Self-healing must never resolve ambiguous financial state automatically.

---

## 1.14 Operational Continuity

Operational continuity is the goal that IIOS continues to perform its core functions
across disruptions: hardware failures, software crashes, market volatility spikes,
data feed interruptions, broker outages, and infrastructure restarts.

**Continuity requirements:**
- Market hours continuity: During market hours (09:15–15:30 IST), IIOS must be
  capable of managing open positions even if new decision cycles cannot run.
  Open positions must not be abandoned due to a system failure.
- Position safety: If IIOS cannot operate for more than 15 minutes during market
  hours, it must evaluate whether open positions should be closed as a safety measure.
- Kill switch persistence: If the kill switch was active when the system restarted,
  it must remain active after restart until explicitly lifted by an operator.
- Audit continuity: The audit record must never have a gap. If an operation cannot
  be audited, it must not proceed.

**Business Continuity vs Disaster Recovery:**
- Business Continuity: IIOS continues to operate at reduced capability during
  partial failures (degraded but functional).
- Disaster Recovery: IIOS is restored to full operation from a complete failure
  (all processes stopped, data restored from backup).

Both plans must be defined, documented, tested, and executable by the operations
team.

---

## 1.15 The Exception Philosophy Summary

The eight principles that govern exception and failure management in IIOS:

**Principle 1 — Safety First:** When in doubt, stop trading. An exception in the
risk or execution path that cannot be resolved within the cycle's latency budget
triggers a safe halt. Capital preservation overrides trading continuity.

**Principle 2 — Every Exception is Handled:** No exception propagates unhandled.
Every layer has a default handler that catches, logs, classifies, and responds
appropriately.

**Principle 3 — Expected Failures are Planned For:** Every component has a defined
set of expected exceptions with explicit handling. Unexpected exceptions are
escalated.

**Principle 4 — Fail Loudly, Not Silently:** Failures are reported immediately
and visibly. Silent failures — where the system appears to work but is producing
incorrect results — are architecturally prohibited.

**Principle 5 — Contain Before Recover:** Containment precedes recovery. An active
failure must be isolated before recovery attempts to prevent the failure from
spreading.

**Principle 6 — Recovery is Verified:** A recovery attempt is not complete until
the recovered component is verified functional. Declaring recovery without
verification is not recovery.

**Principle 7 — Every Failure Teaches:** Every failure is an opportunity to improve
the system. Post-incident analysis is mandatory, and learnings are captured in the
Knowledge Base.

**Principle 8 — Human Override is Always Available:** Automation handles recoverable
failures. Human operators can always override automated decisions. No automated
recovery action may be made irreversible.

---

*End of Part I*

---

# PART II — EXCEPTION TAXONOMY

## 2.1 Taxonomy Overview

The IIOS Exception Taxonomy defines 35 exception categories. Each category
represents a distinct domain of exceptions with common characteristics, common
causes, and common handling strategies. Categories are hierarchical — more specific
categories inherit the handling rules of their parent categories.

The taxonomy is the reference used by the Exception Classifier component to assign
every detected exception to a category. Correct classification determines severity,
routing, handling strategy, and audit requirements.

---

## 2.2 Category 1 — System Exceptions (SYSTEM)

**Namespace:** SYSTEM
**Scope:** The IIOS platform as a whole.
**Description:** Exceptions that affect the operation of the IIOS process itself —
not specific to any individual engine or service but representing conditions at
the platform level.

**Sub-categories:**
- SYSTEM.STARTUP_FAILURE — The system fails to initialize correctly.
- SYSTEM.SHUTDOWN_FAILURE — The system fails to shut down cleanly.
- SYSTEM.MODE_CHANGE_FAILURE — A requested mode change (paper/live) fails.
- SYSTEM.SCHEDULER_FAILURE — The cycle scheduler stops functioning.
- SYSTEM.OHS_CRITICAL — System-wide OHS drops below the CRITICAL threshold.
- SYSTEM.KILL_SWITCH_FAILURE — The kill switch mechanism fails to activate.
- SYSTEM.SIGNAL_HANDLER_FAILURE — A process signal (SIGTERM, SIGINT) cannot
  be handled.

**Severity range:** WARNING to CRITICAL.
**SYSTEM.KILL_SWITCH_FAILURE is always CRITICAL** — this is the highest-severity
exception in the taxonomy. It represents a situation where the system's primary
safety mechanism has failed.

**Handling principle:** System exceptions are handled at the MasterOrchestrator
level. They are always logged and alerted. CRITICAL system exceptions may trigger
an emergency shutdown to protect open positions.

---

## 2.3 Category 2 — Application Exceptions (APP)

**Namespace:** APP
**Scope:** Application-level logic in IIOS engines and workflows.
**Description:** Exceptions arising from the application code itself — incorrect
states, violated invariants, programming errors that manifest at runtime, or
conditions not covered by the application's design.

**Sub-categories:**
- APP.INVARIANT_VIOLATION — A design invariant was found to be false at runtime.
- APP.UNEXPECTED_STATE — An engine encountered a state that should never occur.
- APP.NULL_REFERENCE — A required object reference was null.
- APP.TYPE_MISMATCH — A value was of unexpected type.
- APP.BOUNDS_VIOLATION — A value exceeded expected bounds (e.g., negative quantity).
- APP.CONCURRENCY_VIOLATION — A shared resource was accessed incorrectly.
- APP.CONTRACT_VIOLATION — A function received arguments violating its contract.

**Severity range:** ERROR to CRITICAL.
**Handling principle:** Application exceptions indicate potential defects. They are
logged with full context (including relevant state), and the affected operation is
aborted. The defect is added to the issue backlog for the next Architecture Council
review.

---

## 2.4 Category 3 — Infrastructure Exceptions (INFRA)

**Namespace:** INFRA
**Scope:** The underlying infrastructure IIOS runs on (containers, OS, hardware).
**Description:** Exceptions arising from infrastructure components: container
orchestration failures, OS resource limits, Docker/compose failures, host-level
problems.

**Sub-categories:**
- INFRA.CONTAINER_CRASH — A container exits unexpectedly.
- INFRA.RESOURCE_EXHAUSTION — CPU, memory, or file handle limits reached.
- INFRA.VOLUME_FAILURE — A mounted volume becomes unavailable.
- INFRA.HOST_UNREACHABLE — The host running IIOS is unreachable.
- INFRA.CLOCK_DRIFT — System clock drift exceeds acceptable bounds.
- INFRA.PROCESS_LIMIT — Maximum process/thread count exceeded.

**Severity range:** ERROR to CRITICAL.
**Handling principle:** Infrastructure exceptions are typically not recoverable by
application-level code. They require infrastructure-level intervention (restart,
resize, repair). IIOS must detect them quickly and trigger human notification. The
trading system must halt safely (not abruptly) when infrastructure fails.

---

## 2.5 Category 4 — Network Exceptions (NET)

**Namespace:** NET
**Scope:** Network communication between IIOS and external services.
**Description:** Exceptions arising from network connectivity issues.

**Sub-categories:**
- NET.TIMEOUT — A network operation did not complete within the allowed time.
- NET.CONNECTION_REFUSED — The remote endpoint refused the connection.
- NET.DNS_RESOLUTION_FAILURE — A hostname could not be resolved.
- NET.SSL_HANDSHAKE_FAILURE — TLS/SSL negotiation failed.
- NET.RATE_LIMIT_EXCEEDED — The remote API's rate limit was hit.
- NET.CONNECTION_RESET — An established connection was reset by the remote.
- NET.PROXY_FAILURE — An intermediate proxy failed.

**Severity range:** WARNING to ERROR.
**Handling principle:** Network exceptions are typically transient. The Retry Manager
is the primary handler. After retry exhaustion, the Fallback Manager is engaged.
Most IIOS network exceptions affect data feed access; the auto-fallback to yfinance
is the standard recovery path.

---

## 2.6 Category 5 — Database Exceptions (DB)

**Namespace:** DB
**Scope:** Database operations (SQLite telemetry and state databases).
**Description:** Exceptions arising from database access and operations.

**Sub-categories:**
- DB.CONNECTION_FAILURE — Cannot open or maintain a database connection.
- DB.QUERY_FAILURE — A query execution fails.
- DB.WRITE_FAILURE — A write operation fails (disk full, lock contention).
- DB.CORRUPTION — Database file is corrupt or unreadable.
- DB.LOCK_TIMEOUT — A database lock cannot be acquired within the timeout.
- DB.SCHEMA_MISMATCH — The database schema does not match expected version.
- DB.TRANSACTION_FAILURE — A transaction cannot be committed.

**Severity range:** ERROR to CRITICAL.
**DB.CORRUPTION is always CRITICAL** — it represents potential data loss.
**Handling principle:** Read failures allow fallback to in-memory state. Write
failures are more severe — they may indicate loss of trade records or audit
records. DB.CORRUPTION triggers an immediate halt of all database operations,
human notification, and restoration from backup.

---

## 2.7 Category 6 — Storage Exceptions (STOR)

**Namespace:** STOR
**Scope:** File system and persistent storage operations.
**Description:** Exceptions arising from file system operations — log files,
configuration files, strategy files, and data exports.

**Sub-categories:**
- STOR.DISK_FULL — No space remaining on the storage volume.
- STOR.FILE_NOT_FOUND — A required file does not exist at the expected path.
- STOR.PERMISSION_DENIED — Insufficient permissions to read or write a file.
- STOR.FILE_CORRUPT — A file cannot be parsed or is incomplete.
- STOR.WRITE_FAILURE — A file write operation fails.
- STOR.LOCK_FAILURE — A file lock cannot be acquired.
- STOR.VOLUME_UNAVAILABLE — The storage volume is not mounted or is unreachable.

**Severity range:** WARNING to CRITICAL.
**STOR.DISK_FULL affecting audit or database paths is CRITICAL.**
**Handling principle:** Log write failures use the buffer as a temporary holdover
while the underlying cause is resolved. Configuration file failures are CRITICAL
at startup (system cannot start without configuration) but ERROR at runtime
(system uses last known configuration).

---

## 2.8 Category 7 — Memory Exceptions (MEM)

**Namespace:** MEM
**Scope:** In-process memory management.
**Description:** Exceptions arising from memory allocation, limits, or corruption.

**Sub-categories:**
- MEM.OUT_OF_MEMORY — Allocation request cannot be satisfied.
- MEM.MEMORY_LEAK_DETECTED — Memory usage growing unboundedly over time.
- MEM.CACHE_OVERFLOW — An in-memory cache has exceeded its configured limit.
- MEM.BUFFER_OVERFLOW — An in-memory buffer has exceeded its configured limit.
- MEM.STACK_OVERFLOW — Call stack depth exceeded (typically deep recursion).
- MEM.ALLOCATION_FAILURE — A specific memory allocation failed.

**Severity range:** WARNING (CACHE_OVERFLOW) to CRITICAL (OUT_OF_MEMORY).
**Handling principle:** Cache overflows use eviction policies. Buffer overflows use
defined drop strategies. Out-of-memory conditions require process restart (after
safe position assessment). Memory leak detection triggers an alert and a planned
restart at the next low-activity window.

---

## 2.9 Category 8 — CPU Resource Exceptions (CPU)

**Namespace:** CPU
**Scope:** CPU utilization and processing capacity.
**Description:** Exceptions arising from CPU resource constraints.

**Sub-categories:**
- CPU.THROTTLING — CPU is being throttled by the container runtime.
- CPU.SUSTAINED_HIGH_USAGE — CPU above 90% for more than 5 minutes.
- CPU.COMPUTATION_TIMEOUT — A computation exceeded its allocated time budget.
- CPU.SPIN_DETECTED — A tight loop consuming 100% CPU is detected.

**Severity range:** WARNING to ERROR.
**Handling principle:** CPU exceptions affect cycle latency. If a computation
timeout occurs within a critical path, the operation is aborted and the system
falls back to a cached or default result. The Monitoring Manager tracks CPU
utilization and alerts before throttling occurs.

---

## 2.10 Category 9 — Thread Exceptions (THR)

**Namespace:** THR
**Scope:** Thread and concurrent execution management.
**Description:** Exceptions arising from multi-threaded operation.

**Sub-categories:**
- THR.DEADLOCK — Two or more threads are waiting on each other indefinitely.
- THR.RACE_CONDITION — Concurrent access produces inconsistent state.
- THR.THREAD_CRASH — A background thread terminates unexpectedly.
- THR.THREAD_LEAK — Threads are created but not terminated.
- THR.LOCK_CONTENTION — High lock contention is degrading throughput.
- THR.POOL_EXHAUSTION — The thread pool has no available threads.

**Severity range:** WARNING to CRITICAL.
**THR.DEADLOCK is always CRITICAL** — it requires process restart.
**Handling principle:** Deadlocks are detected by the watchdog timer (no thread
should hold a lock for more than 10 seconds). Thread crashes are detected and the
affected background service is restarted. Thread leaks trigger an alert when the
thread count exceeds a threshold.

---

## 2.11 Category 10 — Configuration Exceptions (CFG)

**Namespace:** CFG
**Scope:** Configuration loading, validation, and application.
**Description:** Exceptions arising from system or engine configuration.

**Sub-categories:**
- CFG.FILE_NOT_FOUND — A required configuration file is missing.
- CFG.PARSE_ERROR — A configuration file cannot be parsed (YAML/JSON error).
- CFG.VALIDATION_FAILURE — A configuration value fails validation rules.
- CFG.SCHEMA_MISMATCH — The configuration file version does not match expected.
- CFG.REQUIRED_KEY_MISSING — A required configuration key is absent.
- CFG.VALUE_OUT_OF_RANGE — A configuration value is outside its allowed range.
- CFG.CIRCULAR_REFERENCE — Configuration inheritance has a circular dependency.
- CFG.DRIFT_DETECTED — Running configuration does not match stored version.

**Severity range:** WARNING to CRITICAL.
**Startup CFG exceptions are CRITICAL** — the system must not start with an invalid
configuration. Runtime CFG exceptions use the last known valid configuration.
**Handling principle:** Configuration exceptions at startup are blocking. Runtime
configuration drift is alerted but does not stop the system. The Configuration
Framework (IIOS-CFG-FWK-001) governs configuration management in detail.

---

## 2.12 Category 11 — Authentication Exceptions (AUTH)

**Namespace:** AUTH
**Scope:** Authentication operations (broker auth, API auth).
**Description:** Exceptions arising from authentication failures.

**Sub-categories:**
- AUTH.CREDENTIAL_INVALID — Provided credentials are rejected.
- AUTH.TOKEN_EXPIRED — An authentication token has expired.
- AUTH.TOKEN_REFRESH_FAILURE — An attempt to refresh a token failed.
- AUTH.MFA_REQUIRED — Multi-factor authentication is required (unexpected).
- AUTH.ACCOUNT_LOCKED — The account has been locked after failed attempts.
- AUTH.SESSION_EXPIRED — An authenticated session has expired.

**Severity range:** ERROR to CRITICAL.
**AUTH.CREDENTIAL_INVALID for broker is CRITICAL** — live trading requires
authenticated broker access.
**Handling principle:** Token refresh is automatic. Credential invalidity requires
human intervention (new token must be provided). During authentication failure, the
affected service (data feed or broker) is marked unavailable and fallback is engaged.

---

## 2.13 Category 12 — Authorization Exceptions (AUTHZ)

**Namespace:** AUTHZ
**Scope:** Authorization and access control.
**Description:** Exceptions arising from insufficient permissions or access control
violations.

**Sub-categories:**
- AUTHZ.PERMISSION_DENIED — An operation was denied due to insufficient permissions.
- AUTHZ.RESOURCE_FORBIDDEN — A requested resource is not accessible.
- AUTHZ.SCOPE_EXCEEDED — An operation attempted to exceed its granted scope.
- AUTHZ.UNAUTHORIZED_ACCESS — An access attempt without valid credentials.

**Severity range:** WARNING to CRITICAL.
**AUTHZ.UNAUTHORIZED_ACCESS is always CRITICAL** — it may indicate a security
incident.
**Handling principle:** Authorization exceptions are always logged in the security
audit trail. The affected operation is immediately aborted. The Security Manager
is notified. Three or more AUTHZ exceptions within 5 minutes from the same source
trigger a security incident.

---

## 2.14 Category 13 — Security Exceptions (SEC)

**Namespace:** SEC
**Scope:** Security-related anomalies across the system.
**Description:** Exceptions arising from detected security violations or anomalies.

**Sub-categories:**
- SEC.INJECTION_DETECTED — Log injection or input injection attempt detected.
- SEC.AUDIT_CHAIN_BROKEN — Audit hash chain integrity has failed.
- SEC.TAMPERING_DETECTED — Evidence of unauthorized modification of system files.
- SEC.CREDENTIAL_EXPOSURE — A credential was detected in an unsanitized path.
- SEC.ANOMALOUS_ACCESS — Access pattern deviating significantly from baseline.
- SEC.POLICY_VIOLATION — A security policy rule was violated.

**Severity range:** ERROR to CRITICAL.
**All security exceptions are always CRITICAL** by default unless explicitly
classified otherwise in the exception specification.
**Handling principle:** Security exceptions trigger immediate CRITICAL alert,
the affected operation is halted, and the Incident Manager is engaged. Security
incidents are never auto-resolved — human review is always required.

---

## 2.15 Category 14 — Encryption Exceptions (ENC)

**Namespace:** ENC
**Scope:** Encryption and decryption operations.
**Description:** Exceptions arising from cryptographic operations.

**Sub-categories:**
- ENC.KEY_NOT_FOUND — Encryption key is not available.
- ENC.DECRYPTION_FAILURE — Cannot decrypt a ciphertext.
- ENC.CERT_EXPIRED — A TLS certificate has expired.
- ENC.CERT_INVALID — A certificate fails validation.
- ENC.ALGORITHM_UNSUPPORTED — A required cryptographic algorithm is unavailable.

**Severity range:** ERROR to CRITICAL.
**ENC.KEY_NOT_FOUND for the audit store key is CRITICAL** — audit records cannot
be written or read without the key.

---

## 2.16 Category 15 — Workflow Exceptions (WF)

**Namespace:** WF
**Scope:** Multi-step workflow execution.
**Description:** Exceptions arising from workflow orchestration — when a defined
sequence of steps cannot be completed as planned.

**Sub-categories:**
- WF.STEP_TIMEOUT — A workflow step did not complete within its time limit.
- WF.STEP_FAILURE — A workflow step failed and cannot be retried.
- WF.DEPENDENCY_UNAVAILABLE — A required input from a preceding step is unavailable.
- WF.CYCLE_ABORT — A decision cycle is aborted due to downstream failure.
- WF.PARTIAL_COMPLETION — A workflow completed some but not all steps.
- WF.SEQUENCE_VIOLATION — Steps were executed in the wrong order.
- WF.IDEMPOTENCY_FAILURE — A step that should be idempotent produced different
  results on re-execution.

**Severity range:** WARNING to CRITICAL.
**WF.CYCLE_ABORT is always logged at ERROR** — it represents a lost decision
opportunity.
**Handling principle:** Workflow exceptions are handled by the Recovery Coordinator.
Partial completions require compensation (rolling back or completing the remaining
steps). Cycle aborts trigger a fast retry (up to 2 times) before being abandoned.

---

## 2.17 Category 16 — Business Rule Exceptions (BIZ)

**Namespace:** BIZ
**Scope:** IIOS domain business rules.
**Description:** Exceptions arising from violations of defined trading, risk, or
portfolio management rules.

**Sub-categories:**
- BIZ.MAX_POSITION_EXCEEDED — An order would exceed the maximum position limit.
- BIZ.RISK_LIMIT_BREACH — A risk limit would be exceeded by a proposed action.
- BIZ.KILL_SWITCH_ACTIVE — A trade operation was attempted while the kill switch
  is active.
- BIZ.DAILY_LOSS_LIMIT — The daily loss limit has been reached.
- BIZ.STRATEGY_DISABLED — An operation was attempted for a disabled strategy.
- BIZ.INSUFFICIENT_CAPITAL — Insufficient capital for a proposed trade.
- BIZ.OUTSIDE_TRADING_HOURS — An operation was attempted outside market hours.
- BIZ.DUPLICATE_ORDER — An order that would duplicate an existing position.

**Severity range:** INFO (expected rule check) to CRITICAL (kill switch related).
**Handling principle:** Business rule exceptions are expected and handled gracefully.
They do not indicate system problems — they indicate the rules are working. They are
logged at INFO (for expected checks like position limits) and escalated only when
they indicate something unexpected (a kill switch trade attempt).

---

## 2.18 Category 17 — Validation Exceptions (VAL)

**Namespace:** VAL
**Scope:** Data and input validation across the system.
**Description:** Exceptions arising from data that does not conform to expected
formats, ranges, or constraints.

**Sub-categories:**
- VAL.SCHEMA_VIOLATION — Data does not conform to the expected schema.
- VAL.TYPE_ERROR — A value is of the wrong type.
- VAL.RANGE_VIOLATION — A numeric value is outside its allowed range.
- VAL.NULL_VALUE — A required value is null or missing.
- VAL.FORMAT_ERROR — A string value does not match the expected format.
- VAL.REFERENTIAL_INTEGRITY — A reference to another entity is invalid.
- VAL.BUSINESS_CONSTRAINT — A value violates a business constraint.
- VAL.DUPLICATE — A duplicate value was detected where uniqueness is required.

**Severity range:** WARNING to ERROR.
**Handling principle:** Validation exceptions reject invalid data at the boundary.
The source of invalid data is logged for diagnosis. Valid data continues; invalid
data is rejected and the failure is noted.

---

## 2.19 Category 18 — AI Model Exceptions (MODEL)

**Namespace:** MODEL
**Scope:** AI model execution and output.
**Description:** Exceptions arising from AI and machine learning model operations.

**Sub-categories:**
- MODEL.LOAD_FAILURE — A model cannot be loaded from storage.
- MODEL.INFERENCE_FAILURE — Model inference fails with an error.
- MODEL.OUTPUT_INVALID — Model output is outside expected value range.
- MODEL.CONFIDENCE_TOO_LOW — Model confidence score is below minimum threshold.
- MODEL.TIMEOUT — Model inference exceeded the latency budget.
- MODEL.VERSION_MISMATCH — Model version does not match expected feature schema.
- MODEL.DRIFT_DETECTED — Model output distribution has drifted from baseline.
- MODEL.DEGENERATE_OUTPUT — Model produces extreme or constant outputs.

**Severity range:** WARNING to ERROR.
**Handling principle:** AI model exceptions trigger fallback to default/cached
predictions or rule-based decisions. A model with persistent inference failures
is disabled and replaced by its fallback until it can be retrained and re-validated.
MODEL.DRIFT_DETECTED requires investigation but is not an immediate operational
blocker.

---

## 2.20 Category 19 — Prediction Exceptions (PRED)

**Namespace:** PRED
**Scope:** Prediction engine operations (MetaLearning, signal generation).
**Description:** Exceptions specific to the prediction and signal generation pipeline.

**Sub-categories:**
- PRED.INSUFFICIENT_HISTORY — Not enough historical data for a prediction.
- PRED.FEATURE_UNAVAILABLE — A required feature cannot be computed.
- PRED.STALE_PREDICTION — The last prediction is too old to use.
- PRED.PREDICTION_CONTRADICTION — Multiple prediction sources contradict each other.
- PRED.ENSEMBLE_FAILURE — The prediction ensemble cannot reach a result.

**Severity range:** WARNING to ERROR.
**Handling principle:** Prediction exceptions use cached or default predictions.
If predictions are unavailable, the decision threshold is raised (more conservative)
to compensate for reduced confidence.

---

## 2.21 Category 20 — Learning Exceptions (LEARN)

**Namespace:** LEARN
**Scope:** Learning System operations.
**Description:** Exceptions arising from strategy learning and adaptation processes.

**Sub-categories:**
- LEARN.UPDATE_FAILURE — A learning update cannot be applied.
- LEARN.DATA_INSUFFICIENT — Insufficient data for a learning update.
- LEARN.CONVERGENCE_FAILURE — A learning process does not converge.
- LEARN.ROLLBACK_REQUIRED — A learning update produced worse outcomes and must
  be rolled back.
- LEARN.KNOWLEDGE_CORRUPTION — The knowledge base has inconsistent entries.

**Severity range:** WARNING to ERROR.
**Handling principle:** Learning exceptions do not block trading. If an update
fails, the previous state is retained. Learning is best-effort; trading correctness
takes priority.

---

## 2.22 Category 21 — Market Data Exceptions (MKTDATA)

**Namespace:** MKTDATA
**Scope:** Market data acquisition and processing.
**Description:** Exceptions arising from market data feeds and processing.

**Sub-categories:**
- MKTDATA.FEED_UNAVAILABLE — The market data feed cannot be reached.
- MKTDATA.STALE_DATA — Data has not been updated for too long.
- MKTDATA.INVALID_PRICE — A price value is clearly erroneous (zero, negative,
  extreme spike).
- MKTDATA.SYMBOL_NOT_FOUND — A requested symbol has no data.
- MKTDATA.INCOMPLETE_BAR — An OHLCV bar has missing fields.
- MKTDATA.TIMESTAMP_GAP — A gap in the time series data.
- MKTDATA.CIRCUIT_BREAKER — Exchange has halted trading (circuit breaker active).
- MKTDATA.EXCHANGE_CLOSED — Market data is unavailable because the exchange is
  closed or halted.

**Severity range:** WARNING to CRITICAL.
**MKTDATA.FEED_UNAVAILABLE triggers auto-fallback** — this is the most common
expected exception in IIOS and has the most tested recovery path.
**MKTDATA.INVALID_PRICE is CRITICAL** — using a clearly wrong price for risk
calculations could lead to catastrophic decisions.

---

## 2.23 Category 22 — Broker Exceptions (BROKER)

**Namespace:** BROKER
**Scope:** Broker API interactions (order placement, position management).
**Description:** Exceptions arising from broker communications.

**Sub-categories:**
- BROKER.ORDER_REJECTED — The broker rejected an order.
- BROKER.ORDER_TIMEOUT — No confirmation received within the timeout.
- BROKER.PARTIAL_FILL — An order was partially filled.
- BROKER.FILL_MISMATCH — Actual fill differs significantly from expected.
- BROKER.API_UNAVAILABLE — The broker API cannot be reached.
- BROKER.RATE_LIMIT — Broker API rate limit exceeded.
- BROKER.ACCOUNT_SUSPENDED — Trading account is suspended.
- BROKER.MARGIN_CALL — Margin requirements cannot be met.
- BROKER.POSITION_MISMATCH — Broker-reported positions do not match IIOS records.

**Severity range:** WARNING to CRITICAL.
**BROKER.POSITION_MISMATCH is always CRITICAL** — discrepancy between broker and
IIOS position records represents a financial integrity risk.
**BROKER.ORDER_REJECTED is ERROR** — it means a decision was made but cannot be
executed; the position record must be updated accordingly.

---

## 2.24 Category 23 — Exchange Exceptions (EXCH)

**Namespace:** EXCH
**Scope:** Exchange-level conditions affecting trading.
**Description:** Exceptions arising from the exchange environment itself.

**Sub-categories:**
- EXCH.MARKET_CLOSED — Trading is not possible (pre-market, post-market, holiday).
- EXCH.CIRCUIT_BREAKER_L1 — Exchange-level circuit breaker (15-minute halt).
- EXCH.CIRCUIT_BREAKER_L2 — Exchange-level circuit breaker (45-minute halt).
- EXCH.CIRCUIT_BREAKER_L3 — Exchange-level circuit breaker (day halt).
- EXCH.HIGH_VOLATILITY_FREEZE — Excessive volatility is preventing order matching.
- EXCH.SETTLEMENT_DISRUPTION — Settlement process disrupted.

**Severity range:** INFO (MARKET_CLOSED) to CRITICAL (day halt with open positions).
**Handling principle:** Exchange circuit breakers require IIOS to halt new position
opening and assess existing positions. The Circuit Breaker Manager tracks exchange-
level halts and prevents new orders from being placed until the halt is lifted.

---

## 2.25 Category 24 — Portfolio Exceptions (PORT)

**Namespace:** PORT
**Scope:** Portfolio management operations.
**Description:** Exceptions arising from portfolio-level operations.

**Sub-categories:**
- PORT.ALLOCATION_FAILURE — Capital cannot be allocated as planned.
- PORT.REBALANCE_FAILURE — A portfolio rebalance operation fails.
- PORT.STATE_INCONSISTENCY — Portfolio state is internally inconsistent.
- PORT.CORRELATION_LIMIT — Adding a position would exceed correlation limits.
- PORT.CONCENTRATION_LIMIT — A single position would exceed concentration limits.

**Severity range:** WARNING to ERROR.
**Handling principle:** Portfolio exceptions prevent the specific allocation or
rebalance. The system continues with the existing portfolio state. PORT.STATE_
INCONSISTENCY requires investigation — it may indicate a broker position mismatch.

---

## 2.26 Category 25 — Risk Exceptions (RISK)

**Namespace:** RISK
**Scope:** Risk management and risk control operations.
**Description:** Exceptions arising from risk monitoring and control.

**Sub-categories:**
- RISK.VAR_LIMIT_BREACH — Value at Risk exceeds the defined limit.
- RISK.DRAWDOWN_THRESHOLD — Strategy drawdown exceeds threshold (warning level).
- RISK.DRAWDOWN_LIMIT — Strategy drawdown exceeds limit (disable threshold).
- RISK.KILL_SWITCH_VIX — VIX exceeds 45 (kill switch condition).
- RISK.KILL_SWITCH_DAILY_LOSS — Daily loss exceeds 2% (kill switch condition).
- RISK.STRESS_TEST_FAIL — Monte Carlo simulation reveals extreme risk concentration.
- RISK.CORRELATION_SPIKE — Portfolio correlation has spiked above threshold.

**Severity range:** WARNING to CRITICAL.
**RISK.KILL_SWITCH_VIX and RISK.KILL_SWITCH_DAILY_LOSS are always CRITICAL.**
**Handling principle:** Risk exceptions at the WARNING level trigger alerts and
increased monitoring. At the CRITICAL level, they trigger automated protective
action (strategy disable or kill switch).

---

## 2.27 Category 26 — Strategy Exceptions (STRAT)

**Namespace:** STRAT
**Scope:** Strategy execution and management.
**Description:** Exceptions arising from strategy operations.

**Sub-categories:**
- STRAT.SIGNAL_GENERATION_FAILURE — A strategy cannot generate its signal.
- STRAT.BACKTEST_FAILURE — A backtest run fails.
- STRAT.PARAMETER_VIOLATION — Strategy parameters are outside their allowed range.
- STRAT.WIN_RATE_THRESHOLD — Strategy win rate drops below the disable threshold.
- STRAT.EVOLUTION_FAILURE — Strategy evolution run fails.
- STRAT.PROMOTION_REJECTED — A strategy fails the promotion gate.
- STRAT.NO_ELIGIBLE_STRATEGIES — No eligible active strategies found for current
  regime.

**Severity range:** WARNING to ERROR.
**STRAT.NO_ELIGIBLE_STRATEGIES is ERROR** — it means the system cannot generate
trading signals for the current market condition.
**Handling principle:** Strategy exceptions affect only the specific strategy.
The system continues with remaining active strategies. STRAT.NO_ELIGIBLE_STRATEGIES
triggers a conservative decision: no new positions until at least one strategy
returns to eligibility.

---

## 2.28 Category 27 — Simulation Exceptions (SIM)

**Namespace:** SIM
**Scope:** Monte Carlo and market simulation operations.
**Description:** Exceptions arising from simulation runs.

**Sub-categories:**
- SIM.INSUFFICIENT_SCENARIOS — Fewer than the minimum required scenarios completed.
- SIM.DIVERGENCE — Simulation paths diverge to extreme values (numerical issue).
- SIM.TIMEOUT — Simulation did not complete within its time budget.
- SIM.INPUT_INVALID — Simulation input parameters are invalid.

**Severity range:** WARNING to ERROR.
**Handling principle:** Simulation exceptions reduce confidence in risk estimates.
If fewer than the minimum scenarios complete, the risk estimate is conservative
(uses worst-case from available scenarios). SIM.TIMEOUT results in using the last
completed simulation.

---

## 2.29 Category 28 — Monitoring Exceptions (MON)

**Namespace:** MON
**Scope:** Monitoring system operations.
**Description:** Exceptions arising from the monitoring and observability system.

**Sub-categories:**
- MON.HEALTH_CHECK_FAILURE — A health check cannot be executed.
- MON.METRIC_COLLECTION_FAILURE — A metric cannot be collected.
- MON.ALERT_DELIVERY_FAILURE — An alert cannot be delivered to its channel.
- MON.DASHBOARD_FAILURE — The dashboard is inaccessible.
- MON.SILENCE_DETECTED — An expected source has gone silent.

**Severity range:** WARNING to ERROR.
**Handling principle:** Monitoring exceptions do not stop trading. They reduce
the system's self-awareness. MON.ALERT_DELIVERY_FAILURE is particularly important
to handle — if alerts cannot reach the operator, the safety net is broken. IIOS
should attempt alternative notification channels.

---

## 2.30 Category 29 — Logging Exceptions (LOG)

**Namespace:** LOG
**Scope:** Logging system operations.
**Description:** Exceptions arising from the logging and observability framework.

**Sub-categories:**
- LOG.WRITE_FAILURE — A log event cannot be written to storage.
- LOG.SANITIZER_FAILURE — The sanitizer fails to process an event.
- LOG.AUDIT_WRITE_FAILURE — An audit record cannot be written.
- LOG.BUFFER_OVERFLOW — The log buffer has overflowed.
- LOG.ROTATION_FAILURE — A log file rotation fails.

**Severity range:** WARNING to CRITICAL.
**LOG.AUDIT_WRITE_FAILURE is always CRITICAL** — it is a governance blocker.
**Handling principle:** See the Logging and Observability Framework (IIOS-LOG-OBS-001)
for detailed handling. The key principle: LOG.AUDIT_WRITE_FAILURE blocks the
operation that requires the audit record.

---

## 2.31 Category 30 — Recovery Exceptions (RCV)

**Namespace:** RCV
**Scope:** Recovery operation execution.
**Description:** Exceptions arising during recovery procedures.

**Sub-categories:**
- RCV.RECOVERY_FAILED — A recovery attempt itself failed.
- RCV.STATE_RECONSTRUCTION_FAILURE — Cannot reconstruct state from backup.
- RCV.BACKUP_CORRUPT — A backup file is corrupt or incomplete.
- RCV.VALIDATION_FAILURE — Post-recovery validation fails.
- RCV.TIMEOUT — A recovery procedure exceeded its time limit.

**Severity range:** ERROR to CRITICAL.
**Handling principle:** Recovery exceptions escalate immediately to human intervention.
A failed recovery cannot be auto-resolved — it requires human judgment about the
correct path forward.

---

## 2.32 Category 31 — External Service Exceptions (EXT)

**Namespace:** EXT
**Scope:** Third-party external service integrations.
**Description:** Exceptions arising from external service dependencies.

**Sub-categories:**
- EXT.SERVICE_UNAVAILABLE — An external service cannot be reached.
- EXT.RESPONSE_INVALID — An external service returned unexpected data.
- EXT.SLA_BREACH — An external service is responding but below SLA.
- EXT.API_CHANGED — An external API's schema changed unexpectedly.
- EXT.DEPRECATED_API — A deprecated API endpoint is still being used.

**Severity range:** WARNING to ERROR.
**Handling principle:** External service exceptions use circuit breakers to prevent
cascade failures. When an external service is down, the circuit breaker opens and
fallback logic is applied.

---

## 2.33 Category 32 — Timeout Exceptions (TO)

**Namespace:** TO
**Scope:** Time limit enforcement across all operations.
**Description:** Exceptions arising when operations exceed their allocated time.

**Sub-categories:**
- TO.ENGINE_EXECUTION — An engine exceeded its layer latency threshold.
- TO.OPERATION_TIMEOUT — A specific operation exceeded its time limit.
- TO.LOCK_ACQUISITION — Lock acquisition timed out.
- TO.HEALTH_CHECK — A health check did not complete in time.
- TO.SHUTDOWN — System shutdown did not complete within the shutdown window.
- TO.STARTUP — System startup exceeded its expected duration.

**Severity range:** WARNING to CRITICAL.
**TO.ENGINE_EXECUTION exceeding CRIT threshold is CRITICAL** — it threatens the
entire cycle latency budget.
**Handling principle:** Timeout exceptions abort the timed-out operation. For
engine execution timeouts, the result is treated as unavailable and the next-layer
fallback is applied.

---

## 2.34 Category 33 — Concurrency Exceptions (CONC)

**Namespace:** CONC
**Scope:** Concurrent execution coordination.
**Description:** Exceptions arising from concurrent access to shared resources.

**Sub-categories:**
- CONC.OPTIMISTIC_LOCK_FAILURE — An optimistic lock check failed (value changed).
- CONC.WRITE_CONFLICT — Two concurrent write operations conflict.
- CONC.STALE_READ — A read returned stale data due to concurrent modification.
- CONC.ATOMIC_OPERATION_FAILED — An atomic operation could not be completed.

**Severity range:** WARNING to ERROR.
**Handling principle:** Concurrency exceptions are typically resolved by retry (with
fresh data). If they persist, they indicate a design issue that requires investigation.

---

## 2.35 Category 34 — Dependency Exceptions (DEP)

**Namespace:** DEP
**Scope:** Inter-engine and inter-service dependencies.
**Description:** Exceptions arising when a component's dependencies are unavailable.

**Sub-categories:**
- DEP.DEPENDENCY_UNAVAILABLE — A required upstream component is unavailable.
- DEP.DEPENDENCY_DEGRADED — A required upstream component is in DEGRADED state.
- DEP.DEPENDENCY_TIMEOUT — A dependency call timed out.
- DEP.CIRCULAR_DEPENDENCY — A circular dependency has been detected.
- DEP.VERSION_INCOMPATIBILITY — A dependency is at an incompatible version.

**Severity range:** WARNING to ERROR.
**Handling principle:** Dependency exceptions cause the dependent component to
degrade gracefully. If the dependency provides data, cached data is used. If the
dependency provides a decision, a conservative default is applied.

---

## 2.36 Category 35 — Unknown Exceptions (UNK)

**Namespace:** UNK
**Scope:** Any exception not matching a defined category.
**Description:** Exceptions that cannot be classified into any defined category.
These represent truly unexpected conditions — bugs, untested paths, or novel
failures not anticipated in the taxonomy.

**Sub-categories:**
- UNK.UNCLASSIFIED — Exception cannot be classified.
- UNK.FOREIGN_EXCEPTION — An exception from an external library with no known
  IIOS mapping.

**Severity range:** ERROR by default (elevated to CRITICAL if in the risk or
execution path).
**Handling principle:** Unknown exceptions are always logged with maximum context
(full exception chain, system state snapshot, environment details). The affected
operation is aborted. An alert is always raised. The Knowledge Base is updated
with the new exception pattern so it can be classified in a future taxonomy update.
Unknown exceptions are the primary driver of taxonomy evolution.

---

*End of Part II*

---
# PART III — FRAMEWORK ARCHITECTURE

## 3.1 Architecture Overview

The Exception and Failure Management Framework Architecture defines 20 components
that collectively detect, classify, contain, recover from, escalate, audit, and
learn from every exception and failure in IIOS.

`
FRAMEWORK ARCHITECTURE — COMPONENT MAP

[Exception Sources: Engines, Agents, Workflows, Infrastructure, External]
         |
         v
[Exception Classifier] <--> [Exception Registry / Exception Catalog]
         |
         v
[Failure Detector] -------> [Health Manager]
         |
         v
[Failure Analyzer] -------> [Root Cause Analyzer] <--> [Knowledge Base]
         |
         v
[Isolation Manager] ------> [Circuit Breaker Manager]
         |
         v
[Recovery Coordinator]
    |             |
    v             v
[Retry Manager] [Fallback Manager]
    |             |
    +------+------+
           |
           v
[Compensation Manager] <-- (if state mutation occurred)
           |
           v
[Alert Manager] ----------> [Incident Manager] <--> [Escalation Manager]
           |
           v
[Audit Manager] -----------> Audit Store
           |
           v
[Postmortem Manager] <----> [Continuous Improvement Manager]
`

---

## 3.2 Component 1 — Exception Registry

### Purpose
The Exception Registry is the authoritative catalog of all defined exception types,
their classification metadata, handling specifications, and recovery prescriptions.
It is the reference that makes exception handling consistent across all 18 IIOS engines.

### Responsibilities
- Maintain the complete list of all 35+ exception categories and their sub-types.
- Store classification metadata: default severity, sensitivity, audit requirement.
- Store handling specifications: retry policy, fallback policy, escalation path.
- Store recovery prescriptions: what to do when this exception is encountered.
- Detect unregistered exception types (exceptions raised by code but not in the Registry).
- Serve as the reference for documentation and training materials.
- Track exception type evolution: when new exceptions are added, changed, or removed.

### Inputs
- Exception type definitions from engineering specifications.
- Registration requests from engines at startup.
- New exception type submissions from the Knowledge Base (post-incident learnings).

### Outputs
- Exception type lookup results (for the Classifier).
- Handling specification lookup results (for the Recovery Coordinator).
- Unregistered exception type alerts.
- Registry change records (for the Audit Manager).

### Dependencies
- No runtime dependencies on other framework components (initialized first).
- Exception specification files (must exist before Registry initializes).

### Interactions
- Exception Classifier queries the Registry for classification metadata.
- Recovery Coordinator queries the Registry for handling specifications.
- Knowledge Base writes new exception types to the Registry.

### Failure Modes
- **Registry initialization failure:** Framework startup fails. All exception
  handling falls back to the default handler (log, alert, abort) until the
  Registry is restored.
- **Corrupt Registry entry:** The affected exception type uses the default handler.
  An alert is raised for the corrupt entry.

### Recovery Strategy
- On initialization failure: fix the specification file and restart.
- On corrupt entry: use default handler for the affected type, repair the entry,
  reload without full restart.

### Monitoring
- Registry initialization time (target: < 500ms).
- Registered exception type count (tracked for growth).
- Unregistered exception type rate (target: 0 per week in production).

### Engineering Notes
- The Registry is initialized before all other framework components. It is the
  first component in the startup sequence.
- The Registry is read-heavy and write-once after initialization (new types are
  added only after postmortem review, not during live operation).

---

## 3.3 Component 2 — Exception Catalog

### Purpose
The Exception Catalog provides a human-readable, searchable, and documented view
of all exception types — their definitions, examples, severity classifications,
handling strategies, and historical frequency.

### Responsibilities
- Generate documentation for every registered exception type.
- Provide search by category, severity, engine, and keyword.
- Display example exceptions with context (from anonymized historical incidents).
- Generate frequency statistics per exception type.
- Identify exception type gaps (exceptions expected but not defined).
- Produce coverage reports (which engines have their exception types documented).

### Outputs
- Documentation for the docs/ system.
- Frequency statistics reports.
- Coverage reports.
- Exception gap alerts.

### Engineering Notes
- The Catalog is generated periodically (on CI run, on schema change, weekly).
- Frequency statistics are read from the Audit Manager's historical data.

---

## 3.4 Component 3 — Exception Classifier

### Purpose
The Exception Classifier assigns every detected exception to its category, severity,
sensitivity, and handling track. Correct classification is the prerequisite for
correct handling.

### Responsibilities
- Receive exception notifications from all IIOS components.
- Match the exception against the Exception Registry to identify its type.
- Assign category, severity, sensitivity, and handling track.
- Handle unregistered exceptions: classify as UNK.UNCLASSIFIED with ERROR severity.
- Enrich the exception with context (current cycle, engine, operation, state snapshot).
- Pass the classified exception to the Failure Detector and Recovery Coordinator.
- Track classification accuracy (did the automated classification match human
  review findings?).

### Inputs
- Exception notifications from all IIOS engines (exception type, message, context,
  optional stack reference).
- Exception Registry (for matching and classification metadata).
- Current system context (cycle_id, engine, regime, phase).

### Outputs
- Classified exception record with: type, category, severity, sensitivity, handling
  track, enriched context.

### Classification Logic
`
CLASSIFICATION DECISION TREE

1. Is the exception type in the Registry?
   YES: Look up metadata → Assign registered classification
   NO: Assign UNK.UNCLASSIFIED, severity=ERROR (CRITICAL if in risk/execution path)

2. Is the exception in the risk or execution path?
   YES: Elevate severity by one level (WARNING→ERROR, ERROR→CRITICAL)
   NO: Use registered severity

3. Is the exception during market hours with open positions?
   YES: Elevate to at minimum ERROR
   NO: Use current severity

4. Is this the 3rd+ occurrence of this exception type in 5 minutes?
   YES: Elevate to CRITICAL (pattern indicates permanent failure)
   NO: Use current severity
`

### Failure Modes
- **Classifier unavailable:** Default classification is applied: category=UNK,
  severity=ERROR. Handling continues with default handler.
- **Registry lookup timeout:** Same as classifier unavailable.

### Monitoring
- Classification throughput (exceptions per second).
- Unregistered exception rate.
- Severity elevation events.

---

## 3.5 Component 4 — Failure Detector

### Purpose
The Failure Detector monitors the stream of classified exceptions and system health
signals to detect when a component has transitioned from normal operation to a
failure state.

### Responsibilities
- Monitor the exception stream for patterns indicating component failure.
- Monitor OHS scores from the Health Manager for tier transitions.
- Detect when a component's exception rate exceeds its normal range.
- Detect missing heartbeats (silence from components that should be active).
- Detect cascade failure indicators (failures spreading across components).
- Declare failure states and notify the Failure Analyzer.

### Failure Detection Patterns

**Pattern 1 — Repeated exceptions:** The same exception type from the same
component fires more than 3 times within 60 seconds. Indicates permanent failure.

**Pattern 2 — Error rate spike:** A component's error rate increases by > 300%
vs its 1-hour baseline. Indicates a new problem.

**Pattern 3 — OHS tier drop:** A component's OHS drops by 2 or more tiers in
a single 5-minute window. Indicates a sudden severe degradation.

**Pattern 4 — Heartbeat silence:** A component that should produce events every
N seconds produces nothing for 3*N seconds. Indicates the component may have
stopped.

**Pattern 5 — Cascade correlation:** Multiple downstream components report
similar exceptions within 30 seconds of each other. Indicates a shared upstream
failure.

### Inputs
- Classified exception stream from the Exception Classifier.
- OHS scores from the Health Manager.
- Component heartbeat signals.

### Outputs
- Failure declarations: component name, failure type, evidence, timestamp.
- Cascade failure alerts.

### Monitoring
- Failure declaration accuracy (false positive rate, target < 5%).
- Failure detection latency (time from first exception to failure declaration).

---

## 3.6 Component 5 — Failure Analyzer

### Purpose
The Failure Analyzer evaluates declared failures to determine their scope, impact,
and immediate response priority. It is the triage layer between detection and
recovery.

### Responsibilities
- Receive failure declarations from the Failure Detector.
- Assess failure scope: component, engine, layer, or system level.
- Assess failure impact: what capabilities are lost, what risks are created.
- Assess failure urgency: how quickly does this require response.
- Recommend immediate actions: isolate, recover, escalate, or halt.
- Coordinate with the Root Cause Analyzer for deeper diagnosis.
- Produce failure analysis reports for the Postmortem Manager.

### Impact Assessment Matrix

| Failure Scope | Impact Assessment | Immediate Action |
|--------------|-------------------|------------------|
| Individual service | Reduced engine capability | Retry, fallback |
| Engine complete | Layer unavailable | Skip layer, use cache |
| Kill switch path | Safety risk | Immediate CRITICAL alert |
| Execution path | Cannot trade | Halt new trades |
| Risk path | Uncontrolled risk | Kill switch consideration |
| Audit path | Compliance risk | Block auditable operations |
| Multiple engines | System degradation | Raise all thresholds |
| Full system | Complete failure | Emergency shutdown |

### Outputs
- Failure analysis report: scope, impact, urgency, recommended action.
- Action directives to Recovery Coordinator, Isolation Manager, Alert Manager.

---

## 3.7 Component 6 — Recovery Coordinator

### Purpose
The Recovery Coordinator orchestrates the recovery from failures. It coordinates
the Retry Manager, Fallback Manager, Compensation Manager, and other recovery
components into a coherent recovery plan for each failure type.

### Responsibilities
- Receive recovery directives from the Failure Analyzer.
- Select the appropriate recovery strategy for each failure type.
- Coordinate the execution of recovery steps.
- Track recovery progress and time.
- Verify recovery success via the Health Manager.
- Escalate to the Incident Manager when recovery cannot be completed automatically.
- Record all recovery actions in the Audit Manager.

### Recovery Strategy Selection

The Recovery Coordinator selects a strategy based on:
1. The exception category (from the Registry specification).
2. The failure scope (from the Failure Analyzer).
3. Whether the operation is idempotent (safe to retry).
4. Whether side effects have already occurred (may need compensation).
5. Whether a fallback is available.

`
RECOVERY STRATEGY SELECTION FLOW

Exception Category + Failure Scope
        |
        v
Is the operation idempotent? --> NO --> Has state mutation occurred? --> YES --> Compensation Manager
        |                                       |
       YES                                      NO (safe to abort)
        |                                       |
        v                                       v
Retry Manager (with backoff)              Fallback Manager
        |
Retries exhausted?
        |
       YES --> Fallback Manager
        |
Fallback unavailable?
        |
       YES --> Graceful Degradation or Escalation
`

### Recovery Time Objectives (RTO)

The Recovery Coordinator must complete recovery (or declare recovery failure)
within these time objectives:

| Failure Type | RTO |
|-------------|-----|
| Transient data feed timeout | 30 seconds |
| Engine execution failure | 60 seconds |
| Full engine failure | 120 seconds |
| Data feed primary failure | 90 seconds (fallback switch) |
| Kill switch activation | < 5 seconds |
| Audit store write failure | < 10 seconds (retry or escalate) |

### Failure Modes
- **Recovery Coordinator itself fails:** Each engine falls back to its own local
  exception handler. A CRITICAL alert is raised immediately.

### Monitoring
- Recovery success rate per failure type.
- Mean Time to Recover (MTTR) per failure type.
- Recovery strategy distribution (which strategies are most used).

---

## 3.8 Component 7 — Retry Manager

### Purpose
The Retry Manager implements the retry logic for transient failures — attempting
the failed operation again with appropriate delays and limits.

### Responsibilities
- Execute retry attempts for failed operations.
- Apply retry policies: max attempts, backoff strategy, jitter.
- Track retry attempts per operation.
- Detect permanent failures (retries exhausted or error pattern indicates permanence).
- Report retry outcomes to the Recovery Coordinator.

### Retry Policies

**Policy A — Immediate retry (transient, low-latency):**
- Max attempts: 3
- Delay: 0 (immediate)
- Use for: data queries with sub-second normal response, cache lookups.

**Policy B — Linear backoff:**
- Max attempts: 5
- Delays: 1s, 2s, 3s, 4s, 5s
- Use for: network calls, API requests, database queries.

**Policy C — Exponential backoff with jitter:**
- Max attempts: 5
- Delays: 1s, 2s, 4s, 8s, 16s (each with +/- 20% jitter)
- Use for: external service calls, broker API calls.

**Policy D — Extended backoff (slow-recovering services):**
- Max attempts: 3
- Delays: 30s, 60s, 120s
- Use for: services that need time to recover (rate limits, circuit breakers).

**Policy E — Single attempt (non-idempotent operations):**
- Max attempts: 1
- No retry.
- Use for: order placement (retrying an order placement risks duplicate orders).

### Retry Safety Rules
- Retries are only applied to idempotent operations.
- Order placement uses Policy E always (never retried automatically).
- Audit writes use Policy B (3 retries, then CRITICAL alert — not indefinitely).
- Read operations may be retried more liberally than write operations.

### Monitoring
- Retry success rate per policy.
- Retry count distribution (how many retries before success).
- Retry exhaustion rate (permanent failure rate).

---

## 3.9 Component 8 — Fallback Manager

### Purpose
The Fallback Manager provides alternative implementations or data sources when
the primary operation has failed and retries are exhausted.

### Responsibilities
- Maintain the registry of fallback options for each operation category.
- Activate the appropriate fallback when directed by the Recovery Coordinator.
- Track fallback health (a fallback that is also unavailable is escalated).
- Monitor fallback usage duration (long-running fallbacks require investigation).
- Restore primary service when it recovers.

### IIOS Fallback Map

| Primary Service | Fallback Service | Fallback Quality |
|----------------|-----------------|------------------|
| Dhan data feed | yfinance | GOOD — same data, slight latency increase |
| Dhan broker API | Paper trading simulation | REDUCED — no live execution |
| MetaLearning weights | Equal weights (default) | REDUCED — no adaptive weighting |
| Real-time VIX | Cached VIX (max 15 min old) | REDUCED — stale data risk |
| Telegram notifications | Dashboard + log only | REDUCED — delayed human awareness |
| Primary database | In-memory state | REDUCED — no persistence |
| Configuration server | Last known configuration | REDUCED — drift risk |
| Live OHS computation | Cached OHS (5 min old) | REDUCED — stale health view |

### Fallback Activation Rules
- Fallback must be activated within the defined RTO.
- Fallback activation is logged in the Audit Manager.
- An alert is raised when a fallback activates.
- An alert is raised when a fallback has been active for > 30 minutes
  (primary has not recovered — investigation required).

### Monitoring
- Fallback activation count per service.
- Fallback duration per activation.
- Primary restore success rate.

---

## 3.10 Component 9 — Circuit Breaker Manager

### Purpose
The Circuit Breaker Manager implements the circuit breaker pattern for all external
service calls. It prevents IIOS from repeatedly attempting operations against a
clearly unavailable service.

### Responsibilities
- Track the failure/success rate for each external service.
- Open circuit breakers when failure rates exceed defined thresholds.
- Manage the half-open state (allow limited probe requests to test recovery).
- Close circuit breakers when recovery is confirmed.
- Provide circuit breaker state to the Fallback Manager (closed = try primary;
  open = go directly to fallback).

### Circuit Breaker State Machine

`
CIRCUIT BREAKER STATE MACHINE

[CLOSED] ----[failure_rate > threshold]----> [OPEN]
   ^                                            |
   |                                     [cooldown elapsed]
   |                                            |
   |                                            v
   +----------[probe_succeeds]------------ [HALF-OPEN]
                                                |
                                          [probe_fails]
                                                |
                                                v
                                            [OPEN again]
`

### Circuit Breaker Thresholds (IIOS defaults)

| Service Category | Open Threshold | Cooldown | Probe Count |
|----------------|---------------|----------|-------------|
| Data feed APIs | 5 failures in 60s | 30s | 1 |
| Broker API | 3 failures in 60s | 60s | 1 |
| External analytics | 10 failures in 120s | 120s | 2 |
| Database | 3 failures in 30s | 30s | 1 |

### Monitoring
- Circuit breaker state per service (CLOSED/OPEN/HALF-OPEN).
- Open duration per service.
- Probe success rate.

---

## 3.11 Component 10 — Compensation Manager

### Purpose
The Compensation Manager handles the undo or completion of partially-executed
operations when recovery by retry or fallback is not possible.

### Responsibilities
- Identify when an operation left partial state changes (partial side effects).
- Determine the appropriate compensation action: undo, complete, or tolerate.
- Execute compensation operations.
- Verify the system state after compensation.
- Log all compensation actions in the Audit Manager.

### Compensation Categories

**Financial compensation (highest priority):**
If an order was partially placed (some legs of a multi-leg order placed but not
all), the compensation action is to close the partial positions immediately using
market orders, regardless of price. The risk of holding an incomplete position
is greater than the cost of an unfavorable exit.

**State compensation:**
If a configuration change was partially applied, the compensation action is to
roll back to the previous configuration. IIOS must never operate with a partially-
applied configuration.

**Learning compensation:**
If a learning update was partially applied, the compensation action is to roll
back to the previous model weights. Partial model state is worse than stale state.

### Monitoring
- Compensation action count per category.
- Compensation success rate.
- Compensation latency.

---

## 3.12 Component 11 — Isolation Manager

### Purpose
The Isolation Manager contains failures by preventing them from spreading to
other components. It implements bulkheads, isolation boundaries, and quarantine
procedures.

### Responsibilities
- Implement engine-level isolation: a failing engine must not corrupt adjacent
  engines' state.
- Implement data isolation: suspect data (from a failing feed or computation) must
  not propagate to production decisions.
- Implement resource isolation: a resource-exhausting component must not starve
  other components.
- Manage isolation boundaries: define what crosses boundaries and what is blocked.
- Remove isolation when failure is resolved.

### IIOS Isolation Boundaries

**Engine isolation:** Each engine runs in its own context. An exception in one
engine does not propagate to the next unless the next engine depends on the first
engine's output. If the first engine's output is unavailable, the next engine uses
its fallback.

**Kill switch isolation:** The Risk Guardian runs with the highest isolation
guarantee. No exception from any other engine can prevent the Risk Guardian from
checking kill switch conditions.

**Audit isolation:** The Audit Manager's write path is isolated from operational
exception handling. An operational exception cannot prevent an audit record from
being written (the audit write is synchronous and blocking at the operation level).

**Data quality isolation:** A data point flagged as suspect (e.g., MKTDATA.INVALID_PRICE)
is quarantined. It does not propagate to calculations. Last known-good data is used
instead.

### Monitoring
- Active isolation boundaries.
- Isolation duration per component.
- Cross-boundary propagation events (should be 0 — any crossing is an alert).

---

## 3.13 Component 12 — Alert Manager

### Purpose
The Alert Manager transforms exception and failure events into actionable human
notifications. It is the bridge between the automated framework and the human
operator.

### Responsibilities
- Receive alert directives from the Failure Analyzer and Incident Manager.
- Apply alert severity, deduplication, and routing rules.
- Dispatch alerts to configured channels (Telegram, dashboard, log).
- Track alert acknowledgement and resolution.
- Report alert quality metrics (false positive rate, response time).

### Alert Severity for Exception Events

| Exception Severity | Alert Level | Channel |
|-------------------|------------|---------|
| CRITICAL | CRITICAL alert | Telegram + Dashboard + Log |
| ERROR | ERROR alert | Telegram + Dashboard + Log |
| WARNING | WARNING alert | Dashboard + Log |
| INFO | INFO notification | Log only |

### Deduplication Rules for Exception Alerts

Exception alerts have special deduplication rules to prevent alert storms during
mass failure events:

- First occurrence: immediate alert.
- Same exception type from same source within 5 minutes: suppress (count tracked).
- Every 5 minutes during active failure: summary alert with count.
- Alert storm (> 5 different CRITICAL exceptions within 1 minute): raise one
  CRITICAL "alert storm" notification with a summary.

---

## 3.14 Component 13 — Incident Manager

### Purpose
The Incident Manager handles exceptions and failures that cannot be resolved
automatically — those requiring human coordination, judgment, and response.

### Responsibilities
- Receive escalated failures from the Recovery Coordinator and Failure Analyzer.
- Declare formal incidents with severity classification.
- Coordinate incident response activities.
- Track incident timeline (detection time, escalation time, response time, resolution).
- Manage the incident knowledge base (what happened, what was done, what resolved it).
- Generate incident reports.
- Ensure no incident is silently closed without proper resolution.

### Incident Severity Levels

**SEV-1 (CRITICAL):** System is down or trading is halted incorrectly. Positions
are at risk. Requires immediate response. Examples: full system failure, kill switch
stuck, broker position mismatch with open positions.

**SEV-2 (HIGH):** Major capability degradation. Primary fallbacks are active.
Resolution required within 1 hour. Examples: primary data feed down (fallback
active), multiple engines in CRITICAL OHS.

**SEV-3 (MEDIUM):** Partial capability degradation. System is operational but
at reduced quality. Resolution required within 1 day. Examples: one engine in
DEGRADED OHS, strategy temporarily disabled.

**SEV-4 (LOW):** Minor issues. System is fully functional. Resolution within 1 week.
Examples: documentation gap discovered, configuration drift, minor performance
regression.

### Incident Lifecycle

`
[Failure Escalated] --> [Incident Declared] --> [Triage: SEV-1/2/3/4]
         |
         v
[Response Coordinator Assigned]
         |
         v
[Investigation] --> [Mitigation Actions] --> [Monitoring for Improvement]
         |
         v
[Resolution] --> [Validation] --> [Post-Incident Review Scheduled]
         |
         v
[Incident Closed] --> [Postmortem Manager]
`

### Monitoring
- Open incident count by severity.
- Mean time to acknowledge (MTTA) per severity.
- Mean time to resolve (MTTR) per severity.
- Incident recurrence rate (same root cause within 30 days).

---

## 3.15 Component 14 — Escalation Manager

### Purpose
The Escalation Manager ensures that exceptions and failures that require human
attention are escalated through the appropriate channels with appropriate urgency.

### Responsibilities
- Apply escalation policies: who gets notified for what severity at what time.
- Manage escalation escalation (if no response within N minutes, escalate to next tier).
- Track escalation acknowledgement.
- Prevent under-escalation (critical issues going unacknowledged).
- Prevent over-escalation (alert fatigue from unnecessary escalations).

### Escalation Policy (IIOS default)

| Severity | Initial Notification | Escalation If No Response |
|---------|---------------------|--------------------------|
| SEV-1 | Immediate Telegram | Escalate after 5 minutes |
| SEV-2 | Telegram within 2 min | Escalate after 30 minutes |
| SEV-3 | Telegram within 15 min | Escalate after 4 hours |
| SEV-4 | Dashboard only | Escalate after 5 business days |

---

## 3.16 Component 15 — Audit Manager

### Purpose
The Audit Manager records all exception-handling and failure-management events
in the immutable audit trail. It is the accountability backbone of the framework.

### Responsibilities
- Record every CRITICAL and ERROR exception in the audit trail.
- Record every failure declaration, recovery action, and incident declaration.
- Record every compensation action.
- Record every kill switch trigger and lift.
- Provide the exception audit history for postmortem analysis.
- Detect gaps in the audit trail (expected events not recorded).

### Audit Requirements by Exception Category

| Category | Audit Required | Audit Level |
|---------|---------------|-------------|
| SYSTEM.KILL_SWITCH_FAILURE | Always | CRITICAL |
| RISK.KILL_SWITCH_* | Always | CRITICAL |
| BROKER.POSITION_MISMATCH | Always | CRITICAL |
| SEC.* | Always | CRITICAL |
| BROKER.ORDER_* | Always | HIGH |
| CFG.* at CRITICAL | Always | HIGH |
| All CRITICAL severity | Always | HIGH |
| All ERROR severity | Yes | MEDIUM |
| All WARNING severity | No | — |
| Recovery actions | Always | HIGH |
| Compensation actions | Always | HIGH |

---

## 3.17 Component 16 — Health Manager

### Purpose
The Health Manager computes and tracks the Operational Health Score (OHS) for
every component, providing the quantitative health signal used by the Failure
Detector and Recovery Coordinator.

### Responsibilities
- Run scheduled health checks for all IIOS engines and services.
- Compute OHS scores using the standard formula.
- Track OHS tier transitions.
- Publish health signals to the Failure Detector.
- Provide health history for trend analysis.
- Produce the system-wide aggregate OHS.

### Health Manager's Own Exception Handling

The Health Manager must be fault-tolerant itself. If a health check for a single
engine fails, the engine's last known OHS is used (with a staleness penalty applied).
If the Health Manager itself enters a CRITICAL state, it raises a CRITICAL alert
immediately and restarts.

A Health Manager failure is treated as though all engines are in UNKNOWN state —
a conservative assumption that triggers increased caution in the trading system
(thresholds raised, no new positions opened until health visibility is restored).

---

## 3.18 Component 17 — Root Cause Analyzer

### Purpose
The Root Cause Analyzer identifies the underlying cause of failures and incidents,
beyond the immediate exception that was detected.

### Responsibilities
- Analyze the exception chain leading to a failure.
- Correlate exceptions across components to find shared root causes.
- Apply root cause classification: code defect, configuration error, external
  dependency failure, resource exhaustion, design limitation.
- Generate root cause hypotheses for investigation.
- Verify root cause hypotheses by correlation with system state.
- Provide root cause analysis reports to the Postmortem Manager.

### Root Cause Categories

| Category | Definition | Examples |
|----------|------------|---------|
| Code defect | Implementation error creating a runtime fault | Null reference, off-by-one |
| Configuration error | System misconfiguration causing unexpected behavior | Wrong threshold, wrong path |
| External dependency | Upstream service or data source failure | Data feed down, broker API down |
| Resource exhaustion | Insufficient compute, memory, disk, or network | Disk full, OOM |
| Design limitation | Architectural gap encountered at scale or edge case | Race condition in design |
| Human error | Operator action causing system problem | Wrong config change |
| Environmental | Infrastructure or environmental change | OS update, clock drift |

---

## 3.19 Component 18 — Knowledge Base

### Purpose
The Knowledge Base accumulates learnings from incidents, postmortems, and exception
patterns to continuously improve IIOS's resilience and exception handling.

### Responsibilities
- Store validated root cause analyses from postmortems.
- Store remediation recipes: given this root cause, here is how to resolve it.
- Store detection improvement suggestions: given this failure, here is how to
  detect it earlier next time.
- Feed new exception type patterns to the Exception Registry.
- Feed new fallback strategies to the Fallback Manager.
- Feed new circuit breaker thresholds to the Circuit Breaker Manager.
- Provide the Knowledge Base to the Root Cause Analyzer for pattern matching.

### Knowledge Base Entry Structure

Each entry in the Knowledge Base contains:
- Exception pattern signature: what exceptions, in what sequence, from what components.
- Root cause category.
- Validated remediation steps.
- Detection improvement recommendations.
- Prevention recommendations.
- Historical incidents that match this pattern.
- Date of entry, incident reference.

---

## 3.20 Component 19 — Postmortem Manager

### Purpose
The Postmortem Manager coordinates the post-incident review process, ensuring that
every significant incident produces documented learnings that are fed back into the
system.

### Responsibilities
- Schedule postmortems for all SEV-1 and SEV-2 incidents.
- Optionally schedule postmortems for recurring SEV-3 patterns.
- Provide the postmortem template and structure.
- Ensure postmortems produce actionable outcomes (not just descriptions).
- Track postmortem action items to completion.
- Feed postmortem learnings to the Knowledge Base and Continuous Improvement Manager.

### Postmortem Structure

Every IIOS postmortem must address:

1. **Incident Summary:** What happened, when, for how long, what impact.
2. **Timeline:** Chronological sequence of events from first detection to resolution.
3. **Detection:** How was it detected? Could it have been detected earlier?
4. **Root Cause:** Verified root cause analysis.
5. **Contributing Factors:** What made the incident worse or harder to detect.
6. **Resolution:** What resolved the incident.
7. **Action Items:** Specific, assignable, time-bounded actions to prevent recurrence.
8. **Metrics Impact:** Was trading affected? Were positions at risk?
9. **Learnings:** What the team learned. Knowledge Base entries to create.

### Postmortem Timeline Requirements

| Severity | Postmortem Deadline |
|---------|---------------------|
| SEV-1 | Within 48 hours |
| SEV-2 | Within 5 business days |
| SEV-3 (if recurring) | Within 10 business days |

---

## 3.21 Component 20 — Continuous Improvement Manager

### Purpose
The Continuous Improvement Manager drives systematic improvements to the exception
and failure management framework based on operational experience.

### Responsibilities
- Aggregate learnings from the Knowledge Base and Postmortem Manager.
- Identify patterns indicating systemic improvement opportunities.
- Propose improvements to the Architecture Council.
- Track improvement initiatives from proposal to implementation.
- Measure the impact of improvements on MTTR, MTTD, and incident frequency.
- Report improvement progress in the monthly Architecture Council review.

### Improvement Categories

**Detection improvements:** Add or refine exception detection to catch problems
earlier. Reduce MTTD.

**Recovery improvements:** Add or refine recovery strategies. Reduce MTTR.

**Prevention improvements:** Code changes, configuration hardening, or architectural
changes to prevent known failure modes. Reduce incident frequency.

**Resilience improvements:** Add redundancy, fallbacks, or circuit breakers where
none exist today.

**Documentation improvements:** Add runbooks, update exception specifications,
improve operator guidance.

---

*End of Part III*

---

# PART IV — EXCEPTION HIERARCHY

## 4.1 Hierarchy Overview

The IIOS Exception Hierarchy defines 14 contextual levels at which exceptions arise
and propagate. The hierarchy reflects the operational structure of the system: from
the widest (system-wide) to the narrowest (individual exception in a specific
operation). Understanding the hierarchy is essential for containment — exceptions
should be handled at the lowest applicable level before propagating upward.

`
EXCEPTION HIERARCHY — LEVELS

Level 1:  SYSTEM           Widest scope — entire IIOS platform
    |
Level 2:  INFRASTRUCTURE   Underlying compute, storage, network
    |
Level 3:  PLATFORM         Python runtime, OS interfaces, container
    |
Level 4:  APPLICATION      IIOS application code layer
    |
Level 5:  ENGINE           Individual engine (e.g., RiskGuardian)
    |
Level 6:  WORKFLOW         Named multi-step process within engine
    |
Level 7:  SERVICE          Service class within an engine
    |
Level 8:  AGENT            Individual AI agent
    |
Level 9:  OPERATION        A single discrete operation
    |
Level 10: DATA             Data layer access and processing
    |
Level 11: BUSINESS         Business rule evaluation
    |
Level 12: SECURITY         Security boundary enforcement
    |
Level 13: EXTERNAL         External service boundary
    |
Level 14: UNKNOWN          Uncategorized — does not fit any level
`

---

## 4.2 Level 1 — System Exceptions

**Scope:** The entire IIOS process.
**Handler:** MasterOrchestrator default handler.
**Examples:** System startup failure, kill switch mechanism failure, scheduler crash.
**Propagation rule:** System exceptions cannot propagate further — they are the
top of the hierarchy. A system-level exception that cannot be handled triggers
emergency shutdown.
**Constitutional guarantee:** A system exception never silently swallows itself.
It is always logged and alerted.

---

## 4.3 Level 2 — Infrastructure Exceptions

**Scope:** Underlying infrastructure.
**Handler:** Infrastructure monitoring subsystem, with escalation to human.
**Examples:** Container crash, disk failure, host unreachable.
**Propagation rule:** Infrastructure exceptions propagate upward to the System level
if they prevent the application from running. If they are isolated (e.g., one volume
is slow but not failed), they are contained at the Infrastructure level.

---

## 4.4 Level 3 — Platform Exceptions

**Scope:** Python runtime, OS interfaces, container runtime.
**Handler:** Application-level default handler (catches platform exceptions that
bubble up from lower library code).
**Examples:** OOM error, thread crash, file descriptor limit.
**Propagation rule:** Platform exceptions that can be caught and handled at the
Application level are handled there. Platform exceptions that cannot be caught
(e.g., OOM killing the process) propagate to the Infrastructure level (the
process manager restarts the container).

---

## 4.5 Level 4 — Application Exceptions

**Scope:** IIOS application code.
**Handler:** Application-level exception handler in the MasterOrchestrator.
**Examples:** Invariant violation, null reference, contract violation.
**Propagation rule:** Application exceptions are the first level at which IIOS
code can directly handle exceptions. Exceptions caught here that are not handled
propagate to the System level.

---

## 4.6 Level 5 — Engine Exceptions

**Scope:** A single IIOS engine.
**Handler:** Each engine has its own default exception handler.
**Examples:** Engine execution timeout, engine OHS CRITICAL transition.
**Propagation rule:** Engine exceptions are first handled by the engine's own
handler. If the engine cannot handle the exception (e.g., the engine cannot
produce its required output), the exception propagates to the Workflow level
(the workflow that called the engine handles the missing output).

---

## 4.7 Level 6 — Workflow Exceptions

**Scope:** A named multi-step workflow.
**Handler:** The workflow orchestrator.
**Examples:** Step failure, dependency unavailable, cycle abort.
**Propagation rule:** Workflow exceptions are handled by the workflow orchestrator.
If the workflow cannot complete (partial completion), compensation logic is triggered.
If compensation fails, the exception propagates to the Engine level.

---

## 4.8 Level 7 — Service Exceptions

**Scope:** A service class within an engine.
**Handler:** The calling code within the engine.
**Examples:** Service method failure, cache miss leading to error, service timeout.
**Propagation rule:** Service exceptions are handled by the calling code. If the
calling code cannot recover (e.g., the service it needs is completely unavailable),
the exception propagates to the Workflow or Engine level.

---

## 4.9 Level 8 — Agent Exceptions

**Scope:** An individual AI agent within the Debate and Decision engine.
**Handler:** The Debate and Decision engine's agent coordinator.
**Examples:** Agent timeout, agent output invalid, agent confidence too low.
**Propagation rule:** Agent exceptions are handled by the agent coordinator. A
failed agent is excluded from the debate and the decision proceeds with remaining
agents (minimum 3 agents required). If fewer than 3 agents produce valid outputs,
the exception propagates to the Engine level.

---

## 4.10 Level 9 — Operation Exceptions

**Scope:** A single discrete operation (e.g., one VIX fetch, one order placement).
**Handler:** The operation caller.
**Examples:** Network timeout on a specific request, parse error on a specific
response.
**Propagation rule:** Operation exceptions are the most granular level of exception
handling. Most operation exceptions are expected and handled locally (retry the
operation, use cached data). Unresolvable operation exceptions propagate to the
Service level.

---

## 4.11 Level 10 — Data Exceptions

**Scope:** Data access and processing.
**Handler:** The data layer within each engine.
**Examples:** Schema validation failure, null field, stale data.
**Propagation rule:** Data exceptions are handled by the consuming code. Invalid
data is rejected and a fallback (cached data, default values) is used. If no
fallback is available and the data is required, the exception propagates to the
Operation level.

---

## 4.12 Level 11 — Business Exceptions

**Scope:** Business rule evaluation.
**Handler:** The business rule enforcement layer.
**Examples:** Max position exceeded, kill switch active, daily loss limit.
**Propagation rule:** Business exceptions are typically non-propagating — they
produce a defined business outcome (reject the trade, disable the strategy) without
propagating upward. Business exceptions are expected outcomes of rule evaluation,
not system failures.

---

## 4.13 Level 12 — Security Exceptions

**Scope:** Security boundary enforcement.
**Handler:** Security Manager and Audit Manager.
**Examples:** Authorization failure, audit chain corruption, injection detected.
**Propagation rule:** Security exceptions propagate immediately to the System level.
They are never handled silently at a lower level. A security exception always
generates an audit record and an alert.

---

## 4.14 Level 13 — External Exceptions

**Scope:** External service boundaries (data feeds, broker, external APIs).
**Handler:** The integration layer for each external service.
**Examples:** API timeout, rate limit, service unavailable, response invalid.
**Propagation rule:** External exceptions are handled at the integration layer.
Retries and circuit breakers are applied here. If the external service is
persistently unavailable, the exception propagates to the Operation or Service
level, which triggers the fallback.

---

## 4.15 Level 14 — Unknown Exceptions

**Scope:** Any exception not matching levels 1–13.
**Handler:** The universal default handler (catch-all).
**Propagation rule:** Unknown exceptions are always propagated to at least the
Application level (level 4) for logging, alerting, and investigation. They are
never silently swallowed.

---

## 4.16 Exception Propagation Diagram

`
EXCEPTION PROPAGATION MODEL

Level 14 (Unknown) --> Default handler --> Log + Alert
Level 13 (External) --> Integration handler --> Retry --> Circuit Breaker --> Fallback
Level 12 (Security) --> Security handler --> Immediate alert --> Audit --> HALT
Level 11 (Business) --> Business handler --> Reject operation --> Continue
Level 10 (Data) --> Data handler --> Reject invalid data --> Use fallback
Level 9 (Operation) --> Retry --> if exhausted --> propagate UP to Level 7
Level 8 (Agent) --> Agent coordinator --> Exclude agent --> if < 3 agents --> propagate to Level 5
Level 7 (Service) --> Engine default handler --> if unresolved --> propagate UP to Level 5
Level 6 (Workflow) --> Workflow orchestrator --> Compensation --> if failed --> propagate to Level 5
Level 5 (Engine) --> Engine handler --> Fallback output --> if unavailable --> propagate to Level 4
Level 4 (Application) --> Application default handler --> Graceful degradation
Level 3 (Platform) --> OS/runtime handler --> Container restart
Level 2 (Infrastructure) --> Infrastructure manager --> Alert --> Human intervention
Level 1 (System) --> Emergency handler --> Safe shutdown if necessary
`

---

*End of Part IV*

---

# PART V — FAILURE LIFECYCLE

## 5.1 Lifecycle Overview

Every failure in IIOS travels through a 12-stage lifecycle from the moment it is
detected to the moment it produces a systemic improvement. The lifecycle ensures
that no failure goes unaddressed and that every failure contributes to making the
system more resilient.

`
FAILURE LIFECYCLE — 12 STAGES

Stage 1:  DETECTION        Exception or anomaly first detected
    |
Stage 2:  CLASSIFICATION   Failure type, scope, and severity assigned
    |
Stage 3:  VALIDATION       Confirmation that this is a genuine failure
    |
Stage 4:  ISOLATION        Failure contained — prevented from spreading
    |
Stage 5:  CONTAINMENT      Impact scope defined — blast radius minimized
    |
Stage 6:  NOTIFICATION     Human operators notified (if required by severity)
    |
Stage 7:  RECOVERY         Automated or manual recovery actions executed
    |
Stage 8:  VERIFICATION     Recovery confirmed — system returned to functional state
    |
Stage 9:  AUDIT            All failure and recovery events recorded in audit trail
    |
Stage 10: ROOT CAUSE ANALYSIS   Underlying cause identified
    |
Stage 11: KNOWLEDGE CAPTURE   Learnings stored in Knowledge Base
    |
Stage 12: CONTINUOUS IMPROVEMENT   Actions taken to prevent recurrence
`

---

## 5.2 Stage 1 — Detection

**Actor:** Failure Detector, Exception Classifier, Health Manager.
**Trigger:** An exception is raised, a health check fails, or a monitoring rule
fires.
**Time target:** < 5 seconds for CRITICAL exceptions, < 30 seconds for others.

**Detection methods:**
- **Exception-driven detection:** An exception propagates to a handler that reports
  it to the Failure Detector.
- **Health-check-driven detection:** The Health Manager's periodic check reveals
  a degraded or failed component.
- **Metric-threshold detection:** A metric crosses an alert threshold.
- **Pattern detection:** The Failure Detector identifies a pattern of related
  exceptions indicating a systemic failure.
- **Silence detection:** An expected event source produces no events (heartbeat
  missing).

**Detection quality principles:**
- Early detection is better. A failure caught at Stage 1 with 1 exception is
  better than one caught after 100 exceptions.
- False positives in detection (detecting failures that are not real) waste recovery
  resources and cause alert fatigue. Detection must be calibrated.
- False negatives (missing real failures) are more dangerous than false positives.

---

## 5.3 Stage 2 — Classification

**Actor:** Exception Classifier, Failure Analyzer.
**Trigger:** Failure detection event.
**Outputs:** Category, severity, scope (component/engine/system), urgency.

**Classification drives everything:** The recovery strategy, escalation policy,
alert channel, and audit requirement are all determined by the classification.
A misclassified exception may receive the wrong treatment — too aggressive (over-
reaction causing unnecessary downtime) or too passive (under-reaction leading to
worse failure).

**Classification validation:** The Failure Analyzer reviews the Classifier's output
for CRITICAL exceptions. Human review of the classification is triggered for any
exception causing a trade halt or kill switch evaluation.

---

## 5.4 Stage 3 — Validation

**Actor:** Failure Analyzer.
**Trigger:** Initial classification complete.
**Purpose:** Confirm that the detected failure is genuine (not a transient glitch
or monitoring artifact).

**Validation checks:**
- Is this a transient glitch? (first occurrence; try one immediate retry before
  declaring failure)
- Is this a monitoring artifact? (is the monitoring tool itself failing?)
- Is this consistent with other signals? (do health checks, metrics, and logs
  all agree?)
- Has this been observed before? (is it a known false positive pattern?)

**Validation outcome:**
- CONFIRMED: Proceed to isolation and recovery.
- FALSE_POSITIVE: Cancel the failure lifecycle. Log the false positive for
  calibration.
- DEFERRED: Continue monitoring — insufficient evidence yet.

---

## 5.5 Stage 4 — Isolation

**Actor:** Isolation Manager.
**Trigger:** Failure confirmed.
**Purpose:** Prevent the failure from spreading to other components.

**Isolation actions (examples):**
- Disconnect the failing component's output from downstream consumers
  (downstream components use fallbacks).
- Quarantine suspect data (do not propagate data from a failing feed).
- Open the circuit breaker for the failing service.
- Suspend health-check-driven restarts for the affected component
  (to allow investigation).

**Isolation is not the same as recovery:** Isolation stops the spread. Recovery
restores function. A component can be isolated (contained failure) without being
recovered (still failed).

---

## 5.6 Stage 5 — Containment

**Actor:** Isolation Manager, Failure Analyzer.
**Trigger:** Isolation actions applied.
**Purpose:** Define and minimize the blast radius of the failure.

**Blast radius assessment:**
- Which capabilities are directly affected? (the failing component itself)
- Which capabilities are indirectly affected? (downstream consumers of the failing
  component)
- Which safety mechanisms are still fully functional? (kill switch, risk limits)
- What is the impact on current open positions?

**Containment success criteria:** The blast radius does not grow while recovery is
in progress. If the blast radius is growing (cascade failure pattern), emergency
escalation triggers.

---

## 5.7 Stage 6 — Notification

**Actor:** Alert Manager, Escalation Manager.
**Trigger:** Failure confirmed, contained, scope assessed.
**Purpose:** Inform human operators of the failure.

**Notification principles:**
- Notify at the correct severity level (do not over-alert or under-alert).
- Provide actionable context (what failed, what is affected, what recovery is
  underway, what the operator needs to do).
- Track notification delivery (was the Telegram message delivered?).
- Escalate if no acknowledgement within the defined window.

**Notification content standard:**
Every failure notification must include:
- What failed (component name and description).
- When it failed (timestamp).
- Current severity and scope.
- What automated recovery is underway (if any).
- What the operator must do (if anything) and urgency.
- Reference to the incident ID (for tracking).

---

## 5.8 Stage 7 — Recovery

**Actor:** Recovery Coordinator, Retry Manager, Fallback Manager, Compensation
Manager.
**Trigger:** Isolation and containment complete; recovery plan selected.
**Purpose:** Restore the failed component to functional state.

**Recovery plan selection:** The Recovery Coordinator selects the appropriate
recovery strategy from Part VI based on the failure classification.

**Recovery execution principles:**
- Recovery is logged at every step (each action produces an audit record).
- Recovery that could have financial side effects (compensation actions) requires
  explicit operator confirmation for SEV-1 incidents.
- Recovery has a time limit (RTO). If recovery cannot complete within the RTO,
  the incident is escalated.
- Recovery that partially succeeds records exactly what was completed and what
  remains.

---

## 5.9 Stage 8 — Verification

**Actor:** Health Manager, Recovery Coordinator.
**Trigger:** Recovery actions complete.
**Purpose:** Confirm the system is genuinely recovered.

**Verification checks:**
- OHS of the recovered component is NOMINAL or better.
- The operation that failed previously now succeeds.
- Downstream components that relied on the failed component's output are receiving
  valid data.
- No new exceptions of the same type have occurred since recovery.
- All circuit breakers that were opened are closed (or intentionally in HALF-OPEN
  probe mode).

**Verification failure:** If verification fails, the recovery is not complete. The
incident remains active and a new recovery attempt is planned.

---

## 5.10 Stage 9 — Audit

**Actor:** Audit Manager.
**Trigger:** Throughout the lifecycle (records created at each stage for CRITICAL/
ERROR failures) and consolidated at the end.
**Purpose:** Create the immutable, complete record of the failure and its handling.

**Audit record requirements for failures:**
- Detection event record.
- Classification record.
- Isolation action records.
- Each recovery action record.
- Verification result record.
- Resolution record.

For SEV-1 and SEV-2 incidents, the audit record chain must be complete enough
to reconstruct the entire incident timeline from audit data alone.

---

## 5.11 Stage 10 — Root Cause Analysis

**Actor:** Root Cause Analyzer, Postmortem Manager.
**Trigger:** Incident resolved and verified.
**Purpose:** Identify the underlying cause, not just the symptom.

**Root cause analysis approach:**
- Start with the observable symptom (the first detected exception).
- Trace backward through the exception chain.
- Identify the earliest detectable point of deviation.
- Ask "why did this happen?" at least 5 times (5-Whys method).
- Verify the root cause hypothesis by checking whether the proposed cause
  is consistent with all observed evidence.

**Root cause quality standard:** A valid root cause explanation must answer:
- Why did this specific failure occur at this specific time?
- Why was it not detected earlier?
- Why did the existing recovery mechanisms not prevent the impact?

---

## 5.12 Stage 11 — Knowledge Capture

**Actor:** Knowledge Base, Postmortem Manager.
**Trigger:** Root cause analysis validated.
**Purpose:** Store learnings to improve future detection, recovery, and prevention.

**Knowledge capture artifacts:**
- Exception pattern signature (how to recognize this failure faster next time).
- Remediation recipe (step-by-step resolution for this root cause).
- Detection improvement recommendation.
- Prevention recommendation.

**Knowledge Base update:** The Knowledge Base is updated after every SEV-1 and
SEV-2 incident. For SEV-3 incidents, the update is optional but recommended when
there is a novel pattern.

---

## 5.13 Stage 12 — Continuous Improvement

**Actor:** Continuous Improvement Manager, Architecture Council.
**Trigger:** Knowledge capture complete.
**Purpose:** Translate learnings into systemic improvements.

**Improvement categories triggered by lifecycle completion:**
- Exception Registry update (new exception type added).
- Alert rule refinement (threshold adjustment).
- Recovery strategy improvement (new fallback added).
- Monitoring enhancement (earlier detection mechanism added).
- Architectural hardening (isolation boundary strengthened).
- Code improvement (defect fixed).
- Documentation update (runbook updated).

**Improvement tracking:** All improvement actions from lifecycle completions are
tracked in the Continuous Improvement Manager. Progress is reported at the monthly
Architecture Council meeting.

---

## 5.14 Lifecycle Flow Diagram

`
FAILURE LIFECYCLE FLOW DIAGRAM

[System Running]
     |
     v
[Exception Raised] -----[false positive]----> [Cancel, calibrate detection]
     |
[DETECTION + CLASSIFICATION]
     |
     v
[Severity: CRITICAL/ERROR/WARNING?]
     |
CRITICAL/ERROR -----> [ISOLATION] --> [CONTAINMENT] --> [NOTIFICATION]
     |                                                        |
     v                                                        v
[RECOVERY COORDINATOR]                              [Operator Notified]
     |                                                        |
     v                                                   [Ack?] --NO--> [ESCALATION]
[Recovery Strategy Selected]                               YES
     |                                                        |
     v                                                   [Monitoring]
[RETRY / FALLBACK / COMPENSATION / MANUAL]
     |
[VERIFICATION]
     |
PASS ----> [AUDIT COMPLETE] ----> [ROOT CAUSE ANALYSIS]
     |                                      |
FAIL ----> [RETRY RECOVERY]       [KNOWLEDGE CAPTURE]
           [OR ESCALATE]                    |
                                 [CONTINUOUS IMPROVEMENT]
                                            |
                                       [CLOSED]
`

---

*End of Part V*

---
# PART VI — RECOVERY STRATEGIES

## 6.1 Recovery Strategy Overview

IIOS employs 16 defined recovery strategies. Each strategy is appropriate for
specific failure types and conditions. The Recovery Coordinator selects from these
strategies based on the failure classification and the operational context.

A recovery strategy must specify:
- **Applicability:** When to use this strategy.
- **Mechanism:** How it works.
- **Strengths:** What makes it well-suited for certain failures.
- **Limitations:** Where it is inappropriate or insufficient.
- **Engineering guidance:** How to implement it correctly in IIOS.

---

## 6.2 Strategy 1 — Immediate Retry

### Applicability
Transient, low-latency operations where the failure is likely a momentary glitch.
Examples: in-memory cache lookup, local file read, fast database query.

### Mechanism
The failed operation is retried immediately without delay, up to N times (default 3).

### Strengths
- Resolves momentary glitches instantly.
- Zero delay — does not add latency when the failure is a single glitch.
- Simple to implement and reason about.

### Limitations
- Will not help for anything beyond a momentary glitch.
- If N retries all fail, it still takes time (N * operation_time before failure
  is declared).
- Can hammer a partially-failed service if not capped.

### Engineering Guidance (IIOS)
- Use only for fast (< 100ms) idempotent operations.
- Cap at 3 immediate retries maximum.
- After 3 immediate retries fail, switch to exponential backoff retry.
- Do not use for any operation with external network dependencies.

---

## 6.3 Strategy 2 — Retry with Exponential Backoff

### Applicability
Network operations, API calls, and database queries where transient failure is
expected (network blip, brief rate limit, connection pool exhaustion).

### Mechanism
The failed operation is retried after progressively longer delays. Each retry
waits longer than the previous:
`
Attempt 1: 1 second wait
Attempt 2: 2 second wait
Attempt 3: 4 second wait
Attempt 4: 8 second wait
Attempt 5: 16 second wait
`
Jitter (random variation of +/- 20%) is added to prevent synchronized retry
storms when multiple components fail simultaneously.

### Strengths
- Gives the failing service time to recover.
- Jitter prevents thundering herd problems.
- Well-proven pattern for transient network failures.

### Limitations
- Total wait time can be significant (1+2+4+8+16 = 31 seconds for 5 attempts).
- Does not work for permanent failures (wastes time).
- If the operation has time-sensitive requirements, backoff may exceed the budget.

### Engineering Guidance (IIOS)
- Use for all external API calls (data feeds, broker).
- Maximum 5 attempts (31 second maximum backoff).
- If the cycle latency budget would be exceeded during retries, abort the retry
  and use fallback immediately.
- Treat all retries as idempotent (if the operation has side effects, do not
  retry automatically).

---

## 6.4 Strategy 3 — Fallback to Alternate Source

### Applicability
When a primary data or service source fails and an alternate source providing
equivalent or similar data exists.

### Mechanism
The system switches from the primary source to a pre-configured alternate source.
The alternate continues to be used until the primary recovers (detected by the
circuit breaker moving to HALF-OPEN state) and the switch-back is confirmed.

### IIOS Fallbacks

| Primary | Fallback | Switch Trigger | Switch-Back Trigger |
|---------|---------|---------------|-------------------|
| Dhan data feed | yfinance | Circuit breaker opens | Dhan health probe success |
| Live VIX | Cached VIX | VIX fetch timeout | VIX fetch success |
| MetaLearning weights | Equal weights | Engine OHS CRITICAL | OHS NOMINAL recovery |
| Telegram alerts | Dashboard + log | Telegram timeout | Telegram health probe success |

### Strengths
- Provides continuity of service during primary failure.
- Automatic switching is faster than manual intervention.
- Trade-off (slightly lower quality) is accepted for continuity.

### Limitations
- The fallback must be maintained and tested. A fallback that has never been
  tested is not a fallback.
- The system must not silently operate on fallback indefinitely. Long-running
  fallback states indicate the primary is not recovering.

### Engineering Guidance (IIOS)
- All fallback activations are logged and alerted.
- Fallback health must be independently monitored (a fallback failure while
  the primary is also failed leaves the system with no source).
- Periodic testing of fallback paths is mandatory (at minimum monthly).

---

## 6.5 Strategy 4 — Graceful Degradation

### Applicability
When a non-critical capability is unavailable but the system can continue with
reduced functionality.

### Mechanism
The system identifies which capabilities are still available and continues
operating within those constraints, explicitly acknowledging the reduced capability
in its decisions.

### IIOS Degradation Modes

| Capability Lost | Degradation Response |
|----------------|---------------------|
| MetaLearning weights | Use equal strategy weights |
| One debate agent | Lower decision confidence; raise threshold by 0.5 |
| Telegram notifications | Log only; no impact on trading |
| Dashboard | No visual monitoring; trading continues |
| Historical data | Current-session only analysis |
| Performance analytics | Trading continues; reports are stale |

### Strengths
- Maintains trading continuity for non-critical failures.
- Explicitly documents what is and is not available.
- Makes the trade-off (reduced quality for continuity) explicit.

### Limitations
- Degradation must be limited to genuinely non-critical capabilities.
- Must not silently hide that quality is reduced.
- Accumulating degradations can compound — if many capabilities degrade
  simultaneously, the compound degradation may warrant halting.

### Engineering Guidance (IIOS)
- Every engine must define its degraded mode.
- Degraded mode must not reduce safety. Safety capabilities (kill switch, risk
  limits) must never be degraded.
- If more than 3 non-critical capabilities are simultaneously degraded, raise
  the decision threshold by 1.0 point as a conservative response.

---

## 6.6 Strategy 5 — Circuit Breaker

### Applicability
External service calls where repeated failure should trigger a pause in attempts
to prevent wasting resources and overwhelming a recovering service.

### Mechanism
A circuit breaker tracks the failure rate of a specific service. When the failure
rate exceeds the threshold within the time window, the circuit "opens" — all
subsequent calls return immediately with a fallback response without actually
attempting to reach the service. After a cooldown period, the circuit moves to
HALF-OPEN, allowing one probe request. If the probe succeeds, the circuit closes
and normal operation resumes.

### Strengths
- Prevents resource waste on a known-failed service.
- Gives the failing service time to recover without continued bombardment.
- Provides fast failure (callers immediately get the fallback response without
  waiting for timeouts).

### Limitations
- Requires tuning: too sensitive and it opens on transient glitches; too lenient
  and it stays open too long allowing continued resource waste.
- The cooldown period must be appropriate to the service's recovery characteristics.

### Engineering Guidance (IIOS)
- Every external API integration must have a circuit breaker.
- Default thresholds: 5 failures in 60 seconds, 30-second cooldown.
- Broker API: tighter threshold (3 failures) due to financial sensitivity.
- Circuit breaker state must be visible on the dashboard.

---

## 6.7 Strategy 6 — Fail Fast

### Applicability
Operations where proceeding with partial or uncertain state is more dangerous
than stopping.

### Mechanism
The system detects an unacceptable condition early in a workflow and immediately
aborts the operation before any irreversible actions are taken. The fail-fast
principle means: if there is reason to believe the operation cannot complete
successfully and safely, abort before starting (or as early as possible).

### IIOS Fail-Fast Conditions

- Kill switch active → fail fast on any new trade placement attempt.
- OHS of Risk Guardian is FAILED → fail fast on any decision cycle.
- Position mismatch detected → fail fast on any order placement.
- Audit store write failure → fail fast on any auditable operation.
- Kill switch check cannot execute → fail fast on the full cycle.

### Strengths
- Prevents damage from partial operations.
- Reduces the blast radius by aborting before side effects occur.
- Simple to implement and understand.

### Limitations
- May abort valid operations if the fail-fast condition check has false positives.
- Can reduce throughput if the condition check has high overhead.

### Engineering Guidance (IIOS)
- Fail-fast checks must be the first thing run in any critical operation (before
  any state mutation).
- Fail-fast conditions must be clearly documented per operation.
- Fail-fast aborts are logged (they represent important operational events).

---

## 6.8 Strategy 7 — Compensation

### Applicability
When a multi-step operation has partially completed and cannot be fully retried
(because some steps had non-idempotent side effects).

### Mechanism
The Compensation Manager determines what side effects occurred and applies
compensating operations to either undo them (rollback) or complete them (forward
completion). The goal is to leave the system in a consistent, defined state.

### IIOS Compensation Scenarios

**Scenario A — Partial multi-leg position:**
An order for both legs of a paired trade was placed. One leg filled, the other
was rejected. Compensation: close the filled leg immediately at market price.
The loss is the cost of the compensation; the risk of an unhedged partial position
is unacceptable.

**Scenario B — Partial configuration change:**
A configuration change was applied to some engines but not others before a failure.
Compensation: roll back all engines to the previous configuration.

**Scenario C — Failed learning update:**
A learning update was partially applied. Compensation: roll back all model weights
to the last complete, validated state.

### Strengths
- Allows multi-step operations to maintain consistency even when steps fail.
- Prevents the system from being left in an indeterminate state.

### Limitations
- Compensation may have its own cost (e.g., market-price exit of a partial position).
- Compensation must be faster and simpler than the original operation.
- Not all operations are compensatable.

### Engineering Guidance (IIOS)
- Every multi-step, non-idempotent workflow must define its compensation action.
- Compensation actions are logged in the Audit Manager with explicit notation
  that they are compensations.
- Compensation involving financial transactions requires immediate operator notification.

---

## 6.9 Strategy 8 — Rollback

### Applicability
When a state change has occurred and the new state is incorrect or inconsistent.

### Mechanism
The system reverts to a previous known-good state. The rollback uses a previously
persisted checkpoint or snapshot.

### IIOS Rollback Scenarios
- Strategy parameter update produces worse performance → rollback to previous
  parameters.
- Configuration change causes engine failures → rollback to previous configuration.
- Model update degrades prediction quality → rollback to previous model weights.

### Strengths
- Provides a clean recovery path for state change failures.
- Defined checkpoints make rollback predictable and fast.

### Limitations
- Requires that checkpoints exist (checkpoint strategy must be part of the design).
- Data created between the checkpoint and the rollback may be lost.
- Business logic may not be time-reversible (already-placed orders cannot be
  unplaced, only closed).

### Engineering Guidance (IIOS)
- All mutable system state has a defined checkpoint strategy.
- Before any state change that could require rollback, verify the checkpoint exists.
- Rollback actions are always logged in the Audit Manager.

---

## 6.10 Strategy 9 — Checkpoint Recovery

### Applicability
When a process terminates unexpectedly and must be restarted from a defined
consistent state rather than from the beginning.

### Mechanism
The system periodically persists its state to a durable checkpoint. On restart,
the most recent valid checkpoint is loaded. Work done after the checkpoint and
before the failure is replayed from the operation log if possible, or abandoned.

### IIOS Checkpoints
- Open positions: persisted to database on every state change.
- Kill switch state: persisted to database immediately on change.
- Strategy active/inactive status: persisted to database.
- Daily P&L: persisted to database every cycle.
- MetaLearning weights: persisted to database after every update.

### Strengths
- Prevents loss of work after a restart.
- Ensures critical state survives process crashes.
- Kill switch active state being persisted is a critical safety property.

---

## 6.11 Strategy 10 — Restart

### Applicability
When a component has entered a permanently degraded state that cannot be recovered
by other means, and when a clean restart is safe.

### Mechanism
The failed component is cleanly shut down and started fresh. State that must survive
the restart is checkpointed to durable storage before shutdown.

### IIOS Restart Safety Rules
- Restart is safe only when the component is not in the middle of an atomic
  financial operation.
- Restart of any component with open positions requires position state to be
  persisted first.
- Kill switch state must be restored after restart before any trading resumes.
- Maximum 3 automatic restarts. After 3 restarts within 60 minutes, the component
  escalates to human intervention (automatic restart loop is not recovery).

### Strengths
- Resolves memory leaks, deadlocks, and other accumulated state problems.
- Often the fastest path back to NOMINAL health.

### Limitations
- Brief unavailability during restart.
- Does not fix the underlying cause.

---

## 6.12 Strategy 11 — Replication

### Applicability
Critical state that must survive any single component failure.

### Mechanism
The critical state is maintained in multiple copies simultaneously. A failure in
one copy does not cause data loss because other copies are available.

### IIOS Replication
- Audit store: written to primary storage + backup volume simultaneously.
- Open positions: maintained in both in-memory state and database.
- Kill switch state: maintained in memory, database, and a state file (triple
  redundancy for the most critical state).

---

## 6.13 Strategy 12 — Redundancy

### Applicability
Services that must be available continuously.

### Mechanism
Multiple instances of the same service run simultaneously. A failure in one
instance is absorbed by the remaining instances.

### IIOS Redundancy
- Multiple data feed sources (Dhan + yfinance + additional).
- Multiple AI agents in the debate (5 agents; system can operate with 3).
- Multiple alert channels (Telegram + dashboard + log).

---

## 6.14 Strategy 13 — Isolation

### Applicability
Failures that are localized and must not be allowed to propagate.

### Mechanism
The failing component is isolated from others: its output is quarantined, its
consumers switch to fallback, and it is allowed to fail without affecting the
rest of the system.

### Already covered in Component 11 (Isolation Manager). See Section 3.12.

---

## 6.15 Strategy 14 — Human Intervention

### Applicability
Failures that cannot be safely resolved by automated means — those requiring
judgment, access not available to the system, or irreversible actions.

### Mechanism
The system triggers an escalation alert, provides the operator with a clear
description of the failure and its impact, and waits for operator action.
The system enters a safe passive state (no new trading) while waiting.

### When Human Intervention is Required in IIOS
- BROKER.POSITION_MISMATCH: Only a human can confirm the correct position.
- SEC.AUDIT_CHAIN_BROKEN: Tamper investigation requires human judgment.
- BROKER.ACCOUNT_SUSPENDED: Account issues require human interaction with broker.
- DB.CORRUPTION: Data restoration decisions require human judgment.
- SEV-1 incidents: All SEV-1 incidents require human response.

### Engineering Guidance
- The system must clearly describe what the operator needs to do.
- The system must never leave the operator with an ambiguous required action.
- Human intervention actions are recorded in the Audit Manager.

---

## 6.16 Strategy 15 — Disaster Recovery

### Applicability
Complete system failure requiring restoration from backup.

### Mechanism
From a defined Recovery Point Objective (RPO) backup, the system is restored to
a known-good state. Then operations resume from that point.

### IIOS Disaster Recovery Framework

**RPO (Recovery Point Objective):** Maximum data age at time of recovery.
- Open positions: 0 seconds (real-time persistence; no data loss accepted).
- Audit store: < 24 hours (daily backup).
- Telemetry: < 24 hours.
- Configuration: < 24 hours.
- Strategy definitions: < 24 hours.

**RTO (Recovery Time Objective):** Maximum time to restore operations.
- Stage 1 (safe mode — know what positions are open): < 30 minutes.
- Stage 2 (monitoring restored — can watch positions): < 60 minutes.
- Stage 3 (trading restored — can take new positions): < 120 minutes.

**Disaster Recovery Priority Order:**
1. Restore open position state (safety — know what is held).
2. Restore kill switch state (safety — was trading halted?).
3. Restore database connectivity.
4. Restore data feed access.
5. Restore broker connectivity.
6. Restore monitoring and alerting.
7. Restore decision cycle capability.

---

## 6.17 Strategy 16 — Business Continuity

### Applicability
Extended or unresolvable system failures during active trading hours.

### Mechanism
Business continuity activates when the system cannot be restored within a reasonable
time. Pre-defined manual procedures allow operators to manage open positions and
obligations without the automated system.

### IIOS Business Continuity Actions

1. **Identify all open positions:** Access broker portal directly. Document all
   open positions, entry prices, and current P&L.
2. **Apply position risk assessment:** Manually assess each position's risk given
   current market conditions.
3. **Execute close decisions manually:** If positions represent unacceptable risk
   (e.g., approaching stop-loss levels), close them manually via the broker portal.
4. **Document all manual actions:** Record every manual trade action for audit
   purposes.
5. **Restore system:** Follow disaster recovery steps.
6. **Reconcile:** After system restoration, reconcile automated records with manual
   actions.

---

## 6.18 Recovery Strategy Selection Matrix

`
RECOVERY STRATEGY SELECTION MATRIX

Exception Type                Recommended Strategy
----------------------------------------------------
Transient network timeout     Retry with backoff (Strategy 2)
Data feed unavailable         Fallback (Strategy 3) + Circuit Breaker (Strategy 5)
Engine execution failure      Immediate Retry (Strategy 1), then Restart (Strategy 10)
Partial order fill            Compensation (Strategy 7)
Config error detected         Rollback (Strategy 8)
Model output invalid          Fallback to defaults (Strategy 3)
Dead component                Restart (Strategy 10)
Kill switch condition         Fail Fast (Strategy 6)
Position mismatch             Human Intervention (Strategy 14)
Database corruption           Disaster Recovery (Strategy 15)
Security incident             Fail Fast + Human Intervention (Strategy 6 + 14)
Multiple simultaneous fails   Graceful Degradation (Strategy 4)
Complete system failure       Disaster Recovery (Strategy 15)
Market hours, can't recover   Business Continuity (Strategy 16)
`

---

*End of Part VI*

---

# PART VII — RELIABILITY FRAMEWORK

## 7.1 Reliability Framework Overview

The Reliability Framework defines 12 quality dimensions that IIOS must achieve
and maintain. These dimensions are measurable, and the system tracks quality scores
for each dimension. A System Reliability Score (SRS) is computed analogously to
the OHS and LQS scores.

---

## 7.2 Dimension 1 — Availability

**Definition:** The proportion of time the system is operational and capable of
executing its defined function (decision cycles, position management, monitoring).

**Measurement:** Uptime during scheduled operating hours (pre-market + market hours).

**Quality targets:**
- System availability during market hours: 99.9%.
- Decision cycle availability (cycles completing as scheduled): 99.5%.
- Kill switch mechanism availability: 100% (no acceptable downtime).

**Calculation:**
`
Availability = (Scheduled_Time - Downtime) / Scheduled_Time * 100
`

**Constitutional requirement:** Kill switch availability is 100%. The kill switch
must be able to activate at any moment. It is the one capability that has no
acceptable downtime.

---

## 7.3 Dimension 2 — Reliability

**Definition:** The probability that the system performs its required function
correctly (not just that it runs, but that it produces correct results).

**Measurement:**
- Decision accuracy rate: percentage of decisions that reflect the correct
  computation (verified by re-running computations on a sample).
- Order placement accuracy: percentage of placed orders that match the intended
  decision.
- Kill switch accuracy: 100% correct triggering (no false triggers, no missed
  triggers).

**Quality targets:**
- Decision accuracy: > 99.9%.
- Order placement accuracy: > 99.9%.
- Kill switch accuracy: 100%.

---

## 7.4 Dimension 3 — Resilience

**Definition:** The ability to absorb disruptions, adapt, and recover.

**Measurement:**
- Mean Time to Recover (MTTR) per failure type.
- Recovery success rate (percentage of failures resolved without human intervention
  within the RTO).
- Fallback activation rate (how often fallbacks are used).

**Quality targets:**
- MTTR for data feed failure: < 90 seconds.
- MTTR for engine failure: < 120 seconds.
- Recovery success rate: > 90% for ERROR-level failures.

---

## 7.5 Dimension 4 — Recoverability

**Definition:** The ability to restore the system from failure to its pre-failure
state.

**Measurement:**
- Checkpoint completeness: percentage of critical state that is checkpointed.
- Recovery validation pass rate.
- Backup freshness: time since last verified backup.

**Quality targets:**
- Checkpoint completeness: 100% for financial state.
- Recovery validation pass rate: 100%.
- Backup freshness: < 25 hours.

---

## 7.6 Dimension 5 — Fault Tolerance

**Definition:** The ability to continue operating correctly despite component faults.

**Measurement:**
- Fault injection test pass rate (does the system handle simulated faults correctly).
- Fallback coverage: percentage of single-component failures for which a fallback exists.

**Quality targets:**
- Fault injection pass rate: > 95%.
- Fallback coverage: 100% for critical path components.

---

## 7.7 Dimension 6 — Consistency

**Definition:** The system produces consistent results across executions given
the same inputs. State changes are atomic and correctly applied.

**Measurement:**
- Idempotency test pass rate.
- State consistency checks (position state matches broker state).
- Decision consistency (same market data produces same decision if run twice).

**Quality targets:**
- Position state consistency: 100%.
- Idempotency test pass rate: 100% for marked idempotent operations.

---

## 7.8 Dimension 7 — Integrity

**Definition:** Data and financial records are accurate, complete, and unmodified
from their original state.

**Measurement:**
- Audit chain integrity check pass rate.
- Position record accuracy vs broker confirmation.
- P&L calculation accuracy.

**Quality targets:**
- Audit chain integrity: 100%.
- Position record accuracy: 100%.

---

## 7.9 Dimension 8 — Security

**Definition:** The system resists unauthorized access, data exposure, and
security attacks.

**Measurement:**
- Security exception rate (authorized vs unauthorized).
- Audit store integrity.
- Credential exposure incidents.

**Quality targets:**
- Credential exposure incidents: 0.
- Unauthorized access incidents: 0.
- Security exception false positive rate: < 5%.

---

## 7.10 Dimension 9 — Scalability

**Definition:** The system handles increasing load without proportional degradation.

**Measurement:**
- Performance under increasing market volatility (more exception events per cycle).
- Recovery throughput (how many simultaneous failures can be handled).

**Quality targets:**
- System must handle 10x current exception rate without degradation.
- Recovery Coordinator must handle 5 simultaneous failures without queue backup.

---

## 7.11 Dimension 10 — Observability

**Definition:** Every failure, exception, and recovery action is visible to operators.

**Measurement:**
- Exception detection coverage (are all known failure modes detectable).
- MTTD per failure type.
- Alert false negative rate.

**Quality targets:**
- Exception detection coverage: > 95%.
- MTTD for CRITICAL failures: < 5 seconds.
- Alert false negative rate: 0 (no failure goes unnoticed).

---

## 7.12 Dimension 11 — Maintainability

**Definition:** The exception framework is easy to understand, extend, and improve.

**Measurement:**
- Exception Registry documentation coverage: 100%.
- Time to add a new exception type: < 1 hour.
- Postmortem action completion rate.

**Quality targets:**
- Registry documentation coverage: 100%.
- Postmortem action completion within SLA: > 90%.

---

## 7.13 Dimension 12 — Operational Stability

**Definition:** Day-to-day operations are predictable and free from chronic
failure patterns.

**Measurement:**
- Daily exception count trend (should be stable or decreasing).
- Chronic failure rate (same exception type occurring more than once per week
  for > 4 weeks indicates a systemic problem).
- Incident recurrence rate.

**Quality targets:**
- No chronic failure pattern (same type > 1/week for > 4 weeks): requires
  mandatory investigation.
- Incident recurrence within 30 days: < 10%.

---

## 7.14 System Reliability Score (SRS)

The SRS is a composite score (0.0 to 1.0) computed from weighted dimension scores.

**Dimension weights:**
- Availability: 15%
- Reliability: 15%
- Resilience: 10%
- Recoverability: 10%
- Fault Tolerance: 10%
- Consistency: 8%
- Integrity: 12%
- Security: 10%
- Scalability: 5%
- Observability: 5%
- Maintainability: 5%
- Operational Stability: 5%

**SRS tiers use the same boundaries as OHS:**
- OPTIMAL: 0.95+
- NOMINAL: 0.80–0.95
- DEGRADED: 0.60–0.80
- CRITICAL: 0.35–0.60
- FAILED: < 0.35

---

*End of Part VII*

---

# PART VIII — EXCEPTION GOVERNANCE

## 8.1 Governance Overview

Exception Governance defines who owns exception decisions, how exceptions are
classified and managed over time, what standards must be maintained, and how
compliance is verified.

---

## 8.2 Ownership Tiers

**Tier 1 — Architecture Council:**
Owns the Engineering Constitution (Part IX), the Exception Taxonomy (Part II),
the Reliability Framework (Part VII), the recovery strategy catalog, and all
cross-engine exception policies. Changes at this level require unanimous vote.

**Tier 2 — Chief Reliability Officer (CRO):**
Owns the Exception Registry, exception classification standards, escalation policies,
incident severity definitions, and postmortem standards. Reports to the Architecture
Council.

**Tier 3 — Engine Owners:**
Own the exception types specific to their engine, their engine's degradation modes,
their engine's recovery configuration (retry counts, fallback choice).

**Tier 4 — Operations Team:**
Owns incident response execution, alert configuration, monitoring thresholds, and
operational runbooks.

---

## 8.3 Classification Standards

### Exception Severity Classification

The 5-level severity classification is constitutional (LOG-SEV rules from the Logging
and Observability Framework apply equally here):

**CRITICAL:** The system cannot safely continue without human intervention. Trading
is halted or positions are at risk.

**ERROR:** A significant capability is degraded. The system is still operating but
at reduced quality or safety margin. Investigation required within hours.

**WARNING:** A boundary condition has been approached. No capability lost yet.
Monitoring increased. Investigation optional within 1 day.

**INFO:** An expected exception was encountered and handled. No operator action
required. Logged for information.

**DEBUG:** Internal handling detail. Not exposed in production.

### Severity Escalation Rules

Exceptions are escalated from their base severity when:
1. The exception is in the risk or execution path (escalate by 1 level).
2. The exception has recurred 3+ times within 5 minutes (escalate to CRITICAL).
3. Open positions are affected by the exception's impact (escalate by 1 level).
4. The exception is in the kill switch path (always CRITICAL).

---

## 8.4 Priority Matrix

Exceptions are prioritized by combining severity and scope:

| Severity | System Scope | Engine Scope | Service Scope |
|---------|-------------|-------------|--------------|
| CRITICAL | P0 — Immediate | P1 — 5 minutes | P1 — 5 minutes |
| ERROR | P1 — 5 minutes | P2 — 30 minutes | P2 — 30 minutes |
| WARNING | P2 — 30 minutes | P3 — 4 hours | P3 — 4 hours |
| INFO | P4 — Review weekly | P4 — Review weekly | P4 — Review weekly |

**Priority Definitions:**
- P0: All hands. Trading halted. Immediate response. Escalate every 5 minutes.
- P1: Operator responds within 5 minutes. May require another person to assist.
- P2: Operator responds within 30 minutes. Investigation ticket created.
- P3: Operator reviews within 4 hours. Added to improvement backlog.
- P4: Reviewed in weekly operations meeting.

---

## 8.5 Escalation Policy

### Escalation Triggers

An exception escalates to the next severity tier when:
- No operator response within the response time target for the current severity.
- Automated recovery fails within the RTO.
- The failure scope expands (more components affected).
- The same failure recurs after recovery within 30 minutes.

### Escalation Chain

**Level 1 — Automated response:** Recovery Coordinator handles.
**Level 2 — Operations alert:** Alert dispatched to operator. Operations team
responds.
**Level 3 — Incident Manager:** Formal incident declared. Incident response
coordinator assigned.
**Level 4 — Architecture Council:** SEV-1 escalation. Council informed. Emergency
response.

---

## 8.6 Incident Management

### Incident Declaration

A formal incident is declared when:
- Recovery cannot be completed automatically within the RTO.
- The failure scope is engine-level or broader.
- Financial integrity is in question.
- A security exception is confirmed.

### Incident Naming

Incidents are named with a unique identifier: INC-YYYYMMDD-NNN.
Example: INC-20260704-001 — the first incident declared on July 4, 2026.

### Incident Communication Standards

- Initial notification: within 5 minutes of incident declaration.
- Status update: every 15 minutes for P0/P1, every hour for P2.
- Resolution notification: immediately upon resolution.
- Postmortem notification: when scheduled.

---

## 8.7 Review Process

### Weekly Review

Operations team reviews:
- All exceptions from the past week (frequency, trend).
- All open incidents.
- Alert effectiveness (false positive rate).
- Postmortem action item status.

### Monthly Review

Architecture Council reviews:
- SRS trend (System Reliability Score).
- Incident frequency and severity trends.
- Recovery strategy effectiveness.
- Postmortem completions and quality.
- Improvement initiative progress.

### Annual Review

Architecture Council comprehensive review:
- Full exception taxonomy review.
- Engineering Constitution review.
- Reliability Framework targets review.
- Recovery strategy catalog review.

---

## 8.8 Knowledge Capture Standards

### What Must Be Captured

Every SEV-1 and SEV-2 incident produces:
- Root cause analysis (validated, not speculative).
- Postmortem with action items.
- Knowledge Base entries for new or updated patterns.
- Proposed exception type additions or modifications (if applicable).
- Proposed monitoring enhancements (if detection was slow).

### Knowledge Base Entry Quality Standards

A Knowledge Base entry must be:
- **Actionable:** Provides concrete steps, not just descriptions.
- **Accurate:** Based on validated root cause, not assumption.
- **Complete:** Covers detection, remediation, and prevention.
- **Reviewed:** Approved by the CRO before publication.

---

## 8.9 Compliance

### Audit Completeness

All CRITICAL and ERROR exceptions, all recovery actions, and all compensation
actions must have audit records. This is non-negotiable. Missing audit records
for critical events are a compliance violation.

### Postmortem Completeness

All SEV-1 and SEV-2 incidents must have completed postmortems within the defined
deadline. Overdue postmortems are escalated to the Architecture Council.

### Retention

Exception records are retained according to the Logging and Observability Framework
retention policies. RISK.KILL_SWITCH and security exceptions are retained for a
minimum of 1 year. All CRITICAL and ERROR exceptions are retained for a minimum
of 90 days.

---

## 8.10 Continuous Improvement Process

**Trigger for improvement initiatives:**
- SRS below 0.85 for any dimension.
- Any P0 incident.
- Any SEV-1 or SEV-2 incident that recurs.
- Exception rate trend increasing for > 4 consecutive weeks.
- Postmortem action item completion rate below 80%.

**Improvement cycle:**
1. Identify the gap or incident.
2. Analyze root cause.
3. Propose improvement.
4. Review and approve.
5. Implement and deploy.
6. Measure impact.
7. Document in governance records.

---

*End of Part VIII*

---
# PART IX — ENGINEERING CONSTITUTION

## 9.1 Constitution Overview

The Engineering Constitution is a set of 110 inviolable engineering rules governing
exception and failure management in IIOS. These are not guidelines or best practices
— they are architectural laws. Any rule violation is an incident requiring
investigation and remediation. The Constitution cannot be amended without unanimous
Architecture Council vote.

Rules are organized into 14 categories:
- **EXC-ID (10 rules):** Exception Identity
- **EXC-CLS (10 rules):** Classification
- **EXC-DET (8 rules):** Detection
- **EXC-RCV (10 rules):** Recovery
- **EXC-ISO (8 rules):** Isolation
- **EXC-SEC (8 rules):** Security
- **EXC-REL (8 rules):** Reliability
- **EXC-AUD (8 rules):** Auditability
- **EXC-ESC (8 rules):** Escalation
- **EXC-DOC (8 rules):** Documentation
- **EXC-KNW (8 rules):** Knowledge Capture
- **EXC-OPS (8 rules):** Operational Continuity
- **EXC-HUM (6 rules):** Human Override
- **EXC-EXT (8 rules):** Future Extensibility

---

## 9.2 Exception Identity Rules (EXC-ID)

**EXC-ID-001:** Every exception in IIOS must have a unique exception_id. No two
exception events may share the same exception_id.

**EXC-ID-002:** Every exception must have a timestamp in ISO 8601 UTC format with
at minimum millisecond precision. The timestamp must reflect the time the exception
was first detected, not the time it was logged.

**EXC-ID-003:** Every exception must have a source field identifying the component
that raised it, using its fully qualified IIOS path.

**EXC-ID-004:** Every exception must be traceable to the cycle, operation, or
workflow in which it occurred (via cycle_id, trace_id, or operation_id).

**EXC-ID-005:** Exception records must not be modified after creation. If an
exception is later reclassified, the reclassification creates a new record that
references the original.

**EXC-ID-006:** Exception records must not be deleted. Deletion of exception records
is a compliance violation.

**EXC-ID-007:** Duplicate suppression is not permitted for exception identity.
If the same exception occurred twice, two records must exist.

**EXC-ID-008:** An exception that propagates through multiple layers must maintain
its original exception_id. Each handling layer may add a new record but must
reference the original.

**EXC-ID-009:** The exception chain (the sequence from root exception to surface
exception) must be preserved and accessible. Deep exception nesting that loses
the root cause is a quality violation.

**EXC-ID-010:** Exception records must not contain sensitive values (API keys,
passwords, account numbers). Sensitive values in exception messages are a security
violation.

---

## 9.3 Classification Rules (EXC-CLS)

**EXC-CLS-001:** Every exception must be classified before any response action
is taken. An unclassified exception must use the UNK.UNCLASSIFIED type with
ERROR severity.

**EXC-CLS-002:** Classification must be based on the Exception Registry. Ad-hoc,
undocumented classification is forbidden.

**EXC-CLS-003:** The severity assigned at classification must reflect the actual
impact of the exception. Severity inflation (using higher severity for attention)
and severity deflation (using lower severity to avoid alerts) are both violations.

**EXC-CLS-004:** Exceptions in the kill switch path must always be classified at
minimum ERROR. Exceptions in the kill switch path that affect the kill switch
mechanism are always CRITICAL.

**EXC-CLS-005:** Exceptions in the execution path (order placement, position
management) are elevated by one severity level from their base classification.

**EXC-CLS-006:** Classification must be performed as close to the point of exception
as possible. Classification should not be deferred.

**EXC-CLS-007:** Security exceptions are always CRITICAL regardless of context.

**EXC-CLS-008:** Classification includes sensitivity: AUDIT exceptions are always
HIGH sensitivity. Security exceptions are always HIGH sensitivity.

**EXC-CLS-009:** The same exception type must receive consistent classification
across all occurrences. Classification drift (the same exception receiving different
classifications at different times) is a quality violation.

**EXC-CLS-010:** Classification may be revised by the CRO after investigation.
Revised classifications are recorded in the Exception Registry with a rationale.

---

## 9.4 Detection Rules (EXC-DET)

**EXC-DET-001:** Every defined exception type must have at least one detection
mechanism. An exception type that can occur but cannot be detected is an
architecture gap.

**EXC-DET-002:** Detection mechanisms must be tested. A detection mechanism that
has never been tested is not a detection mechanism — it is an assumption.

**EXC-DET-003:** CRITICAL exception detection latency must be < 5 seconds from
occurrence to detection. Detection latency exceeding 5 seconds for CRITICAL
exceptions is an architecture violation.

**EXC-DET-004:** Silence detection must be implemented for all critical components.
A component that stops producing expected events must be detected as a candidate
failure within 3x its expected heartbeat interval.

**EXC-DET-005:** Detection must not produce significant false positives. A detection
mechanism with a false positive rate > 10% must be recalibrated.

**EXC-DET-006:** Detection mechanisms must operate independently of the components
they detect. A detection mechanism that fails when the component it monitors fails
provides no value.

**EXC-DET-007:** Detection of the kill switch conditions (VIX > 45, daily loss > 2%)
must be independent of the decision pipeline. The kill switch must trigger even if
the decision cycle is not running.

**EXC-DET-008:** Unknown exceptions (UNK category) must generate an immediate alert
regardless of severity. Unknown exceptions are always investigated.

---

## 9.5 Recovery Rules (EXC-RCV)

**EXC-RCV-001:** Every exception type must have a defined recovery strategy.
An exception type without a defined recovery strategy is an architecture gap.

**EXC-RCV-002:** Recovery actions must be logged in the Audit Manager at each step.
An unrecorded recovery action is a governance violation.

**EXC-RCV-003:** Recovery must be verified before it is declared complete. A declared
recovery that has not been verified is not a recovery — it is an assumption.

**EXC-RCV-004:** Retry strategies must only be applied to idempotent operations.
Non-idempotent operations must not be retried automatically without explicit operator
confirmation.

**EXC-RCV-005:** Automatic recovery is capped at 3 attempts for any single failure
instance. After 3 automatic recovery attempts fail, the failure is escalated to
human intervention.

**EXC-RCV-006:** Recovery time must not exceed the defined RTO. If the RTO is
exceeded, the failure is escalated to the next severity tier regardless of current
severity.

**EXC-RCV-007:** Recovery from a financial state inconsistency (position mismatch,
incorrect P&L) requires human confirmation before any automated correction is applied.

**EXC-RCV-008:** Compensation actions (financial or state) are always logged in
the Audit Manager with explicit notation that they are compensations.

**EXC-RCV-009:** Recovery strategies must be tested at minimum quarterly via
fault injection or tabletop exercises.

**EXC-RCV-010:** A recovery action that makes the situation worse (secondary failure
during recovery) is a P0 incident regardless of the original failure severity.

---

## 9.6 Isolation Rules (EXC-ISO)

**EXC-ISO-001:** Every failure must be contained before recovery is attempted.
Attempting recovery without containment risks spreading the failure.

**EXC-ISO-002:** The kill switch mechanism must be isolated from all other exception
handling. No exception, regardless of severity, may disable or bypass the kill
switch evaluation.

**EXC-ISO-003:** A failing component's output must be isolated (quarantined)
before downstream components use it. Invalid data must never propagate downstream.

**EXC-ISO-004:** Resource isolation must prevent a resource-exhausting component
from starving other components (CPU limits, memory limits, I/O limits per component).

**EXC-ISO-005:** Engine isolation boundaries are constitutional. An exception in
one engine must not corrupt the state of another engine.

**EXC-ISO-006:** Security exceptions must always be isolated immediately. A security
exception that is not isolated (e.g., an unauthorized access attempt that continues)
is a P0 incident.

**EXC-ISO-007:** Isolation actions must be reversible. Permanent isolation (a
component that can never be re-integrated) is a system design flaw, not a recovery.

**EXC-ISO-008:** Isolation status must be visible on the dashboard. Hidden isolation
boundaries are unacceptable.

---

## 9.7 Security Rules (EXC-SEC)

**EXC-SEC-001:** Security exceptions are always CRITICAL. They are never downgraded
regardless of context.

**EXC-SEC-002:** A security exception always produces an audit record. No mechanism
may suppress the audit record for a security exception.

**EXC-SEC-003:** Security exceptions are never auto-resolved. They always require
human review and explicit closure.

**EXC-SEC-004:** Any exception that exposes a credential, key, or other sensitive
value is treated as a security exception (SEC.CREDENTIAL_EXPOSURE) regardless of
the component or context.

**EXC-SEC-005:** An audit chain integrity failure (SEC.AUDIT_CHAIN_BROKEN) triggers
an immediate trading halt. Continuing to trade without a functioning audit trail
is a compliance violation.

**EXC-SEC-006:** Log injection attempts (SEC.INJECTION_DETECTED) are logged to a
separate tamper-resistant security log that is not writable by the component that
detected the injection.

**EXC-SEC-007:** Security incident response is always a human-led process.
Automated security incident resolution is prohibited.

**EXC-SEC-008:** Security exception handling code must be reviewed by the
Architecture Council before deployment. Security handling is too critical for
individual engine owners to implement without review.

---

## 9.8 Reliability Rules (EXC-REL)

**EXC-REL-001:** The System Reliability Score (SRS) must be computed and reported
weekly. An SRS below 0.80 for two consecutive weeks triggers a mandatory improvement
initiative.

**EXC-REL-002:** The kill switch mechanism has a reliability requirement of 100%.
No other component may operate with a reliability target lower than 99% during
market hours.

**EXC-REL-003:** Single points of failure in the kill switch path are prohibited.
The kill switch must function even if any single other component fails.

**EXC-REL-004:** Reliability targets must be measurable. A reliability claim that
cannot be measured is not a reliability commitment.

**EXC-REL-005:** Fault injection testing is mandatory at minimum quarterly. Every
defined failure mode must be tested.

**EXC-REL-006:** A chronic failure (same exception type occurring > 1x per week
for > 4 weeks) is classified as a systemic reliability problem and triggers a
mandatory Architecture Council review.

**EXC-REL-007:** Reliability degradation is never accepted silently. If a reliability
dimension drops below its target, an improvement initiative is opened.

**EXC-REL-008:** Reliability improvements are prioritized over feature additions.
The system must be reliable before it is feature-rich.

---

## 9.9 Auditability Rules (EXC-AUD)

**EXC-AUD-001:** Every CRITICAL and ERROR exception must produce an audit record.
An exception of these severities that has no audit record is a compliance violation.

**EXC-AUD-002:** Every recovery action taken on a CRITICAL or ERROR exception must
produce an audit record.

**EXC-AUD-003:** Every compensation action must produce an audit record with explicit
notation that it is a compensation.

**EXC-AUD-004:** The audit trail for any incident must be complete enough to
reconstruct the full incident timeline from audit data alone.

**EXC-AUD-005:** Audit records for exception handling may never be deleted. Exception
audit retention is governed by the Logging and Observability Framework retention
policies for AUDIT and RISK categories.

**EXC-AUD-006:** Exception audit records must be readable for compliance review.
They must use plain-language descriptions that a non-engineering reviewer can
understand.

**EXC-AUD-007:** The Audit Manager must verify that all expected exception audit
records are present. Missing expected records are flagged as audit gaps and alerted.

**EXC-AUD-008:** Any exception in the audit path (LOG.AUDIT_WRITE_FAILURE) is a
CRITICAL exception that blocks the operation requiring the audit record.

---

## 9.10 Escalation Rules (EXC-ESC)

**EXC-ESC-001:** Every exception type must have a defined escalation path. An
exception type without a defined escalation path is an architecture gap.

**EXC-ESC-002:** Escalation must be automatic when recovery fails within the RTO.
Manual escalation trigger is a backup, not the primary path.

**EXC-ESC-003:** Escalated exceptions must not be downgraded without explicit written
justification reviewed by the CRO.

**EXC-ESC-004:** CRITICAL exceptions must trigger immediate escalation to the
operations team. Batching or delaying CRITICAL escalations is prohibited.

**EXC-ESC-005:** Escalation silence (no acknowledgement within the defined window)
must trigger re-escalation to the next tier. Unacknowledged escalations are never
silently dropped.

**EXC-ESC-006:** SEV-1 incidents must trigger escalation to the Architecture Council
within 30 minutes of declaration.

**EXC-ESC-007:** Escalation channels must be tested monthly. An escalation channel
that fails its test must be repaired before the next market open.

**EXC-ESC-008:** Escalation records are stored in the audit trail. Every escalation
event (trigger, delivery, acknowledgement) is audited.

---

## 9.11 Documentation Rules (EXC-DOC)

**EXC-DOC-001:** Every exception type in the Exception Registry must have complete
documentation: description, typical causes, impact, handling strategy, and
escalation path.

**EXC-DOC-002:** Every recovery strategy must be documented with applicability,
mechanism, strengths, limitations, and engineering guidance.

**EXC-DOC-003:** Every engine must have a documented exception specification:
which exception types it can raise, what it does with each, what its degraded mode is.

**EXC-DOC-004:** Operational runbooks must be maintained for every P0/P1 incident
scenario. Runbooks must be reviewed quarterly.

**EXC-DOC-005:** Documentation must be kept current. A change to exception handling
code must be accompanied by a documentation update.

**EXC-DOC-006:** Documentation must be accessible to the operations team without
requiring code access. It must be in the docs/ directory.

**EXC-DOC-007:** Documentation must be written for the intended audience. Operational
runbooks are for operators (not engineers). Engineering specifications are for
engineers (not operators).

**EXC-DOC-008:** Undocumented exception types detected in production must be
documented within 5 business days.

---

## 9.12 Knowledge Capture Rules (EXC-KNW)

**EXC-KNW-001:** Every SEV-1 and SEV-2 incident must produce a completed postmortem
within the defined deadline.

**EXC-KNW-002:** Postmortems must be blameless. Root cause analysis focuses on
system and process failures, not individual blame.

**EXC-KNW-003:** Postmortem action items must be assignable, time-bounded, and
tracked. Vague action items (e.g., "improve the system") are not acceptable.

**EXC-KNW-004:** Knowledge Base entries must be validated (root cause verified)
before being published. Speculative entries are marked as hypotheses until verified.

**EXC-KNW-005:** The Knowledge Base must be searchable. An operator facing an
incident must be able to find relevant Knowledge Base entries within 2 minutes.

**EXC-KNW-006:** Knowledge Base entries must be kept current. When a pattern is
superseded by a new understanding, the old entry is updated or deprecated.

**EXC-KNW-007:** Knowledge capture is not optional for SEV-1 incidents. A postmortem
that produces no Knowledge Base entries is incomplete.

**EXC-KNW-008:** The Knowledge Base is reviewed at every Architecture Council meeting.
Entries that have not been referenced in > 1 year are reviewed for relevance.

---

## 9.13 Operational Continuity Rules (EXC-OPS)

**EXC-OPS-001:** Trading must always be halted in a controlled manner. Abrupt
termination that leaves positions open is a P0 incident.

**EXC-OPS-002:** Open positions must never be abandoned due to a system failure.
If the system cannot manage open positions, it must close them or alert an operator
to manage them manually.

**EXC-OPS-003:** Kill switch state must survive system restarts. A system restart
must not inadvertently lift an active kill switch.

**EXC-OPS-004:** Daily loss limit tracking must survive system restarts. A restart
mid-day must not reset the daily loss counter.

**EXC-OPS-005:** The system must be able to produce a current position report even
in degraded mode. Position visibility is a safety requirement.

**EXC-OPS-006:** During system recovery, no new positions may be opened until the
OHS of the Risk Guardian is NOMINAL or better.

**EXC-OPS-007:** Business continuity procedures must be reviewed quarterly. An
operator who has never reviewed the business continuity procedure is not prepared.

**EXC-OPS-008:** The disaster recovery procedure must be tested at minimum annually.
An untested disaster recovery procedure is not a procedure — it is a hope.

---

## 9.14 Human Override Rules (EXC-HUM)

**EXC-HUM-001:** Human override is always available. No automated system may make
an irreversible action without providing a human override mechanism.

**EXC-HUM-002:** Human override of the kill switch is permitted. Only explicitly
authorized operators may override the kill switch, and every override is logged
in the Audit Manager.

**EXC-HUM-003:** Human override of automated recovery is permitted. An operator
may choose a different recovery path than the automated system selected.

**EXC-HUM-004:** Human override actions are audited at the same level as automated
actions. Human actions are not exempt from audit requirements.

**EXC-HUM-005:** The system must present a human override operator with the full
context of the situation: what failed, what automated action was taken, what the
proposed manual action is, and what the risks of each path are.

**EXC-HUM-006:** Human override during SEV-1 incidents requires documentation of
the decision rationale within 4 hours. A human override with no documented rationale
is a governance gap.

---

## 9.15 Future Extensibility Rules (EXC-EXT)

**EXC-EXT-001:** New exception types can always be added to the taxonomy. The taxonomy
is additive — adding does not require changing existing handling.

**EXC-EXT-002:** New recovery strategies can always be added. Adding a new strategy
does not invalidate existing strategies.

**EXC-EXT-003:** Exception handling code must be designed to be extended without
modification (open/closed principle). New exception types must be handleable by
adding handlers, not by modifying existing ones.

**EXC-EXT-004:** The Exception Registry must be able to accept new entries without
requiring a system restart.

**EXC-EXT-005:** New detection mechanisms must be addable without modifying existing
detection logic.

**EXC-EXT-006:** The Escalation Policy must be configurable without code changes.
Escalation thresholds and routing are configuration, not code.

**EXC-EXT-007:** The circuit breaker thresholds are configuration, not code.
Threshold adjustments must not require deployment.

**EXC-EXT-008:** The Knowledge Base structure must be able to accommodate new
entry types as the system learns new patterns over time.

---

*End of Part IX*

---

# PART X — READINESS CHECKLIST AND CERTIFICATION MATRIX

## 10.1 Readiness Checklist Overview

The Exception and Failure Management Readiness Checklist defines the criteria that
must be satisfied before IIOS is considered exception-ready for production operation.
74 HARD (must pass) and 23 SOFT (should pass) checks across 11 domains.

---

## 10.2 Domain 1 — Exception Registry Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-REG-01 | Exception Registry initializes without errors | HARD | Zero errors on startup |
| ER-REG-02 | All 35+ exception categories are registered | HARD | Category count verified |
| ER-REG-03 | All engine exception types are registered | HARD | Engine specs match registry |
| ER-REG-04 | All exception types have severity assignments | HARD | No missing severity |
| ER-REG-05 | All exception types have handling strategies | HARD | No missing strategy |
| ER-REG-06 | All exception types have escalation paths | HARD | No missing escalation |
| ER-REG-07 | Registry documentation is 100% complete | SOFT | Documentation audit passes |
| ER-REG-08 | No duplicate exception type registrations | HARD | Uniqueness check passes |
| ER-REG-09 | Registry loads within 500ms | SOFT | Startup timing measured |

**Domain 1 certification:** HARD: 7/7 required. SOFT: 2/2 recommended.

---

## 10.3 Domain 2 — Exception Detection Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-DET-01 | Exception Classifier is operational | HARD | Test exception classified correctly |
| ER-DET-02 | Failure Detector is operational | HARD | Test failure pattern detected |
| ER-DET-03 | Health Manager is computing OHS | HARD | All 18 engine OHS present |
| ER-DET-04 | Heartbeat monitoring is active | HARD | Silence detection tested |
| ER-DET-05 | CRITICAL exception detection < 5s | HARD | Latency test passes |
| ER-DET-06 | Kill switch condition monitoring is independent | HARD | Isolated check confirmed |
| ER-DET-07 | Cascade failure detection is active | SOFT | Pattern test confirmed |
| ER-DET-08 | Unknown exception detection and alerting work | HARD | UNK test passes |

**Domain 2 certification:** HARD: 7/7 required. SOFT: 1/1 recommended.

---

## 10.4 Domain 3 — Recovery Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-RCV-01 | Recovery Coordinator is operational | HARD | No startup errors |
| ER-RCV-02 | Retry Manager is operational with all policies | HARD | Policy test passes |
| ER-RCV-03 | Fallback Manager is operational | HARD | Fallback activation tested |
| ER-RCV-04 | All fallback paths are tested | HARD | All fallbacks have test results |
| ER-RCV-05 | Circuit Breaker Manager is operational | HARD | State machine test passes |
| ER-RCV-06 | Compensation Manager is operational | HARD | Compensation test passes |
| ER-RCV-07 | Recovery verification is functional | HARD | Post-recovery check runs |
| ER-RCV-08 | Recovery RTOs are met in testing | SOFT | Timing tests pass |
| ER-RCV-09 | All recovery strategies have runbooks | SOFT | Runbook audit passes |
| ER-RCV-10 | Automatic restart limit (3 max) is enforced | HARD | Restart limit test passes |

**Domain 3 certification:** HARD: 8/8 required. SOFT: 2/2 recommended.

---

## 10.5 Domain 4 — Resilience Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-RES-01 | All engines have degraded mode defined | HARD | Specification audit passes |
| ER-RES-02 | Graceful degradation does not reduce safety | HARD | Safety audit passes |
| ER-RES-03 | Kill switch is operational in degraded mode | HARD | Degradation test confirms |
| ER-RES-04 | Data feed fallback is tested and working | HARD | Fallback switch tested |
| ER-RES-05 | Debate agent degradation (< 5 agents) handled | HARD | Agent failure test passes |
| ER-RES-06 | Fault injection tests pass | HARD | Fault injection test suite run |
| ER-RES-07 | Resilience test results are documented | SOFT | Test report exists |

**Domain 4 certification:** HARD: 6/6 required. SOFT: 1/1 recommended.

---

## 10.6 Domain 5 — Fault Tolerance Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-FT-01 | Kill switch path has no single point of failure | HARD | Architecture audit passes |
| ER-FT-02 | Data feed redundancy is operational | HARD | Both sources functional |
| ER-FT-03 | Alert channel redundancy is functional | HARD | Secondary channel tested |
| ER-FT-04 | Position state persisted in dual locations | HARD | Dual persistence verified |
| ER-FT-05 | Kill switch state triple-persistence confirmed | HARD | Triple store verified |
| ER-FT-06 | Audit store replication is active | HARD | Replication test passes |
| ER-FT-07 | Fallback coverage is 100% for critical path | HARD | Coverage audit passes |

**Domain 5 certification:** HARD: 7/7 required.

---

## 10.7 Domain 6 — Monitoring Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-MON-01 | Alert Manager is operational | HARD | Test alert delivered |
| ER-MON-02 | CRITICAL alert < 1 second delivery | HARD | Latency test passes |
| ER-MON-03 | Telegram alert channel is functional | HARD | Test message delivered |
| ER-MON-04 | Dashboard shows exception/health status | HARD | Visual verification |
| ER-MON-05 | Escalation Manager is operational | HARD | Escalation test passes |
| ER-MON-06 | Incident Manager is operational | HARD | Test incident created |
| ER-MON-07 | SRS computation is functional | SOFT | SRS score displayed |
| ER-MON-08 | Monitoring independence verified | HARD | Monitoring survives component fail |

**Domain 6 certification:** HARD: 7/7 required. SOFT: 1/1 recommended.

---

## 10.8 Domain 7 — Security Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-SEC-01 | Security exception detection is active | HARD | Injection test detected |
| ER-SEC-02 | Security exceptions always produce audit records | HARD | Audit test passes |
| ER-SEC-03 | Audit chain integrity check operational | HARD | Integrity check runs |
| ER-SEC-04 | No credential appears in exception records | HARD | Scan of test exceptions clean |
| ER-SEC-05 | Security exceptions require human resolution | HARD | Auto-resolve is disabled |
| ER-SEC-06 | SEC.AUDIT_CHAIN_BROKEN halts trading | HARD | Test halts trading |
| ER-SEC-07 | Security exception logging is tamper-resistant | SOFT | Isolation verified |

**Domain 7 certification:** HARD: 6/6 required. SOFT: 1/1 recommended.

---

## 10.9 Domain 8 — Audit Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-AUD-01 | Audit Manager records CRITICAL exceptions | HARD | Test exception audited |
| ER-AUD-02 | Audit Manager records recovery actions | HARD | Test recovery audited |
| ER-AUD-03 | Audit Manager records compensation actions | HARD | Test compensation audited |
| ER-AUD-04 | Audit records are immutable (no delete/edit) | HARD | Code audit confirms |
| ER-AUD-05 | LOG.AUDIT_WRITE_FAILURE blocks operations | HARD | Block test passes |
| ER-AUD-06 | Audit chain integrity is verifiable | HARD | Verification test passes |
| ER-AUD-07 | Audit query interface is functional | SOFT | Test query returns results |

**Domain 8 certification:** HARD: 6/6 required. SOFT: 1/1 recommended.

---

## 10.10 Domain 9 — Disaster Recovery Ready

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-DR-01 | Disaster recovery procedure is documented | HARD | Runbook exists |
| ER-DR-02 | Backup of all critical state is operational | HARD | Backup confirmed fresh |
| ER-DR-03 | Backup can be restored (test restore) | HARD | Restore test passes |
| ER-DR-04 | RPO targets are achievable | HARD | RPO test measurement passes |
| ER-DR-05 | RTO targets are achievable | HARD | RTO test measurement passes |
| ER-DR-06 | Position state can be recovered | HARD | Position restore test passes |
| ER-DR-07 | Kill switch state survives restart | HARD | Kill switch persist test passes |
| ER-DR-08 | Daily P&L survives restart | HARD | P&L persist test passes |
| ER-DR-09 | Business continuity procedure is documented | SOFT | BC procedure exists |
| ER-DR-10 | Operations team has reviewed DR procedure | SOFT | Review confirmed |

**Domain 9 certification:** HARD: 8/8 required. SOFT: 2/2 recommended.

---

## 10.11 Domain 10 — Documentation Complete

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-DOC-01 | Exception Framework document is complete | HARD | This document |
| ER-DOC-02 | All exception types are documented | HARD | Documentation audit passes |
| ER-DOC-03 | All engine exception specifications exist | HARD | Spec audit passes |
| ER-DOC-04 | Recovery runbooks exist for all P0/P1 scenarios | HARD | Runbook audit passes |
| ER-DOC-05 | Operations runbook is reviewed and current | SOFT | Last review < 90 days |
| ER-DOC-06 | Postmortem template is published | SOFT | Template accessible |
| ER-DOC-07 | Knowledge Base is accessible to operations | SOFT | Access confirmed |

**Domain 10 certification:** HARD: 4/4 required. SOFT: 3/3 recommended.

---

## 10.12 Domain 11 — Operational Certification

| # | Check | Type | Criterion |
|---|-------|------|-----------|
| ER-OPS-01 | Exception handling verified in staging | HARD | Staging test suite passes |
| ER-OPS-02 | All fault injection tests pass | HARD | 100% pass rate |
| ER-OPS-03 | Recovery strategies tested for each failure type | HARD | Test coverage > 95% |
| ER-OPS-04 | Operations team has been trained on runbooks | HARD | Training confirmed |
| ER-OPS-05 | Escalation channels tested and confirmed | HARD | Test alerts delivered |
| ER-OPS-06 | SRS is NOMINAL or better | HARD | SRS > 0.80 |
| ER-OPS-07 | No open P0/P1 incidents | HARD | Incident tracker clean |
| ER-OPS-08 | All overdue postmortems are complete | SOFT | Postmortem tracker clean |

**Domain 11 certification:** HARD: 7/7 required. SOFT: 1/1 recommended.

---

## 10.13 Certification Matrix

`
EXCEPTION AND FAILURE MANAGEMENT READINESS CERTIFICATION MATRIX

Domain                              HARD  SOFT  Status
----------------------------------------------------------
D1 — Exception Registry Ready        7/7   2/2   [ ]
D2 — Exception Detection Ready       7/7   1/1   [ ]
D3 — Recovery Ready                  8/8   2/2   [ ]
D4 — Resilience Ready                6/6   1/1   [ ]
D5 — Fault Tolerance Ready           7/7   0/0   [ ]
D6 — Monitoring Ready                7/7   1/1   [ ]
D7 — Security Ready                  6/6   1/1   [ ]
D8 — Audit Ready                     6/6   1/1   [ ]
D9 — Disaster Recovery Ready         8/8   2/2   [ ]
D10 — Documentation Complete         4/4   3/3   [ ]
D11 — Operational Certification      7/7   1/1   [ ]
----------------------------------------------------------
TOTAL                               73/73  15/15
----------------------------------------------------------

HARD pass: All 73 HARD checks must pass.
SOFT pass: At least 12/15 SOFT checks recommended.

CERTIFICATION STATEMENT:
"I certify that all 73 HARD exception and failure management readiness checks
pass and that the IIOS exception and failure management system meets the
standards defined in IIOS-EXC-FLR-001."

Certified by: _____________________ Date: _________________
Role:         Chief Reliability Officer
`

---

*End of Part X*

---
# SUPPLEMENT A — EXCEPTION TAXONOMY QUICK REFERENCE

## A.1 All 35 Exception Categories at a Glance

| # | Namespace | Category | Default Severity | Audit Required |
|---|-----------|---------|-----------------|----------------|
| 1 | SYSTEM | System-level platform exceptions | CRITICAL | All CRITICAL |
| 2 | APP | Application logic exceptions | ERROR | All CRITICAL |
| 3 | INFRA | Infrastructure exceptions | ERROR–CRITICAL | All CRITICAL |
| 4 | NET | Network exceptions | WARNING–ERROR | ERROR+ |
| 5 | DB | Database exceptions | ERROR–CRITICAL | All |
| 6 | STOR | Storage/filesystem exceptions | WARNING–CRITICAL | CRITICAL |
| 7 | MEM | Memory exceptions | WARNING–CRITICAL | CRITICAL |
| 8 | CPU | CPU resource exceptions | WARNING–ERROR | ERROR+ |
| 9 | THR | Thread exceptions | WARNING–CRITICAL | CRITICAL |
| 10 | CFG | Configuration exceptions | WARNING–CRITICAL | All changes |
| 11 | AUTH | Authentication exceptions | ERROR–CRITICAL | All |
| 12 | AUTHZ | Authorization exceptions | WARNING–CRITICAL | All |
| 13 | SEC | Security exceptions | CRITICAL | Always |
| 14 | ENC | Encryption exceptions | ERROR–CRITICAL | All |
| 15 | WF | Workflow exceptions | WARNING–CRITICAL | CRITICAL |
| 16 | BIZ | Business rule exceptions | INFO–CRITICAL | Kill switch |
| 17 | VAL | Validation exceptions | WARNING–ERROR | No |
| 18 | MODEL | AI model exceptions | WARNING–ERROR | No |
| 19 | PRED | Prediction exceptions | WARNING–ERROR | No |
| 20 | LEARN | Learning exceptions | WARNING–ERROR | No |
| 21 | MKTDATA | Market data exceptions | WARNING–CRITICAL | INVALID_PRICE |
| 22 | BROKER | Broker exceptions | WARNING–CRITICAL | All orders |
| 23 | EXCH | Exchange exceptions | INFO–CRITICAL | Halts |
| 24 | PORT | Portfolio exceptions | WARNING–ERROR | No |
| 25 | RISK | Risk exceptions | WARNING–CRITICAL | Kill switch |
| 26 | STRAT | Strategy exceptions | WARNING–ERROR | Promotions |
| 27 | SIM | Simulation exceptions | WARNING–ERROR | No |
| 28 | MON | Monitoring exceptions | WARNING–ERROR | No |
| 29 | LOG | Logging exceptions | WARNING–CRITICAL | AUDIT_WRITE_FAILURE |
| 30 | RCV | Recovery exceptions | ERROR–CRITICAL | All |
| 31 | EXT | External service exceptions | WARNING–ERROR | No |
| 32 | TO | Timeout exceptions | WARNING–CRITICAL | CRITICAL |
| 33 | CONC | Concurrency exceptions | WARNING–ERROR | No |
| 34 | DEP | Dependency exceptions | WARNING–ERROR | No |
| 35 | UNK | Unknown/unclassified | ERROR by default | Always |

---

# SUPPLEMENT B — SEVERITY CATALOG

## B.1 Severity Level Reference

### CRITICAL — Immediate Response Required

Characteristics:
- The system cannot safely continue without human intervention.
- Trading is or should be halted.
- Financial integrity may be at risk.
- A safety mechanism may be compromised.

IIOS CRITICAL exception examples:
- SYSTEM.KILL_SWITCH_FAILURE — kill switch cannot activate.
- RISK.KILL_SWITCH_VIX — VIX > 45 detected.
- RISK.KILL_SWITCH_DAILY_LOSS — daily loss > 2%.
- BROKER.POSITION_MISMATCH — broker and IIOS disagree on positions.
- SEC.* — any security exception.
- DB.CORRUPTION — database file is corrupt.
- LOG.AUDIT_WRITE_FAILURE — cannot record a governance event.
- INFRA.HOST_UNREACHABLE — the host running IIOS is gone.

### ERROR — Investigation Required Within Hours

Characteristics:
- A significant capability is degraded.
- The system is operating but at reduced quality or safety margin.
- Left unaddressed, the ERROR may escalate to CRITICAL.

IIOS ERROR exception examples:
- Engine OHS entering CRITICAL tier.
- Primary data feed unavailable (fallback active).
- Multiple debate agents failing.
- Database write failure (non-audit path).
- Order rejected by broker.
- Strategy win rate approaching disable threshold.

### WARNING — Monitoring Increased

Characteristics:
- A boundary condition has been approached.
- No capability has been lost yet.
- Trends toward ERROR if not addressed.

IIOS WARNING exception examples:
- Data feed latency increasing.
- Engine OHS entering DEGRADED tier.
- Log storage utilization above 80%.
- Circuit breaker approaching open threshold.
- Strategy drawdown approaching threshold.

### INFO — Expected Condition, No Action Required

Characteristics:
- An expected exception was encountered and handled gracefully.
- No operator action is required.
- Logged for operational awareness.

IIOS INFO exception examples:
- Business rule check rejected an over-limit trade (expected business behavior).
- Circuit breaker opened and fallback activated (expected recovery path).
- Retry succeeded on second attempt.
- Strategy automatically disabled (win rate threshold met — expected governance).

---

# SUPPLEMENT C — RECOVERY CATALOG

## C.1 Recovery Strategy Summary

| Strategy | Code | Applicability | RTO Impact |
|---------|------|---------------|------------|
| Immediate Retry | R01 | Transient fast operations | Minimal |
| Exponential Backoff Retry | R02 | Network and API calls | 1–31 seconds |
| Fallback to Alternate | R03 | Any service with defined alternate | < 90 seconds |
| Graceful Degradation | R04 | Non-critical capability loss | None |
| Circuit Breaker | R05 | External service calls | Instant (no retry wait) |
| Fail Fast | R06 | Safety-critical abort conditions | Instant |
| Compensation | R07 | Partial operation with side effects | Minutes |
| Rollback | R08 | State change failures | Seconds to minutes |
| Checkpoint Recovery | R09 | Process restart | Seconds |
| Restart | R10 | Accumulated state problems | 5–30 seconds |
| Replication | R11 | Critical state preservation | Zero (continuous) |
| Redundancy | R12 | Continuous availability requirements | Zero (continuous) |
| Isolation | R13 | Containing failure spread | Seconds |
| Human Intervention | R14 | Non-automatable failures | Human response time |
| Disaster Recovery | R15 | Complete system failure | 30–120 minutes |
| Business Continuity | R16 | Extended unresolvable failure | Immediate (manual) |

---

# SUPPLEMENT D — INCIDENT RESPONSE MATRIX

## D.1 Incident Response by Exception Type

| Exception | Severity | Auto-Recovery | Human Required | Response Time |
|-----------|---------|---------------|----------------|---------------|
| RISK.KILL_SWITCH_VIX | CRITICAL | YES (halt trading) | YES (lift confirmation) | Immediate |
| RISK.KILL_SWITCH_DAILY_LOSS | CRITICAL | YES (halt trading) | YES (lift confirmation) | Immediate |
| BROKER.POSITION_MISMATCH | CRITICAL | NO | YES | < 5 minutes |
| SEC.AUDIT_CHAIN_BROKEN | CRITICAL | YES (halt trading) | YES | < 5 minutes |
| DB.CORRUPTION | CRITICAL | NO | YES | < 5 minutes |
| INFRA.HOST_UNREACHABLE | CRITICAL | YES (container restart) | YES if 3+ restarts | < 30 minutes |
| MKTDATA.FEED_UNAVAILABLE | ERROR | YES (fallback) | YES if > 30 min | < 15 minutes |
| BROKER.API_UNAVAILABLE | ERROR | YES (circuit breaker) | YES if > 15 min | < 15 minutes |
| ENGINE.OHS_CRITICAL | ERROR | YES (restart) | YES if 3+ restarts | < 30 minutes |
| SEC.INJECTION_DETECTED | CRITICAL | NO | YES | < 5 minutes |
| LOG.AUDIT_WRITE_FAILURE | CRITICAL | YES (retry) | YES if persistent | < 10 minutes |
| STRAT.NO_ELIGIBLE_STRATEGIES | ERROR | NO (wait for recovery) | YES if > 1 hour | < 1 hour |

---

# SUPPLEMENT E — FAILURE PATTERN REFERENCE

## E.1 Common Failure Patterns

### Pattern 1 — Cascade Failure

**Description:** A failure in one component triggers failures in dependent
components, creating a chain of failures.

**Indicators:** Multiple exceptions across different components within 30 seconds.
All components can trace to a single upstream failure.

**Prevention:** Isolation boundaries and circuit breakers. Downstream components
must use fallbacks rather than propagating the upstream failure.

**Detection:** Failure Detector cascade correlation pattern.

---

### Pattern 2 — Data Feed Degradation Spiral

**Description:** A degrading data feed produces progressively worse data quality
before completely failing. Decisions made on degraded data are suboptimal.

**Indicators:** MKTDATA.STALE_DATA appearing with increasing frequency, followed
by MKTDATA.INVALID_PRICE, followed by MKTDATA.FEED_UNAVAILABLE.

**Prevention:** Data quality monitoring with staleness detection. Early fallback
activation before data becomes invalid.

**Detection:** Data freshness metric trending toward staleness threshold.

---

### Pattern 3 — Memory Leak Induced Degradation

**Description:** A slowly growing memory leak causes gradual performance degradation
as memory pressure increases, eventually causing OOM or severe slowdowns.

**Indicators:** Memory utilization trending upward over hours or days. Latency
increasing gradually. Eventual OOM error or garbage collection pauses.

**Prevention:** Memory profiling, regular restarts during low-activity windows.

**Detection:** Memory trend monitoring (alert if memory grows by > 20% in 6 hours).

---

### Pattern 4 — Configuration Drift

**Description:** Over time, the running configuration diverges from the stored
configuration, typically due to manual overrides that were not persisted.

**Indicators:** CFG.DRIFT_DETECTED exceptions during configuration validation.
Unexpected behavior that aligns with a previous (non-current) configuration.

**Prevention:** All configuration changes through the Configuration Framework.
No manual overrides that are not persisted.

**Detection:** Periodic configuration hash comparison.

---

### Pattern 5 — Alert Fatigue Mask

**Description:** A high volume of lower-severity alerts desensitizes operators
to alerts, causing them to miss a critical alert buried in the noise.

**Indicators:** High alert volume, low operator acknowledgement rate, delayed
response to genuine CRITICAL alerts.

**Prevention:** Alert deduplication, alert quality monitoring, regular alert
rule calibration to reduce false positives.

**Detection:** Alert acknowledgement rate monitoring.

---

### Pattern 6 — Broker Reconnect Loop

**Description:** The broker connection drops and the system attempts to reconnect
repeatedly, each reconnect attempt consuming a new connection resource, eventually
exhausting the connection pool.

**Indicators:** BROKER.API_UNAVAILABLE followed by repeated AUTH exceptions,
followed by connection pool exhaustion.

**Prevention:** Circuit breaker on broker connection. Exponential backoff.
Connection pool monitoring.

---

### Pattern 7 — Silent Strategy Failure

**Description:** A strategy that appears active is producing signals that are
systematically wrong (e.g., always at wrong threshold, producing stale signals),
resulting in consistently unprofitable trades without triggering explicit exceptions.

**Indicators:** Strategy win rate declining below 40% over 30 days without a
STRAT.SIGNAL_GENERATION_FAILURE exception.

**Prevention:** Strategy health monitoring with win rate threshold alerts.
Automatic strategy disable at the governance threshold.

---

# SUPPLEMENT F — ENGINEERING DECISION RECORDS

## F.1 Framework Design Decisions

| Record ID | Decision | Rationale | Date |
|-----------|---------|-----------|------|
| EXC-EDR-001 | Kill switch path is fully isolated | Safety: no exception in any other path can prevent kill switch activation | Inception |
| EXC-EDR-002 | Maximum 3 automatic restarts before escalation | Prevents restart loops; ensures human review after persistent failure | Inception |
| EXC-EDR-003 | Non-idempotent operations never auto-retried | Financial safety: duplicate orders are worse than missed orders | Inception |
| EXC-EDR-004 | Security exceptions always require human resolution | Security requires judgment; automation cannot assess context | Inception |
| EXC-EDR-005 | Position mismatch always requires human confirmation | Financial integrity; automated correction could amplify error | Inception |
| EXC-EDR-006 | Kill switch state triple-persisted | Criticality: the one state that must survive any failure mode | Inception |
| EXC-EDR-007 | 35 exception categories (not fewer) | Granularity enables precise handling; too few categories reduces precision | Inception |
| EXC-EDR-008 | RTO for data feed fallback: 90 seconds | Empirically derived from yfinance initialization time + circuit breaker cooldown | Inception |

---

# SUPPLEMENT G — COMMON ANTI-PATTERNS

## G.1 Eight Exception Management Anti-Patterns

### Anti-Pattern 1 — Swallowing Exceptions

**Description:** An exception is caught and silently discarded — no logging,
no alerting, no recovery.

**Problem:** The failure is invisible. The system may be producing incorrect
results without any indication. Debugging is impossible because there is no
record of the exception.

**Correct approach:** Every exception must be at minimum logged at WARNING.
If the exception represents a genuine failure, it must be escalated appropriately.
No exception is silently swallowed.

---

### Anti-Pattern 2 — Catch-and-Continue Without Recovery

**Description:** An exception is caught, logged, and then execution continues
as if nothing happened — without validating that the operation's result is correct.

**Problem:** The operation may have produced a partial or incorrect result.
Continuing with that result may produce worse failures downstream.

**Correct approach:** When an exception is caught, validate the result before
continuing. If the result is invalid, apply fallback logic or abort.

---

### Anti-Pattern 3 — Infinite Retry

**Description:** A failed operation is retried indefinitely, occupying resources
and never escalating.

**Problem:** The underlying failure is permanent but invisible because the system
appears to be "handling" it. Resources are wasted. The operator is never notified.

**Correct approach:** Retry is capped at defined limits. After exhaustion, the
failure is escalated (fallback, then human intervention).

---

### Anti-Pattern 4 — Over-Broad Exception Catching

**Description:** A catch block catches all exception types uniformly, regardless
of their severity or handling requirements.

**Problem:** Exceptions that should trigger CRITICAL alerts are handled as silently
as minor expected exceptions. Security exceptions may be caught and handled as
if they were ordinary errors.

**Correct approach:** Exception handlers are specific. Security exceptions have
their own handler. CRITICAL exceptions have their own handler. A catch-all handler
is only a final safety net, not a primary handler.

---

### Anti-Pattern 5 — Exception-as-Control-Flow

**Description:** Business logic uses exceptions as a normal flow control mechanism
(e.g., throwing an exception to indicate "not found" rather than returning null
or an optional type).

**Problem:** Exceptions are expensive. Using them as control flow inflates the
exception rate, making it impossible to distinguish genuine failures from normal
operations. Alert rules that trigger on exception rates produce false positives.

**Correct approach:** Use exceptions for exceptional conditions only. Normal
"no result found" conditions should use explicit return types.

---

### Anti-Pattern 6 — Recovery Without Verification

**Description:** A recovery action is taken and immediately declared successful
without verifying that the system actually recovered.

**Problem:** A declared recovery that did not actually work leaves the system in
a false "healthy" state while the problem persists.

**Correct approach:** Every recovery action is followed by a verification step.
The component's OHS is checked. A test operation is performed. Recovery is not
declared until verification passes.

---

### Anti-Pattern 7 — Missing Compensation Logic

**Description:** A multi-step workflow with non-idempotent steps has no compensation
defined. When a step fails mid-workflow, the system is left in a partial state.

**Problem:** Partial state is often worse than no state. A partially-placed trade
(one leg in, one leg out) creates unintended risk exposure.

**Correct approach:** Every multi-step workflow with non-idempotent steps defines
its compensation action. Compensation is tested as part of the workflow's test suite.

---

### Anti-Pattern 8 — Treating Fallback as Normal Operation

**Description:** The system switches to a fallback path and remains there indefinitely
without alerting that the primary is unavailable.

**Problem:** The operator is unaware the system is running on degraded capability.
The fallback may have lower quality. Problems may accumulate invisibly.

**Correct approach:** Fallback activation is always alerted. An active fallback
that has persisted > 30 minutes generates a second alert. The operations team
investigates why the primary has not recovered.

---

# SUPPLEMENT H — OPERATIONAL RUNBOOK

## H.1 Common Scenarios and Responses

### Scenario 1 — Kill Switch Triggered During Market Hours

**Indicators:**
- RISK.KILL_SWITCH_VIX or RISK.KILL_SWITCH_DAILY_LOSS CRITICAL alert received.
- Dashboard: Kill Switch panel shows ACTIVE (red).
- No new orders are being placed.

**Operator Actions:**
1. Confirm the kill switch condition (VIX or daily loss) via broker portal.
2. Do not lift the kill switch until market conditions normalize.
3. Review all open positions manually.
4. If conditions normalize: lift via main.py --lift-kill-switch (authorized
   operators only). Every lift is logged.
5. Document the trigger event and response in the incident log.

---

### Scenario 2 — Primary Data Feed (Dhan) Unavailable

**Indicators:**
- MKTDATA.FEED_UNAVAILABLE ERROR alert.
- Data feed panel: Dhan shows UNAVAILABLE, yfinance shows ACTIVE.
- Decisions continue (on fallback data).

**Operator Actions:**
1. Confirm yfinance fallback is producing data (dashboard data freshness check).
2. Investigate Dhan API status (Dhan status page, check token validity).
3. If Dhan token expired: refresh token and restart.
4. Monitor decision quality (data from yfinance may have slight latency).
5. If fallback also fails: halt trading manually until data is restored.
6. Document the outage in the incident log.

---

### Scenario 3 — Broker Position Mismatch

**Indicators:**
- BROKER.POSITION_MISMATCH CRITICAL alert.
- Trading halted automatically.
- Dashboard: position count mismatch shown.

**Operator Actions:**
1. Log in to broker portal immediately. Note all open positions.
2. Compare broker positions with IIOS position report.
3. Identify the discrepancy: which position does IIOS have that broker doesn't,
   or vice versa.
4. Do NOT resume trading until reconciled.
5. If a position exists in broker but not IIOS: add manually to IIOS records.
6. If a position exists in IIOS but not broker: investigate (was an order lost?).
7. Resume trading only after full reconciliation and operator confirmation.
8. File SEV-1 incident report.

---

### Scenario 4 — Multiple Engines in CRITICAL OHS

**Indicators:**
- Multiple ERROR alerts for engine OHS CRITICAL transitions.
- SRS dropping.
- Cycle latency increasing.

**Operator Actions:**
1. Identify which engines are in CRITICAL state.
2. Check if they share a dependency (if so, the dependency is likely the root cause).
3. Restart the most degraded engine first.
4. Monitor OHS recovery after each restart.
5. If engines do not recover after 3 restarts each, investigate the dependency.
6. If OHS does not recover within 30 minutes, halt trading and investigate.

---

### Scenario 5 — Audit Chain Integrity Failure

**Indicators:**
- SEC.AUDIT_CHAIN_BROKEN CRITICAL alert.
- Trading automatically halted.
- Dashboard: audit status shows BROKEN.

**Operator Actions:**
1. Do not resume trading. This is a compliance issue.
2. Identify the affected records (chain verification report shows first break).
3. Investigate whether this is a software bug (hash calculation error) or
   potential tampering.
4. If software bug: fix, regenerate chain from audit record backup, validate.
5. If potential tampering: security incident procedure. Contact Architecture Council.
6. Resume trading only after chain is verified intact and incident is closed.

---

# SUPPLEMENT I — COMPREHENSIVE GLOSSARY

| Term | Definition |
|------|-----------|
| Alert Fatigue | Desensitization to alerts due to high volume or frequent false positives. |
| Alert Manager | The framework component transforming exceptions into human notifications. |
| Audit Manager | The framework component recording exception and recovery events immutably. |
| Backoff | A waiting strategy where retry intervals increase to avoid overwhelming a recovering service. |
| Blast Radius | The scope of impact of a failure — which components or capabilities are affected. |
| Business Continuity | Pre-defined manual procedures to manage obligations when the system is unavailable. |
| Cascade Failure | A failure that propagates through dependent components, causing a chain of failures. |
| Checkpoint | A persisted snapshot of system state that allows recovery from the checkpoint without replaying all history. |
| Circuit Breaker | A pattern that stops retrying a failing service after a threshold, resuming after a cooldown. |
| Compensation | An action that undoes or completes a partial state change from a failed operation. |
| Chronic Failure | The same failure type recurring more than once per week for more than 4 consecutive weeks. |
| Circuit Breaker Manager | The framework component managing circuit breaker state for all external services. |
| Containment | The act of defining and limiting the scope of a failure's impact. |
| Continuous Improvement Manager | The framework component driving systemic improvements from operational learnings. |
| CRO | Chief Reliability Officer — owns the Exception Registry and classification standards. |
| Defect | An error in design or implementation that creates a fault when deployed. |
| Escalation | The process of notifying higher-tier responders when a failure is not resolved at the current tier. |
| Escalation Manager | The framework component enforcing escalation policies. |
| Exception | A condition deviating from expected operation that the normal execution path cannot handle. |
| Exception Catalog | The searchable, documented view of all registered exception types. |
| Exception Classifier | The component assigning category, severity, and handling track to each exception. |
| Exception Registry | The authoritative catalog of all defined exception types and their handling specs. |
| Fail Fast | A strategy that aborts an operation early when success is known to be impossible. |
| Failure | The inability to complete a required function. The consequence of an unrecovered exception. |
| Failure Analyzer | The component assessing failure scope, impact, and immediate response priority. |
| Failure Detector | The component monitoring exception streams and OHS for failure conditions. |
| Fallback | An alternate implementation or data source used when the primary is unavailable. |
| Fallback Manager | The framework component activating and managing fallback paths. |
| Fault | An incorrect runtime state that will produce incorrect behavior if encountered. |
| Fault Tolerance | The ability to continue operating correctly despite component faults. |
| Graceful Degradation | Maintaining partial functionality with explicitly reduced capability during failures. |
| Health Manager | The component computing and tracking OHS for all IIOS components. |
| Idempotency | The property of an operation that produces the same result when performed multiple times. |
| Incident | A formally declared condition requiring coordinated response and investigation. |
| Incident Manager | The component managing formal incident lifecycle from declaration to postmortem. |
| Isolation | Containing a failure to prevent it from spreading to other components. |
| Isolation Manager | The framework component implementing isolation boundaries and quarantines. |
| Jitter | Random variation added to retry backoff intervals to prevent synchronized retry storms. |
| Kill Switch | The mechanism that halts all trading when VIX > 45 or daily loss > 2%. |
| Knowledge Base | The accumulated learnings from incidents and postmortems. |
| MTTD | Mean Time to Detect — average time from failure occurrence to detection. |
| MTTR | Mean Time to Recover — average time from failure detection to recovery. |
| MTTF | Mean Time to Failure — average time between failures. |
| Non-Recoverable Exception | An exception from which the system cannot return to acceptable operation automatically. |
| OHS | Operational Health Score — a 0.0–1.0 score for an IIOS component. |
| Operational Continuity | The goal that IIOS continues core functions across disruptions. |
| Permanent Failure | A failure that will not resolve without explicit intervention. |
| Postmortem | A structured post-incident review producing root cause analysis and action items. |
| Postmortem Manager | The framework component coordinating post-incident reviews. |
| Priority Matrix | A classification of exception urgency combining severity and scope. |
| Recovery Coordinator | The framework component orchestrating recovery strategy execution. |
| Recoverability | The ability to restore the system from failure to its pre-failure state. |
| Resilience | The ability to absorb disruption, adapt, and recover quickly. |
| Reliability | The probability that the system performs correctly over a specified period. |
| Retry Manager | The framework component executing retry logic for transient failures. |
| Rollback | Reverting to a previous known-good state after a failed state change. |
| Root Cause Analyzer | The component identifying the underlying cause of failures. |
| RPO | Recovery Point Objective — maximum acceptable data loss in a disaster recovery. |
| RTO | Recovery Time Objective — maximum time to restore operations after failure. |
| Self-Healing | The ability to detect and correct problems automatically without human intervention. |
| SEV-1/2/3/4 | Incident severity levels: CRITICAL, HIGH, MEDIUM, LOW. |
| SRS | System Reliability Score — a 0.0–1.0 composite score across 12 reliability dimensions. |
| Transient Failure | A temporary failure that will resolve without intervention. |
| UNK | Unknown exception category — for exceptions not matching any defined type. |
| Verification | Confirming that recovery has actually restored function (not just assuming it has). |

---

# DOCUMENT METRICS

| Attribute | Value |
|-----------|-------|
| Document Code | IIOS-EXC-FLR-001 |
| Framework Version | 1.0.0 |
| Document Status | Active |
| Total Parts | 10 |
| Total Supplements | 9 (A through I) |
| Total Constitution Rules | 110 |
| Total Readiness Checks | 73 HARD + 15 SOFT = 88 total |
| Total Framework Components | 20 |
| Total Recovery Strategies | 16 |
| Total Exception Categories | 35 |
| Total Reliability Dimensions | 12 |
| Total Failure Lifecycle Stages | 12 |
| Total Exception Hierarchy Levels | 14 |
| Total Failure Patterns Documented | 7 |
| Total Anti-Patterns | 8 |
| Total Operational Scenarios | 5 |
| Total Glossary Entries | 52 |
| Total Engineering Decision Records | 8 |

---

# AMENDMENT HISTORY

| Version | Date | Author | Change Description |
|---------|------|--------|-------------------|
| 1.0.0 | 2026-07-04 | Architecture Council | Initial publication |

---

# CLOSING STATEMENT

This document — the Exception and Failure Management Framework for the Investment
Intelligence Operating System (IIOS), bearing document code IIOS-EXC-FLR-001 —
is the complete, authoritative specification for how every error, exception, fault,
failure, degradation, timeout, interruption, dependency issue, infrastructure problem,
AI anomaly, data inconsistency, security incident, and recovery process shall be
handled throughout the entire IIOS system.

The framework is built on a single foundational principle: in a system that manages
real capital in live markets, the cost of failing to handle an exception correctly
is not merely a degraded user experience — it is a financial loss, a compliance
breach, or a safety incident. Every rule in this framework, every recovery strategy,
every constitutional requirement exists to ensure that exceptions are handled
precisely, safely, and accountably.

The 35-category exception taxonomy provides the vocabulary. The 20 framework
components provide the infrastructure. The 16 recovery strategies provide the
tools. The 110-rule constitution provides the law. The 88-check readiness
certification provides the proof.

No exception is silently swallowed. No failure goes undetected. No incident goes
unlearned. No knowledge is lost. This is the standard IIOS is held to.

---

*IIOS-EXC-FLR-001 / Version 1.0.0 / Status: Active*
*Exception and Failure Management Framework — Investment Intelligence Operating System*
*Architecture Council Approved*
