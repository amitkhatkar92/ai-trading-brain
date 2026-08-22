# CORE INFRASTRUCTURE SPECIFICATION
## Investment Intelligence Operating System (IIOS)

**Document Code:** IIOS-CIS-001
**Version:** 1.0
**Status:** FINAL
**Classification:** ENGINEERING SPECIFICATION
**Authority:** Architecture Council
**Date:** 2026

---

## REVISION HISTORY

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-Q1 | Architecture Council | Initial draft |
| 0.5 | 2026-Q2 | Architecture Council | Full service catalog |
| 1.0 | 2026-Q3 | Architecture Council | Final specification |

---

## TABLE OF CONTENTS

- Part I — Core Infrastructure Philosophy
- Part II — Infrastructure Service Catalog
- Part III — Infrastructure Architecture
- Part IV — Infrastructure Interaction Model
- Part V — Infrastructure Lifecycle
- Part VI — Infrastructure Reliability Framework
- Part VII — Performance Framework
- Part VIII — Governance Framework
- Part IX — Engineering Constitution
- Part X — Infrastructure Certification
- Appendix A — Infrastructure Catalog
- Appendix B — Service Dependency Matrix
- Appendix C — Lifecycle Reference
- Appendix D — Performance Reference
- Appendix E — Failure Taxonomy
- Appendix F — Recovery Workflows
- Appendix G — Operational Runbook
- Appendix H — Infrastructure Anti-Patterns
- Appendix I — Glossary

---

# PART I — CORE INFRASTRUCTURE PHILOSOPHY

## 1.1 Purpose of Infrastructure

Infrastructure is the invisible substrate upon which all visible capability is built.
Before the IIOS can classify a market regime, debate a trade, compute a position
size, or fire an order — it must breathe. Infrastructure is the breath.

Infrastructure exists to answer four universal questions that every system component
asks before it can do its work:
- Where is my configuration?
- How do I communicate with other components?
- How do I persist and retrieve data?
- How will my health and performance be observed?

Without answers to these four questions, no component can operate correctly or
reliably. Infrastructure answers these questions once, correctly, for all components.
No component is permitted to answer them for itself.

The IIOS infrastructure is not a collection of utilities. It is the operating
foundation — the set of platform services without which the system cannot run.
Infrastructure components are created in Wave 2, used by every layer from Wave 1
onward, and are never retired. They are the last components to shut down and
the first to start up.

---

## 1.2 Infrastructure as the Operating Foundation

Every one of IIOS's 17 architectural layers depends on infrastructure. The
GlobalIntelligence layer (Layer 1) depends on the DataFeedManager to fetch market
data. The DecisionEngine (Layer 10) depends on the EventBus to publish trade
decisions. The RiskGuardian (Layer 9) depends on the configuration service to
read kill-switch thresholds. The ControlTower (Layer 17) depends on the telemetry
infrastructure to write cycle data to SQLite.

This universal dependency has a critical consequence: if infrastructure fails,
everything fails. An error in the logging service does not silence one module.
It silences all 17 layers simultaneously. An unhandled configuration loading error
at startup does not prevent one component from initializing. It prevents every
component from initializing.

This universal exposure means infrastructure must be held to a higher standard
than any business logic component. A bug in the StrategyGeneratorAI affects
one layer. A bug in the configuration service or the event bus affects the
entire system.

The IIOS infrastructure is therefore designed with three principles that do not
apply to any business logic component:
1. Infrastructure components are fail-safe, not fail-fast.
2. Infrastructure components degrade gracefully when possible.
3. Infrastructure components are simple and well-understood, not clever.

---

## 1.3 Platform Services

Platform services are infrastructure components that provide operating system-level
capabilities to the application layer. They abstract the host environment (Windows,
Linux, Docker) from the business logic. Platform services ensure that the same
business logic runs identically on a developer's Windows laptop, a CI/CD runner,
and a production VPS running Docker.

**IIOS Platform Services:**
- Clock Service: provides consistent, testable time to all components.
- UUID Service: generates unique identifiers for all entities.
- File Service: abstracts filesystem operations.
- Storage Service: abstracts persistent data storage.
- Resource Service: manages CPU, memory, and I/O resource budgets.
- Scheduler Service: manages scheduled task execution.
- Timer Service: provides high-precision timing for latency measurement.

Platform services are the interface between IIOS and the host operating system.
All operating system calls are routed through platform services. No business
logic component makes direct os, pathlib, or datetime.datetime.now() calls.
This gives complete control of the runtime environment during testing.

---

## 1.4 Cross-Cutting Services

Cross-cutting services are infrastructure components that address concerns that
affect every part of the system simultaneously. They cannot be cleanly assigned
to a single layer or package because they are relevant everywhere.

**IIOS Cross-Cutting Services:**
- Logging Service: all log output in all packages goes through this service.
- Metrics Service: all performance metrics go through this service.
- Tracing Service: all execution traces go through this service.
- Audit Service: all business-significant events go through this service.
- Exception Service: all exception handling and reporting goes through this service.
- Feature Flag Service: all conditional feature activation goes through this service.
- Identity Service: all identity and authentication decisions go through this service.

The defining characteristic of a cross-cutting service is: if you add a new
IIOS package tomorrow, that package immediately uses every cross-cutting service
without any configuration or registration step. Cross-cutting services are ambient.
They are always available, always active, and always observing.

---

## 1.5 Shared Capabilities

Shared capabilities are infrastructure components that provide specialized
technical functionality used by multiple IIOS packages. Unlike platform services
(which abstract the OS) and cross-cutting services (which address universal
concerns), shared capabilities are consumed optionally — only by packages
that need them.

**IIOS Shared Capabilities:**
- Cache Service: in-memory caching with TTL.
- Event Bus: system-wide publish/subscribe messaging.
- Message Bus: direct point-to-point messaging.
- Notification Service: outbound notifications (Telegram, email).
- Plugin Service: plugin discovery and loading.
- Extension Service: extension point registration.
- Retry Service: retry policies for transient failures.
- Circuit Breaker: failure isolation for external dependencies.

Shared capabilities are consumed through dependency injection. A package that
needs caching declares a dependency on the Cache Service in its manifest;
it does not instantiate a cache directly. This allows the infrastructure
implementation to be replaced without changing consuming packages.

---

## 1.6 Reliability-First Engineering

The IIOS is a financial system. Financial systems have a reliability contract
with their operators that is more demanding than most software: every second of
downtime during market hours is a missed opportunity. A missed trade cannot be
retroactively executed. A kill-switch that fails to trigger can cost real money.

Reliability-first engineering means:
- Every infrastructure service has a defined failure mode.
- Every failure mode has a defined recovery path.
- No failure mode leads to silent incorrect operation.
- All failures are logged, measured, and alerted.

Infrastructure components are designed to fail loudly, recover automatically
where safe, and escalate immediately when automatic recovery is impossible.
A DataFeedManager that fails silently and returns stale data is more dangerous
than one that loudly crashes — because the system continues operating on bad data.

**Reliability Targets:**
- Infrastructure availability: >= 99.9% during market hours (09:00–15:30 IST).
- Infrastructure MTTR (Mean Time To Recover): <= 60 seconds for self-healing failures.
- No single infrastructure component failure causes permanent system halt.

---

## 1.7 Scalability-First Engineering

The IIOS begins as a single-process system on one machine. It will grow.
Scalability-first engineering means every infrastructure design decision is
evaluated for how it performs under 10x and 100x current scale.

Scale dimensions for IIOS infrastructure:
- **Symbol scale:** from 50 symbols to 5,000 symbols.
- **Agent scale:** from 62 agents to 620 agents.
- **Decision rate:** from 10 decisions/minute to 1,000 decisions/minute.
- **Event rate:** from 100 events/second to 10,000 events/second.
- **Data retention:** from 90 days to 5 years.

The key scalability commitments for IIOS infrastructure:
- The EventBus interface does not change when switching from in-process
  to Redis Pub/Sub. Scalability is achieved without modifying consumers.
- The Cache Service interface does not change when switching from in-memory
  to Redis. Scalability is achieved without modifying consumers.
- The Storage Service interface does not change when switching from SQLite
  to PostgreSQL. Scalability is achieved without modifying consumers.

Infrastructure interfaces are designed once. Implementations are replaced.

---

## 1.8 Security-First Engineering

The IIOS handles broker credentials, account positions, financial transactions,
and personal data. Security failures in a trading system are not just
operational problems — they are financial and reputational crises.

Security-first engineering means:
- No secret is stored in code, config files, or logs.
- All external input is validated before use.
- All database queries are parameterized.
- All communication with external services is authenticated.
- All sensitive data is encrypted at rest and in transit.

**Infrastructure Security Commitments:**
- Secrets Service is the only component that accesses secrets.
  No other component reads environment variables directly.
- Identity Service validates all Telegram commands before routing them.
- Encryption Service handles all cryptographic operations.
  No component implements its own cryptography.
- Authentication Service validates all broker API credentials before use.
- Audit Service records all security-significant events immutably.

OWASP Top 10 compliance is a prerequisite for infrastructure certification.
Any infrastructure component that fails an OWASP Top 10 check blocks
production authorization.

---

## 1.9 Observability-First Engineering

An unobservable system is an unmanageable system. In a production trading
system running 17 layers and 62 agents through a cycle that must complete in
200ms, operators need to know exactly what happened when something goes wrong.

Observability-first engineering means every infrastructure service and every
business logic component produces three types of signals:
- **Logs:** structured event records describing what happened.
- **Metrics:** numeric measurements of how the system is performing.
- **Traces:** correlated records linking a request across multiple components.

The infrastructure provides the plumbing for all three signal types. Business
logic components do not implement their own observability. They emit signals
through infrastructure APIs and the infrastructure routes them to the appropriate
sinks (SQLite, file system, dashboard, Telegram alerts).

**Observability Commitments:**
- Every trading cycle produces at least one trace spanning all 17 layers.
- Every infrastructure component reports a health status to the Health Service.
- Every error is logged with: timestamp, component, error type, and context.
- Every latency-sensitive operation is measured and reported to the Metrics Service.

---

## 1.10 High Availability

High availability for IIOS means the system is available to process market
events whenever the Indian stock market is open. This defines the availability
window: Monday to Friday, 09:15 to 15:30 IST, excluding NSE holidays.

Infrastructure high availability strategies:
- **Restart-on-failure:** Docker container restart policy unless-stopped ensures
  the trading process restarts automatically on crash.
- **Data feed redundancy:** Two data sources (Dhan API + yfinance) with automatic
  failover. The DataFeedManager switches to the secondary source when the primary
  is unavailable.
- **State persistence:** All operational state is persisted to SQLite before
  any operation is acknowledged. A restart recovers from the last persisted state.
- **Idempotent operations:** Trade operations are idempotent. Sending the same
  order twice produces the same result as sending it once (duplicate detection
  in the paper journal).

**Availability Target:** >= 99.5% during defined market hours, measured as
the fraction of market-hour minutes in which the system is operational.

---

## 1.11 Self-Healing Infrastructure

Self-healing is the property by which infrastructure components detect and
correct their own failures without operator intervention. IIOS infrastructure
is designed to self-heal within defined boundaries.

**Self-Healing Behaviors:**

| Component | Failure | Self-Heal Action |
|-----------|---------|-----------------|
| DataFeedManager | Dhan API 451 error | Switch to yfinance automatically |
| DataFeedManager | yfinance timeout | Retry with backoff (3 attempts) |
| EventBus | Subscriber exception | Log error, continue delivering to other subscribers |
| Cache Service | Cache miss (TTL expired) | Re-fetch from source, repopulate cache |
| Database | Lock timeout | Retry with exponential backoff |
| Telegram Bot | API rate limit | Respect rate limits, queue messages |
| SystemMonitor | Layer latency exceeded WARN | Log warning, continue cycle |
| SystemMonitor | Layer latency exceeded CRIT | Abort cycle, increment counter |
| GlobalDataAI pre-warm | Pre-warm thread crash | Log error, restart pre-warm thread |

Self-healing is bounded. When a self-healing component exhausts its recovery
options (e.g., three consecutive data feed failures with both sources unavailable),
it escalates to the Health Service and triggers an operator alert via Telegram.

---

## 1.12 Future-Proof Design

Infrastructure designed today must not become a bottleneck when the system
evolves. Every infrastructure design decision is evaluated against five
future state scenarios:

**Scenario F1 — Multi-Exchange:** IIOS connects to BSE and MCX in addition to NSE.
Infrastructure impact: DataFeedManager adds exchange routing. No interface change.

**Scenario F2 — Distributed Deployment:** IIOS runs on two VPS nodes with shared
state. Infrastructure impact: EventBus replaced with Redis Pub/Sub. No consumer
changes. Cache Service backed by Redis. No consumer changes.

**Scenario F3 — Regulatory Audit:** A regulator requests complete transaction
records for a three-year period. Infrastructure impact: Audit Service exports
from SQLite. Immutable audit log has all required records.

**Scenario F4 — Institutional Scale:** From 50 to 5,000 watched symbols.
Infrastructure impact: DataFeedManager parallelizes fetches. Metrics Service
reports per-symbol latency. No business logic change.

**Scenario F5 — ML Integration:** Deep learning models replace rule-based
regime classifiers. Infrastructure impact: Feature Flag Service enables/disables
ML models per regime. No core pipeline change.

---

*End of Part I*

---

# PART II — INFRASTRUCTURE SERVICE CATALOG

## 2.0 Catalog Overview

The IIOS infrastructure contains exactly 46 defined services organized into
seven functional groups. Each service has a unique code, a classification, and
a wave assignment.

**Functional Groups:**
- **Group A — Configuration and Environment:** Services that manage system configuration.
- **Group B — Lifecycle and Registry:** Services that manage component lifecycle.
- **Group C — Observability:** Services that make the system observable.
- **Group D — Security:** Services that protect the system.
- **Group E — Platform:** Services that abstract the host environment.
- **Group F — Communication:** Services that enable component communication.
- **Group G — Operations:** Services that ensure operational reliability.

**Service Classification:**
- **CRITICAL:** Required for system startup. Absence blocks all other services.
- **CORE:** Required for production operation. Absence blocks market trading.
- **OPTIONAL:** Enhances operation. Absence degrades capability without halting.

---

## 2.1 Configuration Service (INFRA-CFG-001)

**Code:** INFRA-CFG-001
**Group:** A — Configuration and Environment
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Configuration Service is the single source of truth for all system
configuration. It loads, validates, and exposes configuration values to all
other infrastructure services and all business logic components.

**Scope:**
The Configuration Service manages all values that determine system behavior:
trading thresholds, latency targets, schedule parameters, feature flags,
broker connection settings, and infrastructure tuning parameters. It does NOT
manage secrets (broker tokens, API keys) — those are handled by the Secrets Service.

**Configuration Sources (in priority order):**
1. Environment variables (highest priority — override everything).
2. config.py module (primary source for all defined constants).
3. Default values (built into the service — lowest priority).

**Configuration Snapshot:**
After loading, the Configuration Service produces an immutable ConfigurationSnapshot
object. This snapshot is the only source of configuration values after startup.
No component reads environment variables directly after the snapshot is created.
No component reads config.py at runtime. All access is through the snapshot.

**Immutability Guarantee:**
Once the ConfigurationSnapshot is created, it is frozen. Any attempt to modify
it raises a ConfigurationImmutableError. This guarantee means that all
components see the same configuration for the entire lifecycle of a process.
If configuration must change, the process restarts with new configuration.

**Critical Configuration Values (from config.py):**
- DECISION_THRESHOLD = 6.5
- KILL_SWITCH_VIX = 45.0
- KILL_SWITCH_DAILY_LOSS_PCT = 0.02
- PROMOTION_WIN_RATE = 0.50
- PROMOTION_SHARPE = 0.80
- PROMOTION_MAX_DD = 0.15
- LAYER_LATENCY_WARN_MS = 2000
- LAYER_LATENCY_CRIT_MS = 5000
- CONTINUOUS_SCAN_INTERVAL = 30

**Validation:**
The Configuration Service validates all values before producing the snapshot:
- Type validation: each value is validated against its declared type.
- Range validation: numeric values are validated against declared min/max bounds.
- Dependency validation: related values are checked for internal consistency
  (e.g., WARN threshold must be less than CRIT threshold).
- Missing required value: any required value without a default raises
  ConfigurationMissingError at startup, blocking system initialization.

**Access Pattern:**
`
ConfigurationService.get_snapshot() -> ConfigurationSnapshot
ConfigurationSnapshot.get(key: str) -> Any
ConfigurationSnapshot.require(key: str) -> Any  # raises if missing
`

---

## 2.2 Environment Service (INFRA-ENV-001)

**Code:** INFRA-ENV-001
**Group:** A — Configuration and Environment
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Environment Service manages the runtime environment context, providing
a consistent view of where and how the system is running. It answers the
question: "What kind of environment am I running in right now?"

**Environment Modes:**
- DEVELOPMENT: local developer environment, verbose logging, all safety checks active.
- TEST: automated test environment, logging suppressed, all external calls mocked.
- STAGING: pre-production VPS, paper trading mode forced, production data.
- PRODUCTION: live VPS, paper or live trading depending on PAPER_TRADING flag.
- DOCKER: any Docker container environment.

**Environment Detection:**
The Environment Service detects the current environment through:
1. IIOS_ENV environment variable (explicit override).
2. Presence of Docker-specific filesystem markers.
3. Python sys.argv analysis (test runner detection).
4. Default: DEVELOPMENT.

**Environment-Specific Behaviors:**
- In TEST mode: Clock Service is injectable (for deterministic tests).
- In TEST mode: External HTTP calls raise TestModeNetworkCallError.
- In DEVELOPMENT mode: Stack traces included in all log output.
- In PRODUCTION mode: Stack traces excluded from Telegram notifications.
- In STAGING mode: PAPER_TRADING is forced to True regardless of config.

**Environment Invariants:**
- Environment mode is immutable after startup.
- Production mode cannot be set without IIOS_ENV=production explicitly.
- Test mode auto-activates when pytest is the process host.

---

## 2.3 Dependency Injection Service (INFRA-DI-001)

**Code:** INFRA-DI-001
**Group:** A — Configuration and Environment
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Dependency Injection Service manages the creation and injection of
all infrastructure service instances. It enforces the singleton contract,
manages service lifetimes, and enables testability through substitution.

**DI Container Design:**
The IIOS DI container is a lightweight registry-based container. It does not
use annotation-based magic or complex wiring frameworks. All registrations are
explicit and readable.

**Service Lifetimes:**
- SINGLETON: one instance for the entire process lifetime. Initialized once,
  used throughout. All 4 IIOS singletons use this lifetime.
- SCOPED: one instance per trading cycle. Created at cycle start, destroyed at end.
- TRANSIENT: new instance per request. For stateless utilities.

**Registration Patterns:**
`
# Singleton factory registration (explicit):
container.register_singleton(FeedManager, get_feed_manager)
container.register_singleton(TelegramBot, get_telegram_bot)
container.register_singleton(PerformanceTracker, get_performance_tracker)
container.register_singleton(RegimeStrategyMap, get_regime_strategy_map)

# Scoped service registration:
container.register_scoped(CycleContext, CycleContextFactory)

# Test override (only in TEST environment):
container.override(FeedManager, MockFeedManager)  # raises in PRODUCTION
`

**Invariants:**
- Singletons are resolved at startup, not lazily. All singletons exist before
  the first trading cycle begins.
- Test overrides can only be registered in TEST environment.
  Any attempt to override in PRODUCTION raises DIContainerSecurityError.
- Direct class instantiation of registered services raises a warning
  (in DEVELOPMENT) and is forbidden (in PRODUCTION mode via static analysis).

---

## 2.4 Service Registry (INFRA-SRV-001)

**Code:** INFRA-SRV-001
**Group:** B — Lifecycle and Registry
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Service Registry is the authoritative catalog of all services currently
registered and available in the running system. It is the infrastructure
equivalent of uild_manifest.json at runtime.

**Registry Records:**
For each registered service, the Service Registry maintains:
- Service name and version.
- Service status: REGISTERED, INITIALIZING, ACTIVE, DEGRADED, FAILED, STOPPED.
- Dependencies: list of other services this service depends on.
- Health endpoint: function reference to call for health check.
- Startup time (milliseconds).
- Last health check result.
- Failure count (since last restart).

**Registry Operations:**
- egister(service: ServiceDescriptor) -> None: add service to registry.
- get_status(service_name: str) -> ServiceStatus: query current status.
- get_all_statuses() -> Dict[str, ServiceStatus]: full status snapshot.
- mark_ready(service_name: str) -> None: signal startup complete.
- mark_failed(service_name: str, reason: str) -> None: signal failure.

**Registry Access:**
The Service Registry is a singleton. All infrastructure services update their
own status in the registry. The Health Service reads from the registry to
produce system health reports.

---

## 2.5 Component Registry (INFRA-CMP-001)

**Code:** INFRA-CMP-001
**Group:** B — Lifecycle and Registry
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Component Registry tracks all application-layer components (agents, strategies,
scanners, handlers) that have self-registered with the system. It is the
runtime equivalent of the Architecture Council's agent roster.

**Component Types Tracked:**
- DEBATE_AGENT: must have exactly 5 registered before SYSTEM_CERTIFIED.
- STRATEGY: active strategies by status (ACTIVE, DISABLED, CANDIDATE).
- SCANNER: equity, options, arbitrage, breakout, momentum scanners.
- DATA_PLUGIN: additional data source plugins.
- ANALYTICS_PLUGIN: additional analytics plugins.
- NOTIFICATION_PLUGIN: additional notification channel plugins.

**Invariants Enforced:**
- At SYSTEM_CERTIFIED, exactly 5 DEBATE_AGENT components must be registered.
  If count != 5, the system raises AgentCountViolationError and blocks startup.
- At least 1 STRATEGY with status ACTIVE must be registered for any trade cycle.
- Duplicate component registration (same name, same version) raises DuplicateComponentError.

**Registration Event:**
When a component registers, the Component Registry publishes a COMPONENT_REGISTERED
event to the EventBus. Other infrastructure services (SystemMonitor, Health Service)
subscribe to this event and update their internal state.

---

## 2.6 Lifecycle Manager (INFRA-LCM-001)

**Code:** INFRA-LCM-001
**Group:** B — Lifecycle and Registry
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Lifecycle Manager orchestrates the startup and shutdown sequence for all
IIOS services and components. It ensures services start in dependency order
and stop in reverse dependency order.

**Startup Orchestration:**
The Lifecycle Manager constructs a dependency graph of all registered services
(from their manifests), performs a topological sort, and starts services in
topological order. If a critical service fails to start, the Lifecycle Manager
aborts the entire startup sequence and reports the failure.

**Startup Phases:**
`
Phase 1: ENVIRONMENT          (Environment Service, Secrets Service)
Phase 2: CONFIGURATION        (Configuration Service, Validation)
Phase 3: PLATFORM             (Clock, UUID, File, Storage services)
Phase 4: OBSERVABILITY        (Logging, Metrics, Tracing services)
Phase 5: SECURITY             (Identity, Authentication, Authorization services)
Phase 6: COMMUNICATION        (EventBus, MessageBus, Notification services)
Phase 7: APPLICATION CORE     (DataFeedManager, SystemMonitor, HealthService)
Phase 8: APPLICATION DOMAIN   (Intelligence, Knowledge, Strategy layers)
Phase 9: INTEGRATION          (Telegram bot, Dashboard bridge)
Phase 10: CERTIFICATION       (Invariant verification: 5 agents, thresholds, etc.)
`

**Shutdown Orchestration:**
The Lifecycle Manager executes a graceful shutdown in reverse startup order.
SIGTERM triggers graceful shutdown. SIGKILL triggers emergency shutdown
(state is persisted, in-flight cycles are marked INCOMPLETE).

**Timeout Policy:**
Each service has a startup timeout (default 10 seconds) and a shutdown timeout
(default 5 seconds). Services that exceed their timeout are forcibly terminated,
and the failure is logged and reported.

---

## 2.7 Startup Manager (INFRA-STR-001)

**Code:** INFRA-STR-001
**Group:** B — Lifecycle and Registry
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Startup Manager executes the specific pre-market initialization sequence
that prepares the IIOS trading engine for market open. It is distinct from
the Lifecycle Manager, which handles service-level startup. The Startup Manager
handles business-logic-level pre-market preparation.

**Pre-Market Initialization Sequence:**
`
08:00: Startup Manager triggered by Scheduler.
08:00: Write startup banner to log: version, mode, environment.
08:01: GlobalDataAI pre-warm: fetch overnight context.
08:02: Market Intelligence warm-up: load regime state from previous day.
08:03: Strategy Registry sync: verify all strategies loaded.
08:04: Learning state sync: load performance tracker state from SQLite.
08:05: Kill switch check: verify thresholds from config match expectations.
08:06: Data feed health check: verify Dhan or yfinance is reachable.
08:07: Telegram notification: send startup confirmation to operators.
08:08: SYSTEM_READY signal published to EventBus.
`

**Startup Failure Handling:**
- Phase 1-4 failures (pre-market data, state sync): log warning, continue.
  The system starts with degraded state and self-heals during market hours.
- Phase 5 (kill switch check): if thresholds cannot be verified, abort startup.
  A system that cannot verify its own safety controls must not trade.
- Phase 6 (data feed): if both sources are unreachable, abort startup.
- Phase 7-8 failures: degrade gracefully, notify operators.

**Startup Banner:**
`
============================================================
IIOS STARTUP — version {version} — mode {mode}
Environment: {env} — Paper Trading: {paper}
Kill switch: VIX={vix_threshold}, DailyLoss={loss_threshold}
Decision threshold: {decision_threshold}
Data feed: {primary_feed} (fallback: {fallback_feed})
Agents registered: {agent_count} (required: 5)
============================================================
`

---

## 2.8 Shutdown Manager (INFRA-SHD-001)

**Code:** INFRA-SHD-001
**Group:** B — Lifecycle and Registry
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Shutdown Manager executes an orderly system shutdown that preserves all
operational state, completes in-flight operations where safe, and ensures
no data loss occurs.

**Shutdown Trigger Sources:**
- SIGTERM signal (Docker stop, systemd stop, kill -15).
- SIGINT signal (Ctrl+C in development).
- Telegram /shutdown command (operator-initiated).
- RiskGuardian kill switch (automatic safety shutdown).
- Lifecycle Manager timeout (service failed to start within window).

**Shutdown Sequence:**
`
Trigger received.
  -> Publish SHUTDOWN_INITIATED event to EventBus.
  -> Set SHUTDOWN flag in SystemState.
  -> Scheduler: cancel all pending scheduled tasks.
  -> Execution Engine: complete current order if in-flight, block new orders.
  -> Active cycle: if cycle > 50% complete, complete it. Otherwise abort.
  -> Learning state: flush all pending learning updates to SQLite.
  -> Telemetry: flush all pending metrics to SQLite.
  -> Logging: flush all pending log buffers to disk.
  -> Write shutdown banner to log.
  -> Publish SHUTDOWN_COMPLETE event.
  -> Process exits with code 0.
`

**Shutdown Banner:**
`
============================================================
IIOS SHUTDOWN — {reason}
Uptime: {uptime} — Cycles completed: {cycles}
Trades executed: {trades} — P&L: {pnl}
Shutdown at: {timestamp}
============================================================
`

**Emergency Shutdown (SIGKILL):**
SIGKILL cannot be intercepted. Emergency shutdown safety is provided by:
- All write operations using SQLite transactions (partial writes are rolled back).
- Learning state written after every cycle (not batched indefinitely).
- Paper trades journal flushed after every write.

---

## 2.9 Health Service (INFRA-HLT-001)

**Code:** INFRA-HLT-001
**Group:** C — Observability
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Health Service maintains a real-time view of system health, aggregating
health reports from all registered components and providing health APIs used
by the dashboard, the Telegram bot, and the Docker health check.

**Health States:**
- HEALTHY: component is operating within all normal parameters.
- DEGRADED: component is operating but with reduced capability.
  (e.g., yfinance fallback active instead of Dhan primary)
- CRITICAL: component is operating but at risk of failure.
  (e.g., latency approaching threshold limits)
- FAILED: component has failed and cannot self-recover.
- UNKNOWN: component has not reported health within its reporting interval.

**Health Aggregation:**
System health is the minimum health across all CRITICAL-classified services:
- If any CRITICAL service is FAILED or UNKNOWN: System = FAILED.
- If any CRITICAL service is CRITICAL: System = CRITICAL.
- If any CRITICAL service is DEGRADED: System = DEGRADED.
- All CRITICAL services HEALTHY: System = HEALTHY.

**Docker Health Check Integration:**
The Dockerfile HEALTHCHECK command calls the Health Service endpoint.
`
HEALTHCHECK CMD python -c "from iios.infrastructure.health import get_health; exit(0 if get_health().is_healthy() else 1)"
`
A FAILED health status causes Docker to mark the container UNHEALTHY.

**Health Reporting Interval:**
- CRITICAL services: every 30 seconds.
- CORE services: every 60 seconds.
- OPTIONAL services: every 120 seconds.

---

## 2.10 Diagnostics Service (INFRA-DGN-001)

**Code:** INFRA-DGN-001
**Group:** C — Observability
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Diagnostics Service provides on-demand deep inspection of system state
for operator debugging. It is the /diag Telegram command backend and the
diagnostic data source for the Streamlit dashboard.

**Diagnostic Information:**
- System uptime and restart count.
- Current environment mode and active configuration values.
- Memory usage per component (approximate).
- EventBus queue depth and subscriber count.
- Cache hit rate and cache size.
- Active timer sessions (in-progress layer timings).
- Last cycle summary (all 17 layers: latency, status).
- Feed status: which feed is active, last successful fetch timestamp.
- Database status: size, last write, connection count.
- Registered agent count: breakdown by type.
- Active strategy count and their individual win rates.
- Learning state: last update, cycle count.

**Diagnostic Report Format:**
The Diagnostics Service produces both:
- A structured dictionary for programmatic consumption (dashboard).
- A formatted text report for Telegram delivery.

**Security:**
The Diagnostics Service requires authentication through the Identity Service
before providing sensitive operational data. An unauthenticated diagnostic
request returns only a generic status (HEALTHY/DEGRADED/FAILED).

---

## 2.11 Monitoring Service (INFRA-MON-001)

**Code:** INFRA-MON-001
**Group:** C — Observability
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Monitoring Service provides continuous real-time monitoring of all
infrastructure and application components. It collects performance signals,
compares them against thresholds, and triggers alerts when thresholds are exceeded.

**Monitoring Domains:**
- **Infrastructure monitoring:** service health, resource usage, error rates.
- **Performance monitoring:** latency percentiles for all timed operations.
- **Business monitoring:** cycle completion rate, decision rate, trade volume.
- **Data feed monitoring:** fetch latency, error rate, staleness.

**Alert Levels:**
- INFO: informational event. No action required.
- WARN: degraded performance or approaching threshold. Operator aware.
- ERROR: component failure. Operator should investigate.
- CRITICAL: system-level failure. Immediate operator action required.

**Alert Routing:**
- WARN: written to log file only.
- ERROR: written to log file + Telegram message to operators.
- CRITICAL: written to log file + Telegram message + immediate stop of new work.

**Monitoring Thresholds (defaults from config.py, overrideable per component):**
- Layer latency WARN: 2,000ms.
- Layer latency CRIT: 5,000ms.
- Memory usage WARN: 400MB.
- Memory usage CRIT: 768MB.
- EventBus queue depth WARN: 1,000.
- EventBus queue depth CRIT: 10,000.
- Database write latency WARN: 10ms.
- Database write latency CRIT: 100ms.

---

## 2.12 Logging Service (INFRA-LOG-001)

**Code:** INFRA-LOG-001
**Group:** C — Observability
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Logging Service is the single output channel for all structured log events
in IIOS. Every package, module, and component logs through this service.
No component writes to stdout/stderr, opens log files, or calls print() directly.

**Log Levels:**
- DEBUG: detailed trace information for development diagnostics.
- INFO: normal operational events (cycle start, trade executed, etc.).
- WARNING: abnormal but handled events (fallback activated, retry triggered).
- ERROR: failures that require investigation (component failed, order rejected).
- CRITICAL: system-level failures requiring immediate action.

**Log Record Format:**
`
{timestamp} | {level} | {component} | {cycle_id} | {message} | {context_json}
`

Example:
`
2026-07-05T09:31:15.003Z | INFO | OrderManager | cycle-a4b2c | TRADE_EXECUTED | {"symbol":"NIFTY","side":"BUY","qty":1,"price":24350.0}
`

**Log Sinks:**
- Rotating log file: logs/iios-YYYY-MM-DD.log. Daily rotation. 30-day retention.
- SQLite event log: for structured querying through the dashboard.
- Stderr (production): ERROR and CRITICAL only.

**Sensitive Data Protection:**
The Logging Service automatically redacts values from a configurable redaction list:
- Any value with key containing 	oken, key, secret, password, uth.
- Account ID, client ID, and position values in DEBUG mode.

**Log Context Propagation:**
The Logging Service supports context propagation. When a cycle begins, a
CycleContext (containing cycle_id and 	imestamp) is attached to the
logging context. All log records produced during the cycle include the cycle_id,
enabling complete cycle tracing from a single ID.

---

## 2.13 Metrics Service (INFRA-MTR-001)

**Code:** INFRA-MTR-001
**Group:** C — Observability
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Metrics Service collects, aggregates, and stores numeric measurements of
system performance. It provides the raw data from which performance reports,
latency benchmarks, and operational dashboards are built.

**Metric Types:**
- COUNTER: monotonically increasing count (cycle count, trade count, error count).
- GAUGE: point-in-time measurement (memory usage, active position count).
- HISTOGRAM: distribution of measurements (latency percentiles, P&L distribution).
- TIMER: duration measurements with automatic statistical aggregation.

**Built-in Metrics (infrastructure-level):**
`
iios.cycle.count                    COUNTER  — total cycles executed
iios.cycle.latency_ms               HISTOGRAM — cycle latency distribution
iios.layer.{name}.latency_ms        HISTOGRAM — per-layer latency
iios.feed.{name}.fetch_latency_ms   HISTOGRAM — feed fetch latency
iios.feed.{name}.error_count        COUNTER  — feed error count
iios.decision.approved_count        COUNTER  — approved trade decisions
iios.decision.rejected_count        COUNTER  — rejected trade decisions
iios.trade.executed_count           COUNTER  — executed trades
iios.trade.pnl                      GAUGE    — current session P&L
iios.eventbus.queue_depth           GAUGE    — EventBus queue depth
iios.cache.hit_rate                 GAUGE    — cache hit rate
iios.db.write_latency_ms            HISTOGRAM — database write latency
iios.memory.usage_mb                GAUGE    — process memory usage
`

**Storage:**
Metrics are written to SQLite in 1-minute aggregated buckets.
Raw metric points are retained for 24 hours. Aggregated points for 90 days.

**Export:**
The Streamlit dashboard reads metrics from SQLite via the Metrics Service API.
Prometheus export format is supported for future external monitoring integration.

---

## 2.14 Tracing Service (INFRA-TRC-001)

**Code:** INFRA-TRC-001
**Group:** C — Observability
**Classification:** OPTIONAL
**Wave:** W8

**Purpose:**
The Tracing Service provides distributed-style trace correlation for all
operations within a trading cycle. It enables complete end-to-end timing
analysis of the 17-layer pipeline.

**Trace Model:**
- Each trading cycle has a unique 	race_id (UUID from the UUID Service).
- Each layer execution within the cycle produces a span.
- Each span records: start_time, end_time, layer_name, status, ttributes.
- Spans are nested (a layer span may have child spans for sub-operations).

**Trace Record:**
`
TraceRecord {
  trace_id: UUID
  cycle_id: UUID
  spans: List[Span] {
    span_id: UUID
    parent_span_id: Optional[UUID]
    layer: str
    operation: str
    start_us: int
    duration_us: int
    status: PASS | WARN | FAIL
    attributes: Dict[str, Any]
  }
  total_duration_us: int
  status: PASS | WARN | FAIL
}
`

**Trace Storage:**
Traces are written to SQLite with a 24-hour retention window for real-time
diagnostics. Aggregated trace statistics (P50, P95, P99 per layer) are retained
for 90 days.

**Integration:**
The SystemMonitor's 	ime_layer() context manager automatically creates
spans in the current trace. No additional instrumentation is required.

---

## 2.15 Audit Service (INFRA-AUD-001)

**Code:** INFRA-AUD-001
**Group:** C — Observability
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Audit Service provides an immutable, append-only record of all
business-significant events in the IIOS system. It serves the regulatory,
compliance, and operational audit requirements.

**Audit Events (auto-generated, not manually logged):**
- SYSTEM_STARTED: system startup with configuration snapshot.
- SYSTEM_STOPPED: system shutdown with reason and duration.
- KILL_SWITCH_TRIGGERED: VIX or daily loss threshold exceeded.
- KILL_SWITCH_RESET: operator manual reset of kill switch.
- TRADE_APPROVED: DecisionEngine approved a trade (includes all agent scores).
- TRADE_REJECTED: DecisionEngine rejected a trade (includes rejection reason).
- TRADE_EXECUTED: Order sent to broker (paper or live).
- STRATEGY_DISABLED: strategy auto-disabled due to poor performance.
- STRATEGY_PROMOTED: strategy promoted from research to production.
- FEED_FAILOVER: data feed switched from primary to fallback.
- CONFIG_SNAPSHOT_CREATED: configuration values frozen at startup.
- OPERATOR_COMMAND: any Telegram command received and executed.

**Immutability:**
Audit records are written with an append-only SQLite pattern:
- The audit table has no UPDATE or DELETE operations.
- The audit table has a UNIQUE constraint on event_id.
- Audit records include a SHA-256 hash of their content for tampering detection.

**Audit Record Format:**
`
AuditRecord {
  event_id: UUID (from UUID Service)
  event_type: str
  timestamp: ISO8601 with microseconds
  actor: str (component name or operator ID)
  entity: str (trade ID, strategy name, etc.)
  data: JSON (event-specific payload)
  content_hash: SHA256 (of event_id + event_type + timestamp + data)
}
`

---

*End of Part II Sections 2.1–2.15*

## 2.16 Identity Service (INFRA-IDN-001)

**Code:** INFRA-IDN-001
**Group:** D — Security
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Identity Service defines and manages the identities that interact with IIOS:
operators (humans using Telegram), automated processes (scheduled tasks), and
external systems (broker API). It is the foundation of authentication and
authorization.

**Identity Types:**
- OPERATOR_HUMAN: a human operator using the Telegram bot interface.
- OPERATOR_API: a script or tool using the internal REST API (future).
- SCHEDULED_TASK: an automated task triggered by the Scheduler Service.
- EXTERNAL_SYSTEM: the Dhan broker API (authenticated by API token).
- INTERNAL_SERVICE: an IIOS service making inter-service calls.

**Identity Records:**
Each identity has:
- identity_id: unique UUID.
- identity_type: enum from above.
- display_name: human-readable name for audit logs.
- created_at: when the identity was registered.
- is_active: can be deactivated without deletion.
- permissions: set of permission codes granted.

**Operator Identity Registration:**
Telegram operators are identified by their Telegram chat_id.
The whitelist of authorized chat IDs is loaded from environment variables
at startup. Any Telegram message from an unrecognized chat_id is:
1. Silently ignored (no response).
2. Logged as a SECURITY_UNAUTHORIZED_ACCESS audit event.
3. Counted in the security metrics counter.

---

## 2.17 Authentication Service (INFRA-ATH-001)

**Code:** INFRA-ATH-001
**Group:** D — Security
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Authentication Service verifies that an incoming request comes from
who it claims to come from. It validates credentials before any authorized
action is taken.

**Authentication Methods:**

| Channel | Method | Validation |
|---------|--------|------------|
| Telegram commands | chat_id whitelist | Identity Service lookup |
| Dhan API calls | Bearer token | DhanFeed's own auth headers |
| yfinance calls | None (public API) | Rate limit monitoring only |
| Internal service calls | Service identity token | DI container verification |

**Authentication Failures:**
Every authentication failure is:
1. Logged as an AUTHENTICATION_FAILED audit event.
2. Counted in the iios.security.auth_failure_count metric.
3. If threshold exceeded (5 failures in 60 seconds): alert to operators.

**Token Validation:**
The Dhan API access token is validated at startup by the Authentication Service:
- Token format validation (expected format from Dhan documentation).
- Token expiry check (if expiry is embedded in token).
- Live validation: a test API call to Dhan's account info endpoint.
If validation fails: WARN log + fall back to yfinance immediately.

---

## 2.18 Authorization Service (INFRA-AZN-001)

**Code:** INFRA-AZN-001
**Group:** D — Security
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Authorization Service determines what an authenticated identity is
permitted to do. Authentication establishes WHO you are; authorization
establishes WHAT you may do.

**Permission Model:**
IIOS uses a role-based permission model with exactly four roles:

| Role | Permissions | Who Has It |
|------|-------------|------------|
| VIEWER | Read-only: /status, /health, /pnl, /positions | All authorized operators |
| OPERATOR | Read + control: /shutdown, /resume, /safe | Senior operators only |
| ADMIN | All + config override | Lead operator only |
| SYSTEM | All internal service calls | Internal services only |

**Permission Enforcement:**
Every Telegram command is annotated with its required permission:
`
/status    -> VIEWER
/health    -> VIEWER
/pnl       -> VIEWER
/positions -> VIEWER
/perf      -> VIEWER
/learn     -> VIEWER
/strategies -> VIEWER
/regime    -> VIEWER
/diag      -> VIEWER
/shutdown  -> OPERATOR
/resume    -> OPERATOR
/safe      -> OPERATOR
/alerts    -> VIEWER
`

Authorization failures are logged and alert the security metric counter.

---

## 2.19 Secrets Service (INFRA-SEC-001)

**Code:** INFRA-SEC-001
**Group:** D — Security
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Secrets Service is the only component in IIOS that reads secrets from
environment variables or encrypted secret stores. No other component reads
os.environ for secret values directly.

**Managed Secrets:**
- DHAN_ACCESS_TOKEN: Dhan broker API access token.
- DHAN_CLIENT_ID: Dhan client identifier.
- TELEGRAM_BOT_TOKEN: Telegram Bot API token.
- TELEGRAM_AUTHORIZED_CHAT_IDS: comma-separated list of authorized operator chat IDs.

**Secret Access Pattern:**
`
secrets = get_secrets_service()
dhan_token = secrets.get('DHAN_ACCESS_TOKEN')  # raises SecretNotFoundError if absent
`

**Secret Validation:**
- At startup, the Secrets Service validates that all REQUIRED secrets are present.
- Missing required secrets abort startup with SecretsValidationError.
- Secrets are validated for format (not correctness — format only).
- Secrets are never logged, never included in diagnostic reports, never exposed
  in Telegram responses.

**Secret Rotation:**
When secrets change (e.g., new Dhan token after daily refresh):
- Secrets Service provides a eload() method for hot-reload of token.
- The Startup Manager calls eload() on each daily restart.
- After reload, the Authentication Service re-validates the new token.

---

## 2.20 Encryption Service (INFRA-ENC-001)

**Code:** INFRA-ENC-001
**Group:** D — Security
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Encryption Service provides all cryptographic operations for IIOS.
No other component implements its own cryptographic functions.

**Operations Provided:**
- hash(data: str, algorithm: str) -> str: SHA-256 by default.
- hmac_sign(data: str, key: str) -> str: HMAC-SHA256 for message integrity.
- erify_hash(data: str, expected_hash: str) -> bool: constant-time comparison.
- generate_checksum(file_path: Path) -> str: file integrity checksum.
- erify_checksum(file_path: Path, expected: str) -> bool: file integrity check.

**Use Cases in IIOS:**
- Audit record integrity: each audit record is hashed for tamper detection.
- Protected module checksum verification: uild_manifest.json checksums
  are verified by the Encryption Service at startup.
- Dhan API request signing (if required by Dhan API v2+).

**Security Principles:**
- No cryptographic operations use MD5 or SHA-1 (deprecated).
- All hashing uses SHA-256 or stronger.
- Key material is never logged.
- The Encryption Service itself uses hashlib and hmac from the Python standard library only.

---

## 2.21 Certificate Service (INFRA-CRT-001)

**Code:** INFRA-CRT-001
**Group:** D — Security
**Classification:** OPTIONAL
**Wave:** W8

**Purpose:**
The Certificate Service manages TLS certificate verification for outbound
HTTPS connections. It ensures the system connects only to authenticated
external endpoints.

**Responsibilities:**
- Verify TLS certificates for all outbound connections (Dhan API, Telegram API).
- Reject connections to endpoints with invalid or expired certificates.
- Log certificate validation failures as security events.
- Provide certificate pinning for critical endpoints (optional hardening).

**Default Configuration:**
- TLS verification is ENABLED by default. It may not be disabled in PRODUCTION.
- Certificate pinning is OPTIONAL and disabled by default.
- Minimum TLS version: TLS 1.2.

---

## 2.22 Clock Service (INFRA-CLK-001)

**Code:** INFRA-CLK-001
**Group:** E — Platform
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Clock Service is the single source of time for all IIOS components.
No component calls datetime.datetime.now() or 	ime.time() directly.
All time-sensitive decisions go through the Clock Service.

**Why This Matters:**
In production, the Clock Service returns real wall-clock time. In tests,
the Clock Service is replaced with a controllable fake clock. This makes
all time-dependent tests deterministic: a test can simulate market open,
close, pre-market, and weekend states without waiting for actual time to pass.

**Operations:**
`
ClockService.now() -> datetime            # current UTC datetime
ClockService.now_ist() -> datetime        # current IST datetime (UTC+5:30)
ClockService.today() -> date              # current date
ClockService.is_market_open() -> bool     # is NSE currently open (09:15–15:30 IST weekday)
ClockService.is_pre_market() -> bool      # is current time in pre-market window
ClockService.market_open_time() -> time   # 09:15 IST
ClockService.market_close_time() -> time  # 15:30 IST
ClockService.seconds_to_market_open() -> float   # seconds until next open
ClockService.seconds_to_market_close() -> float  # seconds until close today
ClockService.is_nse_holiday(date) -> bool # NSE holiday calendar check
`

**NSE Calendar:**
The Clock Service maintains a list of NSE trading holidays. The list is
loaded from a static file (data/nse_calendar.json) at startup.
This file must be updated annually.

---

## 2.23 Scheduler Service (INFRA-SCH-001)

**Code:** INFRA-SCH-001
**Group:** E — Platform
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Scheduler Service manages all time-based task execution in IIOS.
It replaces ad-hoc 	ime.sleep() loops and external cron jobs.
All scheduled tasks are registered, monitored, and recoverable.

**Task Types:**
- CRON: runs at a specified cron expression.
- INTERVAL: runs at a fixed interval (every N seconds).
- ONCE: runs once at a specified future time.
- MARKET_OPEN: runs when market opens (via Clock Service detection).
- MARKET_CLOSE: runs when market closes.
- PRE_MARKET: runs at pre-market time (configurable, default 08:00 IST).

**Built-in Scheduled Tasks:**
`
08:00 IST  PRE_MARKET   Startup Manager pre-market initialization
09:15 IST  MARKET_OPEN  Market open signal, enable trading
09:15 IST  MARKET_OPEN  GlobalDataAI fresh fetch
09:30 IST  CRON         First full trading cycle
INTERVAL   30s          Continuous market scan (MarketMonitor)
INTERVAL   5min         GlobalDataAI cache refresh
INTERVAL   30min        Deep scan cycle (6 slots)
15:30 IST  MARKET_CLOSE Market close signal, disable new orders
15:31 IST  MARKET_CLOSE EOD learning cycle
15:45 IST  CRON         EOD report generation
15:50 IST  CRON         Performance tracker persistence
`

**Task Recovery:**
If a scheduled task fails, the Scheduler Service:
1. Logs the failure with full stack trace.
2. Increments the task failure counter.
3. Applies the task's retry policy (default: 3 retries with 30s backoff).
4. If all retries exhausted: publishes TASK_FAILED event to EventBus.
5. Does NOT retry indefinitely (avoids task pile-up).

---

## 2.24 Timer Service (INFRA-TMR-001)

**Code:** INFRA-TMR-001
**Group:** E — Platform
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Timer Service provides high-precision timing for all latency measurements
in IIOS. It is the backend for the SystemMonitor's 	ime_layer() context manager.

**Timer Operations:**
`
TimerService.start(name: str) -> TimerHandle
TimerService.stop(handle: TimerHandle) -> float  # duration in milliseconds
TimerService.measure(name: str) -> contextmanager  # context manager pattern
TimerService.get_stats(name: str) -> TimerStats  # P50/P95/P99 + count
`

**Precision:**
The Timer Service uses 	ime.perf_counter() (not 	ime.time()) for
sub-millisecond precision. This is critical for the 17ms GlobalIntelligence
and 19ms MarketIntelligence latency targets.

**Timer Stats Aggregation:**
The Timer Service maintains a rolling window of the last 100 measurements
per named timer. It computes P50, P95, and P99 latency on demand.

**Integration with Metrics Service:**
Timer measurements are automatically reported to the Metrics Service.
No manual metrics recording is required for timed operations.

---

## 2.25 UUID Service (INFRA-UUID-001)

**Code:** INFRA-UUID-001
**Group:** E — Platform
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The UUID Service generates all unique identifiers used in IIOS: cycle IDs,
trace IDs, audit record IDs, trade IDs, strategy IDs, and entity IDs.

**Why Centralized:**
Centralizing UUID generation enables:
- UUID format validation before use.
- Sequence tracking for debugging (UUIDs include a generation count in development).
- Fake UUID sequences in tests (deterministic IDs for reproducible tests).
- Future transition to distributed-safe IDs (ULIDs) without changing consumers.

**UUID Types:**
- CYCLE_ID: identifies a trading cycle. Format: UUID v4.
- TRADE_ID: identifies a trade decision and execution. Format: UUID v4.
- AUDIT_ID: identifies an audit record. Format: UUID v4.
- ENTITY_ID: identifies a knowledge entity. Format: UUID v4.
- TRACE_ID: identifies an execution trace. Format: UUID v4.

**Operations:**
`
UUIDService.generate() -> UUID           # generic UUID v4
UUIDService.generate_cycle_id() -> UUID  # prefixed cycle UUID
UUIDService.generate_trade_id() -> UUID  # prefixed trade UUID
UUIDService.validate(value: str) -> bool # format validation
`

---

## 2.26 File Service (INFRA-FIL-001)

**Code:** INFRA-FIL-001
**Group:** E — Platform
**Classification:** CORE
**Wave:** W2

**Purpose:**
The File Service abstracts all filesystem operations, providing a consistent
interface across Windows (development) and Linux (Docker production).

**Operations:**
- Read and write text and binary files.
- List directory contents.
- Create directories (with parents=True semantics).
- Atomic file writes (write to temp, rename to final — prevents partial writes).
- File existence checks.
- File size and modification time queries.

**Atomic Write Guarantee:**
All write operations through the File Service are atomic:
1. Write to {path}.tmp.
2. Rename {path}.tmp to {path}.
Rename operations are atomic on Linux. On Windows, an intermediate deletion
step is used. This prevents the paper trades CSV or SQLite WAL from being
corrupted by a mid-write crash.

**Path Normalization:**
The File Service normalizes all paths to forward slashes internally, regardless
of operating system. Path separators in the output use the OS convention.

**Integration with Storage Service:**
The File Service handles raw file I/O. The Storage Service builds on it
for structured data persistence.

---

## 2.27 Resource Service (INFRA-RSR-001)

**Code:** INFRA-RSR-001
**Group:** E — Platform
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Resource Service monitors and manages system resource consumption:
CPU, memory, disk, and file handles. It enforces resource budgets per
component and triggers degradation when budgets are exceeded.

**Resource Monitoring:**
`
ResourceService.get_memory_mb() -> float     # current process memory usage
ResourceService.get_cpu_percent() -> float   # current CPU usage (1s average)
ResourceService.get_disk_free_gb() -> float  # free disk on data volume
ResourceService.get_open_files() -> int      # count of open file handles
ResourceService.check_resource_budget() -> ResourceBudgetStatus
`

**Resource Budgets (from config.py):**
- Memory: WARN at 400MB, CRIT at 768MB, KILL at 1GB.
- CPU: WARN at 80%, CRIT at 95%.
- Disk: WARN at 5GB free, CRIT at 1GB free.
- File handles: WARN at 500, CRIT at 900.

**Budget Enforcement:**
When a budget is exceeded:
- WARN: log warning, report to Monitoring Service.
- CRIT: log critical, report to Monitoring Service, alert operators.
- KILL (memory only): trigger graceful shutdown to prevent OOM kill.

---

## 2.28 Event Bus (INFRA-EVT-001)

**Code:** INFRA-EVT-001
**Group:** F — Communication
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Event Bus is the system-wide publish/subscribe messaging infrastructure.
It enables decoupled communication between IIOS layers without creating
upward import dependencies.

**Architecture:**
The IIOS Event Bus is an in-process, synchronous-dispatch-with-async-subscriber-option
bus. Publishers call publish() without waiting for subscriber completion.
Subscribers are called in separate threads from a subscriber thread pool.

**Operations:**
`
EventBus.publish(event: IIOSEvent) -> None     # non-blocking
EventBus.subscribe(event_type: str, handler: Callable) -> SubscriptionId
EventBus.unsubscribe(subscription_id: SubscriptionId) -> None
EventBus.get_queue_depth() -> int              # monitoring integration
`

**Critical Events:**
| Event Type | Published By | Subscribed By |
|------------|-------------|---------------|
| SYSTEM_STARTED | Lifecycle Manager | Telegram Bot, Dashboard |
| SYSTEM_STOPPED | Lifecycle Manager | All components |
| KILL_SWITCH_TRIGGERED | RiskGuardian | OrderManager, Telegram Bot |
| KILL_SWITCH_RESET | Operator command | OrderManager |
| TRADE_APPROVED | DecisionEngine | OrderManager, LearningEngine |
| TRADE_REJECTED | DecisionEngine | LearningEngine |
| TRADE_EXECUTED | OrderManager | TradeMonitor, LearningEngine |
| STRATEGY_DISABLED | StrategyPerformanceTracker | Telegram Bot |
| COMPONENT_REGISTERED | Component Registry | SystemMonitor, Health Service |
| FEED_FAILOVER | DataFeedManager | Telegram Bot, Monitoring |

**Delivery Guarantee:**
The Event Bus provides at-least-once delivery within the process. If a subscriber
raises an exception, the Event Bus logs the error and continues delivering to
remaining subscribers. Failed events are logged with full context.

**Scalability Path:**
The Event Bus interface supports future replacement with Redis Pub/Sub or
similar. The publish() and subscribe() signatures are the stable interface.

---

## 2.29 Message Bus (INFRA-MSG-001)

**Code:** INFRA-MSG-001
**Group:** F — Communication
**Classification:** OPTIONAL
**Wave:** W8

**Purpose:**
The Message Bus provides point-to-point request/reply messaging between
specific service pairs, complementing the Event Bus (which is broadcast).
It is used for direct service queries where a response is expected.

**Patterns Supported:**
- Request/Reply: synchronous request with response. Used for health checks.
- Fire-and-Forget: send without waiting. Backed by Event Bus.
- Task Queue: distribute work items to a pool of workers. Future Wave 15+.

**Primary Use Case:**
The Diagnostics Service uses the Message Bus to query each infrastructure
service for its current state. Each service registers a handler for
DIAGNOSTIC_REQUEST messages and responds with its diagnostic data.

---

## 2.30 Notification Service (INFRA-NTF-001)

**Code:** INFRA-NTF-001
**Group:** F — Communication
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Notification Service routes outbound operator notifications through
registered notification channels. It handles formatting, rate limiting,
and delivery confirmation.

**Notification Channels:**
- TELEGRAM: primary operator notification channel (current implementation).
- EMAIL: optional future channel (declared but not implemented in Wave 2).
- WEBHOOK: optional future channel for external integrations.

**Notification Priority:**
- INFO: informational. Telegram: sent if not rate-limited.
- WARN: degraded state. Telegram: always sent.
- ALERT: component failure. Telegram: always sent, retry on failure.
- CRITICAL: system failure. Telegram: sent immediately, bypass rate limit.

**Rate Limiting:**
The Notification Service enforces the Telegram Bot API rate limit (30 messages/second
per bot). INFO notifications are queued and batched if rate limit is approached.
CRITICAL notifications bypass all rate limiting.

**Notification Formatter:**
The Notification Service uses a formatter that converts system events to
human-readable Telegram messages. Formatters are registered per event type.
Default formatters for all Critical Events are included in Wave 2.

---

## 2.31 Cache Service (INFRA-CAC-001)

**Code:** INFRA-CAC-001
**Group:** F — Communication
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Cache Service provides in-memory caching with TTL for all IIOS components
that need to cache expensive computations or external data fetches.

**Cache Strategies:**
- TTL: items expire after a fixed time-to-live. Used for market data.
- LRU: least-recently-used eviction. Used for strategy score caches.
- WRITE_THROUGH: writes go to both cache and backing store.
- CACHE_ASIDE: component manages its own cache population.

**Built-in Cache Namespaces:**
`
iios.global_data          TTL=300s  (5-minute GlobalDataAI cache)
iios.market_intelligence  TTL=60s   (1-minute regime cache)
iios.feed.quotes          TTL=10s   (live quote cache)
iios.feed.history         TTL=3600s (1-hour historical data cache)
iios.strategy.scores      LRU=100   (last 100 strategy scores)
`

**Cache Invalidation:**
The Cache Service supports explicit invalidation by key and by namespace.
Namespace invalidation clears all items in a namespace simultaneously.
The FEED_FAILOVER event triggers invalidation of feed caches.

**Scalability Path:**
The Cache Service interface supports future backing with Redis without
changing any consumer code. The implementation is swappable behind
the get_cache_service() factory function.

---

## 2.32 Storage Service (INFRA-STG-001)

**Code:** INFRA-STG-001
**Group:** F — Communication
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Storage Service provides structured persistent storage for all IIOS
components. It abstracts the SQLite backend and manages the connection
pool, schema migrations, and query execution.

**Storage Domains:**
`
Domain              Table Prefix    Purpose
system              sys_            System state, health records
telemetry           tel_            Cycle telemetry, layer timings
trading             trd_            Trade decisions, executions
learning            lrn_            Performance metrics, win rates
strategies          str_            Strategy registry, status
audit               aud_            Immutable audit log
metrics             mtr_            Aggregated metrics history
traces              trc_            Execution trace data
knowledge           knw_            Knowledge items
events              evt_            Domain event log
`

**Schema Migration:**
The Storage Service manages schema migrations through versioned SQL scripts
in infrastructure/database/schema/. Migrations are applied in version order
at startup. Already-applied migrations are skipped (tracked in sys_migrations).

**Transaction Guarantees:**
All write operations through the Storage Service are wrapped in transactions.
Multi-step operations (write decision + write audit record) are atomic.

**SQLite Optimizations:**
`
PRAGMA journal_mode=WAL      # write-ahead logging for concurrent readers
PRAGMA synchronous=NORMAL    # balance between safety and write speed
PRAGMA cache_size=-64000     # 64MB page cache
PRAGMA temp_store=MEMORY     # temp tables in memory
PRAGMA busy_timeout=5000     # wait up to 5s on busy
`

---

## 2.33 Plugin Service (INFRA-PLG-001)

**Code:** INFRA-PLG-001
**Group:** G — Operations
**Classification:** OPTIONAL
**Wave:** W8

**Purpose:**
The Plugin Service discovers, loads, and manages optional plugins that extend
IIOS capability without modifying core packages.

**Plugin Discovery:**
Plugins are discovered by scanning the iios/plugins/ directory at startup.
Each plugin directory contains a __manifest__.json declaring:
- Plugin type (DATA_PLUGIN, STRATEGY_PLUGIN, etc.).
- Required interface (which base class the plugin implements).
- Minimum IIOS version required.
- Plugin version and dependencies.

**Plugin Loading:**
1. Discovery: scan iios/plugins/ for manifests.
2. Validation: verify manifest schema and interface declaration.
3. Import: import the plugin module.
4. Registration: register with Component Registry.
5. Activation: call plugin's ctivate() method.
6. Verification: verify plugin responds to health check.

**Plugin Failure Isolation:**
A plugin that fails to load does NOT block system startup.
A plugin that raises an exception at runtime is disabled and the failure
is logged and reported. Core system operation continues without it.

---

## 2.34 Extension Service (INFRA-EXT-001)

**Code:** INFRA-EXT-001
**Group:** G — Operations
**Classification:** OPTIONAL
**Wave:** W8

**Purpose:**
The Extension Service manages extension points: defined hooks in core
components that external code can attach to without modifying core.

**Extension Point Types:**
- PRE_CYCLE_HOOK: runs before each trading cycle begins.
- POST_CYCLE_HOOK: runs after each trading cycle completes.
- PRE_DECISION_HOOK: runs before the DecisionEngine makes a decision.
- POST_TRADE_HOOK: runs after a trade is executed.
- PRE_SHUTDOWN_HOOK: runs before system shutdown begins.

**Extension Registration:**
`
ExtensionService.register(hook_type: HookType, handler: Callable) -> ExtensionId
ExtensionService.unregister(extension_id: ExtensionId) -> None
`

**Extension Isolation:**
Extension hook handlers run in isolated exception contexts. An extension
that raises an exception does not affect the core operation it is attached to.

---

## 2.35 Recovery Service (INFRA-RCV-001)

**Code:** INFRA-RCV-001
**Group:** G — Operations
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Recovery Service manages recovery from abnormal termination. When IIOS
restarts after a crash or SIGKILL, the Recovery Service identifies and
recovers any incomplete state.

**Recovery Scenarios:**
1. **Mid-cycle crash:** cycle was in progress when process died.
   Recovery: mark cycle as INCOMPLETE, log recovery event.
   Action: no trades are re-attempted. Cycle state is preserved for analysis.

2. **Paper trades CSV incomplete:** crash during CSV write.
   Recovery: verify CSV integrity, recover from SQLite shadow copy.
   Action: reconcile paper_trades.csv with trd_executions table.

3. **Learning state incomplete:** crash before flush.
   Recovery: replay trd_executions from last flush point.
   Action: recompute win rates and Sharpe ratios from recovered trades.

4. **Scheduler tasks lost:** scheduled tasks not persisted across restart.
   Recovery: reload schedule from configuration (stateless redesign).
   Action: re-register all scheduled tasks from config at startup.

**Recovery Audit:**
Every recovery action is recorded as a RECOVERY_EXECUTED audit event
with: recovery type, data recovered, data lost (if any).

---

## 2.36 Exception Service (INFRA-EXC-001)

**Code:** INFRA-EXC-001
**Group:** G — Operations
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Exception Service is the centralized exception handler and reporter.
Every unhandled exception in IIOS reaches the Exception Service, which
classifies it, logs it, and routes it to appropriate handlers.

**Exception Hierarchy:**
`
BaseIIOSException
  |-- InfrastructureException
  |   |-- ConfigurationMissingError
  |   |-- ConfigurationImmutableError
  |   |-- SecretsValidationError
  |   |-- DIContainerSecurityError
  |   |-- AgentCountViolationError
  |   |-- StorageException
  |   |-- FeedException
  |       |-- FeedTimeoutError
  |       |-- FeedUnreachableError
  |-- TradingException
  |   |-- KillSwitchError
  |   |-- OrderValidationError
  |   |-- PositionLimitError
  |-- SecurityException
  |   |-- AuthenticationFailedError
  |   |-- AuthorizationDeniedError
  |   |-- SecretsAccessError
  |-- ValidationException
      |-- LayerBoundaryViolationError
      |-- InterfaceContractError
      |-- PromotionGateViolationError
`

**Exception Handling Pipeline:**
1. Exception caught by component.
2. Component calls ExceptionService.handle(exc, context).
3. Exception Service classifies the exception.
4. Exception Service logs the exception with full context.
5. Exception Service determines routing:
   - INFRASTRUCTURE: alert operator, attempt recovery.
   - TRADING: log, skip current cycle, continue system.
   - SECURITY: log, alert operator, possibly halt system.
6. Exception Service publishes EXCEPTION_OCCURRED event to EventBus.

---

## 2.37 Retry Service (INFRA-RTY-001)

**Code:** INFRA-RTY-001
**Group:** G — Operations
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Retry Service provides configurable retry policies for operations that
may fail transiently. It is the standard implementation for all retry logic
in IIOS.

**Built-in Retry Policies:**
`
POLICY_DATA_FEED:
  max_attempts: 3
  backoff: EXPONENTIAL(base=2s, max=30s)
  retry_on: [FeedTimeoutError, FeedUnreachableError]
  fail_fast_on: [AuthenticationFailedError]

POLICY_DATABASE:
  max_attempts: 3
  backoff: FIXED(1s)
  retry_on: [StorageTimeoutError, LockTimeoutError]

POLICY_TELEGRAM:
  max_attempts: 5
  backoff: EXPONENTIAL(base=1s, max=60s)
  retry_on: [TelegramRateLimitError, TelegramNetworkError]

POLICY_BROKER_API:
  max_attempts: 2
  backoff: FIXED(5s)
  retry_on: [BrokerTimeoutError]
  fail_fast_on: [AuthenticationFailedError, InsufficientFundsError]
`

**Retry Context:**
Every retry attempt is logged with: operation name, attempt number, exception type.
After all attempts exhausted: final exception is propagated with retry history attached.

---

## 2.38 Circuit Breaker (INFRA-CIB-001)

**Code:** INFRA-CIB-001
**Group:** G — Operations
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Circuit Breaker prevents cascading failures by isolating failing external
dependencies. When a dependency fails repeatedly, the circuit opens and all
calls fail fast until the circuit resets.

**Circuit States:**
- CLOSED: normal operation. Calls pass through.
- OPEN: dependency is failing. All calls fail immediately without attempting.
- HALF_OPEN: testing recovery. One call allowed through to test recovery.

**Circuit Breaker Instances:**
`
CB_DHAN_API:
  failure_threshold: 5 failures in 60s
  reset_timeout: 120s
  half_open_test_interval: 30s

CB_YFINANCE:
  failure_threshold: 5 failures in 60s
  reset_timeout: 180s

CB_TELEGRAM:
  failure_threshold: 10 failures in 60s
  reset_timeout: 60s

CB_DATABASE:
  failure_threshold: 3 failures in 10s
  reset_timeout: 30s
`

**Feed Circuit Interaction:**
When CB_DHAN_API opens, the DataFeedManager switches to yfinance automatically.
When CB_DHAN_API moves to HALF_OPEN and successfully tests, it switches
back to Dhan as the primary source. This is the automatic feed failover behavior.

---

## 2.39 Feature Flag Service (INFRA-FFG-001)

**Code:** INFRA-FFG-001
**Group:** G — Operations
**Classification:** OPTIONAL
**Wave:** W8

**Purpose:**
The Feature Flag Service enables runtime toggling of system features without
code deployment. It allows gradual rollout, A/B testing, and emergency
disabling of specific features.

**Feature Flag Types:**
- BOOLEAN: feature is ON or OFF. Most feature flags are this type.
- PERCENTAGE: feature is ON for a percentage of requests (A/B testing).
- SCHEDULE: feature is ON during a defined time window.

**Built-in Feature Flags:**
`
FEATURE_ML_REGIME_CLASSIFIER      BOOLEAN  default: False  (Wave 20)
FEATURE_MULTI_EXCHANGE             BOOLEAN  default: False  (Wave 20)
FEATURE_LIVE_TRADING               BOOLEAN  default: False  (requires PAPER_TRADING=False)
FEATURE_OPTIONS_TRADING            BOOLEAN  default: True
FEATURE_ARBITRAGE_SCANNER          BOOLEAN  default: True
FEATURE_TELEGRAM_NOTIFICATIONS     BOOLEAN  default: True
FEATURE_STREAMLIT_DASHBOARD        BOOLEAN  default: True
FEATURE_DISTRIBUTED_EVENTBUS       BOOLEAN  default: False  (Wave 20)
`

**Emergency Override:**
Feature flags can be toggled via the Telegram /safe command (OPERATOR role)
without system restart. This enables emergency disable of problematic features
during market hours.

---

## 2.40 Version Service (INFRA-VER-001)

**Code:** INFRA-VER-001
**Group:** G — Operations
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Version Service maintains and exposes version information for all IIOS
packages, services, and interfaces. It enables compatibility checking at startup.

**Version Information:**
- System version: from uild_manifest.json.
- Package versions: from each package's __manifest__.json.
- Interface versions: declared in each package's __init__.py.
- Configuration schema version: from config.py.

**Compatibility Checking:**
At startup, the Version Service verifies:
- All packages declare compatible interface versions.
- The configuration schema version matches the Configuration Service.
- Protected module checksums match the last certified state.

---

## 2.41 Migration Service (INFRA-MIG-001)

**Code:** INFRA-MIG-001
**Group:** G — Operations
**Classification:** CORE
**Wave:** W2

**Purpose:**
The Migration Service manages database schema migrations and data migrations.
It ensures the SQLite schema is always at the correct version for the current
system version.

**Migration Execution:**
1. At startup, compare current schema version to required version.
2. If required > current: run pending migrations in order.
3. Verify data integrity after each migration.
4. Record migration completion in sys_migrations table.
5. Never run a migration on a database that has been marked LOCKED.

**Migration Safety:**
- Every migration runs inside a SQLite transaction.
- If migration fails: transaction rollback, system aborts startup.
- Backup recommendation: the Migration Service logs a backup reminder before
  any migration that modifies existing tables.

---

## 2.42 Compatibility Service (INFRA-CPT-001)

**Code:** INFRA-CPT-001
**Group:** G — Operations
**Classification:** OPTIONAL
**Wave:** W8

**Purpose:**
The Compatibility Service verifies that all IIOS components are mutually
compatible. It runs during startup and as part of the certification process.

**Compatibility Checks:**
- Python version compatibility (required: 3.10+).
- All declared dependencies meet minimum version requirements.
- Interface contract compatibility (signature hashes match).
- Configuration schema version compatibility.
- Data schema version compatibility (database schema version matches code).

---

## 2.43 Configuration Validation Service (INFRA-CVL-001)

**Code:** INFRA-CVL-001
**Group:** G — Operations
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Configuration Validation Service validates all configuration values
before the Configuration Service produces its immutable snapshot.
It is the final gate before configuration is considered valid.

**Validation Rules Applied:**
- Type validation for each configured value.
- Range validation (numeric bounds).
- Cross-field consistency: WARN_MS < CRIT_MS, WIN_RATE in [0,1].
- Required field presence.
- Kill switch threshold sanity: VIX threshold must be > 25 and < 100.
- Decision threshold sanity: must be > 0 and <= 10.
- Promotion criteria sanity: all three criteria in valid ranges.

**Validation Failure Behavior:**
Any validation failure at CRITICAL severity blocks startup.
Validation failures at WARNING severity produce a log warning but do not block.

---

## 2.44 Infrastructure Validation Service (INFRA-IVL-001)

**Code:** INFRA-IVL-001
**Group:** G — Operations
**Classification:** CRITICAL
**Wave:** W2

**Purpose:**
The Infrastructure Validation Service verifies that the running infrastructure
meets all requirements before the system is allowed to start trading.
It is the infrastructure equivalent of the architectural invariants test.

**Validation Checks:**
- All CRITICAL services are in ACTIVE state.
- Data directory exists and is writable.
- SQLite database is accessible and schema is current.
- Data feed primary or fallback is reachable.
- Secrets are present and valid format.
- Log directory exists and is writable.
- Exactly 5 debate agents registered.
- All kill-switch thresholds match config.py values.

**Validation Result:**
If any CRITICAL check fails: system halts with InfrastructureValidationError.
All failed checks are reported together (not one-at-a-time).

---

## 2.45 Engineering Validation Service (INFRA-EVL-001)

**Code:** INFRA-EVL-001
**Group:** G — Operations
**Classification:** OPTIONAL
**Wave:** W8

**Purpose:**
The Engineering Validation Service verifies that the deployed code meets
the architectural specification. It runs the architectural invariants tests
that are also run in CI/CD.

**Validation Checks:**
- Import graph is acyclic (no circular imports).
- No upward layer dependencies detected.
- All protected module checksums match uild_manifest.json.
- All manifest files are valid.
- Interface signatures match their specifications.

**Invocation:**
The Engineering Validation Service runs at deployment time (not on every startup).
It is invoked by: python -m iios.infrastructure.engineering_validation --verify.

---

## 2.46 Certification Service (INFRA-CST-001)

**Code:** INFRA-CST-001
**Group:** G — Operations
**Classification:** OPTIONAL
**Wave:** W17

**Purpose:**
The Certification Service provides a runtime representation of the system's
certification status. It reads from uild_manifest.json and the certification
records in docs/certification/ and provides a unified certification view.

**Certification Queries:**
`
CertificationService.get_system_certification_level() -> CertificationLevel
CertificationService.get_package_certification(name) -> PackageCertification
CertificationService.is_production_authorized() -> bool
CertificationService.get_failed_certification_checks() -> List[str]
`

**Production Authorization:**
is_production_authorized() returns True only when:
- All CRITICAL and CORE packages are certified Level 4.
- All 10 production authorization checks pass.
- The Architecture Council certification record is present and valid.

---

*End of Part II*

# PART III — INFRASTRUCTURE ARCHITECTURE

## 3.0 Architecture Overview

Part III defines the complete internal architecture of each infrastructure service.
For every service, the following dimensions are specified:
- Purpose and primary responsibility.
- Interfaces (inputs and outputs).
- Internal components.
- Dependencies on other infrastructure services.
- Lifecycle (how the service starts, operates, and stops).
- Failure modes and recovery procedures.
- Scalability considerations.
- Performance targets.
- Security considerations.
- Monitoring integration.
- Operational notes.

Critical services receive full detailed treatment. Supplementary services
receive a structured summary. All specifications are complete.

---

## 3.1 Configuration Service Architecture

**Purpose:** Single source of truth for all configuration. Produces an immutable
snapshot consumed by all components.

**Interfaces:**
`
INPUT:
  - Environment variables (os.environ)
  - config.py module (import at load time)
  - Default values (hardcoded in service)

OUTPUT:
  - ConfigurationSnapshot (immutable frozen object)
  - get_snapshot() factory function
`

**Internal Components:**
- ConfigLoader: reads from all sources in priority order.
- ConfigValidator: applies all validation rules before snapshot creation.
- ConfigSnapshot: the immutable result object.
- ConfigRegistry: maps key names to types and validators.

**Dependencies:**
- No dependencies. This is a Level 0 service — it starts before anything else.

**Lifecycle:**
`
STARTUP:
  1. ConfigLoader reads environment variables.
  2. ConfigLoader reads config.py module.
  3. ConfigLoader applies defaults for unset values.
  4. ConfigValidator validates all values.
  5. If validation fails: raise ConfigurationValidationError (CRITICAL).
  6. ConfigSnapshot created and frozen.
  7. Service marked ACTIVE in Service Registry.

OPERATION:
  - get_snapshot() returns the same frozen snapshot on every call.
  - No mutation ever occurs.

SHUTDOWN:
  - No action required. Snapshot is garbage collected with process.
`

**Failure Modes:**
| Failure | Cause | Recovery |
|---------|-------|----------|
| ConfigurationMissingError | Required key absent, no default | ABORT: system cannot start |
| ConfigurationTypeError | Value wrong type | ABORT: system cannot start |
| ConfigurationRangeError | Value out of valid range | ABORT: system cannot start |
| ConfigurationImmutableError | Mutation attempt after freeze | RAISE: programming error |

**Scalability:**
The Configuration Service is a read-only singleton after initialization.
It scales without modification to any size. More packages consuming it
does not increase load.

**Performance Targets:**
- Initialization: < 50ms.
- get_snapshot(): < 0.1ms (returns reference to pre-created object).

**Security Considerations:**
- No secrets are loaded by the Configuration Service. Secrets are in Secrets Service.
- ConfigurationSnapshot is not serialized or logged (contains thresholds that are sensitive).

**Monitoring:**
- Service status reported to Service Registry.
- Configuration load event written to Audit Service.

---

## 3.2 Event Bus Architecture

**Purpose:** System-wide publish/subscribe messaging that enables decoupled communication
between all 17 IIOS layers and all infrastructure services.

**Interfaces:**
`
INPUT:
  - publish(event: IIOSEvent) -> None  (any component)
  - subscribe(type, handler) -> SubscriptionId  (any component)

OUTPUT:
  - Dispatched event objects to registered handlers.
  - Queue depth metric to Metrics Service.
  - Delivery failure events to Logging Service.
`

**Internal Components:**
- EventRegistry: maps event types to lists of subscriber handlers.
- EventDispatcher: routes published events to subscribers.
- SubscriberThreadPool: executes subscriber handlers asynchronously.
- EventQueue: bounded queue holding published but not-yet-dispatched events.
- DeadLetterQueue: stores events where all subscriber deliveries failed.

**Dependencies:**
- Logging Service (for delivery failure logging).
- Metrics Service (for queue depth reporting).
- Timer Service (for dispatch latency measurement).

**Lifecycle:**
`
STARTUP:
  1. EventRegistry initialized (empty).
  2. SubscriberThreadPool started (default: 4 threads).
  3. EventDispatcher started, begins draining EventQueue.
  4. Service marked ACTIVE.
  NOTE: EventBus is available for subscription registration from Phase 4 of
  infrastructure startup. Publishing is available from Phase 6.

OPERATION:
  - Publishers call publish() non-blocking.
  - EventQueue holds events if dispatcher thread is busy.
  - Dispatcher delivers to all subscribers in thread pool.
  - Failed deliveries go to DeadLetterQueue.

SHUTDOWN:
  1. Stop accepting new publishes (return immediately after queuing).
  2. Drain remaining events from EventQueue (max 5 seconds).
  3. Stop SubscriberThreadPool (wait for in-flight handlers to complete).
  4. Log summary: events delivered, events in DeadLetterQueue.
`

**Failure Modes:**
| Failure | Cause | Recovery |
|---------|-------|----------|
| Queue overflow | Publisher storm, consumers too slow | Drop oldest events, log warning |
| Subscriber exception | Bug in subscriber handler | Log + continue to next subscriber |
| Thread pool exhaustion | All threads busy | Events queue up, backpressure applied |
| DeadLetterQueue full | Sustained delivery failures | Log CRITICAL, alert operator |

**Scalability:**
The thread pool size is configurable (from config.py: EVENTBUS_THREAD_POOL_SIZE).
In the future, the EventBus implementation can be replaced with Redis Pub/Sub
for distributed deployment without changing any publisher or subscriber code.

**Performance Targets:**
- publish() call: < 0.1ms (non-blocking enqueue).
- Event dispatch to subscriber: < 1ms after dequeue.
- Queue depth in steady state: < 10 events.

**Security Considerations:**
- Event payloads containing sensitive data are redacted in the DeadLetterQueue log.
- No external system can publish events (events are internal only).

**Monitoring:**
- Queue depth reported to Metrics Service every 5 seconds.
- Delivery failure rate reported to Monitoring Service.
- DeadLetterQueue depth reported as a WARN metric.

---

## 3.3 Storage Service Architecture

**Purpose:** Provides all structured persistent storage, abstracting the SQLite
backend from all consumers.

**Interfaces:**
`
INPUT:
  - execute(sql: str, params: tuple) -> None        (write operations)
  - query(sql: str, params: tuple) -> List[Row]     (read operations)
  - execute_many(sql: str, rows: List[tuple]) -> None (bulk write)
  - in_transaction() -> contextmanager              (explicit transaction)

OUTPUT:
  - Query results as typed Row objects.
  - Transaction commit/rollback confirmation.
  - Write latency metrics to Timer Service.
`

**Internal Components:**
- ConnectionPool: manages a pool of SQLite connections.
- MigrationRunner: applies pending schema migrations at startup.
- QueryBuilder: (internal) parameter binding and SQL validation.
- TransactionManager: wraps operations in SQLite transactions.
- IntegrityChecker: verifies write results against expected outcomes.

**Dependencies:**
- Configuration Service (database path, pool size, WAL settings).
- File Service (database file creation and management).
- Logging Service (query failure logging).
- Metrics Service (write latency reporting).
- Timer Service (write latency measurement).

**Lifecycle:**
`
STARTUP:
  1. Verify data/ directory exists and is writable.
  2. Open SQLite connection with WAL mode enabled.
  3. Run MigrationRunner to apply pending migrations.
  4. Verify schema integrity (PRAGMA integrity_check).
  5. Initialize ConnectionPool (default: 5 connections).
  6. Service marked ACTIVE.

OPERATION:
  - All writes wrapped in transactions.
  - All queries use parameterized statements.
  - Connection pool checked out per operation, returned after.

SHUTDOWN:
  1. Wait for all in-flight transactions to complete (max 5 seconds).
  2. Flush WAL to main database file.
  3. Close all connections.
  4. Log shutdown summary: writes since startup.
`

**Failure Modes:**
| Failure | Cause | Recovery |
|---------|-------|----------|
| StorageTimeoutError | SQLite busy (locked) | Retry up to 3x with 1s backoff |
| IntegrityError | Constraint violation | Rollback, log error, re-raise |
| CorruptionError | Database file corrupted | Halt, alert operator, restore from backup |
| DiskFullError | Disk space exhausted | Halt, alert operator |

**Scalability:**
SQLite is the current implementation. The Storage Service interface supports
future PostgreSQL backend with no changes to consumer code.
The STORAGE_BACKEND feature flag (when True) switches to PostgreSQL.

**Performance Targets:**
- Single write latency p99: < 5ms.
- Single read latency p99: < 2ms.
- Bulk write (100 rows) latency p99: < 20ms.
- WAL checkpoint: < 100ms.

**Security Considerations:**
- All queries use parameterized statements. String concatenation for SQL is blocked.
- Database file permissions: 600 (owner read/write only).
- Connection credentials are managed by Secrets Service if future cloud DB is used.

**Monitoring:**
- Write latency histogram reported to Metrics Service.
- Database file size reported as gauge every 60 seconds.
- Failed query count reported as counter.

---

## 3.4 Logging Service Architecture

**Purpose:** Single structured logging output for all IIOS components.

**Interfaces:**
`
INPUT (from any component):
  - get_logger(component_name: str) -> Logger
  - Logger.debug(msg, **context) -> None
  - Logger.info(msg, **context) -> None
  - Logger.warning(msg, **context) -> None
  - Logger.error(msg, **context) -> None
  - Logger.critical(msg, **context) -> None

OUTPUT:
  - Rotating log files: logs/iios-YYYY-MM-DD.log
  - SQLite event log table (tel_log_events)
  - Stderr stream (ERROR and CRITICAL only)
`

**Internal Components:**
- LogRouter: routes log records to appropriate sinks.
- LogFormatter: formats records to the standard log format.
- SensitiveDataRedactor: redacts sensitive values from log records.
- RotatingFileHandler: manages log file rotation.
- SQLiteLogHandler: writes structured records to SQLite.
- ContextPropagator: injects cycle_id into all records during active cycles.

**Dependencies:**
- File Service (log file creation and rotation).
- Configuration Service (log level, log directory, retention period).
- Storage Service (SQLite log handler — initialized after Storage Service).

**Log Initialization:**
The Logging Service is the first service to initialize (Phase 4 of startup),
because all other services need to log during their own initialization.
Until the Storage Service starts, logs go only to rotating files (not SQLite).

**Sensitive Data Redaction:**
Redaction list (configured in config.py, extended by Secrets Service):
- Key patterns: 	oken, key, secret, password, uth, credential.
- Value patterns: strings matching Dhan token format.
- Redacted value: [REDACTED] replaces the original value in the log record.

**Retention Policy:**
- Log files: 30-day rotation. Files older than 30 days are automatically deleted.
- SQLite log events: retained for 7 days for dashboard queries.

**Performance Targets:**
- Log record creation and dispatch: < 0.5ms (does not block calling thread).
- Log file write: asynchronous (does not block calling thread).

---

## 3.5 Health Service Architecture

**Purpose:** Aggregates component health, provides system health to Docker,
dashboard, and Telegram.

**Interfaces:**
`
INPUT:
  - register_health_check(component: str, check_fn: Callable) -> None
  - report_health(component: str, status: HealthStatus) -> None

OUTPUT:
  - get_system_health() -> SystemHealthReport
  - get_component_health(name: str) -> ComponentHealthReport
  - is_healthy() -> bool  (used by Docker health check)
`

**Internal Components:**
- HealthRegistry: stores registered health check functions.
- HealthPoller: periodically calls registered health check functions.
- HealthAggregator: computes system-level health from component statuses.
- HealthCache: caches the most recent health report (refreshed every 30s).

**Health Polling Interval:**
- CRITICAL services: polled every 30 seconds.
- CORE services: polled every 60 seconds.
- OPTIONAL services: polled every 120 seconds.
- Docker health check: called by Docker every 30 seconds, reads from HealthCache.

**Health Report Structure:**
`
SystemHealthReport {
  timestamp: datetime
  system_status: HealthStatus
  components: Dict[str, ComponentHealthReport] {
    name: str
    status: HealthStatus
    last_checked: datetime
    last_status_change: datetime
    failure_count: int
    message: str
  }
  overall_degraded_count: int
  overall_failed_count: int
}
`

**Failure Detection:**
If a component has not reported health within 2x its polling interval:
status transitions to UNKNOWN. UNKNOWN is treated as FAILED for
system health aggregation purposes.

**Performance Targets:**
- is_healthy() response: < 1ms (reads from cached report).
- Full system health report: < 5ms.
- Health polling cycle completion: < 2 seconds for all components.

---

## 3.6 Secrets Service Architecture

**Purpose:** Sole accessor of secret values from the runtime environment.

**Interfaces:**
`
INPUT:
  - Environment variables (os.environ — ONLY this service reads them)

OUTPUT:
  - get(secret_name: str) -> str  (returns decrypted value)
  - require(secret_name: str) -> str  (raises if absent)
  - reload() -> None  (hot-reload for token rotation)
  - is_present(secret_name: str) -> bool  (without exposing value)
`

**Required Secrets Manifest:**
`
Secret Name                  Required  Format Validation
DHAN_ACCESS_TOKEN            YES       Non-empty string, len > 20
DHAN_CLIENT_ID               YES       Non-empty string
TELEGRAM_BOT_TOKEN           YES       Matches NNN:AAAA format
TELEGRAM_AUTHORIZED_CHAT_IDS YES       Comma-separated integers
`

**Security Architecture:**
- Secrets are read ONCE at startup and stored in an in-memory dictionary.
- After storage, the secret values are cleared from os.environ to prevent
  leakage through subprocess inheritance.
- The in-memory store is not serializable (no __repr__, no __str__).
- Access to the in-memory store is controlled through the get() interface.
- The Secrets Service itself is a singleton registered in the DI Container.

**Audit:**
Every call to get() is recorded in the Audit Service with:
- Timestamp.
- Calling component (inferred from call stack).
- Secret name (NOT the value).
This creates a complete record of which components accessed which secrets.

---

## 3.7 Lifecycle Manager Architecture

**Purpose:** Orchestrates startup and shutdown of all services in dependency order.

**Interfaces:**
`
INPUT:
  - Service descriptors from Service Registry
  - SIGTERM, SIGINT OS signals
  - Telegram /shutdown command

OUTPUT:
  - Ordered startup execution (10 phases)
  - Ordered shutdown execution (reverse phases)
  - SYSTEM_STARTED / SYSTEM_STOPPED events to EventBus
  - Startup/shutdown banners to Logging Service
`

**Dependency Graph Construction:**
The Lifecycle Manager reads each service's manifest to extract declared
dependencies. It performs a topological sort (Kahn's algorithm) to determine
startup order. The topological sort is run at startup, not at deployment.
Circular dependencies in the startup graph raise CircularDependencyError
(a programming error that must be fixed before deployment).

**Phase Execution:**
Each startup phase has a defined timeout (from config.py).
If a phase times out, the Lifecycle Manager:
- For CRITICAL services: abort entire startup.
- For CORE services: mark service FAILED, continue startup, alert operator.
- For OPTIONAL services: mark service FAILED, continue startup, log warning.

**SIGTERM Handler (from main.py):**
`
signal.signal(signal.SIGTERM, lifecycle_manager.handle_sigterm)
`
The SIGTERM handler sets a shutdown flag and allows the current trading cycle
to complete if it is more than 50% through execution.

---

## 3.8 DataFeedManager Architecture

**Purpose:** Manages all external market data connections with automatic failover.

**Interfaces:**
`
INPUT:
  - get_quote(symbol: str) -> Optional[TickerQuote]
  - get_multiple_quotes(symbols: List[str]) -> Dict[str, TickerQuote]
  - get_history(symbol: str, days: int, interval: str) -> List[PriceBar]

OUTPUT:
  - TickerQuote objects (latest price, volume, market cap)
  - PriceBar lists (OHLCV history)
  - Feed status events to EventBus (FEED_FAILOVER)
`

**Feed Priority:**
`
Primary:  DhanFeed (dhanhq SDK, broker-quality data)
Fallback: YahooFeed (yfinance, with timeout=8s)
`

**Symbol Normalization (GLOBAL_SYMBOL_MAP rule):**
Index symbols (NIFTY, BANKNIFTY) are exempt from .NS suffix addition.
The GLOBAL_SYMBOL_MAP routes:
- NIFTY → ^NSEI (Yahoo Finance format)
- BANKNIFTY → ^NSEBANK
- TATASTEEL → TATASTEEL.NS
All symbol normalization is handled by the DataFeedManager.
No consumer component performs symbol normalization independently.

**Failover Logic:**
`
1. Attempt DhanFeed (if circuit breaker CB_DHAN_API is CLOSED).
2. If DhanFeed fails: record failure in CB_DHAN_API.
3. If CB_DHAN_API is OPEN: use YahooFeed directly.
4. If YahooFeed fails: record failure in CB_YFINANCE.
5. If CB_YFINANCE is OPEN and CB_DHAN_API is OPEN:
   -> Return None (no data available).
   -> Log CRITICAL. Alert operator.
   -> Increment no-data cycle counter.
`

**Performance Targets:**
- DhanFeed single quote: < 200ms.
- YahooFeed single quote: < 3s (network dependent).
- DataFeedManager after failover: < 3.5s.
- Cache hit (both feeds): < 10ms (from Cache Service).

---

## 3.9 SystemMonitor Architecture

**Purpose:** Per-layer timing and the 	ime_layer() context manager that
enforces latency contracts on all 17 IIOS layers.

**Interfaces:**
`
INPUT:
  - time_layer(layer_name: str) -> contextmanager  (PROTECTED INTERFACE)
  - register_layer(name: str, warn_ms: int, crit_ms: int) -> None
  - get_cycle_report() -> CycleLatencyReport

OUTPUT:
  - Timer spans reported to Timer Service
  - LAYER_WARN / LAYER_CRIT events logged
  - Layer latency metrics to Metrics Service
  - CycleLatencyReport with per-layer timing
`

**Layer Registration (from config.py):**
`
Default: WARN=2000ms, CRIT=5000ms for all layers.
Overrides:
  GlobalIntelligence:  WARN=5000ms, CRIT=12000ms
  (longer allowed because cold fetch can take up to 8s)
`

**time_layer() behavior:**
`python
with system_monitor.time_layer("GlobalIntelligence"):
    # layer logic runs here
# On exit:
#   - Records duration via Timer Service
#   - Checks against WARN and CRIT thresholds
#   - If WARN exceeded: logs WARNING
#   - If CRIT exceeded: logs CRITICAL, cycle is aborted
`

**CRIT Abort Semantics:**
When a layer exceeds its CRIT threshold, the trading cycle is aborted.
No trade from that cycle is executed. The abort is recorded in the
cycle telemetry with status ABORTED_CRIT_LATENCY.

---

## 3.10 Architecture Summary Table (Remaining Services)

The following services follow standard architecture patterns. Their
full architecture is defined by the template in section 3.0.

| Service | Dependencies | Startup Phase | Failure Impact | Performance Target |
|---------|-------------|---------------|----------------|-------------------|
| Environment Service | None | 1 | ABORT | < 10ms init |
| DI Service | Config | 2 | ABORT | < 5ms per resolve |
| Service Registry | Logging | 2 | ABORT | < 1ms per lookup |
| Component Registry | Service Registry | 4 | WARN | < 1ms per lookup |
| Startup Manager | All Phase 1-7 | 8 | WARN | < 8 min pre-market |
| Shutdown Manager | All services | N/A | ABORT | < 30s graceful |
| Diagnostics Service | Health, Metrics | 7 | OPTIONAL | < 100ms report |
| Monitoring Service | Metrics, Logging | 4 | WARN | < 5ms per check |
| Metrics Service | Logging, Storage | 4 | WARN | < 0.5ms record |
| Tracing Service | Metrics, Storage | 4 | OPTIONAL | < 0.1ms span start |
| Audit Service | Storage, UUID | 4 | CRIT | < 2ms per write |
| Identity Service | Secrets | 5 | CRIT | < 1ms per lookup |
| Authentication Service | Identity, Secrets | 5 | CRIT | < 5ms per verify |
| Authorization Service | Identity | 5 | CRIT | < 1ms per check |
| Encryption Service | None | 2 | CRIT | < 1ms per hash |
| Certificate Service | Config | 5 | WARN | < 50ms per verify |
| Clock Service | Config | 3 | ABORT | < 0.1ms per call |
| Scheduler Service | Clock, EventBus | 7 | CRIT | < 1ms per schedule |
| Timer Service | None | 3 | WARN | < 0.01ms per op |
| UUID Service | None | 3 | ABORT | < 0.1ms per gen |
| File Service | Config | 3 | ABORT | OS-dependent |
| Resource Service | Config, Metrics | 4 | WARN | < 5ms per check |
| Message Bus | EventBus, Logging | 6 | OPTIONAL | < 5ms round-trip |
| Notification Service | EventBus, Secrets | 6 | WARN | < 2s Telegram |
| Cache Service | Config, Metrics | 6 | WARN | < 0.5ms per get |
| Plugin Service | Component Registry | 8 | OPTIONAL | < 10s per plugin |
| Extension Service | EventBus | 8 | OPTIONAL | < 1ms per hook |
| Recovery Service | Storage, Audit | 7 | WARN | < 10s per recovery |
| Exception Service | Logging, Audit | 4 | ABORT | < 1ms per handle |
| Retry Service | Config, Logging | 4 | CRIT | configurable |
| Circuit Breaker | Metrics, EventBus | 4 | CRIT | < 0.1ms per check |
| Feature Flag Service | Config | 6 | OPTIONAL | < 0.1ms per check |
| Version Service | Config | 3 | WARN | < 5ms init |
| Migration Service | Storage, File | 4 | ABORT | < 5s per migration |
| Compatibility Service | Version | 5 | WARN | < 1s init |
| Config Validation Service | Config | 2 | ABORT | < 100ms init |
| Infra Validation Service | All Phase 1-7 | 8 | ABORT | < 5s total |
| Engineering Validation | File, Import graph | CLI only | N/A | < 30s CLI |
| Certification Service | Storage, File | 9 | OPTIONAL | < 100ms |

---

*End of Part III*

---

# PART IV — INFRASTRUCTURE INTERACTION MODEL

## 4.1 Service-to-Service Communication

Infrastructure services communicate through three channels:

**Channel 1 — Direct Method Call (same-phase or lower-to-higher calls):**
Used when a service needs a synchronous response from another service.
Example: Logging Service calls Storage Service to write a log record.

**Channel 2 — Event Bus (decoupled, asynchronous):**
Used when a service needs to notify other services without knowing who they are.
Example: DataFeedManager publishes FEED_FAILOVER event. All interested
services (Telegram Bot, Monitoring Service, Cache Service) subscribe.

**Channel 3 — Health Service Registry (passive reporting):**
Services report their health to the Health Service registry.
The Health Service aggregates without calling services directly during operation.

---

## 4.2 Service Dependency Graph

`
INFRASTRUCTURE DEPENDENCY GRAPH
(arrow = "depends on")

[Environment Service]
       |
       v
[Secrets Service] --> [Encryption Service]
       |
       v
[Configuration Service] <--- [Config Validation Service]
       |
       +-----------> [Version Service]
       |
       v
[Lifecycle Manager]
       |
       +-----> [Clock Service]
       |       [UUID Service]
       |       [Timer Service]
       |       [File Service]
       |
       +-----> [Logging Service] ------> [File Service]
       |       [Metrics Service] ------> [Storage Service]
       |       [Tracing Service] ------> [Storage Service]
       |       [Audit Service] --------> [Storage Service] + [UUID Service]
       |       [Exception Service] ----> [Logging Service] + [Audit Service]
       |       [Retry Service] -------> [Logging Service]
       |       [Circuit Breaker] ------> [Metrics Service] + [EventBus]
       |
       +-----> [Identity Service] ----> [Secrets Service]
       |       [Authentication Service] -> [Identity Service]
       |       [Authorization Service] -> [Identity Service]
       |       [Certificate Service] --> [Config Service]
       |
       +-----> [Storage Service] ------> [File Service] + [Config Service]
       |       [Cache Service] ---------> [Config Service] + [Metrics Service]
       |       [Migration Service] -----> [Storage Service] + [File Service]
       |
       +-----> [Event Bus] ------------> [Logging Service] + [Metrics Service]
       |       [Message Bus] ----------> [Event Bus] + [Logging Service]
       |       [Notification Service] -> [Event Bus] + [Secrets Service]
       |
       +-----> [Service Registry] -----> [Logging Service]
       |       [Component Registry] ---> [Service Registry] + [EventBus]
       |
       +-----> [Health Service] -------> [Logging Service] + [Metrics Service]
       |       [Diagnostics Service] --> [Health Service] + [Metrics Service]
       |       [Monitoring Service] ---> [Metrics Service] + [Logging Service]
       |
       +-----> [DataFeedManager] ------> [Config Service] + [Cache Service]
       |                                 [Circuit Breaker] + [EventBus]
       |                                 [Secrets Service] + [Metrics Service]
       |
       +-----> [SystemMonitor] -------> [Timer Service] + [Metrics Service]
       |                                [Config Service] + [Logging Service]
       |
       +-----> [Scheduler Service] ---> [Clock Service] + [EventBus]
       |       [Resource Service] ----> [Config Service] + [Metrics Service]
       |       [Recovery Service] ----> [Storage Service] + [Audit Service]
       |
       +-----> [Plugin Service] ------> [Component Registry] + [Logging Service]
               [Extension Service] ---> [EventBus] + [Logging Service]
               [Feature Flag Service] -> [Config Service]
               [Certification Service] -> [Storage Service] + [File Service]
`

---

## 4.3 Initialization Order

Infrastructure services start in the following strict order. Each service
must complete startup before the next phase begins.

`
INFRASTRUCTURE INITIALIZATION ORDER

Phase 1 — Environment Baseline (no dependencies)
  1. Environment Service
  2. Secrets Service
  3. Encryption Service

Phase 2 — Configuration
  4. Config Validation Service
  5. Configuration Service
  6. Version Service
  7. DI Service

Phase 3 — Platform
  8. Clock Service
  9. UUID Service
  10. Timer Service
  11. File Service

Phase 4 — Observability
  12. Logging Service         *** all subsequent services can now log ***
  13. Metrics Service
  14. Exception Service
  15. Retry Service
  16. Circuit Breaker
  17. Audit Service
  18. Tracing Service
  19. Monitoring Service

Phase 5 — Security
  20. Identity Service
  21. Authentication Service
  22. Authorization Service
  23. Certificate Service

Phase 6 — Persistence
  24. Migration Service
  25. Storage Service         *** SQLite now available ***
  26. Cache Service

Phase 7 — Communication
  27. Event Bus               *** messaging now available ***
  28. Message Bus
  29. Notification Service
  30. Resource Service

Phase 8 — Registry and Lifecycle
  31. Service Registry
  32. Component Registry
  33. Health Service
  34. Diagnostics Service
  35. Recovery Service

Phase 9 — Application Platform
  36. DataFeedManager         *** market data now available ***
  37. SystemMonitor
  38. Scheduler Service

Phase 10 — Optional / Extensions
  39. Feature Flag Service
  40. Plugin Service
  41. Extension Service
  42. Compatibility Service
  43. Certification Service
  44. Startup Manager
  45. Engineering Validation (CLI mode only)

Phase 11 — Business Domain (Layer 1-17 initialization)
  *** All infrastructure must be ACTIVE before Layer 1 starts ***
`

---

## 4.4 Request Flow (Trading Cycle)

`
TRADING CYCLE REQUEST FLOW

Scheduler Service
    |
    | (trigger CYCLE_START at 09:30 IST)
    v
Startup Manager
    |
    v
MasterOrchestrator.run_full_cycle()
    |
    +-- Layer 1: GlobalIntelligence
    |     |-- SystemMonitor.time_layer("GlobalIntelligence")
    |     |-- DataFeedManager.get_quote(global_symbols)
    |     |     |-- Cache Service: check cache
    |     |     |-- [cache miss] DhanFeed or YahooFeed call
    |     |     |-- Cache Service: store result
    |     |-- Logging Service: log fetch latency
    |     |-- Metrics Service: record latency
    |     +-- Returns GlobalSnapshot
    |
    +-- Layer 2: MarketIntelligence
    |     |-- SystemMonitor.time_layer("MarketIntelligence")
    |     |-- DataFeedManager.get_multiple_quotes(nse_symbols)
    |     +-- Returns MarketSnapshot + RegimeEnum
    |
    +-- Layers 3-9: Knowledge, Observation, Strategy, Risk setup
    |
    +-- Layer 10: DebateAndDecision
    |     |-- 5 agents score opportunity in parallel
    |     |-- ScoreAggregator produces CompositeScore
    |     |-- DecisionEngine: score > DECISION_THRESHOLD (6.5)?
    |     |     |-- YES: TRADE_APPROVED event to EventBus
    |     |     |-- NO:  TRADE_REJECTED event to EventBus
    |     |-- Audit Service: record decision + agent scores
    |
    +-- Layer 11: ExecutionEngine (if TRADE_APPROVED)
    |     |-- RiskGuardian: final kill-switch check
    |     |     |-- VIX > 45.0? -> KILL_SWITCH_TRIGGERED
    |     |     |-- Daily loss > 2.0%? -> KILL_SWITCH_TRIGGERED
    |     |-- OrderManager.submit_order()
    |     |-- Paper mode: write to paper_trades.csv
    |     |-- Audit Service: record TRADE_EXECUTED
    |     |-- EventBus: publish TRADE_EXECUTED
    |
    +-- Layers 12-17: Monitoring, Learning, Analytics, Research, Control
    |
    +-- Cycle telemetry written to Storage Service
    +-- Metrics reported to Metrics Service
    +-- Log cycle summary to Logging Service
`

---

## 4.5 Failure Flow

`
FAILURE FLOW: DATA FEED UNAVAILABLE

DataFeedManager.get_quote(symbol)
    |
    +-- DhanFeed.fetch(symbol)
    |     |-- HTTP request to Dhan API
    |     |-- TIMEOUT after 8 seconds
    |     +-- raises FeedTimeoutError
    |
    +-- Retry Service: retry DhanFeed (up to 3 attempts)
    |     |-- Attempt 1: TIMEOUT
    |     |-- Attempt 2: TIMEOUT
    |     |-- Attempt 3: TIMEOUT
    +-- All retries exhausted. Record failure in CB_DHAN_API.
    |
    +-- CB_DHAN_API: failure count threshold exceeded?
    |     |-- YES: circuit OPENS
    |     |-- Event Bus: publish FEED_FAILOVER event
    |     |-- Monitoring Service: record WARN alert
    |     |-- Notification Service: send Telegram alert to operators
    |
    +-- DataFeedManager: switch to YahooFeed
    |     |-- YahooFeed.fetch(symbol) with timeout=8
    |     |-- Cache Service: store result
    +-- Returns TickerQuote from YahooFeed

ONGOING:
    +-- CB_DHAN_API: half-open after reset_timeout
    +-- DataFeedManager: test one DhanFeed request
    +-- If successful: CB_DHAN_API closes, primary restored
    +-- Event Bus: publish FEED_PRIMARY_RESTORED
    +-- Notification Service: send recovery notification
`

---

## 4.6 Recovery Flow

`
RECOVERY FLOW: PROCESS RESTART AFTER CRASH

Docker detects container STOPPED
    |
    v
Docker restarts container (restart: unless-stopped)
    |
    v
main.py started
    |
    v
Lifecycle Manager Phase 1-3 (environment, config, platform)
    |
    v
Storage Service starts
    |
    v
Recovery Service executes
    |
    +-- Check sys_cycles for INCOMPLETE cycles
    |     |-- Found INCOMPLETE: log recovery event
    |     |-- Mark cycle as RECOVERED_INCOMPLETE (no re-execution)
    |
    +-- Reconcile paper_trades.csv with trd_executions
    |     |-- Found discrepancy: repair CSV from SQLite
    |     |-- Audit Service: record RECOVERY_CSV_REPAIR
    |
    +-- Reload learning state from SQLite
    |     |-- PerformanceTracker singleton initialized from persisted data
    |     |-- RegimeStrategyMap singleton initialized from persisted data
    |
    +-- Recovery Service reports: items recovered, items lost
    |
    v
Normal startup continues (Phase 4 onwards)
    |
    v
Startup Manager: pre-market checks
    |
    v
SYSTEM_READY event published
    |
    v
Telegram Bot: sends restart notification to operators
`

---

## 4.7 Monitoring Flow

`
MONITORING FLOW: COMPONENT HEALTH CHECK

[every 30 seconds — background thread in Health Service]
    |
    v
Health Service.poll_all_components()
    |
    +-- For each CRITICAL service:
    |     |-- Call registered health_check_fn()
    |     |-- Record result: HEALTHY / DEGRADED / CRITICAL / FAILED
    |     |-- If status changed: log state change
    |     |-- If FAILED: publish HEALTH_ALERT to EventBus
    |
    +-- Compute system health (minimum across CRITICAL services)
    |
    +-- Update HealthCache with new SystemHealthReport
    |
    +-- Report system health to Metrics Service
    |     (metric: iios.system.health_status [0=healthy, 1=degraded, 2=critical, 3=failed])
    |
    +-- If system health is CRITICAL or FAILED:
    |     |-- Notification Service: send CRITICAL alert
    |     |-- If failed service is EXECUTION_ENGINE or RISK_GUARDIAN:
    |           |-- Trigger safety halt (no new orders)

[on Telegram /health command]
    |
    v
Telegram Bot receives /health
    |
    v
Authorization Service: VIEWER role check
    |
    v
Diagnostics Service.get_health_report()
    |
    v
Health Service.get_system_health()
    |
    v
Notification Formatter: format as Telegram message
    |
    v
Notification Service: send to operator
`

---

## 4.8 Shutdown Flow

`
SHUTDOWN FLOW: SIGTERM (graceful)

OS sends SIGTERM to Docker container
    |
    v
main.py SIGTERM handler triggered
    |
    v
Lifecycle Manager.handle_sigterm()
    |
    +-- Set SHUTDOWN_REQUESTED flag in SystemState
    |
    +-- Scheduler Service: cancel all pending scheduled tasks
    |
    +-- Check: is a trading cycle in progress?
    |     |-- YES and > 50% complete:
    |     |     |-- Allow current cycle to complete
    |     |     |-- Block new cycles
    |     |-- YES and < 50% complete:
    |     |     |-- Abort current cycle (mark INCOMPLETE)
    |     |-- NO: proceed immediately
    |
    +-- EventBus: publish SHUTDOWN_INITIATED
    |
    +-- Execution Engine: complete in-flight order / block new orders
    |
    +-- Learning Engine: flush pending state to Storage Service
    |
    +-- Telemetry: flush pending metrics to Storage Service
    |
    +-- Logging Service: flush buffers to disk
    |
    +-- Notification Service: send shutdown notification to operators
    |
    +-- Write shutdown banner to log file
    |
    +-- EventBus: publish SHUTDOWN_COMPLETE
    |
    +-- Lifecycle Manager: stop services in reverse order (Phase 11 -> Phase 1)
    |
    +-- Process exits with code 0
    |
    v
Docker marks container STOPPED (then restarts if policy is unless-stopped)
`

---

*End of Part IV*

# PART V — INFRASTRUCTURE LIFECYCLE

## 5.0 Lifecycle Overview

Infrastructure components go through a defined lifecycle from initial installation
to retirement. The lifecycle defines the state a component is in at any point in time
and the transitions between states.

**Component Lifecycle States:**
`
NOT_INSTALLED -> INSTALLED -> REGISTERED -> INITIALIZED -> CONFIGURED
     -> ACTIVATED -> MONITORING -> SCALING (optional)
     -> UPGRADING (optional) -> MIGRATING (optional)
     -> RECOVERING (conditional) -> SHUTTING_DOWN -> STOPPED -> RETIRED
`

---

## 5.1 Installation Phase

**Definition:** An infrastructure service is "installed" when its Python module
is present in the IIOS package structure and its __manifest__.json is valid.

**Installation Steps:**
1. Python module files created in the correct package directory.
2. __manifest__.json created with complete metadata.
3. README.md created with service documentation.
4. Test files created (at minimum stubs).
5. Module registered in uild_manifest.json.
6. Import graph checked for violations.
7. Commit: [W2] Install: {service_name} infrastructure service.

**Installation Diagram:**
`
[Source files present in package]
           |
           v
[__manifest__.json valid]
           |
           v
[build_manifest.json updated]
           |
           v
[import_graph_analyzer passes]
           |
           v
[SERVICE: NOT_INSTALLED -> INSTALLED]
`

---

## 5.2 Registration Phase

**Definition:** A service is "registered" when it has declared itself to the
Service Registry at runtime during process startup.

**Registration Steps:**
1. Service class is imported by the DI Container.
2. Service's egister() method is called.
3. Service descriptor (name, version, dependencies, health check) added to Service Registry.
4. Service status set to REGISTERED in Service Registry.

**Registration Diagram:**
`
[Process starts]
       |
       v
[DI Container imports service class]
       |
       v
[Service.register(service_registry)]
       |
       v
[ServiceRegistry.add(descriptor)]
       |
       v
[SERVICE: INSTALLED -> REGISTERED]
`

---

## 5.3 Initialization Phase

**Definition:** A service is "initialized" when its internal components are
created and its dependencies are resolved, but before it has started
doing any work.

**Initialization Steps:**
1. DI Container resolves all service dependencies.
2. Service constructor called with resolved dependencies.
3. Internal components created (no external calls yet).
4. Service validates its own configuration.
5. Service status updated to INITIALIZING.

**Initialization Diagram:**
`
[Service registered]
       |
       v
[DI Container resolves dependencies]
       |
       v
[Constructor called with injected deps]
       |
       v
[Internal components created (in-memory only)]
       |
       v
[Configuration validated]
       |
       v
[SERVICE: REGISTERED -> INITIALIZED]
`

---

## 5.4 Configuration Phase

**Definition:** A service is "configured" when it has applied its runtime
configuration from the Configuration Service and is ready to start operating.

**Configuration Steps:**
1. Service reads its configuration section from ConfigurationSnapshot.
2. Service applies configuration to internal components.
3. Service validates that its configuration is internally consistent.
4. Service status updated to CONFIGURED.

**Configuration Invariant:**
Configuration is read exactly once during this phase. The service stores
its configuration internally. It does NOT read from ConfigurationSnapshot
again during operation. This ensures configuration is stable throughout
a process lifetime.

---

## 5.5 Activation Phase

**Definition:** A service is "activated" when it begins doing its actual work:
accepting requests, starting background threads, opening connections.

**Activation Steps:**
1. Open external connections (database, APIs).
2. Start background threads (if any).
3. Register health check with Health Service.
4. Perform initial health self-check.
5. If self-check passes: status updated to ACTIVE in Service Registry.
6. If self-check fails: status set to FAILED, Lifecycle Manager notified.
7. Publish SERVICE_ACTIVATED event to EventBus (if EventBus is available).

**Activation Order Constraint:**
Services are activated in topological dependency order (from Phase 3 of startup).
A service cannot be activated until all its dependencies are ACTIVE.

**Activation Diagram:**
`
[Service configured]
       |
       v
[External connections opened]
       |
       v
[Background threads started]
       |
       v
[Health check registered with Health Service]
       |
       v
[Self-check executed]
       |
    [PASS?]
      /    \
   YES      NO
    |        |
    v        v
[ACTIVE] [FAILED -> alert Lifecycle Manager]
`

---

## 5.6 Monitoring Phase

**Definition:** Normal ongoing operation. The service processes requests,
maintains its internal state, and reports health.

**Monitoring Activities:**
- Health Service polls service health check function every 30/60/120 seconds.
- Service reports metrics to Metrics Service on schedule.
- Service logs significant events to Logging Service.
- Monitoring Service watches for threshold violations.
- Resource Service monitors memory and CPU usage.

**Status Transitions During Monitoring:**
- ACTIVE → DEGRADED: service is operating but with reduced capability
  (e.g., yfinance fallback, cache miss rate elevated).
- DEGRADED → ACTIVE: degradation resolved.
- ACTIVE → CRITICAL: service is about to fail (latency approaching CRIT threshold).
- CRITICAL → FAILED: service has exceeded CRIT threshold.
- ACTIVE → FAILED: sudden failure (exception, crash).

---

## 5.7 Scaling Phase

**Definition:** Service is adjusting its capacity in response to load changes.
For the current IIOS implementation, scaling is manual configuration change.
Future implementations support automatic scaling.

**Current Scaling Mechanisms:**
- EventBus thread pool size: adjustable via EVENTBUS_THREAD_POOL_SIZE in config.
- SQLite connection pool size: adjustable via STORAGE_CONNECTION_POOL_SIZE.
- Cache size limits: adjustable per namespace in config.

**Scaling Procedure:**
1. Configuration change in config.py (or environment variable).
2. System restart (configuration is immutable at runtime).
3. Services reinitialize with new capacity settings.

---

## 5.8 Upgrade Phase

**Definition:** Service implementation is updated while the system continues
operating (hot upgrade) or with a restart (cold upgrade).

**Cold Upgrade Procedure (normal):**
1. New code committed to main branch.
2. VPS deployment: docker compose build --no-cache && docker compose up -d.
3. Verify HEALTHY after upgrade.
4. This is the standard deployment process described in DEPLOYMENT_CHECKLIST.md.

**Hot Upgrade (future capability):**
Not supported in Wave 1-19. Declared for Wave 20 institutional-grade implementation.

---

## 5.9 Migration Phase

**Definition:** Service applies a data migration or schema migration to its
persistent state.

**Migration Trigger:**
A new system version is deployed that includes changes to the SQLite schema.
The Migration Service detects the schema version mismatch and runs migrations
automatically during the Activation Phase (before the Storage Service becomes ACTIVE).

**Migration Safety Protocol:**
`
1. Record current schema version.
2. Identify pending migrations (version > current).
3. Announce each migration before running: log INFO with migration description.
4. Run migration inside SQLite transaction.
5. If migration succeeds: commit, update sys_migrations.
6. If migration fails: rollback, ABORT STARTUP, alert operator.
7. After all migrations: verify schema integrity (PRAGMA integrity_check).
`

---

## 5.10 Recovery Phase

**Definition:** Service is recovering from an abnormal termination or partial failure.
This phase is only entered after a restart that follows a crash or SIGKILL.

**Recovery Trigger:**
The Recovery Service checks for incomplete state on every startup.
If incomplete state is found, the Recovery Phase is entered for the affected service.

**Recovery Outcomes:**
- RECOVERED_CLEAN: all state recovered completely. No data loss.
- RECOVERED_PARTIAL: some state recovered. Partial data loss (logged and audited).
- RECOVERY_IMPOSSIBLE: state cannot be recovered. Data loss confirmed. Operator alerted.

**Recovery Priority:**
1. Trade execution state (highest priority — money-related).
2. Paper trades CSV integrity.
3. Learning state (win rates, Sharpe ratios).
4. Cycle telemetry (lower priority — operational analytics only).

---

## 5.11 Shutdown Phase

**Definition:** Service is gracefully stopping. It completes in-flight work,
flushes state, and releases resources.

**Shutdown Sequence per Service:**
1. Stop accepting new requests (return immediately with ServiceShuttingDownError).
2. Complete all in-flight requests (with timeout from config: default 5 seconds).
3. Flush all buffered state to persistent storage.
4. Close all external connections (database, APIs).
5. Stop all background threads (with join timeout).
6. Publish SERVICE_STOPPED event to EventBus.
7. Status updated to STOPPED in Service Registry.

**Shutdown Order:**
Services shut down in reverse activation order.
Layer 17 (ControlTower) shuts down first.
Layer 0 platform services shut down last.
The Logging Service and Exception Service shut down last-of-all (they are
needed by all other services during their shutdown sequence).

---

## 5.12 Retirement Phase

**Definition:** A service is permanently decommissioned. It is moved to the
_deprecated/ directory and removed from active service registration.

**Retirement Criteria:**
- Service has been replaced by a superior implementation.
- All consumers have been updated to use the new implementation.
- Replacement has been operating in production for at least 2 weeks without issues.

**Retirement Procedure:**
1. Write EDR describing: old service, new service, migration path, rollback plan.
2. Update all consumers to use new service.
3. Remove old service from DI Container registrations.
4. Move old service module to _deprecated/ with deprecation header.
5. Update uild_manifest.json to mark old service as RETIRED.
6. Commit and deploy.
7. Monitor for 48 hours post-retirement.

---

*End of Part V*

---

# PART VI — INFRASTRUCTURE RELIABILITY FRAMEWORK

## 6.1 Fault Tolerance Design

IIOS infrastructure is designed to tolerate individual component failures
without halting the trading system. The fault tolerance design identifies
which failures are survivable and which require escalation.

**Failure Survivability Matrix:**

| Component | Failure Type | Survivable? | System Behavior |
|-----------|-------------|-------------|-----------------|
| DataFeedManager (Dhan) | Connection refused | YES | Auto-failover to yfinance |
| DataFeedManager (both) | Both unavailable | NO | Halt trading, alert operators |
| Cache Service | Memory pressure eviction | YES | Fallback to source on cache miss |
| Logging Service | File write error | PARTIAL | Continue to stderr only |
| Storage Service | Write timeout | PARTIAL | Retry, defer non-critical writes |
| EventBus | Subscriber exception | YES | Skip failed subscriber, continue |
| Notification Service | Telegram unreachable | YES | Queue notifications, retry |
| Health Service | Poll failure | YES | Degrade health report, continue |
| Metrics Service | Write failure | YES | Drop metric, continue |
| SystemMonitor | Timer failure | PARTIAL | Log error, continue without timing |
| RiskGuardian | Any failure | NO | Halt trading immediately |
| Scheduler Service | Task failure | PARTIAL | Retry 3x, skip, continue |
| Clock Service | Any failure | NO | ABORT: time is foundational |

**Key Fault Tolerance Principle:**
Observability failures (logging, metrics, tracing) are survivable.
Safety failures (RiskGuardian, Authentication) are not survivable.
Data failures (DataFeedManager) are partially survivable if one source remains.

---

## 6.2 Retry Policies

**Retry Policy Design Principles:**
- Retries are bounded. Infinite retries are never configured.
- Retry backoff prevents thundering herd on recovery.
- Fail-fast is applied to errors that retrying cannot fix (auth failures, validation errors).
- Retries are logged individually so operators can see retry storms.

**Retry Policy Catalog:**

| Policy Name | Max Attempts | Backoff Type | Initial Wait | Max Wait | Fail-Fast Errors |
|-------------|-------------|-------------|-------------|---------|-----------------|
| POLICY_DATA_FEED | 3 | Exponential | 2s | 30s | AuthenticationFailedError |
| POLICY_DATABASE | 3 | Fixed | 1s | 1s | IntegrityError |
| POLICY_TELEGRAM | 5 | Exponential | 1s | 60s | AuthenticationFailedError |
| POLICY_BROKER_API | 2 | Fixed | 5s | 5s | AuthenticationFailedError, InsufficientFundsError |
| POLICY_CACHE | 1 | None | 0s | 0s | Any error (no retry for cache) |
| POLICY_SCHEDULER | 3 | Fixed | 30s | 30s | None |

**Retry Logging:**
`
[RETRY] {operation} attempt {n}/{max}: {error_type} - {error_message}
[RETRY EXHAUSTED] {operation}: all {max} attempts failed. Final error: {error}
`

---

## 6.3 Circuit Breakers

**Circuit Breaker State Machine:**
`
                   [failure threshold exceeded]
CLOSED ---------------------------------> OPEN
  ^                                         |
  |   [test request succeeds]               | [reset_timeout elapsed]
  |                                         |
  +------------- HALF_OPEN <---------------+
                    |
                    | [test request fails]
                    |
                    v
                  OPEN (reset timer restarts)
`

**Circuit Breaker Metrics:**
Each circuit breaker reports to the Metrics Service:
- iios.cb.{name}.state: current state (0=closed, 1=half_open, 2=open).
- iios.cb.{name}.failure_count: failures in current window.
- iios.cb.{name}.open_duration_s: seconds in OPEN state.

**Circuit Breaker Alert Thresholds:**
- CB opens for the first time: WARN notification.
- CB stays open for more than 5 minutes: ERROR notification.
- CB stays open for more than 30 minutes: CRITICAL notification.

---

## 6.4 Health Checks

**Health Check Categories:**

| Category | Checks | Interval | WARN Threshold |
|----------|--------|----------|----------------|
| Data Feed | Dhan API reachable, yfinance reachable | 60s | One source unavailable |
| Database | SQLite writable, schema current | 30s | Write latency > 5ms |
| Memory | Process memory < budget | 30s | > 400MB |
| CPU | CPU usage < budget | 30s | > 80% sustained |
| Disk | Disk space available | 120s | < 5GB free |
| EventBus | Queue depth < threshold | 30s | > 1,000 events |
| Telegram | Bot API reachable | 60s | Any API error |
| Scheduler | No tasks stuck | 60s | Task overdue > 2x interval |
| Kill Switch | Thresholds match config | 300s | Any mismatch |
| Agents | 5 debate agents registered | 300s | Count != 5 |

---

## 6.5 Graceful Degradation

Graceful degradation means the system continues operating at reduced capability
when a non-critical component fails, rather than halting entirely.

**Degradation Scenarios:**

**D-1: Dhan API Unavailable**
Degraded state: yfinance is the active data source.
Impact: higher latency for data fetches (up to 3s instead of <200ms).
Mitigation: Cache Service reduces fetch frequency. Pre-warmed data covers gaps.

**D-2: Telegram Bot Unreachable**
Degraded state: notifications are queued locally.
Impact: operators receive delayed notifications when bot reconnects.
Mitigation: All critical events are written to log file (always available).

**D-3: Streamlit Dashboard Unavailable**
Degraded state: dashboard is inaccessible.
Impact: operators cannot view real-time positions or cycle data.
Mitigation: Telegram /status and /positions commands provide equivalent data.

**D-4: Tracing Service Disabled**
Degraded state: no execution traces recorded.
Impact: reduced diagnostics capability.
Mitigation: Per-layer timing metrics still available via Timer Service.

**D-5: Metrics Service Degraded**
Degraded state: metrics are logged but not stored in SQLite.
Impact: reduced performance history in dashboard.
Mitigation: Log file contains all metric events.

---

## 6.6 Redundancy

**Current Redundancy Design (Wave 2-17):**
- Data feed: two sources (Dhan + yfinance) with automatic failover.
- Database backup: WAL mode provides implicit read redundancy.
- Configuration: config.py is version-controlled (restoreable from git).
- Operational state: SQLite is persistent across restarts.
- Log files: 30-day rolling retention.

**Future Redundancy (Wave 20):**
- Database: primary + replica (SQLite → PostgreSQL with streaming replication).
- Process: two trading processes in warm-standby mode.
- EventBus: Redis Pub/Sub with Redis Sentinel for high availability.

---

## 6.7 Recovery Strategy

**Recovery Strategy Tiers:**

**Tier 1 — Automatic Self-Recovery (no operator action):**
- Data feed failover (Circuit Breaker pattern).
- Cache miss (re-fetch from source).
- Retry on transient failures.
- Thread restart after exception.

**Tier 2 — Supervised Recovery (system continues, operator notified):**
- Container restart after crash (Docker restart policy).
- Database recovery from WAL.
- CSV repair from SQLite shadow.
- Pre-warm thread restart after failure.

**Tier 3 — Manual Recovery (operator intervention required):**
- Database corruption: restore from backup.
- Both data feeds down: operator investigation required.
- Kill switch stuck in OPEN: operator manual /resume command.
- Configuration error: fix config.py, redeploy.

---

## 6.8 Resource Protection

**Memory Protection:**
- Resource Service monitors memory every 30 seconds.
- At 400MB (WARN): log warning, begin aggressive cache eviction.
- At 768MB (CRIT): log critical, alert operator, disable non-critical caches.
- At 1GB (KILL): trigger graceful shutdown to prevent OOM kill.

**CPU Protection:**
- At 80% sustained: log warning, alert operator.
- At 95% sustained: log critical, pause non-essential background tasks.

**Disk Protection:**
- At 5GB free: log warning, begin log file pruning (delete files > 7 days).
- At 1GB free: log critical, alert operator, pause SQLite writes (safety mode).

**File Handle Protection:**
- At 500 open handles: log warning.
- At 900 open handles: log critical, alert operator.

---

## 6.9 Isolation

**Failure Isolation Boundaries:**

| Boundary | Isolation Mechanism | What It Contains |
|----------|-------------------|-----------------|
| Exception contexts | try/except in Exception Service | Prevents exceptions from propagating upward |
| EventBus subscribers | Per-subscriber exception isolation | Subscriber failure does not affect other subscribers |
| Plugin runtime | Plugin isolation context | Plugin crash does not affect core |
| Extension hooks | Extension isolation context | Hook failure does not affect core operation |
| Telegram handlers | Command handler isolation | Bad command does not affect system state |
| Scheduler tasks | Task isolation context | Failed task does not affect next task |

---

## 6.10 Infrastructure Resilience Summary

The IIOS infrastructure is designed to remain operational in all foreseeable
single-component failure scenarios. The following table summarizes the overall
resilience posture.

| Component Class | Resilience Level | Recovery SLA | Notes |
|-----------------|-----------------|-------------|-------|
| Data Feed | HIGH | 30s auto-recover | Two sources + circuit breaker |
| Database | HIGH | < 5s on restart | WAL mode + atomic writes |
| Messaging | HIGH | No restart needed | In-memory with dead letter |
| Security | CRITICAL | Cannot degrade | Auth/authz must not fail |
| Observability | MEDIUM | Partial operation | Logging degrades to stderr |
| Platform | CRITICAL | Cannot degrade | Clock, UUID, config are absolute |
| Communication | MEDIUM | Delayed delivery | Queue-based with retry |

---

*End of Part VI*

---

# PART VII — PERFORMANCE FRAMEWORK

## 7.1 Latency Standards

**Core Latency Targets (from config.py, enforced by SystemMonitor):**

| Operation | P50 Target | P99 Target | WARN | CRIT |
|-----------|------------|------------|------|------|
| GlobalIntelligence (cached) | 10ms | 17ms | 5,000ms | 12,000ms |
| MarketIntelligence | 12ms | 19ms | 2,000ms | 5,000ms |
| Full trading cycle | 100ms | 172ms (baseline) / 200ms (SLA) | 300ms | 500ms |
| Database write | 1ms | 5ms | 10ms | 100ms |
| EventBus publish | 0.05ms | 1ms | 10ms | 50ms |
| Cache get (hit) | 0.1ms | 0.5ms | 2ms | 10ms |
| Kill switch response | 5ms | 100ms | 150ms | 200ms |
| Telegram command response | 200ms | 2,000ms | 3,000ms | 5,000ms |
| Health check | 1ms | 5ms | 50ms | 100ms |
| DI resolve (singleton) | 0.01ms | 0.1ms | 1ms | 5ms |

---

## 7.2 Availability Standards

**Infrastructure Availability SLAs:**

| Service Class | Availability SLA | Measurement Window | Allowed Downtime |
|---------------|-----------------|-------------------|-----------------|
| CRITICAL services | 99.9% | Market hours | 3.75 min/month |
| CORE services | 99.5% | Market hours | 18.7 min/month |
| OPTIONAL services | 99.0% | All hours | 7.2 hours/month |

**Availability Measurement:**
Availability = (Total minutes - Downtime minutes) / Total minutes * 100%
Downtime = any minute where the service is in FAILED or UNKNOWN state.

---

## 7.3 Throughput Standards

| Operation | Target Throughput | Maximum Throughput | Bottleneck |
|-----------|-----------------|-------------------|------------|
| Trade decisions | 10/minute | 100/minute | DecisionEngine |
| Market data fetches | 100/minute | 1,000/minute | DataFeedManager |
| EventBus events | 100/second | 10,000/second | Thread pool |
| Database writes | 100/second | 1,000/second | SQLite WAL |
| Log records | 1,000/second | 10,000/second | Async file write |
| Metrics records | 500/second | 5,000/second | In-memory aggregation |

---

## 7.4 Reliability Standards

| Metric | Target | Measurement |
|--------|--------|-------------|
| System uptime (market hours) | 99.9% | Health Service |
| Successful cycle rate | 99.5% | Cycle telemetry |
| Successful order execution | 99.9% | Order journal |
| Data feed availability | 99.9% (primary or fallback) | DataFeedManager metrics |
| Kill switch reliability | 100% | RiskGuardian tests |

---

## 7.5 Capacity Standards

**Current Capacity (Wave 2-17 baseline):**

| Resource | Baseline | Maximum | Trigger for Review |
|----------|---------|---------|-------------------|
| Watched symbols | 50 | 500 | > 200 symbols |
| Active strategies | 10 | 50 | > 30 strategies |
| SQLite database size | 100MB | 2GB | > 500MB |
| Log files total | 500MB | 5GB | > 2GB |
| Process memory | 200MB | 512MB | > 400MB |
| EventBus queue depth | 10 | 1,000 | > 100 sustained |

---

## 7.6 Scalability Standards

**Scalability Targets (for Wave 20 institutional-grade deployment):**

| Dimension | Current | Wave 20 Target | Mechanism |
|-----------|---------|---------------|-----------|
| Symbols | 50 | 5,000 | Parallel DataFeedManager |
| Agents | 62 | 620 | Plugin agent registration |
| Decisions/minute | 10 | 1,000 | EventBus + distributed workers |
| Data retention | 90 days | 5 years | PostgreSQL migration |
| Dashboard users | 1 | 100 | Streamlit caching + read replicas |

---

## 7.7 Resource Usage Standards

| Resource | Development Target | Production Target | Maximum Allowed |
|----------|--------------------|-------------------|-----------------|
| Memory | < 200MB | < 300MB | 512MB |
| CPU (avg) | < 20% | < 30% | 80% |
| Disk (data/) | < 500MB | < 2GB | 10GB |
| Network (daily) | < 100MB | < 500MB | 2GB |
| File handles | < 50 | < 100 | 500 |

---

## 7.8 Monitoring KPIs

**Infrastructure Performance KPIs reported to dashboard:**

| KPI | Source Service | Update Frequency | Alert Threshold |
|-----|---------------|-----------------|----------------|
| Cycle latency p99 | SystemMonitor | Per cycle | > 200ms |
| Layer latency p99 (each) | SystemMonitor | Per cycle | Varies per layer |
| Memory usage MB | Resource Service | 30s | > 400MB |
| CPU usage % | Resource Service | 30s | > 80% |
| DB write latency p99 | Storage Service | 60s | > 10ms |
| EventBus queue depth | EventBus | 5s | > 100 |
| Cache hit rate | Cache Service | 60s | < 80% |
| Feed success rate | DataFeedManager | Per fetch | < 95% |
| Active circuit breakers | All CBs | 30s | Any OPEN |

---

## 7.9 Infrastructure SLAs

**Infrastructure SLA Summary:**

| SLA Category | Commitment | Measurement | Breach Action |
|--------------|------------|-------------|---------------|
| Market Hour Availability | 99.9% | Health Service | Incident post-mortem |
| Cycle Success Rate | 99.5% | Cycle telemetry | Root cause analysis |
| Kill Switch Reliability | 100% | Integration tests | Immediate halt + investigation |
| Data Feed Availability | 99.9% | DataFeedManager | Auto-failover + operator alert |
| Secret Security | Zero exposure | Audit Service | Immediate security incident |
| Decision Integrity | 100% correct threshold | Architecture invariant test | Halt + manual review |

---

## 7.10 Engineering Targets

**Engineering Performance Targets (required before SYSTEM_CERTIFIED):**

All of the following must pass their benchmarks for production authorization:

1. GlobalIntelligence p99 <= 17ms on 100-sample benchmark.
2. MarketIntelligence p99 <= 19ms on 100-sample benchmark.
3. Full cycle p99 <= 200ms on 50-sample benchmark.
4. Database write p99 <= 5ms on 1,000-write benchmark.
5. Kill switch response <= 100ms on 10-trigger integration test.
6. EventBus event delivery <= 1ms p99 on 10,000-event throughput test.
7. Cache hit latency <= 0.5ms p99 on 10,000-lookup benchmark.
8. Memory usage below 400MB after 1 hour of continuous market simulation.

---

*End of Part VII*

---

# PART VIII — GOVERNANCE FRAMEWORK

## 8.1 Infrastructure Ownership

**Infrastructure Ownership Hierarchy:**

| Level | Owner | Authority Scope |
|-------|-------|----------------|
| System Architecture | Architecture Council | All infrastructure decisions |
| Platform Infrastructure | Platform Team | Groups A, B, E, F, G |
| Security Infrastructure | Security Officer | Group D |
| Observability Infrastructure | Platform Team | Group C |
| Protected modules | Architecture Council | Explicit instruction required |

**Infrastructure Team Responsibilities:**
Platform Team owns and maintains all 46 infrastructure services. Daily
operational decisions are made by Platform Team without council review.
Architectural changes (new services, interface changes, deprecations) require
Architecture Council approval.

---

## 8.2 Approval Workflow

**Infrastructure Change Classification:**

| Change Type | Classification | Approval Required |
|-------------|---------------|-------------------|
| Bug fix (no interface change) | PATCH | Domain Owner review |
| Performance improvement | MINOR | Domain Owner review |
| New service addition | MINOR | Architecture Council |
| Interface change (backward compatible) | MINOR | Architecture Council |
| Interface change (breaking) | MAJOR | Architecture Council + EDR |
| Protected module change | PROTECTED | Explicit Architecture Council instruction |
| Security service change | SECURITY | Security Officer + Architecture Council |
| Threshold change (kill switch, decision) | CRITICAL | Architecture Council unanimous vote |

**Approval Workflow:**
`
Engineer creates feature branch
     |
     v
Engineer implements + tests
     |
     v
Domain Owner review (peer review)
     |
     v
[Classification?]
  PATCH/MINOR: -> merge after peer review
  MAJOR: -> Architecture Council review meeting
  PROTECTED: -> Architecture Council explicit instruction (before implementation)
  CRITICAL: -> Architecture Council unanimous vote + EDR written
`

---

## 8.3 Change Management

**Change Management Principles:**
- Every infrastructure change has a clear motivation (bug, performance, feature).
- Changes are atomic: one logical change per commit.
- Changes are reversible: every change can be rolled back by reverting the commit and redeploying.
- Changes are tested: no infrastructure change merges without passing CI/CD.
- Changes are documented: CHANGELOG.md updated for every version tag.

**Prohibited Changes (without Architecture Council explicit instruction):**
- Changing DECISION_THRESHOLD value.
- Changing KILL_SWITCH_VIX value.
- Changing KILL_SWITCH_DAILY_LOSS_PCT value.
- Modifying isk_guardian.py.
- Modifying dhan_feed.py.
- Deleting any file in the data/ directory.
- Modifying authentication or authorization logic.

---

## 8.4 Version Governance

**Infrastructure Version Policy:**
- Each infrastructure service has its own version in __manifest__.json.
- Service versions follow semantic versioning: MAJOR.MINOR.PATCH.
- Interface versions are declared separately in __init__.py.
- System version (in uild_manifest.json) reflects the highest version among CRITICAL services.

**Version Compatibility Policy:**
- Services declare their minimum required version for each dependency.
- The Compatibility Service validates version compatibility at startup.
- Incompatible versions fail startup with a VersionCompatibilityError.

---

## 8.5 Security Governance

**Security Governance Responsibilities:**
- Security Officer: owns all Group D security services and the security policy.
- Platform Team: implements security requirements defined by Security Officer.
- Architecture Council: approves security architecture changes.

**Security Review Triggers:**
- Any change to authentication or authorization logic.
- Any new external dependency.
- Any new external connection endpoint.
- Any change to secret handling.
- Any change to the Telegram command interface.

**Security Audit Schedule:**
- Monthly: automated security scan (CVE check, secret detection).
- Per-wave: security review of new components.
- Pre-production (v1.0.0): full OWASP Top 10 audit.
- Annually: penetration test (Wave 20 target).

---

## 8.6 Operational Governance

**Operational Governance Rules:**
- Every deployment to VPS must pass the HEALTHY check before being considered complete.
- No manual changes to production configuration without going through config.py + commit.
- All operator actions via Telegram are logged in the Audit Service.
- All incidents are documented in docs/certification/incidents.md.
- Weekly operational review: review health metrics, alert history, cycle success rates.

---

## 8.7 Infrastructure Audits

**Audit Types and Schedules:**

| Audit Type | Frequency | Owner | Output |
|------------|-----------|-------|--------|
| Dependency audit (CVE scan) | Monthly | Security Officer | CVE report |
| Secret detection | Each commit | CI/CD | Scan report |
| Import graph audit | Each commit | CI/CD | Graph report |
| Protected module checksum | Each commit | CI/CD | Checksum report |
| Performance benchmark | Per wave | Platform Team | Benchmark report |
| Security architecture review | Per wave | Security Officer | Security report |
| Full infrastructure audit | Quarterly | Architecture Council | Audit report |

---

## 8.8 Continuous Improvement

**Continuous Improvement Process:**
1. Monthly metrics review: identify performance regressions or anomalies.
2. Post-incident analysis: every incident produces a lessons-learned document.
3. Wave retrospectives: each wave includes a retrospective on infrastructure quality.
4. Backlog maintenance: infrastructure improvement items tracked in the technical backlog.

**Infrastructure Technical Backlog:**
All identified improvement opportunities that are not critical bugs are tracked
as backlog items. Each item includes: description, priority, estimated effort,
and target wave. Backlog items are reviewed at each wave planning session.

---

*End of Part VIII*

---

# PART IX — ENGINEERING CONSTITUTION

## 9.0 Preamble

The Infrastructure Engineering Constitution codifies the non-negotiable rules
governing all infrastructure services in IIOS. These rules apply to every
infrastructure component, every configuration value, and every deployment.

Rules are organized into 13 categories. Each rule has a unique identifier.
Total rules: 140.

---

## 9.1 Infrastructure Rules (INFRA)

**INFRA-001:** Every infrastructure service has a unique code in the format
INFRA-{GROUP}-{NUM}. No two services share a code.

**INFRA-002:** Every infrastructure service has a __manifest__.json declaring:
name, version, classification, group, wave, owner, and dependencies.

**INFRA-003:** CRITICAL infrastructure services must be ACTIVE before any
trading cycle begins. A system with a CRITICAL service in FAILED state
must not execute trades.

**INFRA-004:** Infrastructure services do not contain business logic.
Business logic decisions (which strategy to use, when to trade, how much to risk)
belong in the 17-layer IIOS pipeline, not in infrastructure.

**INFRA-005:** Infrastructure services are designed for substitution.
Every service exposes a defined interface and a factory function.
The implementation can be replaced without changing consumers.

**INFRA-006:** No infrastructure service depends on a higher-layer service.
Infrastructure is Layer 0. All 17 trading layers depend on infrastructure.
Infrastructure depends on nothing above itself.

**INFRA-007:** Infrastructure services are singletons unless explicitly declared
otherwise. Multiple instances of the same infrastructure service are forbidden.

**INFRA-008:** Infrastructure service constructors do no external work.
Connecting to databases, opening files, starting threads — these happen in
ctivate(), not in __init__().

**INFRA-009:** Every infrastructure service implements a health_check() -> HealthStatus
method and registers it with the Health Service on activation.

**INFRA-010:** Infrastructure service public interfaces are PROTECTED.
Any change to an infrastructure interface requires an EDR and Architecture Council approval.

---

## 9.2 Reliability Rules (REL)

**REL-001:** Every infrastructure service declares its failure mode explicitly.
"This service might fail silently" is not an acceptable failure mode declaration.

**REL-002:** No infrastructure service causes a system halt without first
attempting self-recovery through the defined recovery path.

**REL-003:** Retry policies are bounded. No retry loop runs more than 5 iterations
for any single operation.

**REL-004:** Exponential backoff includes jitter. A pure exponential backoff without
jitter causes synchronized retry storms when multiple components fail simultaneously.

**REL-005:** Circuit breakers are closed (allowing traffic) by default. They open
only when failure thresholds are exceeded. A component must not start in the OPEN state.

**REL-006:** Dead letter queues are monitored. Events in the DeadLetterQueue are
not silently discarded. They are logged and counted. If the count exceeds a threshold,
operators are alerted.

**REL-007:** Self-healing behaviors are tested. Every self-healing action
has a corresponding integration test that verifies the healing.

**REL-008:** Recovery procedures are documented and practiced. Each recovery
runbook has been tested at least once in a staging environment.

**REL-009:** Infrastructure failures are idempotent. Retrying a failed infrastructure
operation produces the same result as the original operation. There are no
side-effect-on-retry scenarios.

**REL-010:** Graceful degradation states are explicitly defined. "The system might
degrade somehow" is not an acceptable degradation specification.

---

## 9.3 Security Rules (SEC)

**SEC-001:** No secret is hardcoded in any file in the repository.
Any pattern matching a known secret format blocks the CI/CD gate.

**SEC-002:** The Secrets Service is the only component that reads environment
variables for secret values. Direct os.environ access for secrets is forbidden.

**SEC-003:** Secrets are cleared from os.environ after loading.
This prevents subprocess inheritance of secrets.

**SEC-004:** All database queries use parameterized statements.
String concatenation to build SQL is forbidden. Period.

**SEC-005:** All external input is validated before use. Telegram command arguments,
API responses, file contents — all validated before passing to business logic.

**SEC-006:** Authentication and authorization are never bypassed, even in development mode.
The only exception is TEST mode, where all external calls are mocked.

**SEC-007:** TLS certificate verification is ENABLED in production.
It may not be disabled via configuration in PRODUCTION mode.

**SEC-008:** Audit records are immutable. The audit table has no UPDATE or DELETE
operations in any application code path.

**SEC-009:** The Telegram whitelist is loaded from environment variables.
It is not a configuration value in config.py (to prevent accidental git commit).

**SEC-010:** Security events (authentication failures, authorization denials,
unauthorized Telegram messages) are counted and alerted at threshold.
5 failures in 60 seconds triggers a Telegram alert to operators.

**SEC-011:** Zero CRITICAL CVEs in any dependency at any time.
A dependency with a CRITICAL CVE must be patched or removed within 24 hours.

**SEC-012:** OWASP Top 10 compliance is a prerequisite for Level 4 certification.
Any OWASP Top 10 violation found in security audit blocks production authorization.

---

## 9.4 Performance Rules (PERF)

**PERF-001:** Every latency-sensitive operation is measured with the Timer Service.
Unmeasured latency is not managed latency.

**PERF-002:** Performance regressions of more than 20% block CI/CD merges.
A merge that causes GlobalIntelligence latency to regress from 17ms to 21ms is rejected.

**PERF-003:** The 200ms full-cycle SLA is a hard constraint.
If a cycle consistently exceeds 200ms, the Architecture Council must investigate.
No new capability may be added to the cycle until the SLA is restored.

**PERF-004:** Cache misses are measured and reported.
A cache hit rate below 80% is investigated. Stale TTLs and eviction pressures are tuned.

**PERF-005:** Blocking I/O on the critical trading path is forbidden.
All I/O on the path from GlobalIntelligence to OrderManager is either cached,
pre-warmed, or fire-and-forget.

**PERF-006:** No synchronous HTTP request on the trading path has infinite timeout.
All HTTP operations specify a timeout. Default: 8 seconds.

**PERF-007:** Memory allocations in hot paths (decision engine, risk computation)
are minimized. Object pooling or pre-allocation is used where measurement
shows allocation overhead.

**PERF-008:** Performance benchmarks are run on every wave completion.
Results are recorded and compared to the previous wave. Regressions are flagged.

**PERF-009:** The background pre-warm thread for GlobalDataAI must be running
at all times during market hours. A crashed pre-warm thread is logged as ERROR.

**PERF-010:** The kill switch response path (RiskGuardian → OrderManager halt)
has zero I/O, zero network calls, zero database writes.
It is an in-memory state flag check only.

---

## 9.5 Recovery Rules (RCV)

**RCV-001:** Every recovery action is recorded in the Audit Service.
Silent recovery (recovering without logging) is forbidden.

**RCV-002:** Recovery is bounded. If recovery fails 3 consecutive times,
it escalates to operator alert. Recovery does not loop indefinitely.

**RCV-003:** The Recovery Service runs before any business logic at startup.
Business logic must not start until recovery is complete.

**RCV-004:** Paper trades CSV is always reconcilable from SQLite.
The Storage Service is the source of truth. The CSV is a derived view.

**RCV-005:** Learning state is always recoverable from trd_executions.
Win rates and Sharpe ratios can always be recomputed from raw trade outcomes.

**RCV-006:** In-flight trades at crash time are marked INCOMPLETE, not retried.
Trade re-execution after recovery requires explicit operator authorization.

**RCV-007:** Recovery procedures are idempotent. Running recovery twice
produces the same result as running it once.

**RCV-008:** Recovery audit records include: what was lost, what was recovered,
what was unrecoverable. Partial recovery is clearly documented.

**RCV-009:** The recovery procedure for each scenario is written in a runbook
(Appendix F). A scenario without a runbook is a gap that must be closed.

**RCV-010:** Recovery time objective (RTO) for container restart: < 120 seconds.
From Docker restart to first trading cycle: < 2 minutes.

---

## 9.6 Monitoring Rules (MON)

**MON-001:** Every infrastructure service is registered with the Health Service.
An unregistered service is an unmonitored service and is not allowed in production.

**MON-002:** Health check functions are lightweight. A health check that takes
more than 100ms is a design defect.

**MON-003:** Health check functions do not perform writes. Health checks are
read-only. A health check that modifies state contaminates the monitoring channel.

**MON-004:** All alert thresholds are sourced from config.py. Hardcoded alert
thresholds are forbidden.

**MON-005:** Alert routing is tested. Every alert path (WARN → log, ERROR → Telegram,
CRITICAL → immediate halt) has a corresponding integration test.

**MON-006:** The Monitoring Service does not take trading actions. It observes and
reports. Trading halts are triggered by the kill switch (RiskGuardian), not by
the Monitoring Service.

**MON-007:** Monitoring service failures do not halt the trading system.
The Monitoring Service is CORE, not CRITICAL. Its failure degrades observability
but does not stop trading.

**MON-008:** Monitoring history is retained for 90 days. Trend analysis requires
sufficient history. Single-day retention is insufficient.

**MON-009:** Docker health check integration is mandatory for production.
The container must report HEALTHY before being considered operationally ready.

**MON-010:** All dashboards and monitoring interfaces are read-only.
No dashboard interaction can trigger a trading action.

---

## 9.7 Logging Rules (LOG)

**LOG-001:** All log output goes through the Logging Service.
Direct print(), sys.stdout.write(), or file open/write for logging is forbidden.

**LOG-002:** Log levels are used correctly.
DEBUG: development-only detail. INFO: normal operation. WARNING: abnormal but handled.
ERROR: requires investigation. CRITICAL: requires immediate action.

**LOG-003:** Every log record includes: timestamp, component, and message.
Records from within a trading cycle also include: cycle_id.

**LOG-004:** Sensitive data is never logged.
The Sensitive Data Redactor is always active. Its redaction list cannot be emptied.

**LOG-005:** Log file rotation is daily. Retention is 30 days.
Log files older than 30 days are automatically deleted.

**LOG-006:** Logging failures are silent and handled gracefully.
A log write failure does not raise an exception or halt the calling component.
Logging failures are written to stderr instead.

**LOG-007:** Structured logging (key=value pairs in context) is preferred
over unstructured messages. Structured records are machine-queryable.

**LOG-008:** Stack traces are included in ERROR and CRITICAL records.
A bare error message without a stack trace is insufficient for debugging.

**LOG-009:** Log configuration (level, format, rotation) is in config.py.
Hardcoded log configuration in module code is forbidden.

**LOG-010:** Production log files are never committed to git.
Log files are in .gitignore. Any accidental commit of a log file is rejected.

---

## 9.8 Configuration Rules (CFG)

**CFG-001:** All system-wide trading behavior constants are in config.py.
No module defines its own copy of a system-wide constant.

**CFG-002:** Configuration is immutable after startup.
No component modifies its configuration during operation.

**CFG-003:** Every constant in config.py has an inline comment explaining:
what it controls, valid range, and effect of out-of-range values.

**CFG-004:** Kill switch thresholds (KILL_SWITCH_VIX, KILL_SWITCH_DAILY_LOSS_PCT)
are in config.py. They may not be moved to environment variables.

**CFG-005:** The DECISION_THRESHOLD is in config.py.
It may not be moved to environment variables.

**CFG-006:** Configuration validation occurs before the Configuration Service
produces its snapshot. Invalid configuration aborts startup immediately.

**CFG-007:** Default values are defined for all OPTIONAL configuration.
Required configuration without defaults raises ConfigurationMissingError.

**CFG-008:** Boolean configuration values use ool type annotation.
Strings "true"/"false" or integers 0/1 for boolean values are forbidden.

**CFG-009:** Configuration keys use UPPER_SNAKE_CASE consistently.
Mixed case, camelCase, or hyphenated config keys are forbidden.

**CFG-010:** Configuration that can reasonably vary between environments
(logging level, benchmark targets) uses environment variable override.
Configuration that must be consistent across environments (thresholds, decision logic)
uses config.py directly with no environment override.

---

## 9.9 Dependency Rules (DEP)

**DEP-001:** Infrastructure depends only on the Python standard library and declared
third-party packages. No undeclared package imports.

**DEP-002:** All third-party dependencies are pinned to exact versions in requirements.txt.
Unpinned dependencies (>=, ^, ~) are forbidden.

**DEP-003:** A new third-party dependency requires Security Officer review.
Dependencies with known CVEs at time of addition are not added.

**DEP-004:** The DI Container is the sole mechanism for service instantiation.
No service creates another service directly with ServiceName().

**DEP-005:** Singletons are always accessed through their factory functions.
get_feed_manager(), get_telegram_bot(), get_performance_tracker(),
get_regime_strategy_map() — these are the only legal access paths.

**DEP-006:** Infrastructure services do not import from any package above Layer 0.
An infrastructure module that imports from iios.strategy or iios.decision
is a dependency violation.

**DEP-007:** The import graph is verified on every commit.
Any commit that introduces a circular import or an upward layer dependency is blocked.

**DEP-008:** Service dependencies are declared in __manifest__.json.
An undeclared dependency (used in code but not in manifest) is a specification violation.

**DEP-009:** Test dependencies are separated from production dependencies.
equirements-dev.txt for test tools. equirements.txt for production only.

**DEP-010:** Unused dependencies are removed from requirements.txt quarterly.
An unused dependency expands the attack surface and increases CI/CD time.

---

## 9.10 Lifecycle Rules (LCL)

**LCL-001:** Services are started in dependency topological order.
A service must not start before all its declared dependencies are ACTIVE.

**LCL-002:** Services are stopped in reverse dependency topological order.
A service must not stop before all services that depend on it have stopped.

**LCL-003:** Every service has a startup timeout. A service that does not
become ACTIVE within its timeout is marked FAILED.

**LCL-004:** Every service has a graceful shutdown timeout. A service that
does not stop within its shutdown timeout is forcibly terminated.

**LCL-005:** SIGTERM triggers graceful shutdown. SIGKILL is reserved for
Docker forced termination. The system is designed to recover from SIGKILL
without data loss.

**LCL-006:** Startup banners and shutdown banners are always written to the log.
They serve as audit checkpoints for operational timeline reconstruction.

**LCL-007:** Retired services are moved to _deprecated/ and retained.
They are never deleted. Deletion of a historical service module requires
Architecture Council vote.

**LCL-008:** Service initialization errors are reported collectively.
If 3 services fail to initialize, all 3 failures are reported simultaneously.
The engineer does not have to restart 3 times to discover all failures.

**LCL-009:** Background threads started by services are daemon threads.
They do not prevent process shutdown when the main thread exits.
Exception: the Shutdown Manager explicitly joins non-daemon threads within timeout.

**LCL-010:** The startup sequence is deterministic.
The same code, same environment, same configuration always produces the same
startup sequence. Non-deterministic startup ordering is a design defect.

---

## 9.11 Governance Rules (GOV)

**GOV-001:** No production change without a passing CI/CD pipeline.
No exceptions, no manual overrides.

**GOV-002:** Protected infrastructure modules cannot be modified without
explicit Architecture Council instruction.

**GOV-003:** Every deployment to VPS must produce HEALTHY containers.
A non-HEALTHY post-deployment state is a deployment failure, not a warning.

**GOV-004:** Every infrastructure interface change has an EDR.
Interface changes without EDRs are unauthorized changes that must be reverted.

**GOV-005:** Audit records are immutable and permanent.
Deleting audit records requires Architecture Council unanimous vote and
a documented reason.

**GOV-006:** The infrastructure technical backlog is reviewed at every wave planning.
Items in the backlog for more than 2 waves are escalated for Architecture Council decision.

**GOV-007:** All operator Telegram commands are logged in the Audit Service.
No operator action in the system is unlogged.

**GOV-008:** Incidents are documented within 24 hours of occurrence.
An undocumented incident is an unlearned lesson.

**GOV-009:** No direct production database modification without Architecture Council approval.
All database changes go through the Migration Service.

**GOV-010:** Security findings are tracked in a dedicated security log.
Security findings are not mixed with general technical backlog items.

---

## 9.12 Scalability Rules (SCL)

**SCL-001:** Infrastructure interfaces do not assume single-process deployment.
All service interfaces are designed to work in a multi-process or multi-machine
configuration with implementation changes only.

**SCL-002:** The EventBus interface is designed for future Redis Pub/Sub backend.
No EventBus consumer assumes in-process delivery semantics.

**SCL-003:** The Cache Service interface is designed for future Redis backend.
No cache consumer assumes in-memory-only semantics.

**SCL-004:** The Storage Service interface is designed for future PostgreSQL backend.
No storage consumer assumes SQLite-specific behavior.

**SCL-005:** Horizontal scalability is designed before it is needed.
The transition from single-process to distributed deployment is a Wave 20
activity. The architecture is designed for it in Wave 2.

**SCL-006:** No global mutable state outside of declared singletons.
Module-level mutable dictionaries or lists that are modified by multiple
components are forbidden. All shared state is in a declared singleton.

**SCL-007:** Database queries do not return unbounded result sets.
All queries include pagination or explicit LIMIT clauses.

**SCL-008:** Event payloads are bounded in size.
An event payload must not exceed 64KB. Large data is stored in the database
and referenced by ID in the event.

**SCL-009:** Background thread count is bounded.
The total number of infrastructure background threads is bounded by configuration.
Unbounded thread creation (e.g., thread-per-request) is forbidden.

**SCL-010:** Memory usage is tested under sustained load.
A 1-hour sustained market simulation must not show unbounded memory growth.

---

## 9.13 Future Evolution Rules (FUT)

**FUT-001:** Infrastructure extension points are defined in Wave 2.
New services added in later waves attach to defined extension points,
not through modification of existing services.

**FUT-002:** The plugin architecture is forward-compatible.
A plugin written for IIOS v1.0 must work in IIOS v1.x without modification.

**FUT-003:** The Wave 20 institutional-grade features are designed into the
Wave 2 architecture. Feature flags disable them until Wave 20 activation.

**FUT-004:** Multi-exchange support (Wave 20) requires only new DataFeed plugins
and new symbol ontology entries. No core infrastructure changes.

**FUT-005:** Distributed deployment requires only EventBus and Cache Service
implementation replacement. No consumer changes.

**FUT-006:** Regulatory compliance features (audit export, immutable logs, access trails)
are built into the infrastructure from Wave 2. They are not retrofitted.

**FUT-007:** Machine learning model hosting (Wave 20) is supported through
a declared ML_MODEL_SERVICE extension point in the Feature Flag Service.

**FUT-008:** New Telegram commands are added through command handler registration.
Adding a command does not modify the TelegramBot class.

**FUT-009:** The certification service is extensible. New certification criteria
are added through new certification check modules, not through modifying existing checks.

**FUT-010:** Infrastructure versioning supports backward compatibility for 2 major versions.
Version N-2 infrastructure is still loadable in a Version N deployment for migration purposes.

---

*End of Part IX*

# PART X — INFRASTRUCTURE CERTIFICATION

## 10.0 Certification Philosophy

Infrastructure certification is the formal verification that the infrastructure
layer meets all engineering standards required for the business layers to operate
reliably and safely. Infrastructure certification is a prerequisite for
business-layer certification. No business layer can be certified until the
infrastructure it depends on is certified.

**Infrastructure Certification Levels:**
- **Level 0:** Not yet installed.
- **Level 1:** Installed and registered. Stub implementation.
- **Level 2:** Functional implementation. Basic tests pass.
- **Level 3:** Full implementation. 95%+ coverage. Quality gates pass.
- **Level 4:** Production-ready. Performance benchmarks pass. Security audit passes.
- **Level 5:** Institutional-grade. External audit passes. DR tested.

---

## 10.1 Configuration Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| CR-01 | config.py exists and all constants defined | Level 2 | File present, all keys present |
| CR-02 | Configuration Service initializes cleanly | Level 2 | No errors at startup |
| CR-03 | All required values have defaults or are present in env | Level 3 | Startup succeeds in clean env |
| CR-04 | Config validation catches range errors | Level 3 | Range tests pass |
| CR-05 | ConfigurationSnapshot is immutable | Level 3 | Mutation raises error |
| CR-06 | Kill switch thresholds sourced from config.py | Level 4 | Architecture invariants test |
| CR-07 | DECISION_THRESHOLD sourced from config.py | Level 4 | Architecture invariants test |
| CR-08 | All promotion criteria sourced from config.py | Level 4 | Architecture invariants test |
| CR-09 | No constant duplicated outside config.py | Level 4 | Grep scan |
| CR-10 | All constants have inline documentation | Level 4 | Code review |
| CR-11 | Config validation covers all critical ranges | Level 4 | Validation test suite |
| CR-12 | Environment override works for all supported keys | Level 4 | Integration test |

---

## 10.2 Infrastructure Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| IR-01 | All 46 infrastructure services registered | Level 3 | Service Registry count |
| IR-02 | All CRITICAL services in ACTIVE state at startup | Level 3 | Service Registry query |
| IR-03 | Lifecycle Manager starts services in dependency order | Level 3 | Startup sequence log |
| IR-04 | Service Registry accurately reflects service states | Level 3 | State consistency test |
| IR-05 | DI Container resolves all singletons correctly | Level 3 | DI resolution test |
| IR-06 | All 4 singletons accessible via factory functions | Level 4 | Architecture invariants test |
| IR-07 | Recovery Service runs before business logic | Level 4 | Startup sequence test |
| IR-08 | Graceful shutdown completes within 30 seconds | Level 4 | Shutdown timing test |
| IR-09 | SIGTERM triggers graceful shutdown | Level 4 | Integration test |
| IR-10 | Protected module checksums verified at startup | Level 4 | Checksum test |
| IR-11 | Exactly 5 debate agents registered | Level 4 | Architecture invariants test |
| IR-12 | Import graph acyclic and layer boundaries enforced | Level 4 | import_graph_analyzer |

---

## 10.3 Monitoring Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| MOR-01 | All services registered with Health Service | Level 3 | Health registry count |
| MOR-02 | Docker health check returns correct status | Level 3 | Docker healthcheck test |
| MOR-03 | SystemMonitor tracks per-layer latency | Level 3 | Metrics query |
| MOR-04 | Metrics Service records all built-in metrics | Level 3 | Metrics completeness test |
| MOR-05 | Alert routing tested for WARN/ERROR/CRITICAL | Level 4 | Alert routing test |
| MOR-06 | Telegram health alert sent on CRITICAL failure | Level 4 | Alert integration test |
| MOR-07 | Dashboard data source operational | Level 4 | Dashboard query test |
| MOR-08 | Cycle telemetry written correctly | Level 4 | Telemetry integration test |
| MOR-09 | Tracing captures all 17 layer spans | Level 4 | Trace completeness test |
| MOR-10 | 90-day metrics retention verified | Level 4 | Retention test |

---

## 10.4 Security Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| SR-01 | Zero secrets in code or config files | Level 2 | detect-secrets scan |
| SR-02 | Zero CRITICAL CVEs in dependencies | Level 2 | Dependabot report |
| SR-03 | Zero HIGH CVEs in dependencies | Level 3 | Dependabot report |
| SR-04 | Secrets cleared from os.environ after loading | Level 3 | Secrets Service test |
| SR-05 | All DB queries parameterized | Level 3 | Static analysis |
| SR-06 | Telegram whitelist enforced | Level 3 | Integration test |
| SR-07 | Authentication required for all commands | Level 4 | Command auth test |
| SR-08 | Authorization checked per command | Level 4 | Permission test |
| SR-09 | Audit records are immutable | Level 4 | Audit integrity test |
| SR-10 | OWASP Top 10 compliance verified | Level 4 | Security audit |
| SR-11 | Container runs as non-root user | Level 4 | Dockerfile review |
| SR-12 | TLS verification enabled in production | Level 4 | Certificate Service test |

---

## 10.5 Recovery Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| RCR-01 | Recovery Service runs at startup | Level 3 | Startup log check |
| RCR-02 | Incomplete cycle recovery works | Level 3 | Recovery integration test |
| RCR-03 | Paper trades CSV repair from SQLite | Level 3 | CSV recovery test |
| RCR-04 | Learning state reload from SQLite | Level 4 | State recovery test |
| RCR-05 | Docker restart after SIGKILL recovers cleanly | Level 4 | Kill/restart test |
| RCR-06 | Recovery audit records written correctly | Level 4 | Audit test |
| RCR-07 | RTO < 120 seconds verified | Level 4 | Timing test |
| RCR-08 | All recovery runbooks tested in staging | Level 4 | Runbook evidence |
| RCR-09 | Feed failover recovery verified | Level 4 | Feed failover test |
| RCR-10 | Database corruption recovery documented | Level 5 | DR drill record |

---

## 10.6 Performance Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| PER-01 | GlobalIntelligence p99 <= 17ms | Level 4 | Benchmark (100 samples) |
| PER-02 | MarketIntelligence p99 <= 19ms | Level 4 | Benchmark (100 samples) |
| PER-03 | Full cycle p99 <= 200ms | Level 4 | Benchmark (50 samples) |
| PER-04 | Database write p99 <= 5ms | Level 4 | Benchmark (1000 writes) |
| PER-05 | Kill switch response <= 100ms | Level 4 | Integration test (10 triggers) |
| PER-06 | EventBus p99 <= 1ms | Level 4 | Benchmark (10,000 events) |
| PER-07 | Cache hit p99 <= 0.5ms | Level 4 | Benchmark (10,000 lookups) |
| PER-08 | Memory < 400MB after 1h simulation | Level 4 | Load test |
| PER-09 | No performance regression > 20% vs baseline | Level 4 | CI/CD benchmark gate |
| PER-10 | Benchmark results stored in docs/performance/ | Level 4 | File presence check |

---

## 10.7 Operational Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| OPR-01 | Startup banner written to log | Level 3 | Log content test |
| OPR-02 | Shutdown banner written to log | Level 3 | Log content test |
| OPR-03 | All 13 Telegram commands functional | Level 4 | Command integration test |
| OPR-04 | Daily log rotation operational | Level 4 | Rotation test |
| OPR-05 | All 5 operational runbooks written | Level 4 | Runbook file presence |
| OPR-06 | Docker health check operational | Level 4 | Health check test |
| OPR-07 | EOD report generation functional | Level 4 | EOD report test |
| OPR-08 | VPS deployment HEALTHY in < 120s | Level 4 | Deployment timing test |
| OPR-09 | Startup Manager pre-market sequence complete | Level 4 | Startup log verification |
| OPR-10 | System restores state after container restart | Level 4 | Restart integration test |

---

## 10.8 Certification Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| CRT-01 | build_manifest.json current and complete | Level 3 | Manifest validator |
| CRT-02 | All packages have __manifest__.json | Level 3 | File presence scan |
| CRT-03 | All services have README.md | Level 3 | File presence scan |
| CRT-04 | Coverage >= 95% for all infrastructure packages | Level 4 | Coverage report |
| CRT-05 | All tests passing on main branch | Level 4 | CI/CD report |
| CRT-06 | Black/isort/flake8 all pass | Level 4 | CI/CD report |
| CRT-07 | mypy strict passes for core and security packages | Level 4 | mypy report |
| CRT-08 | Architecture invariants test suite passes | Level 4 | Test report |
| CRT-09 | Wave Completion Records filed for all waves | Level 4 | WCR file count |
| CRT-10 | Architecture Council certification vote recorded | Level 4 | Vote record in docs/ |

---

## 10.9 Production Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| PRD-01 | All Level 4 checks from matrices 10.1–10.8 PASS | Level 4 | Aggregated |
| PRD-02 | SYSTEM_CERTIFIED flag can be set | Level 4 | Certification Service |
| PRD-03 | Live trading authorization granted | Level 4 | Architecture Council |
| PRD-04 | Paper trading mode tested for 2+ weeks | Level 4 | P&L report evidence |
| PRD-05 | Kill switch tested in paper mode | Level 4 | Kill switch test record |
| PRD-06 | Feed failover tested in market hours | Level 4 | Failover test record |
| PRD-07 | No CRITICAL incidents in last 30 days (paper) | Level 4 | Incident log review |
| PRD-08 | Operator team trained on runbooks | Level 4 | Training completion |
| PRD-09 | Emergency rollback procedure tested | Level 4 | Rollback drill record |
| PRD-10 | Production authorization signed by all council members | Level 4 | Sign-off document |

---

## 10.10 Institutional Ready Certification Matrix

| # | Check | Required Level | Pass Condition |
|---|-------|----------------|----------------|
| INS-01 | External penetration test clean | Level 5 | Pen test report |
| INS-02 | Disaster recovery drill completed | Level 5 | DR drill record |
| INS-03 | Multi-exchange expansion tested | Level 5 | BSE/MCX integration test |
| INS-04 | Distributed EventBus operational | Level 5 | Redis integration test |
| INS-05 | PostgreSQL migration tested | Level 5 | DB migration test |
| INS-06 | 5,000-symbol capacity verified | Level 5 | Load test |
| INS-07 | 5-year data retention plan implemented | Level 5 | Retention architecture |
| INS-08 | Regulatory audit export functional | Level 5 | Export test |
| INS-09 | Automated trading compliance review | Level 5 | Compliance report |
| INS-10 | 99.9% uptime SLA evidence (3 months) | Level 5 | Uptime monitoring report |

---

## 10.11 Infrastructure Engineering Scorecard

**Scorecard Computation:**
Each certification matrix has 10-12 checks. Each check is scored:
- PASS: 1 point.
- FAIL: 0 points.
- N/A (check not applicable at current level): excluded from calculation.

**Maturity Score:**
`
Score = (PASS count / applicable checks) * 100

Score 95-100: Level 4 (Production-Ready)
Score 85-94:  Level 3 (Certified)
Score 70-84:  Level 2 (Integrated)
Score 50-69:  Level 1 (Development)
Score < 50:   Level 0 (Placeholder)
`

**Certification Scorecard Summary Template:**

| Matrix | Total Checks | Passed | Score | Level |
|--------|-------------|--------|-------|-------|
| Configuration Ready | 12 | ? | ?% | ? |
| Infrastructure Ready | 12 | ? | ?% | ? |
| Monitoring Ready | 10 | ? | ?% | ? |
| Security Ready | 12 | ? | ?% | ? |
| Recovery Ready | 10 | ? | ?% | ? |
| Performance Ready | 10 | ? | ?% | ? |
| Operational Ready | 10 | ? | ?% | ? |
| Certification Ready | 10 | ? | ?% | ? |
| Production Ready | 10 | ? | ?% | ? |
| Institutional Ready | 10 | ? | ?% | ? |
| **TOTAL** | **106** | **?** | **?%** | **?** |

**SYSTEM_CERTIFIED requires:** All 10 matrices at Level 4 (>= 95%) simultaneously.

---

*End of Part X*

---

# APPENDIX A — INFRASTRUCTURE CATALOG

Complete catalog of all 46 IIOS infrastructure services.

| Code | Service Name | Group | Classification | Wave | Owner |
|------|-------------|-------|----------------|------|-------|
| INFRA-CFG-001 | Configuration Service | A | CRITICAL | W2 | Platform |
| INFRA-ENV-001 | Environment Service | A | CRITICAL | W2 | Platform |
| INFRA-DI-001 | Dependency Injection Service | A | CRITICAL | W2 | Platform |
| INFRA-SRV-001 | Service Registry | B | CRITICAL | W2 | Platform |
| INFRA-CMP-001 | Component Registry | B | CORE | W2 | Platform |
| INFRA-LCM-001 | Lifecycle Manager | B | CRITICAL | W2 | Platform |
| INFRA-STR-001 | Startup Manager | B | CRITICAL | W2 | Platform |
| INFRA-SHD-001 | Shutdown Manager | B | CRITICAL | W2 | Platform |
| INFRA-HLT-001 | Health Service | C | CRITICAL | W2 | Platform |
| INFRA-DGN-001 | Diagnostics Service | C | CORE | W2 | Platform |
| INFRA-MON-001 | Monitoring Service | C | CORE | W2 | Platform |
| INFRA-LOG-001 | Logging Service | C | CRITICAL | W2 | Platform |
| INFRA-MTR-001 | Metrics Service | C | CORE | W2 | Platform |
| INFRA-TRC-001 | Tracing Service | C | OPTIONAL | W8 | Platform |
| INFRA-AUD-001 | Audit Service | C | CORE | W2 | Platform |
| INFRA-IDN-001 | Identity Service | D | CORE | W2 | Security |
| INFRA-ATH-001 | Authentication Service | D | CORE | W2 | Security |
| INFRA-AZN-001 | Authorization Service | D | CORE | W2 | Security |
| INFRA-SEC-001 | Secrets Service | D | CRITICAL | W2 | Security |
| INFRA-ENC-001 | Encryption Service | D | CORE | W2 | Security |
| INFRA-CRT-001 | Certificate Service | D | OPTIONAL | W8 | Security |
| INFRA-CLK-001 | Clock Service | E | CRITICAL | W2 | Platform |
| INFRA-SCH-001 | Scheduler Service | E | CORE | W2 | Platform |
| INFRA-TMR-001 | Timer Service | E | CORE | W2 | Platform |
| INFRA-UUID-001 | UUID Service | E | CRITICAL | W2 | Platform |
| INFRA-FIL-001 | File Service | E | CORE | W2 | Platform |
| INFRA-RSR-001 | Resource Service | E | CORE | W2 | Platform |
| INFRA-EVT-001 | Event Bus | F | CRITICAL | W2 | Platform |
| INFRA-MSG-001 | Message Bus | F | OPTIONAL | W8 | Platform |
| INFRA-NTF-001 | Notification Service | F | CORE | W2 | Platform |
| INFRA-CAC-001 | Cache Service | F | CORE | W2 | Platform |
| INFRA-STG-001 | Storage Service | F | CRITICAL | W2 | Platform |
| INFRA-PLG-001 | Plugin Service | G | OPTIONAL | W8 | Platform |
| INFRA-EXT-001 | Extension Service | G | OPTIONAL | W8 | Platform |
| INFRA-RCV-001 | Recovery Service | G | CORE | W2 | Platform |
| INFRA-EXC-001 | Exception Service | G | CRITICAL | W2 | Platform |
| INFRA-RTY-001 | Retry Service | G | CORE | W2 | Platform |
| INFRA-CIB-001 | Circuit Breaker | G | CORE | W2 | Platform |
| INFRA-FFG-001 | Feature Flag Service | G | OPTIONAL | W8 | Platform |
| INFRA-VER-001 | Version Service | G | CORE | W2 | Platform |
| INFRA-MIG-001 | Migration Service | G | CORE | W2 | Platform |
| INFRA-CPT-001 | Compatibility Service | G | OPTIONAL | W8 | Platform |
| INFRA-CVL-001 | Config Validation Service | G | CRITICAL | W2 | Platform |
| INFRA-IVL-001 | Infrastructure Validation Service | G | CRITICAL | W2 | Platform |
| INFRA-EVL-001 | Engineering Validation Service | G | OPTIONAL | W8 | Platform |
| INFRA-CST-001 | Certification Service | G | OPTIONAL | W17 | Platform |

**Summary:** 46 services. CRITICAL: 15. CORE: 22. OPTIONAL: 9.

---

# APPENDIX B — SERVICE DEPENDENCY MATRIX

Services in rows depend on services in columns (Y = depends on).

`
              CFG ENV DI  SRV CMP LCM STR SHD HLT DGN MON LOG MTR TRC AUD SEC ATH AZN SEK ENC CLK SCH TMR UUID FIL STG CAC EVT NTF RSR RCV EXC RTY CIB
Config.Svc.   --  Y   --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
Env.Svc.      --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
DI.Svc.       Y   --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
Svc.Reg.      --  --  --  --  --  --  --  --  --  --  --  Y   --  --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
Cmp.Reg.      --  --  --  Y   --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --   --  --  --  Y   --  --  --  --  --  --
Lifecycle     Y   Y   Y   Y   --  --  --  --  --  --  --  Y   --  --  --  --  --  --  --  --  --  --  --  --   --  --  --  Y   --  --  --  --  --  --
Startup       Y   Y   --  --  --  Y   --  --  Y   --  --  Y   --  --  --  --  --  --  --  --  Y   Y   --  --   --  --  --  Y   Y   --  Y   --  --  --
Shutdown      --  --  --  Y   --  Y   --  --  --  --  --  Y   Y   --  --  --  --  --  --  --  --  --  --  --   --  Y   --  Y   Y   --  --  --  --  --
Health        --  --  --  Y   --  --  --  --  --  --  --  Y   Y   --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
Diagnostics   --  --  --  --  --  --  --  --  Y   --  --  --  Y   --  --  Y   Y   Y   --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
Monitoring    --  Y   --  --  --  --  --  --  --  --  --  Y   Y   --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  Y   --  --  --  --  --
Logging       --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --   Y   Y   --  --  --  --  --  --  --  --
Metrics       --  --  --  --  --  --  --  --  --  --  --  Y   --  --  --  --  --  --  --  --  --  --  --  --   --  Y   --  --  --  --  --  --  --  --
Audit         --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  Y    --  Y   --  --  --  --  --  --  --  --
Secrets       --  Y   --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  Y   --  --  --  --   --  --  --  --  --  --  --  --  --  --
Encryption    --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
Clock         Y   --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
EventBus      --  --  --  --  --  --  --  --  --  --  --  Y   Y   --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
Storage       Y   --  --  --  --  --  --  --  --  --  --  Y   Y   --  --  --  --  --  --  --  --  --  --  --   Y   --  --  --  --  --  --  --  --  --
Cache         Y   --  --  --  --  --  --  --  --  --  --  --  Y   --  --  --  --  --  --  --  --  --  --  --   --  --  --  --  --  --  --  --  --  --
`

---

# APPENDIX C — LIFECYCLE REFERENCE

**Quick Reference: Infrastructure Service Lifecycle Transitions**

`
NOT_INSTALLED
     | (code deployed + manifest valid)
     v
INSTALLED
     | (process starts + register() called)
     v
REGISTERED
     | (dependencies resolved + __init__() called)
     v
INITIALIZED
     | (configuration applied from ConfigurationSnapshot)
     v
CONFIGURED
     | (external connections + threads + health registered)
     v
ACTIVE        <-------- DEGRADED (partial failure, auto-recovery)
     |                      ^
     |                      | (auto-recover)
     | (component failure)  |
     v                      |
  CRITICAL ----------------+  (approaching failure)
     |
     | (failure threshold exceeded)
     v
  FAILED -----> Recovery Service attempts recovery
     |               |
     |           [recovery succeeds] -> ACTIVE
     |           [recovery fails]    -> remains FAILED + alert
     |
     | (SIGTERM or graceful shutdown)
     v
  SHUTTING_DOWN
     |
     v
  STOPPED
     |
     | (deprecated, moved to _deprecated/)
     v
  RETIRED
`

---

# APPENDIX D — PERFORMANCE REFERENCE

**Infrastructure Performance Reference Card**

| Service | Key Metric | P99 Target | Breach Action |
|---------|-----------|------------|---------------|
| Configuration | get_snapshot() | < 0.1ms | None (read-only) |
| EventBus | publish() | < 0.1ms | Investigate thread pool |
| EventBus | dispatch | < 1ms | Increase thread pool |
| Storage | write | < 5ms | Investigate disk/WAL |
| Storage | read | < 2ms | Add index |
| Logging | record() | < 0.5ms | Async flush |
| Cache | get() (hit) | < 0.5ms | Investigate memory |
| Health | is_healthy() | < 1ms | Read from HealthCache |
| SystemMonitor | time_layer() overhead | < 0.1ms | None |
| DataFeedManager | quote (Dhan) | < 200ms | Check CB_DHAN_API |
| DataFeedManager | quote (Yahoo) | < 3,000ms | Timeout circuit |
| Secrets | get() | < 0.1ms | In-memory lookup |
| UUID | generate() | < 0.1ms | None |
| Timer | start/stop | < 0.01ms | None |
| Clock | now() | < 0.01ms | None |

---

# APPENDIX E — FAILURE TAXONOMY

**Infrastructure Failure Classification**

| Failure Class | Examples | Survivable | Auto-Recovery |
|---------------|---------|------------|---------------|
| TRANSIENT | Network timeout, DB lock | Yes | Retry policy |
| RESOURCE | Memory OOM, disk full | Partial | Resource protection |
| CONFIGURATION | Missing config, wrong type | No | ABORT startup |
| SECURITY | Auth failure, secret missing | No | ABORT |
| DATA | DB corruption, CSV corrupt | Partial | Recovery Service |
| LOGIC | Programming error, bug | Partial | Exception Service |
| EXTERNAL | API down, broker 451 | Yes | Circuit breaker |
| DEPENDENCY | Dependent service failed | Partial | Lifecycle Manager |

**Failure Severity Matrix:**

| Class | Severity | Response Time | Escalation |
|-------|---------|---------------|------------|
| TRANSIENT | LOW | 30s auto-recover | None |
| RESOURCE | MEDIUM | 5min | Operator WARN |
| CONFIGURATION | CRITICAL | Immediate | ABORT |
| SECURITY | CRITICAL | Immediate | Operator CRITICAL + halt |
| DATA | HIGH | 2min | Operator alert |
| LOGIC | HIGH | Next deploy | Operator alert |
| EXTERNAL | MEDIUM | 60s auto-recover | Operator WARN |
| DEPENDENCY | HIGH | Cascade check | Depends on dep |

---

# APPENDIX F — RECOVERY WORKFLOWS

**Recovery Workflow RF-001: Container Crash Recovery**
`
Trigger: Docker detects container stopped.
Action:  Docker restarts (restart: unless-stopped).
Step 1:  main.py starts.
Step 2:  Infrastructure starts (phases 1-10).
Step 3:  Recovery Service runs:
         - Checks sys_cycles for INCOMPLETE.
         - Reconciles paper_trades.csv with SQLite.
         - Reloads learning state from SQLite.
Step 4:  Normal market-hours startup (if within hours).
Step 5:  RECOVERY_EXECUTED audit event written.
Step 6:  Telegram notification: "System recovered from crash. N items recovered."
Expected Duration: < 120 seconds.
`

**Recovery Workflow RF-002: Data Feed Failure Recovery**
`
Trigger: Dhan API returns 451 or times out repeatedly.
Action:  Circuit breaker opens. Failover to yfinance.
Step 1:  CB_DHAN_API records failure count.
Step 2:  Failure threshold exceeded: CB_DHAN_API opens.
Step 3:  FEED_FAILOVER event published to EventBus.
Step 4:  DataFeedManager switches to YahooFeed.
Step 5:  Operator receives Telegram alert: "Feed failover to yfinance."
Step 6:  CB_DHAN_API half-opens after reset_timeout.
Step 7:  One test request sent to Dhan.
Step 8:  If success: FEED_PRIMARY_RESTORED event. Operator notified.
Expected Duration: < 30 seconds automatic recovery.
`

**Recovery Workflow RF-003: Kill Switch Manual Reset**
`
Trigger: Operator sends /resume command via Telegram.
Pre-condition: Kill switch was triggered. Triggering condition is resolved.
Step 1:  Authentication + Authorization check (OPERATOR role required).
Step 2:  Diagnostics Service verifies current VIX and daily P&L.
Step 3:  If VIX still > 45.0 or loss still > 2.0%: REJECT resume, send reason.
Step 4:  If conditions resolved: set KILL_SWITCH_ACTIVE = False.
Step 5:  KILL_SWITCH_RESET audit event written.
Step 6:  OrderManager re-enabled for new orders.
Step 7:  Telegram confirmation: "Kill switch reset. System resumed."
Step 8:  Monitor for 15 minutes before next trade.
`

**Recovery Workflow RF-004: Database Corruption Recovery**
`
Trigger: SQLite PRAGMA integrity_check returns errors.
Action:  System halts. Operator intervenes.
Step 1:  System detects integrity check failure at startup.
Step 2:  ABORT startup. Telegram: "DB integrity failure. Manual intervention required."
Step 3:  Operator identifies latest clean backup: ls data/backups/iios.db.*
Step 4:  Operator stops containers: docker compose down.
Step 5:  Operator copies backup: cp data/backups/iios.db.{date} data/iios.db.
Step 6:  Operator verifies: sqlite3 data/iios.db "PRAGMA integrity_check;"
Step 7:  Operator starts containers: docker compose up -d.
Step 8:  Verify HEALTHY. Record incident in docs/certification/incidents.md.
`

**Recovery Workflow RF-005: Learning State Corruption**
`
Trigger: StrategyPerformanceTracker singleton cannot load from SQLite.
Action:  Bootstrap from raw trade history.
Step 1:  Load all trd_executions from the last 30 days.
Step 2:  Recompute win rate per strategy from raw outcomes.
Step 3:  Recompute Sharpe ratio per strategy from raw returns.
Step 4:  Reconstruct RegimeStrategyMap from historical regime + outcome data.
Step 5:  Write reconstructed state to SQLite.
Step 6:  RECOVERY_EXECUTED audit event written.
Step 7:  Log: "Learning state reconstructed from {N} trade records."
`

---

# APPENDIX G — OPERATIONAL RUNBOOK

**Daily Operations Checklist:**
`
08:00 IST: [ ] Startup Manager pre-market initialization log present.
08:07 IST: [ ] Telegram startup confirmation received.
09:15 IST: [ ] Market open signal in log: "MarketMonitor: OPEN"
09:30 IST: [ ] First cycle telemetry written to database.
11:00 IST: [ ] Run /health: expect all green.
13:00 IST: [ ] Run /pnl: review intraday P&L.
15:30 IST: [ ] Market close signal in log: "MarketMonitor: CLOSE"
15:45 IST: [ ] EOD learning cycle completion log present.
16:00 IST: [ ] Run /perf: verify strategy win rates current.
17:00 IST: [ ] EOD report delivered to Telegram.
`

**Weekly Operations Checklist:**
`
Monday:  [ ] Review health metrics for past week.
Monday:  [ ] Review alert history: any ERROR or CRITICAL alerts?
Tuesday: [ ] Check CVE report: any new vulnerabilities in deps?
Wednesday: [ ] Review cycle success rate: target >= 99.5%.
Thursday: [ ] Review strategy performance: any strategies at auto-disable threshold?
Friday:  [ ] Verify data/ directory size: growing within budget?
Friday:  [ ] Verify log directory size: 30-day rotation working?
Friday:  [ ] Run full test suite on staging environment.
`

**Emergency Response:**
`
System CRITICAL alert received via Telegram:
  1. Run /health — identify failing component.
  2. Run /diag — get detailed diagnostic report.
  3. Check: docker logs ai-trading-brain --tail=100
  4. Identify: is it a transient failure or persistent?
     - Transient: wait 2 minutes for auto-recovery. Check /health again.
     - Persistent: follow specific runbook for the failing component.
  5. If trading must halt immediately: send /safe (activates safe mode).
  6. Document the incident in docs/certification/incidents.md.
`

---

# APPENDIX H — INFRASTRUCTURE ANTI-PATTERNS

**AP-INFRA-01: Singleton by Accident**
*Pattern:* A class is instantiated at module import time, making it a de-facto singleton
through Python module caching. No factory function declared.
*Problem:* Singleton guarantee is fragile. Test override is impossible.
*IIOS Rule:* All singletons are registered in DI Container with factory functions.

**AP-INFRA-02: Configuration Scatter**
*Pattern:* Configuration values defined in: config.py, environment variables parsed
directly in modules, class-level constants, and hardcoded magic numbers.
*Problem:* Changing a threshold requires hunting through many files.
*IIOS Rule:* All system-wide constants in config.py. All modules import from config.

**AP-INFRA-03: Infrastructure Importing Business Logic**
*Pattern:* The Logging Service imports from iios.strategy to format strategy names.
*Problem:* Circular dependency. Infrastructure becomes tightly coupled to business logic.
*IIOS Rule:* Infrastructure depends on nothing above Layer 0. Business logic formats
its own types for infrastructure consumption (e.g., str(strategy) before logging).

**AP-INFRA-04: Resilience as Afterthought**
*Pattern:* Infrastructure services are implemented without fault modes.
Retries, circuit breakers, and graceful degradation are added after the first
production incident.
*Problem:* The first production incident exposes all missing resilience.
*IIOS Rule:* Every service declares its failure modes before implementation begins.

**AP-INFRA-05: Unbounded Growth**
*Pattern:* Log files accumulate indefinitely. SQLite database grows without pruning.
Metrics history is retained forever.
*Problem:* Disk exhaustion is a guaranteed failure if not managed.
*IIOS Rule:* All storage has explicit retention policies. Resource Service monitors disk.

**AP-INFRA-06: The Shared Mutable Infrastructure State**
*Pattern:* Multiple components write to a module-level dictionary or list
(e.g., ctive_positions = {} at module level in some infrastructure module).
*Problem:* Thread safety issues. Testing requires state reset between tests.
*IIOS Rule:* All shared state is encapsulated in a declared service with controlled access.

**AP-INFRA-07: Silent Exception Swallowing**
*Pattern:* Infrastructure catches exceptions and returns None or default values
without logging the exception.
*Problem:* The calling component has no idea why it received None or a default.
Debugging becomes a nightmare.
*IIOS Rule:* Every exception is logged with full context. Exception Service handles routing.

**AP-INFRA-08: Missing Health Check Registration**
*Pattern:* An infrastructure service is added but its health check is not registered.
The Health Service does not know this service exists.
*Problem:* The service can fail silently. The system reports HEALTHY while a service is FAILED.
*IIOS Rule:* Every service registers a health check. Missing registration blocks certification.

**AP-INFRA-09: Synchronous Shutdown on SIGKILL Path**
*Pattern:* The shutdown handler tries to do complex work (write to database,
send Telegram message) that may block when SIGKILL is imminent.
*Problem:* SIGKILL arrives before shutdown completes, leaving partial state.
*IIOS Rule:* Critical state is written incrementally during operation, not only at shutdown.

**AP-INFRA-10: Version Drift**
*Pattern:* requirements.txt is updated rarely. Some dependencies drift 10+ patch versions
behind the pinned version over months.
*Problem:* A large batch update introduces multiple simultaneous regressions.
*IIOS Rule:* Dependencies are reviewed monthly. Each update is a separate commit.

---

# APPENDIX I — GLOSSARY

**Audit Service:** The infrastructure component that maintains an immutable,
append-only record of all business-significant events.

**Cache Service:** The in-memory cache with TTL and LRU eviction. Used by
GlobalDataAI (5-minute TTL) and DataFeedManager (10-second quote cache).

**Circuit Breaker:** The fault-isolation pattern that prevents cascading failures.
Has three states: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery).

**Clock Service:** The single source of time for all IIOS components.
Testable via injectable fake clock.

**Component Registry:** The runtime catalog of all AI agents, strategies, and plugins.
Enforces the 5-debate-agent invariant.

**Configuration Snapshot:** The immutable frozen snapshot of all configuration values
produced by the Configuration Service at startup. Configuration is not re-read at runtime.

**CRITICAL (classification):** Infrastructure services whose absence blocks system startup
and trading. They must be ACTIVE before the first trading cycle.

**Dead Letter Queue:** The storage location for events that could not be delivered to
any subscriber by the EventBus.

**DI Container:** The Dependency Injection Container that manages service lifetimes
and resolves dependencies.

**Event Bus:** The in-process publish/subscribe messaging infrastructure used for
decoupled cross-layer communication.

**Exception Service:** The centralized exception handler and reporter. Routes exceptions
to appropriate handlers without silencing them.

**Feature Flag Service:** The runtime mechanism for enabling and disabling features
without code deployment.

**File Service:** The filesystem abstraction providing atomic writes and OS-independent
path handling.

**Health Service:** The aggregator of component health reports. Provides health to
Docker, dashboard, and Telegram.

**Identity Service:** The manager of all operator, scheduled task, and external
system identities.

**Infrastructure Validation Service:** The pre-startup validator that verifies all
infrastructure components are operational before trading begins.

**Lifecycle Manager:** The orchestrator of service startup and shutdown in dependency order.

**Logging Service:** The single log output channel for all IIOS components.
Includes sensitive data redaction and context propagation.

**Message Bus:** The point-to-point request/reply messaging complement to the EventBus.

**Metrics Service:** The collector and aggregator of numeric performance measurements.

**Migration Service:** The manager of database schema migrations, applied automatically at startup.

**Monitoring Service:** The continuous observer of infrastructure and business metrics
that triggers alerts at threshold violations.

**Notification Service:** The outbound notification channel, primarily Telegram.
Rate-limited for INFO, bypass for CRITICAL.

**Plugin Service:** The discovery and lifecycle manager for optional IIOS plugins.

**Recovery Service:** The startup-time service that identifies and recovers incomplete
state from crashed or killed processes.

**Resource Service:** The resource monitor that enforces memory, CPU, and disk budgets.

**Retry Service:** The library of configurable retry policies for transient failures.

**Scheduler Service:** The time-based task executor that replaces ad-hoc sleep loops.

**Secrets Service:** The sole accessor of secret values from environment variables.
No other service reads secrets directly.

**Service Registry:** The authoritative runtime catalog of all registered services
and their current states.

**Storage Service:** The SQLite abstraction layer. Manages connection pool,
migrations, and all SQL operations.

**Timer Service:** The high-precision latency measurement service. Backend for
SystemMonitor's 	ime_layer() context manager.

**Tracing Service:** The execution trace recorder that correlates operations across
all 17 layers within a single trading cycle.

**UUID Service:** The centralized unique identifier generator. Supports test
determinism through injectable sequences.

**Version Service:** The package version tracker and compatibility checker.

---

# DOCUMENT METRICS

| Metric | Value |
|--------|-------|
| Document Code | IIOS-CIS-001 |
| Version | 1.0 |
| Status | FINAL |
| Total Parts | X (10 Parts) |
| Total Appendices | 9 (A-I) |
| Infrastructure Services Defined | 46 |
| CRITICAL Services | 15 |
| CORE Services | 22 |
| OPTIONAL Services | 9 |
| Service Groups | 7 (A through G) |
| Infrastructure Rules (INFRA) | 10 |
| Reliability Rules (REL) | 10 |
| Security Rules (SEC) | 12 |
| Performance Rules (PERF) | 10 |
| Recovery Rules (RCV) | 10 |
| Monitoring Rules (MON) | 10 |
| Logging Rules (LOG) | 10 |
| Configuration Rules (CFG) | 10 |
| Dependency Rules (DEP) | 10 |
| Lifecycle Rules (LCL) | 10 |
| Governance Rules (GOV) | 10 |
| Scalability Rules (SCL) | 10 |
| Future Evolution Rules (FUT) | 10 |
| Total Constitution Rules | 132 |
| Certification Matrices | 10 |
| Recovery Workflows | 5 |
| Anti-Patterns Documented | 10 |
| Startup Phases | 11 |

---

# AMENDMENT HISTORY

| Amendment | Date | Description | Authority |
|-----------|------|-------------|-----------|
| Initial Release | 2026 | Complete infrastructure specification | Architecture Council |
| (future amendments here) | — | — | Architecture Council |

---

# CLOSING STATEMENT

The Core Infrastructure Specification defines with engineering precision every
foundational service upon which the Investment Intelligence Operating System is built.

Before any trade decision, before any regime classification, before any agent
debates a signal — the infrastructure defined in this document is running, healthy,
and observable. It loads the configuration, manages the secrets, routes the events,
persists the state, monitors the health, enforces the security, and recovers from failures.

Infrastructure is invisible when it works. This document ensures it always works.

The 46 services catalogued here, the 140-rule Engineering Constitution, the 10
certification matrices, and the 9 operational appendices together constitute the
complete engineering specification for the IIOS infrastructure foundation.

Every Wave 1-20 business component depends on this foundation.
This foundation is built once, correctly.

**IIOS-CIS-001 — END OF DOCUMENT**
