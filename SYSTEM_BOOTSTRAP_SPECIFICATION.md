# SYSTEM_BOOTSTRAP_SPECIFICATION.md

**Document Code:** IIOS-BSS-001
**Version:** 1.0
**Status:** CONTROLLED
**Classification:** Engineering Specification — Implementation Reference
**Issuing Authority:** Architecture Council
**System:** Investment Intelligence Operating System (IIOS)
**Layer Scope:** All 17 Layers — Startup Lifecycle
**Related Documents:** IIOS-IMP-001, IIOS-ENG-STD-001, IIOS-RCF-001, ARCHITECTURE.md

---

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2026-07-05 | Architecture Council | Initial issue. Complete bootstrap specification for all 17 layers. |

---

## Table of Contents

`
PART I    Bootstrap Philosophy ............................  Section 1
PART II   Bootstrap Architecture ..........................  Section 2
PART III  Bootstrap Sequence ..............................  Section 3
PART IV   Initialization Dependencies .....................  Section 4
PART V    Health Verification .............................  Section 5
PART VI   Failure Recovery ................................  Section 6
PART VII  Operational Modes ...............................  Section 7
PART VIII Engineering Constitution ........................  Section 8
PART IX   Readiness Checklist .............................  Section 9
APPENDIX A Bootstrap Timing Specifications ................  Appendix A
APPENDIX B Startup State Transition Diagrams ..............  Appendix B
APPENDIX C Glossary .......................................  Appendix C
`

---

# PART I — BOOTSTRAP PHILOSOPHY

## 1.1 Purpose of Bootstrap

Bootstrap is the process by which a system transforms from a state of
complete inertia — zero processes running, zero memory initialized, zero
connections established — into a state of verified operational readiness.
Bootstrap is not merely starting software. It is a controlled engineering
procedure that produces a system that is known, not assumed, to be ready.

For the Investment Intelligence Operating System, bootstrap carries a weight
beyond typical software systems. IIOS makes autonomous trading decisions.
A system that is partially initialized, incorrectly configured, or missing
critical knowledge components does not produce suboptimal decisions —
it produces incorrect decisions. An incorrect trading decision is a financial
event with real consequences.

For this reason, the IIOS bootstrap specification treats startup as a
first-class engineering discipline. Every stage is defined. Every dependency
is made explicit. Every failure condition is categorized and handled. Every
component that is ready announces its readiness through a defined protocol.
The system does not enter operational mode until all HARD startup requirements
are met. The system does not guess whether it is ready; it proves it.

Bootstrap serves four master purposes:
1. Establish the known-good starting state for every operational cycle.
2. Detect configuration, environment, and dependency problems before they
   affect trading decisions.
3. Provide a repeatable, auditable record of every startup event.
4. Guarantee that no trading activity begins until system integrity is certified.

---

## 1.2 System Startup Philosophy

The IIOS startup philosophy is captured in six principles that govern every
engineering decision in the bootstrap design:

**Principle 1 — Certify Before Operate**
The system does not operate until it certifies itself. Certification is a
structured process with defined inputs, defined checks, and a binary outcome:
CERTIFIED or NOT CERTIFIED. A system that fails certification does not enter
operational mode regardless of external pressure.

**Principle 2 — Explicit Over Implicit**
Every startup dependency is explicit. Every startup assumption is verified.
No component assumes that another component is ready because it was started
first. Every component queries the registry and confirms the readiness state
of its dependencies before consuming their services.

**Principle 3 — Ordered Over Concurrent**
Components that have dependency relationships start in dependency order.
Components that have no dependency relationship may start concurrently.
The startup sequence is not a sequence of time delays — it is a sequence
of dependency satisfactions. A component starts when its dependencies are
ready, not when a timer expires.

**Principle 4 — Fail Fast, Recover Smart**
Configuration errors, missing dependencies, and HARD startup failures cause
an immediate halt with a specific, actionable error message. The system
does not attempt to start with an invalid configuration. The system does
not attempt to work around a missing critical dependency. It fails cleanly,
reports precisely, and waits for human resolution.

**Principle 5 — Recovery Before Catastrophe**
Recoverable failures (network transients, temporary unavailability) are
handled with defined retry strategies and timeouts before escalating to
hard failure. The system distinguishes between a dependency that is
temporarily unavailable (retryable) and one that is permanently absent
(hard fail).

**Principle 6 — Audit Everything**
Every startup event is logged with a timestamp, component name, event type,
and outcome. The startup log is a complete engineering record of the system's
self-verification. Post-incident analysis begins with the startup log.

---

## 1.3 Deterministic Startup

Deterministic startup means that given the same environment, same configuration,
and same state of dependencies, the IIOS bootstrap process produces exactly
the same outcome every time. Not approximately the same — exactly the same.

**Properties of Deterministic Startup:**

Property 1 — Ordered Component Initialization
The startup sequence is defined and fixed. Component A always initializes
before Component B if B depends on A. This order never changes unless the
dependency graph changes (which requires an Engineering Decision Record).

Property 2 — Configuration Snapshot at Startup
All configuration values are read once at startup and stored in the
Configuration Snapshot. Runtime behavior uses the snapshot. Configuration
file changes during runtime are not reflected until the next restart.
This prevents mid-operation configuration drift.

Property 3 — Unique Startup Identifier
Every startup produces a unique Startup Identifier (UUID). All log events
and state records for that startup session are tagged with this identifier.
Two startups are never confused in the log record.

Property 4 — Fixed Timeout Hierarchy
Every startup operation has a defined timeout. Timeouts are not heuristic.
They are engineering-specified based on empirical measurement and
operational requirements. The timeout hierarchy is: operation < stage <
full bootstrap < emergency bootstrap.

Property 5 — Idempotent State Recovery
If the system restarts after a crash, the startup process recovers the
previous state correctly. The recovered state is identical to the state
that would exist if the crash had not occurred, subject to the data
that had been persisted to durable storage before the crash.

---

## 1.4 Dependency-First Initialization

Dependency-first initialization is the engineering discipline of starting
components in the order that satisfies their dependency relationships.
No component starts before all of its dependencies are ready.

**Dependency Readiness Protocol:**
A component's dependency is ready when the dependency has:
1. Completed its own initialization sequence.
2. Passed its self-health check.
3. Registered itself as READY in the Service Registry.
4. The registry has propagated the READY status to dependent components.

**Dependency Graph Management:**
The Dependency Resolver maintains the complete startup dependency graph.
The graph is a directed acyclic graph (DAG). Cycles in the dependency graph
are bootstrap-time errors that halt the startup process with a diagnostic
report identifying the cycle.

**Parallel Initialization:**
Components with no dependency relationship between them are initialized in
parallel to minimize total startup time. Parallelism is subject to:
- Resource constraints (maximum concurrent initializations: configurable).
- Dependency constraints (a component waits for its dependencies).
- Registry capacity (registry must accept all concurrent registrations).

**Startup Critical Path:**
The longest dependency chain defines the startup critical path. The critical
path determines the minimum possible startup time. Optimizing startup time
means optimizing the critical path, not parallelizing non-critical operations.

---

## 1.5 Fail-Fast Principles

Fail-fast is the engineering discipline of detecting failure as early as
possible and stopping immediately, rather than allowing the system to
continue into an undefined or inconsistent state.

**IIOS Fail-Fast Rules:**

Rule FF-1 — Validate Configuration Before Any Operation
Configuration validation runs before any other startup operation. A missing
or invalid configuration value causes startup to halt immediately with a
descriptive error identifying the specific missing or invalid value.

Rule FF-2 — Check Dependencies Before Consuming Them
Every component checks that its declared dependencies are registered as READY
before making any call to them. An unready dependency causes the component's
initialization to fail with a specific dependency-not-ready error.

Rule FF-3 — No Silent Degradation on HARD Requirements
HARD requirements are startup conditions that must be met for the system to
operate correctly. Missing a HARD requirement causes a fail-fast halt.
The system does not start in a degraded mode when a HARD requirement is missing.

Rule FF-4 — No Timeout Suppression
All startup operations have defined timeouts. Timeouts that expire cause
fail-fast. Suppressing a timeout (extending it indefinitely) is prohibited
without an Engineering Decision Record.

Rule FF-5 — Fail-Fast Messages Are Actionable
A fail-fast error message identifies: what failed, why it failed,
what configuration or environment change is needed to resolve it, and
the configuration key or component name involved. Vague error messages
("initialization failed") are forbidden.

---

## 1.6 Graceful Degradation

Graceful degradation defines how IIOS handles the absence of optional
components or the failure of non-critical services while still entering
a useful operational mode.

**Degradation Categories:**

DEGRADED-WARN: A non-critical service is unavailable. The system starts
with a WARNING in the startup log. All critical functions remain available.
The missing service's functions are suspended or replaced with a fallback.

DEGRADED-REDUCED: A significant but non-critical subsystem is unavailable.
The system starts with reduced functionality. Some trading strategies may
be suspended (strategies that depend on the unavailable subsystem).
The Architecture Council is notified.

DEGRADED-SAFE: A component whose absence creates risk is unavailable.
The system starts in SAFE MODE with severely reduced functionality.
Only position management and kill-switch monitoring remain active.
No new positions are opened.

**Degradation Governance:**
The decision to allow degraded startup is made by comparing the failing
component's classification against the degradation policy:
- CRITICAL classification → No degradation allowed. Fail-fast.
- IMPORTANT classification → DEGRADED-REDUCED allowed with notification.
- OPTIONAL classification → DEGRADED-WARN allowed without restriction.

**Primary-Fallback Pattern:**
The IIOS data feed layer implements the primary-fallback pattern. The Dhan
feed is the primary; yfinance is the fallback. If the Dhan feed is unavailable
at startup (returning 451 or timing out after defined retries), the system
automatically initializes with yfinance as the active feed. This is a designed
degradation, not an error. The startup log records the active feed.

---

## 1.7 Recovery-First Startup

Recovery-first startup means the system checks for recoverable state from
a previous session before initializing components to their default state.
A system that crashed at 14:47 and restarts at 14:52 should resume from
its last consistent state, not start fresh.

**Recoverable State:**
- Open paper trades from data/paper_trades.csv (journal).
- Strategy performance metrics from SQLite strategy_performance table.
- Knowledge base entries from SQLite knowledge_items table.
- Learning system state from SQLite learning_state table.
- Market regime context from SQLite egime_context table (if recent enough).

**State Recovery Verification:**
Recovered state is not used blindly. Every recovered state item is validated:
- CSV journal entries are validated for format and completeness.
- SQLite records are validated for schema consistency.
- Timestamps are checked: state older than MAX_STATE_AGE is discarded.
- Checksums (where applicable) are verified.

**Recovery vs. Fresh Start Decision:**
Recovery is preferred when:
1. A SQLite database exists and passes integrity check.
2. A paper trades CSV exists and is parseable.
3. The last shutdown was less than MAX_STATE_AGE hours ago.

Fresh start is forced when:
1. The user passes the --fresh-start flag.
2. Database integrity check fails.
3. State is older than MAX_STATE_AGE.
4. A schema migration is required.

---

## 1.8 Repeatable Initialization

Repeatable initialization means the startup process can be executed multiple
times and produces the same outcome each time, given the same preconditions.
Repeatability is essential for:
- Debugging: a bug reproducible in startup is a bug that can be fixed.
- Testing: automated startup tests require repeatable behavior.
- Deployment: every deployment produces a known-good startup.

**Repeatability Requirements:**
- No startup operation has a non-deterministic side effect unless that side
  effect is idempotent (same result regardless of how many times it runs).
- Database initialization is idempotent: running it twice produces the same
  schema as running it once.
- Registry registration is idempotent: registering a component twice produces
  a defined outcome (latest registration wins, or error if duplicate is detected).
- Log file initialization is idempotent: appending to an existing log file
  is correct behavior; overwriting it is not.

---

## 1.9 Operational Consistency

Operational consistency means the system behaves identically across all
environments where it is deployed: local development, Docker container on VPS,
staging, and production. Configuration values may differ; behavior must not.

**Consistency Guarantees:**
- The Python version is identical across all environments (pinned in Dockerfile).
- The dependency versions are identical across all environments (pinned in requirements.txt).
- The bootstrap sequence is identical across all environments.
- The health check criteria are identical across all environments.
- The startup log format is identical across all environments.

**Environment Isolation:**
Environment-specific values (API tokens, database paths, Telegram bot tokens)
are injected through environment variables. The bootstrap process reads these
values and stores them in the Configuration Snapshot. The code never references
environment-specific values directly; it always references the Configuration Snapshot.

---

## 1.10 Self-Validation

Self-validation is the process by which each IIOS component verifies its own
correctness before announcing readiness. Self-validation is internal to the
component; it does not rely on an external checker.

**Self-Validation Protocol for Each Component:**
1. Validate all constructor arguments.
2. Verify all dependencies are registered and READY.
3. Run internal consistency checks (schema valid, data structures initialized).
4. Run a smoke test (minimal functional test of core capability).
5. Announce READY to the Service Registry.

**Self-Validation is Not Self-Certification:**
Self-validation is a component's internal check. Self-certification is the
Architecture Council's external check of a wave's completeness. A component
that passes self-validation is not certified; it is simply ready for operation.

---

## 1.11 Self-Discovery

Self-discovery is the process by which the bootstrap manager discovers
the available components, plugins, and agents without requiring every
component to be explicitly listed in the startup configuration.

**Discovery Mechanism:**
Each module directory contains a __manifest__.json file that declares:
- Module name and version.
- Component class(es) exported.
- Dependencies (list of module names).
- Classification (CRITICAL, IMPORTANT, OPTIONAL).
- Registration key (the key used for Service Registry registration).

**Discovery Scan:**
The Bootstrap Manager scans the known module directories at startup.
Any directory containing __manifest__.json is considered a discoverable module.
Modules are loaded in dependency order as determined by the Dependency Resolver.

**Discovery Failure Handling:**
A module whose __manifest__.json cannot be parsed produces a DISCOVERY_ERROR
log entry. CRITICAL modules with DISCOVERY_ERROR cause fail-fast. OPTIONAL
modules with DISCOVERY_ERROR are logged and skipped.

---

## 1.12 Self-Certification

Self-certification is the process by which the bootstrap manager verifies,
after all components are initialized, that the complete system meets the
startup requirements for the specified operational mode.

**Self-Certification Checks:**
1. All CRITICAL components are in READY state.
2. All IMPORTANT components are in READY or DEGRADED state (with documented degradation reason).
3. Full cycle latency estimation passes (estimated based on component initialization times).
4. Kill switch components are operational (RiskGuardian READY).
5. Decision engine components are operational (all 5 debate agents READY).
6. Data feed is operational (at least one feed — Dhan or yfinance — READY).
7. Database connections are verified (SQLite accessible and schema current).
8. Startup log is complete (no missing startup events detected).

**Self-Certification Outcome:**
- ALL checks pass: SYSTEM_CERTIFIED → enter operational mode.
- Any HARD check fails: SYSTEM_NOT_CERTIFIED → halt with diagnostic report.
- SOFT checks fail (with documented degradation): SYSTEM_CERTIFIED_DEGRADED → enter reduced operational mode.

---

*End of Part I*

---

# PART II — BOOTSTRAP ARCHITECTURE

## 2.1 Architecture Overview

The bootstrap architecture defines the 21 management components that
orchestrate IIOS startup. These components are not part of the trading
system; they are the initialization infrastructure that constructs the
trading system. After startup is complete, some of these components
transition to monitoring roles; others complete and are retired.

**Bootstrap Component Classification:**

`
CLASSIFICATION    DESCRIPTION                           EXAMPLES
Orchestrators:    Coordinate other bootstrap components  BootstrapManager, InitManager
Loaders:          Load resources from external sources   ConfigLoader, EnvLoader
Validators:       Validate loaded resources              RepoValidator, HealthManager
Registries:       Maintain component inventories         ServiceRegistry, AgentRegistry
Managers:         Manage lifecycle and state             StateManager, ShutdownManager
Coordinators:     Coordinate complex multi-step tasks    StartupCoordinator, DepResolver
`

**Bootstrap Component Interaction Pattern:**
`
BootstrapManager
  |
  +-- InitializationManager
  |       |-- ConfigurationLoader
  |       |-- EnvironmentLoader
  |       |-- SecretsLoader
  |       |-- RepositoryValidator
  |
  +-- StartupCoordinator
  |       |-- DependencyResolver
  |       |-- ModuleRegistry
  |       |-- ServiceRegistry
  |       |-- ComponentRegistry
  |       |-- PluginRegistry
  |
  +-- AgentRegistry
  |       |-- KnowledgeRegistry
  |       |-- OntologyRegistry
  |
  +-- HealthManager
  |       |-- DiagnosticsManager
  |
  +-- RecoveryManager
  |
  +-- StateManager
  |
  +-- ShutdownManager
          |-- RestartManager
`

---

## 2.2 Bootstrap Manager

**Purpose:**
The Bootstrap Manager is the single top-level orchestrator of the entire
startup process. It owns the startup lifecycle from first instruction to
SYSTEM_CERTIFIED or STARTUP_FAILED. It delegates specific startup tasks to
specialized managers but retains authority over the overall startup outcome.

**Responsibilities:**
1. Receive and parse startup arguments (--paper, --telegram, --fresh-start, --mode).
2. Generate the Startup Identifier (UUID) for this startup session.
3. Initialize the startup log (before any other component, so all startup events are recorded).
4. Invoke the Initialization Manager to load configuration, environment, and secrets.
5. Invoke the Startup Coordinator to discover, resolve, and initialize components.
6. Invoke the Health Manager to run startup health checks.
7. Issue the Self-Certification decision (SYSTEM_CERTIFIED or SYSTEM_NOT_CERTIFIED).
8. On certification: announce SYSTEM_READY and hand control to MasterOrchestrator.
9. On failure: generate the Startup Diagnostic Report and halt.

**Inputs:**
- Command-line arguments from the operating system.
- Environment variables from the container or host.
- Configuration files from the filesystem.

**Outputs:**
- Startup Identifier (UUID, propagated to all startup log events).
- Self-Certification result (SYSTEM_CERTIFIED, SYSTEM_CERTIFIED_DEGRADED, or SYSTEM_NOT_CERTIFIED).
- Startup Diagnostic Report (on failure).
- SYSTEM_READY event (on success, published to EventBus).

**Dependencies:**
- No bootstrap dependencies (Bootstrap Manager is the first to start).
- Depends on: operating system process environment, filesystem access.

**Lifecycle:**
- Starts: First process in the system.
- Completes: When SYSTEM_CERTIFIED or SYSTEM_NOT_CERTIFIED is issued.
- Post-startup role: Transitions to background monitor (watchdog) during operation.

**Failure Modes:**
- Cannot initialize startup log: CRITICAL failure. No log record exists.
  Response: Write emergency record to stderr. Halt.
- Startup argument parsing fails: HARD failure.
  Response: Print usage and halt.
- Initialization Manager fails: Propagate failure. Halt.
- Health Manager reports NOT_CERTIFIED: Issue diagnostic report. Halt.

**Recovery:**
Bootstrap Manager has no recovery path for its own failures. Its purpose
is to orchestrate recovery of all other components, not itself.

**Monitoring:**
Bootstrap Manager logs every state transition with timestamp and Startup ID.
After startup, it operates as a watchdog, monitoring component health states
and triggering recovery on CRITICAL component failures.

**Engineering Notes:**
Bootstrap Manager must be designed to have zero external dependencies at the
point of first execution. It cannot import from any IIOS module before
the startup log is initialized. Its import chain must be minimal.

---

## 2.3 Initialization Manager

**Purpose:**
The Initialization Manager handles the loading of all external resources
that the system needs before any component can start. This includes configuration,
environment variables, secrets, and repository validation. It ensures that
the system has a verified, complete, and consistent set of inputs before
any code that depends on those inputs is executed.

**Responsibilities:**
1. Invoke Configuration Loader and receive the Configuration Snapshot.
2. Invoke Environment Loader and receive the Environment Snapshot.
3. Invoke Secrets Loader and receive the Secrets Snapshot (redacted in logs).
4. Invoke Repository Validator and receive the Validation Report.
5. Merge the four snapshots into the System Input Snapshot.
6. Validate the System Input Snapshot for internal consistency.
7. Return the System Input Snapshot to Bootstrap Manager.

**Inputs:**
- Bootstrap Manager startup signal.
- File paths from startup arguments.

**Outputs:**
- System Input Snapshot (merged configuration, environment, secrets, validation).
- Initialization Status (SUCCESS, PARTIAL, FAILED).
- Initialization Error List (if status is not SUCCESS).

**Dependencies:**
- Bootstrap Manager (startup signal).
- Filesystem (configuration files).
- Operating system environment (environment variables).

**Lifecycle:**
- Starts: Immediately after Bootstrap Manager initializes startup log.
- Completes: When System Input Snapshot is returned to Bootstrap Manager.
- Post-startup role: None. Initialization Manager has no runtime role.

**Failure Modes:**
- Configuration file not found: HARD failure. Report missing path. Halt.
- Configuration parse error: HARD failure. Report parse error and line number. Halt.
- Required environment variable missing: HARD failure. Report variable name. Halt.
- Repository validation failure: Configurable (HARD for integrity failures, SOFT for non-critical).
- Secrets missing: HARD failure for required secrets; SOFT for optional.

**Recovery:**
Retry transient failures (file system access errors) up to MAX_INIT_RETRIES
times with exponential backoff. Persistent failures cause halt.

**Monitoring:**
All initialization events logged with component name, input source, and outcome.
Duration of each sub-operation logged for performance baseline.

**Engineering Notes:**
The System Input Snapshot is immutable after creation. No component may
modify it at runtime. All configuration access during operation reads from
the snapshot, not from the filesystem.

---

## 2.4 Startup Coordinator

**Purpose:**
The Startup Coordinator orchestrates the discovery and initialization of
all IIOS components in the correct dependency order. It translates the
abstract dependency graph into a concrete initialization sequence that
starts components in the right order, enables parallelism where safe,
and tracks the progress of the initialization to completion.

**Responsibilities:**
1. Receive the discovered module list from the Bootstrap Manager.
2. Delegate dependency graph construction to the Dependency Resolver.
3. Execute the initialization sequence in dependency order.
4. Manage parallel initialization groups (components with no dependency between them).
5. Track the initialization state of every component.
6. Report initialization progress to Bootstrap Manager.
7. Stop the initialization sequence immediately on CRITICAL component failure.
8. Complete and return the final initialization state to Bootstrap Manager.

**Inputs:**
- Discovered module list (from Bootstrap Manager).
- System Input Snapshot (from Initialization Manager).
- Dependency graph (from Dependency Resolver).

**Outputs:**
- Initialization State Map (component name → READY / FAILED / DEGRADED).
- Critical path timing (time taken for each stage).
- Component initialization log.

**Dependencies:**
- Initialization Manager (System Input Snapshot must be ready first).
- Dependency Resolver (dependency graph must be computed first).
- Module Registry (receives component registrations as initialization completes).

**Lifecycle:**
- Starts: After Initialization Manager returns System Input Snapshot.
- Completes: When all components in initialization queue are either READY or FAILED.
- Post-startup role: Monitors component health during operation (via watchdog).

**Failure Modes:**
- Dependency cycle detected: HARD failure. Report the cycle path. Halt.
- CRITICAL component initialization fails: Halt. Report failed component.
- Initialization timeout exceeded: HARD failure for CRITICAL components.

**Recovery:**
On OPTIONAL or IMPORTANT component failure, Startup Coordinator continues
the initialization sequence and notes the failure in the Initialization State Map.
CRITICAL component failures halt the sequence immediately.

**Monitoring:**
Startup Coordinator logs the start and completion of every component
initialization, including duration. It publishes a STARTUP_PROGRESS event
to EventBus for each component that completes initialization.

**Engineering Notes:**
The maximum concurrency for parallel initialization is defined in config.py
as STARTUP_MAX_CONCURRENCY. Default value: 4 concurrent initializations.
This prevents resource contention during startup.

---

## 2.5 Dependency Resolver

**Purpose:**
The Dependency Resolver builds, validates, and provides the startup
dependency graph. It answers the question: in what order must components
start? It detects cycles, identifies the critical path, and determines
which components can be initialized in parallel.

**Responsibilities:**
1. Read dependency declarations from each module's __manifest__.json.
2. Build a directed acyclic graph (DAG) from dependency declarations.
3. Validate the DAG for cycles. Report cycle if found.
4. Compute the topological sort (startup order) of the DAG.
5. Identify parallelizable initialization groups (components at the same topological level).
6. Compute the startup critical path (longest dependency chain).
7. Return the resolved startup plan to the Startup Coordinator.

**Inputs:**
- Module manifest list (from Bootstrap Manager discovery scan).
- Any explicit ordering overrides from configuration (advanced use).

**Outputs:**
- Dependency DAG (directed acyclic graph).
- Topological sort order (list of initialization stages).
- Parallelizable groups within each stage.
- Critical path specification.
- Cycle detection result (OK or CYCLE_DETECTED with path).

**Dependencies:**
- No component dependencies (Dependency Resolver runs before component initialization).
- Requires only: module manifest files.

**Lifecycle:**
- Starts: After module discovery scan is complete.
- Completes: When the startup plan is returned to Startup Coordinator.
- Post-startup role: None. Resolved at startup only.

**Failure Modes:**
- Manifest parse error: Skip module with OPTIONAL classification.
  CRITICAL module manifest parse error: HARD failure.
- Dependency cycle detected: HARD failure. Report full cycle path.
- Unknown dependency reference: HARD failure if referenced module is CRITICAL.
  SOFT failure if referenced module is OPTIONAL.

**Recovery:**
No recovery for dependency resolution failures. Cycles and missing critical
dependencies require manual resolution.

**Engineering Notes:**
The Dependency Resolver must detect not only direct cycles (A depends on B,
B depends on A) but also transitive cycles (A→B→C→A). Any cycle in the
dependency graph indicates a design error that must be corrected before startup.

---

## 2.6 Configuration Loader

**Purpose:**
The Configuration Loader reads all configuration values from their sources
(primarily config.py), validates that all required values are present
and correctly typed, and produces an immutable Configuration Snapshot.

**Responsibilities:**
1. Load the primary configuration from config.py.
2. Load any environment-specific configuration overrides.
3. Validate that all REQUIRED configuration keys are present.
4. Validate that all configuration values are within their allowed ranges.
5. Produce the immutable Configuration Snapshot.
6. Log all configuration keys loaded (values redacted for sensitive keys).

**Inputs:**
- config.py module (imported at startup).
- Environment-specific override file (if present).
- Required configuration key list (hardcoded in Configuration Loader).

**Outputs:**
- Configuration Snapshot (immutable dictionary of all configuration values).
- Configuration Validation Report (list of missing or invalid keys).

**Configuration Validation Rules:**

| Configuration Key | Type | Range / Constraints | Criticality |
|-------------------|------|--------------------|-|
| DECISION_THRESHOLD | float | 0.0 <= x <= 10.0 | CRITICAL |
| KILL_SWITCH_VIX | float | 0.0 <= x <= 100.0 | CRITICAL |
| KILL_SWITCH_DAILY_LOSS_PCT | float | 0.0 <= x <= 1.0 | CRITICAL |
| PROMOTION_WIN_RATE | float | 0.0 <= x <= 1.0 | CRITICAL |
| PROMOTION_SHARPE | float | x > 0.0 | CRITICAL |
| PROMOTION_MAX_DD | float | 0.0 <= x <= 1.0 | CRITICAL |
| LAYER_LATENCY_WARN_MS | int | x > 0 | IMPORTANT |
| LAYER_LATENCY_CRIT_MS | int | x > WARN | IMPORTANT |
| STARTUP_MAX_CONCURRENCY | int | 1 <= x <= 16 | OPTIONAL |
| PAPER_TRADING | bool | true or false | CRITICAL |
| SCHEDULE | dict | non-empty | IMPORTANT |

**Dependencies:**
- No component dependencies. Runs before any component initialization.
- Requires: config.py importable (Python path set correctly).

**Lifecycle:**
- Starts: First sub-operation of Initialization Manager.
- Completes: When Configuration Snapshot is returned.
- Post-startup role: Configuration Snapshot accessed via read-only getter.

**Failure Modes:**
- config.py import error: HARD failure. Report import error detail.
- Required key missing: HARD failure for CRITICAL keys.
- Value out of range: HARD failure for CRITICAL keys.

**Recovery:**
No retry for configuration loading failures. These require manual correction.

**Monitoring:**
Configuration load duration is logged. Number of keys loaded is logged.
No configuration values are logged (security constraint).

**Engineering Notes:**
The Configuration Loader enforces the single source of truth principle.
All configuration values used during operation come from the Configuration
Snapshot, never from re-reading config.py. This ensures that configuration
does not change during operation.

---

## 2.7 Environment Loader

**Purpose:**
The Environment Loader reads all environment variables required by IIOS,
validates their presence and format, and produces an immutable Environment
Snapshot. Environment variables carry values that differ between environments
and must not be committed to the repository.

**Responsibilities:**
1. Read all required environment variables.
2. Validate that all REQUIRED variables are present.
3. Validate format of structured variables (e.g., URLs, numeric strings).
4. Produce the immutable Environment Snapshot.
5. Log all environment variable keys loaded (values redacted for sensitive variables).

**Required Environment Variables:**

| Variable | Description | Criticality | Format Validation |
|----------|-------------|-------------|------------------|
| DHAN_CLIENT_ID | Dhan broker client identifier | CRITICAL | Non-empty string |
| DHAN_ACCESS_TOKEN | Dhan API access token | CRITICAL | Non-empty string |
| TELEGRAM_BOT_TOKEN | Telegram bot API token | IMPORTANT | Matches token format |
| TELEGRAM_CHAT_ID | Telegram target chat identifier | IMPORTANT | Numeric string |
| DB_PATH | Path to SQLite database file | CRITICAL | Valid filesystem path |
| LOG_PATH | Path to log directory | IMPORTANT | Valid filesystem path |
| ENVIRONMENT | Deployment environment name | OPTIONAL | dev / staging / prod |

**Inputs:**
- Operating system environment variables.
- Required variable list (hardcoded in Environment Loader).

**Outputs:**
- Environment Snapshot (immutable dictionary).
- Environment Validation Report.

**Dependencies:**
- No component dependencies.

**Lifecycle:**
- Starts: After Configuration Loader completes.
- Completes: When Environment Snapshot is returned.
- Post-startup role: Environment Snapshot accessed via read-only getter.

**Failure Modes:**
- CRITICAL variable missing: HARD failure. Report variable name.
- Variable format invalid: HARD failure for CRITICAL variables.
- IMPORTANT variable missing: SOFT failure. Log warning. Continue.

**Recovery:**
No retry. Environment variables are set by the container or host;
their absence requires external correction.

**Monitoring:**
Number of environment variables loaded is logged. Sensitive values are not
logged. Missing OPTIONAL variables are logged as WARN.

**Engineering Notes:**
Secrets (tokens, passwords) are loaded by the Secrets Loader, which may
source them from the environment or from a secrets management system.
The Environment Loader handles only non-secret configuration variables.
The boundary between Environment Loader and Secrets Loader is: if a value
requires redaction in all logs without exception, it goes through Secrets Loader.

---

## 2.8 Secrets Loader

**Purpose:**
The Secrets Loader handles all values that are sensitive enough to require
redaction from logs, error messages, and all diagnostic output. Secrets are
never logged, never included in error messages, and never passed to systems
that may log their inputs.

**Responsibilities:**
1. Read secrets from the configured secrets source (environment variables, secrets file).
2. Validate presence of all required secrets.
3. Produce the immutable Secrets Snapshot.
4. Ensure no secret value appears in any log output.
5. Provide a redacted snapshot (key names only) for audit logging.

**Secrets Managed:**
- Dhan API access token.
- Telegram bot token.
- Any additional API keys for data services.
- Encryption keys (if applicable for SQLite encryption).

**Inputs:**
- Environment variables (primary source).
- Encrypted secrets file (alternative source, if configured).

**Outputs:**
- Secrets Snapshot (immutable, in-memory, never serialized to disk).
- Redacted Secrets Manifest (key names only, for audit log).

**Security Requirements:**
- Secrets Snapshot is stored only in memory.
- Secrets are never written to any file.
- Secrets are never included in log records.
- Secrets are never passed as string arguments to functions that log their arguments.
- On shutdown, Secrets Snapshot memory is overwritten before deallocation.

**Dependencies:**
- No component dependencies.
- Secrets source must be available (environment or secrets file).

**Lifecycle:**
- Starts: After Environment Loader completes.
- Completes: When Secrets Snapshot is created.
- Post-startup role: Secrets Snapshot is kept in memory for the duration of operation.
  Components that need secrets access them via the Secrets Loader's getter (not via snapshot copy).

**Failure Modes:**
- Required secret missing: HARD failure. Report the secret key name (not value). Halt.
- Secrets file not found (if configured): HARD failure. Report file path. Halt.
- Secrets file parse error: HARD failure. Report error type. Halt.

**Recovery:**
No retry. Missing secrets require external correction (environment variable set,
secrets file created).

**Monitoring:**
Only the redacted manifest is logged. The number of secrets loaded is logged.
Any access to a secret value at runtime is logged (key name only) if
security audit logging is enabled.

**Engineering Notes:**
This specification does not implement a secrets management service (e.g., HashiCorp Vault).
The current implementation uses environment variables as the secrets source.
Future evolution to a secrets management service is addressed in Wave 20 (Institutional Expansion)
and requires an Engineering Decision Record. The Secrets Loader interface abstracts the source,
making that evolution possible without changing consumers.

---

## 2.9 Repository Validator

**Purpose:**
The Repository Validator verifies the integrity and completeness of the IIOS
code repository at startup. It ensures that the running code matches
expectations before any component is initialized from that code.

**Responsibilities:**
1. Verify that all expected modules are present (existence check).
2. Verify that no protected modules have been modified unexpectedly.
3. Check module import health (imports resolve without errors).
4. Verify that __manifest__.json files are present and parseable.
5. Verify that the import graph has no cycles.
6. Produce the Repository Validation Report.

**Validation Checks:**

| Check | Description | Criticality | Failure Action |
|-------|-------------|-------------|----------------|
| Module presence | All required modules exist | CRITICAL | Halt |
| Protected module hash | Hash matches known-good hash | IMPORTANT | Warn |
| Import resolution | All imports resolve | CRITICAL | Halt |
| Manifest presence | Manifest exists for all modules | IMPORTANT | Warn |
| Import cycle check | No circular imports | CRITICAL | Halt |
| Interface signature check | Critical interfaces unchanged | CRITICAL | Halt |

**Inputs:**
- Expected module list (from configuration).
- Known-good hash map for protected modules (from build manifest).
- Module directory paths (from configuration).

**Outputs:**
- Repository Validation Report (list of checks with PASS/FAIL and detail).
- Overall validation status (VALID, VALID_WITH_WARNINGS, INVALID).

**Dependencies:**
- Configuration Snapshot (module paths from configuration).
- Filesystem access (module directory).

**Lifecycle:**
- Starts: After all loaders complete (Configuration, Environment, Secrets).
- Completes: When Validation Report is produced.
- Post-startup role: None. Validation is a startup-only operation.

**Failure Modes:**
- Module missing: HARD failure for CRITICAL modules. Log detail. Halt.
- Import resolution failure: HARD failure. Log import error chain. Halt.
- Import cycle: HARD failure. Log full cycle path. Halt.
- Interface signature mismatch: HARD failure. Log expected vs actual signature. Halt.

**Recovery:**
Repository validation failures cannot be recovered by the system.
They require human intervention (code fix, missing file restore, rollback).

**Monitoring:**
Validation report is logged in full (check names, pass/fail, details).
Duration of validation is logged. Protected module hash check results are logged.

**Engineering Notes:**
The build manifest (uild_manifest.json) contains the known-good hashes for
protected modules. This file is updated by the CI/CD pipeline on every successful
wave completion. If the build manifest is absent, protected module hash checks
are skipped with a WARN log (not a HARD failure).

---

## 2.10 Module Registry

**Purpose:**
The Module Registry maintains the authoritative list of all Python modules
that are part of IIOS. It is populated during the discovery phase and is
used by the Dependency Resolver, Startup Coordinator, and Health Manager.

**Responsibilities:**
1. Accept module registrations from the discovery scan.
2. Store module metadata (name, version, classification, dependencies, manifest).
3. Provide lookup by module name, classification, and layer.
4. Report the complete module inventory.
5. Detect duplicate registrations (same name, different version).

**Module Registration Record:**
- Module name (unique identifier).
- Module version (from manifest).
- Python module path (importable path).
- Classification (CRITICAL, IMPORTANT, OPTIONAL).
- IIOS layer number (1–17).
- Declared dependencies (list of module names).
- Manifest path.
- Registration timestamp.

**Inputs:**
- Module manifests from discovery scan.
- Registration calls from Startup Coordinator.

**Outputs:**
- Module lookup responses (single module or filtered list).
- Complete module inventory (for Health Manager and Diagnostics Manager).
- Duplicate detection events.

**Dependencies:**
- No component dependencies (populated before any component initializes).

**Lifecycle:**
- Starts: At discovery phase start (before component initialization).
- Completes: Populated after discovery. Accessible throughout system operation.
- Post-startup role: Read-only reference for all modules that need to know
  the system's module inventory.

**Failure Modes:**
- Duplicate module registration: Log WARNING. Keep first registration.
  For CRITICAL modules with conflicting versions: HARD failure.
- Module registration with undefined dependency: Log WARNING for OPTIONAL.
  HARD failure for CRITICAL.

**Recovery:**
Duplicate registration warnings are logged; resolution requires manual intervention
if the conflict is in a CRITICAL module.

**Monitoring:**
Total module count logged at completion. Module count by classification logged.
Module count by layer logged. Any duplicate registrations logged.

**Engineering Notes:**
The Module Registry is read-only after the discovery phase completes.
No module may register itself after the discovery phase. Late registration
is a bootstrap violation and is rejected with a log error.

---

## 2.11 Service Registry

**Purpose:**
The Service Registry is the runtime component directory. It maintains the
readiness state of every running IIOS service and provides service discovery
for all components that need to call another component's interface.

**Responsibilities:**
1. Accept service registrations from components as they complete initialization.
2. Track the readiness state of every registered service.
3. Provide service lookup by name, interface type, and classification.
4. Propagate readiness state changes to dependent components.
5. Detect and report unresponsive services (heartbeat monitoring).
6. Record service deregistration on shutdown.

**Service Registration Record:**
- Service name (unique identifier, same as module name).
- Service instance reference (in-memory reference).
- Readiness state (INITIALIZING, READY, DEGRADED, FAILED, SHUT_DOWN).
- Classification (CRITICAL, IMPORTANT, OPTIONAL).
- Readiness timestamp.
- Health check callback (function to call for health verification).
- Heartbeat interval (expected heartbeat frequency).
- Last heartbeat timestamp.

**Readiness State Machine:**

`
INITIALIZING --[initialization complete]--> READY
INITIALIZING --[initialization failed]---> FAILED
READY        --[health check fail]-------> DEGRADED
READY        --[fatal error]-------------> FAILED
DEGRADED     --[recovery success]--------> READY
DEGRADED     --[recovery failed]---------> FAILED
FAILED       --[restart success]---------> READY
READY        --[shutdown signal]---------> SHUT_DOWN
`

**Inputs:**
- Service registration calls (from components during initialization).
- Health check results (from Health Manager).
- Heartbeat signals (from components during operation).
- Shutdown signals (from Shutdown Manager).

**Outputs:**
- Service lookup responses.
- Readiness state change events (published to EventBus).
- Service inventory (for Health Manager).
- Unresponsive service alerts (when heartbeat expires).

**Dependencies:**
- EventBus (to publish readiness state change events).
- No component dependencies at startup (Service Registry starts early).

**Lifecycle:**
- Starts: Before component initialization begins.
- Completes: N/A — runs for the lifetime of the system.
- Post-startup role: Primary runtime service directory.

**Failure Modes:**
- Registry full (too many services): HARD failure (capacity must be increased).
- Duplicate service name registration: WARN and reject duplicate. Keep existing.
- CRITICAL service becomes FAILED during operation: Trigger BootstrapManager watchdog.

**Recovery:**
For CRITICAL services that transition to FAILED during operation, the Bootstrap
Manager watchdog triggers the Recovery Manager.

**Monitoring:**
Service Registry logs every state transition. Health check failures are logged
with the health check error detail. Heartbeat expiry events are logged immediately.

**Engineering Notes:**
The Service Registry is the runtime equivalent of the Module Registry.
Module Registry is for static inventory (what modules exist).
Service Registry is for dynamic state (are services running and ready).
Components query the Service Registry, not the Module Registry, at runtime.

## 2.12 Component Registry

**Purpose:**
The Component Registry tracks all instantiated Python objects (components)
that form the operational IIOS system. While the Module Registry tracks
modules and the Service Registry tracks services, the Component Registry
tracks the specific object instances that implement the trading system.

**Responsibilities:**
1. Accept component registrations as components complete instantiation.
2. Store component instance references with metadata.
3. Provide lookup by component type, interface, and layer.
4. Support component replacement (for recovery: replace FAILED component with fresh instance).
5. Report component inventory to Health Manager and Diagnostics Manager.

**Component Registration Record:**
- Component type name.
- Component instance (in-memory reference).
- Interface implemented (e.g., BaseFeed, DebateAgent).
- IIOS layer (1–17).
- Owning module (reference to Module Registry entry).
- Registration timestamp.
- Last activity timestamp.

**Inputs:**
- Component registration calls (from Startup Coordinator during initialization).
- Component replacement calls (from Recovery Manager).

**Outputs:**
- Component lookup responses.
- Component inventory.
- Interface-filtered component lists (e.g., all DebateAgent implementations).

**Dependencies:**
- Module Registry (component must belong to a registered module).
- Service Registry (components that are services register in both registries).

**Lifecycle:**
- Starts: During component initialization phase.
- Completes: N/A — runs for the lifetime of the system.
- Post-startup role: Primary runtime component directory.

**Failure Modes:**
- Component registration with unknown module: WARN. Log and continue.
- Duplicate component of same type without replacement flag: WARN. Reject duplicate.

**Recovery:**
Recovery Manager calls Component Registry to replace a FAILED component's
instance with a newly initialized instance.

**Monitoring:**
Component count by layer logged at startup completion. Component replacements
(recovery events) logged with reason.

**Engineering Notes:**
The Component Registry enables the MasterOrchestrator to discover all
registered agents, all feed implementations, and all strategy instances
without hard-coded references. This makes the system extensible: new agents
and strategies register themselves; the orchestrator discovers them.

---

## 2.13 Plugin Registry

**Purpose:**
The Plugin Registry manages optional components that extend IIOS functionality
without being part of the core trading pipeline. Plugins are OPTIONAL by
classification. Their absence does not prevent startup or operation.

**Responsibilities:**
1. Accept plugin registrations from the discovery scan.
2. Load and initialize plugins in dependency order (after core components).
3. Provide plugin lookup by name and capability.
4. Manage plugin lifecycle (enable, disable, reload).
5. Isolate plugin failures from core system operation.

**Plugin Classification:**
Plugins are categorized by their integration point:
- DATA_PLUGIN: Adds a new data source (e.g., Bloomberg terminal integration).
- STRATEGY_PLUGIN: Adds a new strategy generator.
- REPORTING_PLUGIN: Adds a new reporting output (e.g., email report).
- NOTIFICATION_PLUGIN: Adds a new notification channel.
- ANALYTICS_PLUGIN: Adds a new analytics computation.

**Inputs:**
- Plugin manifests from discovery scan.
- Core component registrations (plugins may depend on core components).

**Outputs:**
- Plugin lookup responses.
- Plugin status (LOADED, FAILED, DISABLED).
- Plugin capability advertisement (what each plugin provides).

**Dependencies:**
- Component Registry (plugins depend on core components being registered first).
- Service Registry (plugins that provide services register there too).

**Lifecycle:**
- Starts: After all CRITICAL and IMPORTANT core components are initialized.
- Completes: When all discovered plugins are either LOADED or FAILED.
- Post-startup role: Plugin Registry manages plugin lifecycle during operation.

**Failure Modes:**
- Plugin load failure: Log error. Mark plugin FAILED. Continue (plugins are OPTIONAL).
- Plugin dependency on missing core component: Log error. Mark plugin FAILED.
- Plugin introduces circular dependency: Log error. Mark plugin FAILED.

**Recovery:**
Plugin failures do not trigger Recovery Manager. Plugins are reloaded only
on explicit operator command via Telegram bot /reload_plugins command.

**Monitoring:**
Plugin count logged. Failed plugins logged with error detail. Plugin capability
advertisement logged (which capabilities are available from plugins).

**Engineering Notes:**
Plugin isolation is critical. A plugin crash must not affect core system
operation. Plugins run in a controlled execution environment where unhandled
exceptions are caught by the Plugin Registry and marked as PLUGIN_FAILED,
not propagated to the core system.

---

## 2.14 AI Agent Registry

**Purpose:**
The AI Agent Registry manages all AI agents in the IIOS system. This includes
the five debate agents, all scanner agents, the regime classifier, the strategy
generator, and all other AI components. The registry provides ordered access
to agents for the orchestration layers.

**Responsibilities:**
1. Accept agent registrations from component initialization.
2. Validate agent interface compliance (all debate agents implement DebateAgent interface).
3. Group agents by type (DEBATE_AGENT, SCANNER_AGENT, STRATEGY_AGENT, etc.).
4. Provide ordered agent lists for the debate cycle.
5. Track agent readiness and performance health.
6. Support agent enable/disable (from learning system auto-disable).

**Agent Types and Expected Count:**

| Agent Type | Expected Count | Interface | Source Wave |
|------------|---------------|-----------|-------------|
| DEBATE_AGENT | 5 (exactly) | DebateAgent | Wave 9 |
| SCANNER_AGENT | variable | ScannerAgent | Wave 10 |
| STRATEGY_AGENT | variable | StrategyAgent | Wave 5, 13 |
| REGIME_CLASSIFIER | 1 | RegimeClassifier | Wave 8 |
| STRATEGY_GENERATOR | 1 | StrategyGenerator | Wave 13 |
| LEARNING_AGENT | 1 | LearningAgent | Wave 14 |
| GLOBAL_INTELLIGENCE | 1 | GlobalIntelligence | Wave 1 |
| MARKET_INTELLIGENCE | 1 | MarketIntelligence | Wave 12 |

**DEBATE_AGENT Validation:**
The AI Agent Registry validates that exactly five DebateAgent implementations
are registered: BullAgent, BearAgent, NeutralAgent, RiskAgent, RegimeAgent.
If any debate agent is missing, startup fails (HARD failure — debate requires all five).

**Inputs:**
- Agent registration calls (from component initialization).
- Agent enable/disable calls (from learning system).
- Health check results (from Health Manager).

**Outputs:**
- Agent lookup by type.
- Ordered debate agent list (fixed order for reproducible debate).
- Agent health status.
- Agent enable/disable state.

**Dependencies:**
- Service Registry (agents register there too for service discovery).
- Component Registry (agents are a subset of all components).
- Learning System (performance-based enable/disable).

**Lifecycle:**
- Starts: During agent initialization phase (after core infrastructure).
- Completes: When all agents are registered and validated.
- Post-startup role: Primary agent directory for MasterOrchestrator and DecisionEngine.

**Failure Modes:**
- Missing debate agent (fewer than 5): HARD failure. Report which agents are missing.
- Agent interface non-compliance: HARD failure for DEBATE_AGENT. WARN for others.
- Duplicate agent of same type: WARN. Keep first registration.

**Recovery:**
DEBATE_AGENT failures halt startup — all 5 are required. Other agent failures
are reported; operation continues with reduced agent coverage.

**Monitoring:**
Agent count by type logged. Debate agent order logged. Agent readiness logged.
Agent enable/disable events logged with reason.

**Engineering Notes:**
The fixed order of debate agents (BullAgent, BearAgent, NeutralAgent, RiskAgent,
RegimeAgent) is required for reproducibility. If the debate is run twice with
identical inputs, the result must be identical. The AI Agent Registry enforces
this order by maintaining agents in registration order and requiring that
debate agents are registered in the specified order.

---

## 2.15 Knowledge Registry

**Purpose:**
The Knowledge Registry provides startup access to the knowledge base system.
It validates that the knowledge base is intact at startup, loads critical
knowledge into memory for fast runtime access, and registers the knowledge
base components with the Service Registry.

**Responsibilities:**
1. Verify knowledge base database is accessible and schema-current.
2. Load critical knowledge items into the in-memory knowledge cache.
3. Validate knowledge base integrity (no corruption, no contradictions).
4. Register knowledge base components with Service Registry.
5. Report knowledge base metrics (total items, recent items, confidence distribution).

**Knowledge Base Startup Checks:**

| Check | Description | Failure Action |
|-------|-------------|----------------|
| Database accessible | SQLite file exists and is readable | Halt |
| Schema current | All expected tables and indexes exist | Attempt migration. Halt if migration fails. |
| Integrity check | SQLite PRAGMA integrity_check passes | Halt |
| No critical contradictions | Knowledge contradiction scan passes | WARN (not halt — contradictions may exist from learning) |
| Minimum knowledge present | At least N knowledge items for operation | WARN |
| Provenance completeness | All items have provenance records | WARN |

**Inputs:**
- Database path (from Configuration Snapshot).
- Schema specification (from embedded schema definition).
- Critical knowledge query list (minimum items required for startup).

**Outputs:**
- Knowledge base readiness status.
- In-memory knowledge cache (hot knowledge items).
- Knowledge base metrics report.
- Knowledge validation report.

**Dependencies:**
- Configuration Snapshot (database path).
- State Manager (for state recovery of knowledge base).

**Lifecycle:**
- Starts: After database connection established.
- Completes: When knowledge cache is populated and health check passed.
- Post-startup role: Knowledge cache maintained in memory; cache refresh on cycle.

**Failure Modes:**
- Database inaccessible: HARD failure. Report path and OS error. Halt.
- Schema migration fails: HARD failure. Halt. Manual intervention required.
- Integrity check fails: HARD failure. Database may be corrupted. Halt.

**Recovery:**
Knowledge base recovery from backup is a manual procedure (see Runbook KB-001).
The bootstrap process cannot automatically restore a corrupted knowledge base.

**Monitoring:**
Knowledge item count logged. Cache population time logged. Contradiction count logged.
Schema version logged. Last knowledge update timestamp logged.

**Engineering Notes:**
The Knowledge Registry is distinct from the knowledge base implementation.
The knowledge base implementation is part of Wave 3 (Knowledge System).
The Knowledge Registry is part of the bootstrap architecture. This distinction
is important: the bootstrap architecture may be updated without modifying the
knowledge base implementation.

---

## 2.16 Ontology Registry

**Purpose:**
The Ontology Registry loads the IIOS entity ontology at startup, validates
its integrity, and provides the ontology to the Ontology Validator component.
The ontology defines all valid entity types, relationship types, and attribute
types used in the knowledge base.

**Responsibilities:**
1. Load the ontology definition from the ontology database or configuration.
2. Validate ontology internal consistency (no undefined references).
3. Register the Ontology Validator component with the Service Registry.
4. Make the ontology available for runtime validation.
5. Report ontology metrics (entity count, relationship type count).

**Ontology Loading Sequence:**
1. Load entity type definitions (all valid entity types).
2. Load relationship type definitions (valid relationships between entity types).
3. Load attribute type definitions (valid attributes for each entity type).
4. Load constraint definitions (cardinality, required attributes).
5. Validate all cross-references (relationship endpoints reference defined entity types).
6. Build the in-memory ontology structure for fast validation.

**Inputs:**
- Ontology source (SQLite database or YAML definition file).
- Ontology schema specification.

**Outputs:**
- Ontology readiness status.
- In-memory ontology structure.
- Ontology metrics report.

**Dependencies:**
- Database connection (if ontology stored in SQLite).
- Configuration Snapshot (ontology source path).

**Lifecycle:**
- Starts: After Knowledge Registry completes.
- Completes: When ontology is loaded and validated.
- Post-startup role: Ontology structure is maintained in memory for runtime validation.

**Failure Modes:**
- Ontology source inaccessible: HARD failure. Halt.
- Ontology internal inconsistency: HARD failure. Report inconsistency detail. Halt.

**Recovery:**
Ontology failures require manual correction of the ontology definition.
There is no automated recovery path.

**Monitoring:**
Entity type count logged. Relationship type count logged. Constraint count logged.
Load time logged.

**Engineering Notes:**
The ontology is loaded once at startup. It does not change during operation.
Ontology evolution (adding new entity types) requires a restart. This is a
deliberate design constraint: the ontology defines the semantic boundary of
the knowledge base, and changes to that boundary require controlled restart.

---

## 2.17 Health Manager

**Purpose:**
The Health Manager runs startup health checks across all registered components
and produces the Health Report that the Bootstrap Manager uses for the
self-certification decision.

**Responsibilities:**
1. Query the Service Registry for all registered components.
2. Execute the health check callback for each component.
3. Categorize health check results by severity (HEALTHY, DEGRADED, FAILED).
4. Apply the health certification matrix (which failures are HARD vs SOFT).
5. Produce the Health Report.
6. After startup, monitor ongoing component health at defined intervals.

**Health Check Categories:**

| Category | Components Checked | Failure Classification |
|----------|--------------------|------------------------|
| Configuration Health | ConfigLoader, EnvLoader, SecretsLoader | CRITICAL |
| Repository Health | RepositoryValidator, ModuleRegistry | CRITICAL |
| Database Health | SQLite connections, schema validity | CRITICAL |
| Knowledge Health | KnowledgeRegistry, KnowledgeBase | CRITICAL |
| Ontology Health | OntologyRegistry, OntologyValidator | CRITICAL |
| Infrastructure Health | DataFeedManager (Dhan+yfinance) | CRITICAL |
| AI Health | All 5 DebateAgents, RegimeClassifier | CRITICAL |
| Reasoning Health | ReasoningEngine, MetaLearning | IMPORTANT |
| Decision Health | DecisionEngine, ScoreAggregator | CRITICAL |
| Performance Health | Latency benchmarks | IMPORTANT |
| Security Health | CVE scan result, secret scan result | CRITICAL |
| Operational Health | Telegram bot, dashboard | OPTIONAL |

**Health Report Structure:**
- Overall status: HEALTHY, DEGRADED, or FAILED.
- Per-category status: HEALTHY, DEGRADED, or FAILED.
- Per-component status: HEALTHY, DEGRADED, or FAILED.
- Failure details: For each FAILED component, the health check error message.
- Degradation details: For each DEGRADED component, the degradation reason.
- Certification recommendation: CERTIFY, CERTIFY_DEGRADED, or REJECT.

**Inputs:**
- Service Registry (complete component list and health check callbacks).
- Component Registry (component health metrics).
- AI Agent Registry (agent readiness states).
- Performance benchmarks (if pre-startup benchmarks are configured).

**Outputs:**
- Health Report.
- Certification recommendation to Bootstrap Manager.

**Dependencies:**
- All registered components (to run their health checks).
- Service Registry (component list).

**Lifecycle:**
- Starts: After all components complete initialization.
- Completes: When Health Report is produced.
- Post-startup role: Runs health checks at HEALTH_CHECK_INTERVAL for ongoing monitoring.

**Failure Modes:**
- Component health check callback raises exception: Log exception.
  Treat component as FAILED for health reporting purposes.
- Health check timeout: Treat component as FAILED.

**Recovery:**
Health Manager itself does not recover components. It reports failures.
Recovery is the Recovery Manager's responsibility.

**Monitoring:**
Health check duration per component logged. Total health check cycle duration logged.
Health check failure rate logged (over time, for trending).

**Engineering Notes:**
Health checks must be fast. Each component's health check callback must
complete within HEALTH_CHECK_TIMEOUT_MS (default: 500ms). A health check that
takes longer than the timeout is treated as a failure, not a success.
Health check callbacks must not have side effects; they must only read state
and return a health status.

---

## 2.18 Diagnostics Manager

**Purpose:**
The Diagnostics Manager captures detailed diagnostic information when the
system encounters startup failures, operational anomalies, or explicit
diagnostic requests. It produces human-readable diagnostic reports that
enable rapid root cause identification.

**Responsibilities:**
1. Capture the complete system state at the moment of a startup failure.
2. Produce the Startup Diagnostic Report (on startup failure).
3. Respond to diagnostic queries from the Telegram bot (/diag command).
4. Log diagnostic snapshots at configurable intervals.
5. Maintain a diagnostic history ring buffer (last N diagnostic snapshots).

**Diagnostic Report Contents (on startup failure):**
- Startup Identifier.
- Startup timestamp.
- Last successful startup stage.
- Failed startup stage.
- Failure cause (error type, message, component name).
- Component state at failure (which components were READY, which were not).
- Configuration Snapshot (values, not secrets).
- Environment Snapshot (keys only, not secrets).
- Recent log entries (last 100 lines).
- Suggested resolution steps (based on failure category).

**Inputs:**
- Bootstrap Manager failure signals.
- Health Manager failure reports.
- All log entries (via logging system).
- Component state from Service Registry.

**Outputs:**
- Startup Diagnostic Report (file: logs/startup_diagnostic_{startup_id}.txt).
- Telegram diagnostic response (on /diag command).
- Diagnostic snapshot records.

**Dependencies:**
- Service Registry (component states).
- Logging system (log entries).
- Startup log (bootstrap events).

**Lifecycle:**
- Starts: Early in startup (after logging is initialized).
- Completes: N/A — runs for the lifetime of the system.
- Post-startup role: Responds to diagnostic queries and captures operational diagnostics.

**Failure Modes:**
- Cannot write diagnostic report to filesystem: Write to stderr as fallback.
- Diagnostic Manager itself fails: Log to startup log and continue (diagnostics are optional).

**Recovery:**
Diagnostics Manager failures are self-healing where possible. Missing diagnostic
output does not affect trading system operation.

**Monitoring:**
Diagnostic report creation events logged. Diagnostic query response times logged.

**Engineering Notes:**
The Diagnostics Manager must not slow down startup. It operates as a passive
observer, capturing state from the registries and logs. It does not make calls
that could block startup progress. All diagnostic writes are asynchronous.

---

## 2.19 Recovery Manager

**Purpose:**
The Recovery Manager handles the recovery of FAILED components during operation.
It attempts to restore failed components to READY state through restart,
reconfiguration, or fallback substitution.

**Responsibilities:**
1. Receive COMPONENT_FAILED events from the Service Registry.
2. Classify the failure (transient vs permanent).
3. Attempt component restart (up to MAX_RECOVERY_ATTEMPTS).
4. If restart succeeds: re-register in Service Registry as READY.
5. If restart fails: escalate to Bootstrap Manager watchdog.
6. Implement fallback substitution where available (e.g., yfinance for Dhan).
7. Notify Architecture Council of CRITICAL component failures.

**Recovery Strategies:**

| Strategy | When Used | Recovery Action |
|----------|-----------|-----------------|
| RESTART | Transient failure | Reinitialize component from scratch |
| RECONFIGURE | Configuration issue | Reload config and reinitialize |
| FALLBACK | Primary has alternative | Switch to fallback component |
| SAFE_MODE | Cannot recover | Enter SAFE_MODE (monitoring only) |
| SHUTDOWN | Unrecoverable | Clean system shutdown |

**Recovery Decision Tree:**
`
COMPONENT_FAILED event received
  |
  +-- Is failure transient? --YES--> RESTART strategy
  |     |
  |     +-- Restart attempts < MAX? --YES--> Attempt restart
  |     |
  |     +-- Restart attempts >= MAX? --NO--> FALLBACK if available
  |
  +-- Is failure permanent? --YES--> FALLBACK if available
        |
        +-- Fallback available? --YES--> Switch to fallback
        |
        +-- No fallback? --------YES--> SAFE_MODE if IMPORTANT
                                        SHUTDOWN if CRITICAL
`

**Inputs:**
- COMPONENT_FAILED events from Service Registry.
- Component metadata from Component Registry.
- Recovery strategy configuration from Configuration Snapshot.

**Outputs:**
- Recovery attempt log entries.
- Component re-registration (on successful recovery).
- SAFE_MODE trigger (on irrecoverable IMPORTANT failure).
- SHUTDOWN trigger (on irrecoverable CRITICAL failure).
- Architecture Council notification (on CRITICAL failure).

**Dependencies:**
- Service Registry (FAILED events, re-registration).
- Component Registry (component metadata).
- Bootstrap Manager (escalation).
- Telegram bot (notification).

**Lifecycle:**
- Starts: After Service Registry is initialized.
- Completes: N/A — runs for the lifetime of the system.
- Post-startup role: Primary recovery orchestrator.

**Failure Modes:**
- Recovery Manager itself fails: Bootstrap Manager watchdog detects via heartbeat timeout.
  Recovery Manager is a CRITICAL component; its failure triggers SAFE_MODE.

**Recovery:**
The Recovery Manager is itself monitored by the Bootstrap Manager watchdog.
If Recovery Manager fails, the watchdog takes direct recovery action.

**Monitoring:**
Every recovery attempt logged with component name, strategy, attempt number, outcome.
Recovery success rate tracked per component (for chronic failure detection).

**Engineering Notes:**
Chronic failures (a component that repeatedly fails and recovers) are detected
by the Recovery Manager after MAX_CHRONIC_FAILURES recovery cycles. A chronically
failing component is disabled and the operator is notified. A component that
fails repeatedly without a clear root cause investigation is more dangerous
than one that is cleanly disabled.

---

## 2.20 Shutdown Manager

**Purpose:**
The Shutdown Manager orchestrates the clean shutdown of the IIOS system.
Clean shutdown ensures that all in-flight operations complete, all state is
persisted, all connections are closed, and the system leaves the environment
in a known state for the next startup.

**Responsibilities:**
1. Receive shutdown signal (SIGTERM, SIGINT, operator command, or kill switch).
2. Determine shutdown type (CLEAN, EMERGENCY, FORCED).
3. For CLEAN shutdown: stop new operations, complete in-flight, flush state.
4. For EMERGENCY shutdown: halt all operations immediately, flush critical state.
5. For FORCED shutdown: immediate halt (no guarantees on state consistency).
6. Deregister all components from Service Registry in reverse initialization order.
7. Close all database connections cleanly.
8. Write the shutdown record to the startup log.
9. Exit with the appropriate exit code.

**Shutdown Types:**

| Type | Trigger | In-flight Operations | State Flush | Connection Close |
|------|---------|---------------------|-------------|------------------|
| CLEAN | SIGTERM, operator | Complete current cycle | Full flush | Ordered close |
| EMERGENCY | Kill switch | Abort immediately | Critical state only | Force close |
| FORCED | SIGKILL, crash | None | None | None |

**Clean Shutdown Sequence:**
1. Stop accepting new trading cycle triggers.
2. Complete the current trading cycle (or timeout after MAX_CYCLE_WAIT_S).
3. Flush strategy performance metrics to SQLite.
4. Flush paper trade journal to CSV.
5. Flush knowledge base pending writes.
6. Close Telegram bot connection.
7. Close data feed connections (Dhan, yfinance).
8. Close SQLite connections.
9. Deregister all components from Service Registry.
10. Write shutdown record (timestamp, reason, last cycle state).
11. Exit with code 0.

**Inputs:**
- Shutdown signals (SIGTERM, SIGINT, operator commands, kill switch events).
- Component state (from Service Registry, for ordered shutdown).
- Current cycle state (from MasterOrchestrator, for in-flight completion).

**Outputs:**
- Shutdown log record.
- Exit code (0: clean, 1: error, 2: emergency).
- Persistent state (flushed to SQLite and CSV).

**Dependencies:**
- All registered components (to complete and deregister).
- Service Registry (deregistration).
- MasterOrchestrator (cycle completion signal).

**Lifecycle:**
- Starts: On shutdown signal receipt.
- Completes: When exit() is called.
- Post-startup role: Activated only on shutdown.

**Failure Modes:**
- Component shutdown timeout: Force-close the component. Log timeout.
- Database flush failure: Log error. Continue with remaining shutdown steps.
  State loss is accepted to avoid hanging the shutdown process.

**Recovery:**
Shutdown Manager cannot recover from its own failure. A hanging shutdown
results in forced kill by the container orchestrator.

**Monitoring:**
Shutdown start timestamp logged. Per-component shutdown duration logged.
Shutdown type logged. Shutdown completion timestamp logged. Exit code logged.

**Engineering Notes:**
The main.py SIGTERM handler calls the Shutdown Manager's clean shutdown
procedure. This is implemented using Python's signal.signal(signal.SIGTERM, handler)
registration. The handler is registered at the end of successful bootstrap,
after SYSTEM_CERTIFIED is issued.

---

## 2.21 Restart Manager

**Purpose:**
The Restart Manager handles the case where the system needs to restart itself
due to an unrecoverable error, a required configuration change, or an operator
restart command. It coordinates with the Shutdown Manager to shut down cleanly
and then re-triggers the bootstrap process.

**Responsibilities:**
1. Receive restart requests (from Recovery Manager, operator commands).
2. Classify restart type (HOT_RESTART, COLD_RESTART, EMERGENCY_RESTART).
3. For HOT_RESTART: Shut down cleanly, preserve state, restart.
4. For COLD_RESTART: Shut down cleanly, clear runtime cache, restart.
5. For EMERGENCY_RESTART: Halt immediately, restart with fresh state.
6. Notify operator via Telegram before restart (if Telegram is available).
7. Record restart event in the startup log.

**Restart Types:**

| Type | Trigger | State | Description |
|------|---------|-------|-------------|
| HOT_RESTART | Config reload, operator command | Preserved | Clean shutdown and restart |
| COLD_RESTART | Upgrade, schema migration | Reset | Clean shutdown, cache cleared, restart |
| EMERGENCY_RESTART | Irrecoverable error | Partial | Fast shutdown, restart |

**Inputs:**
- Restart requests from Recovery Manager or operator.
- Current system state (from Service Registry and State Manager).

**Outputs:**
- Restart log record.
- Telegram notification (restart scheduled, restart completed).
- New bootstrap process invocation.

**Dependencies:**
- Shutdown Manager (performs clean shutdown before restart).
- State Manager (state preservation or reset).
- Telegram bot (notification).

**Lifecycle:**
- Starts: On restart request receipt.
- Completes: When new bootstrap process starts.
- Post-startup role: Activated only on restart request.

**Failure Modes:**
- Shutdown phase fails during restart: Log error. Force restart without clean shutdown.
- New bootstrap fails after restart: Log failure. Send Telegram alert.

**Recovery:**
A restart that fails to produce a healthy system sends a Telegram alert
and enters MAINTENANCE_MODE (waiting for operator action).

**Monitoring:**
Restart count logged. Restart type logged. Time-to-restart logged.
Restart cause logged.

**Engineering Notes:**
Restart in production is a significant operational event. Every restart
records a restart reason. If restart frequency exceeds RESTART_FREQUENCY_THRESHOLD
(e.g., more than 3 restarts in 60 minutes), the system enters MAINTENANCE_MODE
and waits for operator action rather than continuing to restart. Restart loops
are more dangerous than a system that stays down.

---

## 2.22 State Manager

**Purpose:**
The State Manager handles the persistence and recovery of system state across
restarts. It is the central authority for what state is durable, where it
is stored, and how it is recovered.

**Responsibilities:**
1. At startup: load durable state from SQLite and CSV.
2. Validate loaded state for format, schema, and recency.
3. Provide recovered state to components that request it.
4. During operation: accept state flush requests from components.
5. At shutdown: flush all pending state to durable storage.
6. Manage state versioning (schema migrations).

**Durable State Categories:**

| State Item | Storage | Format | Recovery Priority |
|------------|---------|--------|-------------------|
| Paper trades | data/paper_trades.csv | CSV | HIGH |
| Strategy performance | SQLite: strategy_performance | Rows | HIGH |
| Learning state | SQLite: learning_state | Rows | HIGH |
| Regime context | SQLite: regime_context | Row | MEDIUM |
| Knowledge base | SQLite: knowledge_items | Rows | HIGH |
| Cycle telemetry | SQLite: cycle_telemetry | Rows | LOW |
| Agent scores | SQLite: agent_scores | Rows | MEDIUM |

**State Recovery Protocol:**
1. Check state recency: if older than MAX_STATE_AGE_HOURS, discard.
2. Validate schema: if schema mismatch, attempt migration; on failure, discard.
3. Validate format: CSV integrity check; SQLite integrity_check PRAGMA.
4. Load valid state into memory.
5. Notify requesting component of recovered state (or fresh state if recovery failed).

**Inputs:**
- SQLite database (from Configuration Snapshot path).
- CSV files (from Configuration Snapshot paths).
- State flush requests (from components during operation).
- State recovery requests (from components at startup).

**Outputs:**
- Recovered state records (to requesting components).
- State flush confirmations (to components after flush).
- State migration results.

**Dependencies:**
- Configuration Snapshot (database and file paths).
- SQLite connection (from Infrastructure initialization).

**Lifecycle:**
- Starts: After database connection is established.
- Completes: N/A — runs for the lifetime of the system.
- Post-startup role: Manages all state persistence during operation.

**Failure Modes:**
- Database inaccessible: HARD failure at startup. Halt.
- State schema migration failure: HARD failure. Log migration error. Halt.
- State flush failure during operation: Log error. Retry. If retry fails,
  log CRITICAL. Operation continues (data loss is possible but system does not halt).

**Recovery:**
State recovery failures (corrupted data) cause the affected state category
to be reset to its default (fresh) state. The component is notified it is
starting fresh.

**Monitoring:**
State recovery outcomes logged per category. State flush durations logged.
Schema migration events logged. State age at recovery logged.

**Engineering Notes:**
The State Manager enforces the MAX_STATE_AGE_HOURS constraint: state that is
too old is not recovered. This prevents a system that was down for a long period
from loading stale state that no longer reflects market reality. The default
MAX_STATE_AGE_HOURS is 24 hours (configurable in config.py).

---

*End of Part II*

---

# PART III — BOOTSTRAP SEQUENCE

## 3.1 Complete Bootstrap Sequence Overview

`
IIOS COMPLETE BOOTSTRAP SEQUENCE

Stage 0:  Power On / Process Start
Stage 1:  Startup Log Initialization
Stage 2:  Startup Identifier Generation
Stage 3:  Argument Parsing
Stage 4:  Environment Discovery
Stage 5:  Configuration Loading
Stage 6:  Environment Variable Loading
Stage 7:  Secrets Loading
Stage 8:  Repository Validation
Stage 9:  Dependency Graph Construction
Stage 10: Module Discovery and Registration
Stage 11: Startup Plan Computation
Stage 12: Logging System Full Initialization
Stage 13: Database Connection Establishment
Stage 14: State Recovery
Stage 15: Knowledge Base Initialization
Stage 16: Ontology Loading
Stage 17: Shared Utilities Initialization
Stage 18: Core Infrastructure Services
Stage 19: Data Feed Initialization
Stage 20: Cache Initialization
Stage 21: EventBus Initialization
Stage 22: Core AI Framework Initialization
Stage 23: Regime Classifier Initialization
Stage 24: MetaLearning Initialization
Stage 25: Opportunity Engine Initialization
Stage 26: Strategy Lab Initialization
Stage 27: Risk Engine Initialization
Stage 28: Market Simulation Initialization
Stage 29: Risk Guardian Initialization
Stage 30: Debate Agent Registration
Stage 31: Decision Engine Initialization
Stage 32: Execution Engine Initialization
Stage 33: Trade Monitor Initialization
Stage 34: Learning System Initialization
Stage 35: Performance Analytics Initialization
Stage 36: Research Lab Initialization
Stage 37: Validation Engine Initialization
Stage 38: Control Tower Initialization
Stage 39: Telegram Bot Initialization
Stage 40: Dashboard Initialization
Stage 41: Plugin Loading
Stage 42: Health Verification
Stage 43: Self-Certification
Stage 44: Operational Mode Activation
Stage 45: SYSTEM_READY Announcement
`

---

## 3.2 Stage 0 — Power On / Process Start

**Description:**
The operating system starts the Python process from the Docker container
entrypoint or the Windows task scheduler command. The Python interpreter
loads. The main module (main.py) begins execution.

**Pre-conditions:**
- Docker container running (VPS deployment) or Python process started (local).
- Working directory set to IIOS root.
- Environment variables set by Docker Compose or host environment.
- Python virtual environment activated (.venv/ or container Python).

**Actions:**
- Python interpreter initializes.
- main.py begins execution from the top-level if __name__ == "__main__" block.
- Bootstrap Manager class is imported.
- Bootstrap Manager instance is created.
- ootstrap_manager.start() is called.

**Timing Budget:** < 500ms (Python interpreter startup, not counted in IIOS startup time).

**Outputs:**
- Bootstrap Manager instance in memory.
- Process ID (PID) available for PID lock.

**Failure Conditions:**
- Python interpreter not available: OS-level failure. Not handleable by IIOS.
- main.py import error: Python traceback to stderr. Process exits with code 1.

---

## 3.3 Stage 1 — Startup Log Initialization

**Description:**
The very first action of Bootstrap Manager is to initialize the startup log.
This must happen before any other action because all subsequent events must be
logged. If the startup log cannot be initialized, the system writes an
emergency record to stderr and halts.

**Actions:**
1. Determine log directory path (from environment variable LOG_PATH, default: logs/).
2. Create log directory if it does not exist.
3. Open the startup log file (logs/startup_{YYYY-MM-DD}.log).
4. Write the startup log header:
   - Line 1: === IIOS STARTUP INITIATED ===
   - Line 2: Timestamp: {ISO-8601 timestamp}
   - Line 3: Process ID: {PID}
   - Line 4: Python version: {version}
   - Line 5: Working directory: {cwd}

**Timing Budget:** < 100ms.

**Outputs:**
- Startup log file open and writable.
- Log header written.

**Failure Conditions:**
- Log directory creation fails (permissions): Write to stderr. Halt.
- Log file open fails: Write to stderr. Halt.

---

## 3.4 Stage 2 — Startup Identifier Generation

**Description:**
Bootstrap Manager generates the Startup Identifier — a UUID (version 4) that
uniquely identifies this startup session. All subsequent log entries, telemetry
records, and diagnostic reports for this session are tagged with this identifier.

**Actions:**
1. Generate UUID v4.
2. Write Startup Identifier to startup log.
3. Store Startup Identifier in Bootstrap Manager instance.
4. Set Startup Identifier in logging context (all subsequent log records include it).

**Timing Budget:** < 10ms.

**Outputs:**
- Startup Identifier (UUID) in memory and in log.

**Failure Conditions:**
- UUID generation fails: Use timestamp-based fallback identifier. Log warning.

---

## 3.5 Stage 3 — Argument Parsing

**Description:**
Bootstrap Manager parses the command-line arguments passed to main.py.
Arguments determine the operational mode, override specific configuration
values, and enable diagnostic features.

**Supported Arguments:**

| Argument | Type | Description | Default |
|----------|------|-------------|---------|
| --paper | flag | Enable paper trading mode | True if no --live |
| --live | flag | Enable live trading mode | False |
| --telegram | flag | Enable Telegram bot | From config |
| --fresh-start | flag | Ignore recovered state | False |
| --mode | string | Operational mode name | "PAPER_TRADING" |
| --diag | flag | Enable extended diagnostics | False |
| --safe | flag | Force SAFE_MODE startup | False |

**Actions:**
1. Parse sys.argv using defined argument parser.
2. Validate argument combinations (e.g., --paper and --live are mutually exclusive).
3. Store parsed arguments in Bootstrap Manager.
4. Log parsed arguments (excluding any sensitive values).

**Timing Budget:** < 50ms.

**Outputs:**
- Parsed argument set in Bootstrap Manager.

**Failure Conditions:**
- Mutually exclusive arguments both provided: Print usage. Exit with code 1.
- Unknown argument: Print usage. Exit with code 1.

---

## 3.6 Stage 4 — Environment Discovery

**Description:**
Environment Discovery is the process of identifying key characteristics of
the execution environment: operating system, Python version, available disk
space, available memory, and network reachability of required services.

**Actions:**
1. Identify operating system (Windows vs Linux/Docker).
2. Verify Python version meets minimum (>= 3.10).
3. Check available disk space in data directory (minimum 1GB).
4. Check available disk space in log directory (minimum 500MB).
5. Check available memory (minimum 512MB free).
6. Check network reachability of Dhan API endpoint (TCP connect test, 5s timeout).
7. Check network reachability of yfinance (TCP connect test, 5s timeout).
8. Log environment discovery report.

**Timing Budget:** < 5,000ms (network checks are the slow path).

**Outputs:**
- Environment Discovery Report (all checks with PASS/FAIL).

**Failure Conditions:**
- Python version below minimum: HARD failure. Halt.
- Disk space below minimum: HARD failure. Report available and required. Halt.
- Both Dhan and yfinance unreachable: HARD failure (no data feed available). Halt.
- One feed unreachable: WARN. Record which feed is unreachable.

---

## 3.7 Stages 5–8 — Resource Loading

**Description:**
Stages 5 through 8 load the system's external resources: configuration,
environment, secrets, and repository validation. These run sequentially
because each stage may depend on the output of the previous.

**Stage 5 — Configuration Loading (ConfigurationLoader):**
- Load config.py values into Configuration Snapshot.
- Validate all required keys present and in range.
- Timing budget: < 500ms.

**Stage 6 — Environment Variable Loading (EnvironmentLoader):**
- Load required environment variables into Environment Snapshot.
- Validate all CRITICAL variables present.
- Timing budget: < 100ms.

**Stage 7 — Secrets Loading (SecretsLoader):**
- Load sensitive values (API tokens) into Secrets Snapshot.
- Verify no secrets appear in log output.
- Timing budget: < 100ms.

**Stage 8 — Repository Validation (RepositoryValidator):**
- Verify all expected module files exist.
- Verify import graph is acyclic.
- Verify critical interface signatures match expected.
- Timing budget: < 2,000ms.

**Combined Failure Protocol:**
Any HARD failure in Stages 5–8 produces a specific, actionable error message
and halts the startup process. The Startup Diagnostic Report is written before halt.

---

## 3.8 Stages 9–11 — Dependency Graph and Startup Plan

**Description:**
The Dependency Resolver constructs the dependency graph from module manifests,
validates it for cycles, computes the topological sort, and identifies
parallel initialization opportunities.

**Stage 9 — Module Discovery:**
- Scan module directories for __manifest__.json files.
- Parse each manifest and create Module Registry entries.
- Timing budget: < 500ms.

**Stage 10 — Dependency Graph Construction:**
- Build dependency DAG from module manifest declarations.
- Detect cycles. Halt if found.
- Timing budget: < 200ms.

**Stage 11 — Startup Plan Computation:**
- Topological sort of DAG.
- Identify parallel groups (components with same topological level).
- Compute critical path.
- Produce startup plan (ordered list of initialization stages with parallelism annotations).
- Timing budget: < 100ms.

**Startup Plan Output Format:**
`
STARTUP PLAN
Stage 1: [ConfigLoader] — SEQUENTIAL
Stage 2: [EnvLoader] — SEQUENTIAL
Stage 3: [SecretsLoader] — SEQUENTIAL
Stage 4: [RepoValidator] — SEQUENTIAL
Stage 5: [DatabaseManager, LoggingSystem] — PARALLEL (2 components)
Stage 6: [StateManager, KnowledgeRegistry, OntologyRegistry] — PARALLEL (3)
Stage 7: [DataFeedManager] — SEQUENTIAL
Stage 8: [EventBus] — SEQUENTIAL
Stage 9: [GlobalIntelligence, MarketMonitor] — PARALLEL (2)
...
Critical path: {component_chain} — estimated {N}ms
`

---

## 3.9 Stage 12 — Logging System Full Initialization

**Description:**
The full logging system (structured logging with rotation, levels, and
multiple handlers) is initialized. Before this stage, only the startup log
(a simple file) is available. After this stage, the complete logging system
is operational.

**Actions:**
1. Initialize the root logger with structured format.
2. Configure file handler with daily rotation (logs/iios_{YYYY-MM-DD}.log).
3. Configure console handler (for development mode).
4. Configure log level from Configuration Snapshot.
5. Set Startup Identifier as logging context variable.
6. Replace startup log writer with the structured logging system.
7. Log: "Full logging system initialized."

**Timing Budget:** < 200ms.

**Outputs:**
- Fully operational logging system.
- All subsequent log entries are structured (timestamp, level, startup_id, component, message).

---

## 3.10 Stage 13 — Database Connection Establishment

**Description:**
Establish connections to all required databases (SQLite). Verify connectivity,
run integrity checks, and prepare for schema migration if required.

**Actions:**
1. Open SQLite connection to main database (path from Configuration Snapshot).
2. Run SQLite PRAGMA integrity_check. If result is not "ok": HARD failure.
3. Check current schema version against expected version.
4. If schema migration required:
   a. Back up database before migration.
   b. Apply migration scripts in order.
   c. Verify migration succeeded.
   d. Update schema version.
5. Verify all expected tables and indexes exist.
6. Log database connection report.

**Timing Budget:** < 2,000ms (migration may take longer; see migration timeout).

**Outputs:**
- Active SQLite connection.
- Schema version confirmed.
- Database integrity verified.

**Failure Conditions:**
- Database file not found: Create new database. Apply initial schema.
- Integrity check fails: HARD failure. Halt. Manual intervention required.
- Migration fails: HARD failure. Restore backup. Halt.

---

## 3.11 Stages 14–16 — State, Knowledge, Ontology

**Stage 14 — State Recovery (StateManager):**
- Load durable state from SQLite and CSV.
- Apply recency filter (discard state older than MAX_STATE_AGE_HOURS).
- Validate state format and schema.
- Make recovered state available to requesting components.
- Timing budget: < 1,000ms.

**Stage 15 — Knowledge Base Initialization (KnowledgeRegistry):**
- Verify knowledge base tables exist and are readable.
- Load critical knowledge items into in-memory cache.
- Run contradiction scan on loaded items.
- Report knowledge metrics.
- Timing budget: < 1,000ms.

**Stage 16 — Ontology Loading (OntologyRegistry):**
- Load ontology definitions from source.
- Validate internal consistency.
- Build in-memory ontology structure.
- Register OntologyValidator with Service Registry.
- Timing budget: < 500ms.

---

## 3.12 Stages 17–21 — Infrastructure Services

**Stage 17 — Shared Utilities Initialization:**
- Initialize decimal arithmetic utilities (for precise financial calculations).
- Initialize date and time utilities (market calendar, trading day checks).
- Initialize symbol mapping utilities (GLOBAL_SYMBOL_MAP loaded into memory).
- Timing budget: < 200ms.

**Stage 18 — Core Infrastructure Services:**
- Initialize SystemMonitor with per-layer latency thresholds from config.
- Initialize layer timing context manager.
- Initialize performance counter.
- Timing budget: < 100ms.

**Stage 19 — Data Feed Initialization:**
- Initialize DataFeedManager.
- Attempt Dhan feed initialization (using Secrets Snapshot for API token).
- If Dhan initialization fails (451 or timeout): log warning; initialize yfinance feed.
- Verify active feed returns a valid quote for a test symbol.
- Register DataFeedManager as READY (with active feed noted).
- Timing budget: < 5,000ms (network operations).

**Stage 20 — Cache Initialization:**
- Initialize in-memory cache for market data (ring buffer, size from config).
- Initialize GlobalDataAI 5-minute cache with background pre-warm thread.
- Pre-warm cache with last-known market snapshot if available.
- Timing budget: < 500ms.

**Stage 21 — EventBus Initialization:**
- Initialize EventBus with configured subscriber list.
- Verify EventBus can publish and deliver a test event.
- Register EventBus as READY in Service Registry.
- Timing budget: < 100ms.

---

## 3.13 Stages 22–38 — AI and Trading Layer Initialization

**Description:**
These stages initialize the 17 IIOS trading layers in dependency order.
All stages from 22 onward use the SystemMonitor.time_layer() context
manager to measure initialization latency.

**Stage 22 — Layer 1: GlobalIntelligence:**
- Initialize GlobalDataAI.
- Run etch(force=True) to populate initial GlobalSnapshot.
- Verify GlobalSnapshot contains expected fields.
- Timing budget: GlobalIntelligence critical override: 12,000ms.

**Stage 23 — Layer 2: MarketIntelligence:**
- Initialize MarketIntelligenceAI.
- Initialize MarketMonitor (continuous scan, 30-second interval).
- Verify regime classification produces a valid RegimeEnum value.
- Timing budget: MarketIntelligence critical override: 5,000ms.

**Stage 24 — Layer 3: MetaLearning:**
- Initialize MetaStrategyController.
- Load k-NN model from SQLite (or initialize fresh if absent).
- Load RegimeStrategyMap via get_regime_strategy_map().
- Verify strategy weights sum to 1.0.
- Timing budget: 3,000ms.

**Stage 25 — Layer 4: OpportunityEngine:**
- Initialize all scanner agents (equity, options, arbitrage).
- Register each scanner in AI Agent Registry as SCANNER_AGENT.
- Verify at least one scanner is operational.
- Timing budget: 2,000ms.

**Stage 26 — Layer 5: StrategyLab:**
- Initialize MetaStrategyController (if not done in Layer 3).
- Load evolved strategies from strategy_lab/evolved_strategies/.
- Apply strategy enable/disable state from recovered learning system state.
- Verify at least one strategy is active.
- Timing budget: 2,000ms.

**Stage 27 — Layer 6: CapitalRiskEngine:**
- Initialize CapitalRiskEngine with strategy budget allocations from config.
- Verify budget allocations sum to <= total capital.
- Timing budget: 500ms.

**Stage 28 — Layer 7: RiskControl:**
- Initialize RiskManagerAI.
- Initialize PortfolioAllocation.
- Initialize StressTestFilter (14-scenario Monte Carlo setup).
- Timing budget: 1,000ms.

**Stage 29 — Layer 8: MarketSimulation:**
- Initialize Monte Carlo engine (14 scenarios, parameters from config).
- Verify Monte Carlo produces finite results on test input.
- Timing budget: 1,000ms.

**Stage 30 — Layer 9: RiskGuardian (PROTECTED MODULE):**
- Initialize RiskGuardian (PROTECTED: no modification without explicit instruction).
- Verify kill switch thresholds: VIX_THRESHOLD = 45.0, DAILY_LOSS_THRESHOLD = 0.02.
- Register KILL_SWITCH_TRIGGERED event subscription on EventBus.
- Timing budget: 500ms.

**Stage 31 — Layer 10: DebateAndDecision:**
- Initialize BullAgent, BearAgent, NeutralAgent, RiskAgent, RegimeAgent.
- Register each as DEBATE_AGENT in AI Agent Registry.
- Verify exactly 5 debate agents registered.
- Initialize DebateOrchestrator.
- Initialize ScoreAggregator.
- Initialize DecisionEngine (DECISION_THRESHOLD = 6.5 from config).
- Verify decision engine produces correct outcome for test scores.
- Timing budget: 2,000ms.

**Stage 32 — Layer 11: ExecutionEngine:**
- Initialize OrderManager.
- If PAPER_TRADING = True: verify paper journal file is accessible.
- If PAPER_TRADING = False: verify broker connection (Dhan).
- Timing budget: 1,000ms.

**Stage 33 — Layer 12: TradeMonitoring:**
- Initialize TradeMonitor.
- Initialize StrategyHealthMonitor.
- Subscribe to TRADE_EXECUTED events on EventBus.
- Timing budget: 500ms.

**Stage 34 — Layer 13: LearningSystem:**
- Initialize LearningEngine.
- Load StrategyPerformanceTracker via get_performance_tracker().
- Load closed trades from today's paper journal (for post-restart continuation).
- Verify performance metrics recovered or reset correctly.
- Timing budget: 1,000ms.

**Stage 35 — Layer 14: PerformanceAnalytics:**
- Initialize DrawdownAnalyzer.
- Initialize WalkForwardTester.
- Timing budget: 500ms.

**Stage 36 — Layer 15: ResearchLab:**
- Initialize StrategyResearchAgent.
- Verify promotion gate configuration:
  WIN_RATE_THRESHOLD >= 0.50, SHARPE_THRESHOLD > 0.8, MAX_DD_THRESHOLD < 0.15.
- Timing budget: 500ms.

**Stage 37 — Layer 16: ValidationEngine (PROTECTED MODULE):**
- Initialize ValidationEngine (PROTECTED: no modification without explicit instruction).
- Verify 6-stage pipeline configuration.
- Timing budget: 500ms.

**Stage 38 — Layer 17: ControlTower:**
- Initialize SQLite telemetry writer.
- Initialize EventBus telemetry subscriber.
- Initialize Streamlit dashboard data bridge.
- Timing budget: 500ms.

---

## 3.14 Stages 39–41 — Peripheral Services

**Stage 39 — Telegram Bot Initialization:**
- Initialize Telegram bot using Secrets Snapshot (TELEGRAM_BOT_TOKEN).
- Register all 13 command handlers.
- Verify bot can send and receive a test message (if Telegram is reachable).
- Register as READY (or DEGRADED if unreachable).
- Timing budget: 3,000ms.

**Stage 40 — Dashboard Initialization:**
- Initialize Streamlit dashboard data pipeline.
- Start dashboard data refresh background thread.
- Register dashboard as READY.
- Timing budget: 500ms.

**Stage 41 — Plugin Loading:**
- Invoke Plugin Registry to discover and load all plugins.
- Initialize plugins in dependency order after core system is complete.
- Log plugin load results.
- Timing budget: configurable per plugin; total: < 10,000ms.

---

## 3.15 Stages 42–45 — Verification, Certification, Ready

**Stage 42 — Health Verification:**
- Health Manager queries all registered components.
- Runs health check callback for each.
- Categorizes results by severity.
- Produces Health Report.
- Timing budget: < 5,000ms (all health checks must complete within budget).

**Stage 43 — Self-Certification:**
- Bootstrap Manager reviews Health Report.
- Applies certification matrix (HARD vs SOFT checks).
- Issues SYSTEM_CERTIFIED, SYSTEM_CERTIFIED_DEGRADED, or SYSTEM_NOT_CERTIFIED.
- On CERTIFIED or CERTIFIED_DEGRADED: proceed to Stage 44.
- On NOT_CERTIFIED: produce Startup Diagnostic Report. Halt.

**Stage 44 — Operational Mode Activation:**
- Bootstrap Manager reads operational mode from parsed arguments.
- Activates the specified mode (PAPER_TRADING, PRODUCTION, etc.).
- Registers SIGTERM handler with Shutdown Manager.
- Sets system state to OPERATIONAL.
- Timing budget: < 100ms.

**Stage 45 — SYSTEM_READY Announcement:**
- Bootstrap Manager publishes SYSTEM_READY event to EventBus.
- Writes startup completion record to startup log:
  - Total startup duration.
  - Operational mode.
  - Active data feed.
  - Component count.
  - Certification status.
- Hands control to MasterOrchestrator.
- MasterOrchestrator begins first operational cycle.
- Timing budget: < 100ms.

**Total Bootstrap Duration Target:** < 30,000ms (30 seconds) for full startup.
**Emergency Bootstrap Duration Target:** < 10,000ms (10 seconds) for safe-mode startup.

---

*End of Part III*

# PART IV — INITIALIZATION DEPENDENCIES

## 4.1 Dependency Tree Overview

The IIOS initialization dependency tree defines the precise order in which
every component must be ready before another component can start. The tree
is a directed acyclic graph (DAG) where an edge from A to B means "A must be
READY before B can initialize."

---

## 4.2 Master Dependency DAG

`
IIOS INITIALIZATION DEPENDENCY DAG

Level 0 (no dependencies — start in parallel):
  [BootstrapManager]

Level 1 (depends on BootstrapManager only):
  [StartupLog]
  [StartupIdentifier]
  [ArgumentParser]

Level 2 (depends on Level 1):
  [EnvironmentDiscovery]

Level 3 (depends on Level 2):
  [ConfigurationLoader]
  [EnvironmentLoader]
  [SecretsLoader]

Level 4 (depends on Level 3):
  [RepositoryValidator]

Level 5 (depends on Level 4):
  [DependencyResolver]
  [ModuleRegistry]

Level 6 (depends on Level 5):
  [StartupCoordinator]
  [StartupPlan]

Level 7 (depends on Level 6 — parallel group):
  [LoggingSystem]       — no inter-level dependencies
  [DatabaseConnection]  — no inter-level dependencies

Level 8 (depends on Level 7 — parallel group):
  [StateManager]       — requires DatabaseConnection
  [KnowledgeRegistry]  — requires DatabaseConnection
  [OntologyRegistry]   — requires DatabaseConnection

Level 9 (depends on Level 8 — parallel group):
  [SharedUtilities]    — no dependencies on Level 8
  [SystemMonitor]      — no dependencies on Level 8
  [ServiceRegistry]    — no dependencies on Level 8
  [ComponentRegistry]  — requires ServiceRegistry

Level 10 (depends on Level 9):
  [DataFeedManager]    — requires SharedUtilities (GLOBAL_SYMBOL_MAP)

Level 11 (depends on Level 10 — parallel group):
  [Cache]              — requires DataFeedManager (pre-warm)
  [EventBus]           — requires ServiceRegistry

Level 12 (depends on Level 11 — IIOS Layer 1):
  [GlobalDataAI]       — requires DataFeedManager, Cache, EventBus

Level 13 (depends on Level 12 — IIOS Layer 2):
  [MarketIntelligenceAI]  — requires GlobalDataAI
  [MarketMonitor]         — requires MarketIntelligenceAI

Level 14 (depends on Level 13 — IIOS Layer 3):
  [MetaStrategyController]  — requires MarketIntelligenceAI
  [RegimeStrategyMap]       — requires MetaStrategyController

Level 15 (depends on Level 14 — parallel group):
  [OpportunityEngine]  — requires MarketIntelligenceAI, MetaStrategyController
  [StrategyLab]        — requires MetaStrategyController, StateManager

Level 16 (depends on Level 15):
  [CapitalRiskEngine]  — requires StrategyLab (strategy budgets)

Level 17 (depends on Level 16 — parallel group):
  [RiskManagerAI]         — requires CapitalRiskEngine
  [PortfolioAllocation]   — requires CapitalRiskEngine
  [MarketSimulation]      — requires MarketIntelligenceAI

Level 18 (depends on Level 17):
  [StressTestFilter]   — requires RiskManagerAI, MarketSimulation
  [RiskGuardian]       — requires EventBus (PROTECTED MODULE)

Level 19 (depends on Level 18):
  [BullAgent]         — requires MarketIntelligenceAI, KnowledgeRegistry
  [BearAgent]         — requires MarketIntelligenceAI, KnowledgeRegistry
  [NeutralAgent]      — requires KnowledgeRegistry, StrategyLab
  [RiskAgent]         — requires RiskManagerAI, StressTestFilter
  [RegimeAgent]       — requires RegimeStrategyMap, MetaStrategyController

Level 20 (depends on Level 19):
  [DebateOrchestrator]  — requires all 5 DebateAgents
  [ScoreAggregator]     — requires DebateOrchestrator
  [DecisionEngine]      — requires ScoreAggregator, RiskGuardian

Level 21 (depends on Level 20):
  [OrderManager]     — requires DecisionEngine, EventBus

Level 22 (depends on Level 21 — parallel group):
  [TradeMonitor]            — requires OrderManager, EventBus
  [StrategyHealthMonitor]   — requires OrderManager, EventBus

Level 23 (depends on Level 22):
  [LearningEngine]          — requires TradeMonitor, StrategyHealthMonitor
  [StrategyPerformanceTracker]  — requires LearningEngine, StateManager

Level 24 (depends on Level 23 — parallel group):
  [DrawdownAnalyzer]    — requires StrategyPerformanceTracker
  [WalkForwardTester]   — requires StrategyPerformanceTracker, StrategyLab

Level 25 (depends on Level 24):
  [ResearchLab]         — requires DrawdownAnalyzer, WalkForwardTester

Level 26 (depends on Level 25):
  [ValidationEngine]    — requires ResearchLab (PROTECTED MODULE)

Level 27 (depends on Level 26 — parallel group):
  [ControlTower]        — requires EventBus, DatabaseConnection
  [TelegramBot]         — requires EventBus (optional)
  [Dashboard]           — requires ControlTower (optional)

Level 28 (depends on Level 27):
  [PluginRegistry]      — requires all core components

Level 29 (depends on Level 28):
  [HealthManager]       — queries all registered components

Level 30 (depends on Level 29):
  [SelfCertification]   — depends on Health Report from HealthManager
  [MasterOrchestrator]  — starts after SYSTEM_CERTIFIED
`

---

## 4.3 Critical Startup Path

The critical startup path is the longest dependency chain. It determines the
minimum possible startup time.

`
CRITICAL STARTUP PATH

BootstrapManager
  → StartupLog (Stage 1)
  → ConfigurationLoader (Stage 5)
  → RepositoryValidator (Stage 8)
  → DependencyResolver (Stage 9)
  → DatabaseConnection (Stage 13)
  → StateManager (Stage 14)
  → DataFeedManager (Stage 19)
  → EventBus (Stage 21)
  → GlobalDataAI (Stage 22)
  → MarketIntelligenceAI (Stage 23)
  → MetaStrategyController (Stage 24)
  → StrategyLab (Stage 26)
  → CapitalRiskEngine (Stage 27)
  → RiskManagerAI (Stage 28)
  → StressTestFilter (Stage 29)
  → RiskGuardian (Stage 30)
  → [All 5 DebateAgents] (Stage 31)
  → DecisionEngine (Stage 31)
  → OrderManager (Stage 32)
  → TradeMonitor (Stage 33)
  → LearningEngine (Stage 34)
  → DrawdownAnalyzer (Stage 35)
  → ResearchLab (Stage 36)
  → ValidationEngine (Stage 37)
  → ControlTower (Stage 38)
  → HealthManager (Stage 42)
  → SelfCertification (Stage 43)
  → MasterOrchestrator (Stage 45)

ESTIMATED CRITICAL PATH DURATION:
  Configuration and validation:  3,000ms
  Database and state:            2,000ms
  Data feeds:                    5,000ms
  Layer 1-9 initialization:      8,000ms
  Layer 10-17 initialization:    5,000ms
  Peripheral services:           4,000ms
  Health check and certification: 5,000ms
  TOTAL ESTIMATE:               32,000ms (32 seconds maximum)
  TARGET:                        < 30,000ms
`

---

## 4.4 Parallel Initialization Groups

Components within a parallel group can initialize concurrently, reducing
total startup time.

`
PARALLEL GROUP SPECIFICATIONS

Group PG-1 (Level 7 — 2 components):
  Components: LoggingSystem, DatabaseConnection
  Can run in parallel because: No dependency between them.
  Both depend on: StartupPlan (Level 6).
  Time saving: ~1,000ms vs sequential.

Group PG-2 (Level 8 — 3 components):
  Components: StateManager, KnowledgeRegistry, OntologyRegistry
  Can run in parallel because: All depend on DatabaseConnection only.
  Both depend on: DatabaseConnection (Level 7).
  Time saving: ~1,000ms vs sequential.

Group PG-3 (Level 9 — 4 components):
  Components: SharedUtilities, SystemMonitor, ServiceRegistry, ComponentRegistry
  Can run in parallel because: No inter-dependencies.
  Note: ComponentRegistry depends on ServiceRegistry — split into sub-groups.
  PG-3a (parallel): SharedUtilities, SystemMonitor, ServiceRegistry
  PG-3b (after PG-3a): ComponentRegistry
  Time saving: ~500ms vs sequential.

Group PG-4 (Level 11 — 2 components):
  Components: Cache, EventBus
  Can run in parallel because: Cache depends on DataFeedManager; EventBus depends on ServiceRegistry.
  Both are satisfied by Level 10.
  Time saving: ~300ms vs sequential.

Group PG-5 (Level 15 — 2 components):
  Components: OpportunityEngine, StrategyLab
  Can run in parallel because: Opportunity Engine does not depend on StrategyLab.
  Time saving: ~1,000ms vs sequential.

Group PG-6 (Level 17 — 3 components):
  Components: RiskManagerAI, PortfolioAllocation, MarketSimulation
  Can run in parallel because: Independent initializations with same parent dependencies.
  Time saving: ~1,000ms vs sequential.

Group PG-7 (Level 19 — 5 components):
  Components: BullAgent, BearAgent, NeutralAgent, RiskAgent, RegimeAgent
  Can run in parallel because: Each agent initializes independently.
  Time saving: ~2,000ms vs sequential.

Group PG-8 (Level 22 — 2 components):
  Components: TradeMonitor, StrategyHealthMonitor
  Can run in parallel because: No dependency between them.
  Time saving: ~300ms vs sequential.

Group PG-9 (Level 24 — 2 components):
  Components: DrawdownAnalyzer, WalkForwardTester
  Can run in parallel because: No dependency between them.
  Time saving: ~500ms vs sequential.

Group PG-10 (Level 27 — 3 components):
  Components: ControlTower, TelegramBot, Dashboard
  Note: Dashboard depends on ControlTower — sub-groups:
  PG-10a: ControlTower, TelegramBot (parallel)
  PG-10b: Dashboard (after ControlTower)
  Time saving: ~1,000ms vs sequential.
`

---

## 4.5 Optional Startup Path

Some components are OPTIONAL and do not block startup. Their initialization
runs on the optional path.

`
OPTIONAL STARTUP PATH

Optional components (OPTIONAL classification):
  - TelegramBot:     OPTIONAL — degraded operation if unavailable.
  - Dashboard:       OPTIONAL — degraded operation if unavailable.
  - All Plugins:     OPTIONAL — features unavailable if absent.
  - DiagnosticsManager: OPTIONAL — diagnostic output unavailable.

Optional path characteristics:
  - Optional components initialize AFTER all CRITICAL and IMPORTANT components.
  - Optional component failure logs WARNING and continues.
  - Optional component failure does not affect Health Report certification outcome.
  - Optional components are marked as NOT_PRESENT in Service Registry (not FAILED).
`

---

## 4.6 Emergency Startup Mode

Emergency startup mode initializes only the minimum components required to
manage existing positions. No new trading. Only monitoring and kill switch.

`
EMERGENCY STARTUP COMPONENTS (mandatory):
  Level 1: LoggingSystem, DatabaseConnection
  Level 2: StateManager (position recovery only)
  Level 3: DataFeedManager (price monitoring)
  Level 4: EventBus
  Level 5: RiskGuardian (kill switch monitoring)
  Level 6: OrderManager (position management only — no new orders)
  Level 7: TradeMonitor (existing position monitoring)
  Level 8: TelegramBot (operator notification)

EMERGENCY STARTUP TARGET: < 10,000ms.

EMERGENCY MODE RESTRICTIONS:
  - No new trading cycles.
  - No new position entries.
  - Existing position monitoring active.
  - Kill switch monitoring active.
  - Manual position exit available via Telegram bot.
  - Operator notification sent immediately on EMERGENCY MODE entry.
`

---

## 4.7 Safe Mode

Safe mode is a degraded operational mode where the system runs but all
trading activity is suspended. The system monitors positions, monitors
market conditions, and waits for operator authorization to resume.

`
SAFE MODE TRIGGERS:
  - IMPORTANT component fails and no fallback available.
  - Operator issues /safe command via Telegram.
  - System detects anomalous behavior pattern.
  - Startup certification returns SYSTEM_CERTIFIED_DEGRADED with SAFE_MODE recommendation.

SAFE MODE ACTIVE COMPONENTS:
  Same as Emergency Mode plus:
  - MarketIntelligenceAI (regime monitoring)
  - LearningSystem (performance tracking, no new executions)
  - ControlTower (telemetry)
  - Dashboard (monitoring display)

SAFE MODE EXIT:
  - Operator issues /resume command via Telegram.
  - Bootstrap Manager verifies all CRITICAL and IMPORTANT components are READY.
  - Health Manager confirms HEALTHY or DEGRADED-WARN status.
  - MasterOrchestrator resumes normal operational cycles.
`

---

## 4.8 Recovery Mode

Recovery mode is entered when the system detects that it restarted after
a crash or unexpected shutdown. Recovery mode prioritizes state restoration
before operational resumption.

`
RECOVERY MODE TRIGGERS:
  - Last shutdown record is UNEXPECTED_SHUTDOWN (not CLEAN_SHUTDOWN).
  - State recovery finds state from previous session.
  - Database integrity check required.

RECOVERY MODE SEQUENCE:
  1. Full startup sequence (all components).
  2. After Level 8 (StateManager ready):
     a. Load all durable state from previous session.
     b. Validate state consistency.
     c. Run reconciliation (compare recovered positions against broker).
     d. Flag any inconsistencies for operator review.
  3. After full startup:
     a. Send Telegram notification: "System recovered from unexpected shutdown."
     b. Include state recovery summary (positions recovered, metrics recovered).
     c. Wait for operator acknowledgment before resuming trading (configurable).
  4. On operator acknowledgment (or after RECOVERY_AUTO_RESUME_MINUTES):
     Resume normal operational cycles.
`

---

*End of Part IV*

---

# PART V — HEALTH VERIFICATION

## 5.1 Health Verification Framework

Health verification is the structured process of confirming that every
component is in a state that is safe for operation. It runs at three
points in the system lifecycle:
1. At startup (startup health verification — part of bootstrap).
2. Continuously during operation (operational health monitoring).
3. On demand (via Telegram /health command or dashboard).

The Health Manager coordinates all health verification. It maintains a
health state record for every registered component and produces a Health Report
on each verification cycle.

**Health Verification Principles:**
- Every component has a defined health check callback.
- Health checks are fast (<= 500ms per component, hard limit).
- Health checks are non-destructive (read-only, no side effects).
- Health check failures are reported immediately.
- Health state history is maintained (last 10 health check results per component).
- Trend detection: a component that is consistently DEGRADED is escalated.

---

## 5.2 Repository Health

**Purpose:** Verify the code repository is intact and matches expectations.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| RH-01 | All required module files exist | All files present | CRITICAL |
| RH-02 | No unexpected module files in protected directories | No unknown files | IMPORTANT |
| RH-03 | Import graph is acyclic | No cycles detected | CRITICAL |
| RH-04 | Critical interface signatures match expected | All signatures match | CRITICAL |
| RH-05 | Protected module hashes match build manifest | All hashes match | IMPORTANT |
| RH-06 | Version tag matches expected version | Tags consistent | OPTIONAL |

**Repository Health Score Computation:**
- RH-01, RH-03, RH-04 failures: Repository Health = FAILED.
- RH-02, RH-05 failures: Repository Health = DEGRADED.
- RH-06 failure: Repository Health = WARN.

**Monitoring Frequency:** Startup only (repository health is static during operation).

**Health Check Execution Time:** < 2,000ms.

---

## 5.3 Configuration Health

**Purpose:** Verify all configuration values are present, valid, and within operational bounds.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| CH-01 | All CRITICAL config keys present | Present | CRITICAL |
| CH-02 | DECISION_THRESHOLD in valid range | 0.0 <= x <= 10.0 | CRITICAL |
| CH-03 | KILL_SWITCH_VIX in valid range | 0.0 <= x <= 100.0 | CRITICAL |
| CH-04 | KILL_SWITCH_DAILY_LOSS_PCT in valid range | 0.0 <= x <= 1.0 | CRITICAL |
| CH-05 | PROMOTION_WIN_RATE in valid range | 0.0 <= x <= 1.0 | CRITICAL |
| CH-06 | PROMOTION_SHARPE > 0.0 | Positive | CRITICAL |
| CH-07 | LAYER_LATENCY_CRIT_MS > LAYER_LATENCY_WARN_MS | Ordered correctly | IMPORTANT |
| CH-08 | PAPER_TRADING is boolean | True or False | CRITICAL |
| CH-09 | SCHEDULE is non-empty dict | Non-empty | IMPORTANT |
| CH-10 | All environment variables resolve | No missing vars | CRITICAL |

**Configuration Health Score:**
- Any CH-01 through CH-08 failure: Configuration Health = FAILED.
- CH-09 or CH-10 failure: Configuration Health = DEGRADED.

**Monitoring Frequency:** Startup only (Configuration Snapshot is immutable).

**Health Check Execution Time:** < 100ms.

---

## 5.4 Knowledge Health

**Purpose:** Verify the knowledge base is accessible, consistent, and contains
sufficient knowledge for trading decisions.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| KH-01 | Knowledge base database accessible | Accessible | CRITICAL |
| KH-02 | SQLite PRAGMA integrity_check passes | "ok" | CRITICAL |
| KH-03 | Expected tables present | All tables exist | CRITICAL |
| KH-04 | Schema version matches expected | Version match | CRITICAL |
| KH-05 | Knowledge item count > minimum threshold | Count >= MIN_KB_ITEMS | IMPORTANT |
| KH-06 | No CRITICAL knowledge contradictions | Zero contradictions | IMPORTANT |
| KH-07 | Knowledge staleness within bounds | No items older than MAX_KB_AGE | IMPORTANT |
| KH-08 | Provenance completeness > 90% | >= 90% have provenance | OPTIONAL |
| KH-09 | Knowledge cache populated | Cache non-empty | IMPORTANT |
| KH-10 | Confidence score distribution healthy | Mean >= 0.5 | OPTIONAL |

**Knowledge Health Score:**
- KH-01 through KH-04 failure: Knowledge Health = FAILED.
- KH-05 through KH-09 failure: Knowledge Health = DEGRADED.
- KH-10 failure: Knowledge Health = WARN.

**Monitoring Frequency:** Every 60 minutes during operation.

**Health Check Execution Time:** < 1,000ms.

---

## 5.5 Ontology Health

**Purpose:** Verify the ontology is loaded, internally consistent, and available
for entity validation.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| OH-01 | Ontology loaded in memory | Non-empty ontology | CRITICAL |
| OH-02 | Entity type count > 0 | >= 1 entity type | CRITICAL |
| OH-03 | Relationship type count > 0 | >= 1 relationship type | IMPORTANT |
| OH-04 | No undefined references in ontology | Zero undefined refs | CRITICAL |
| OH-05 | OntologyValidator operational | Accepts valid entity | CRITICAL |
| OH-06 | OntologyValidator rejects invalid entity | Rejects invalid | CRITICAL |

**Ontology Health Score:**
- Any OH-01 through OH-06 failure: Ontology Health = FAILED (no partial credit).

**Monitoring Frequency:** Startup only (ontology is static during operation).

**Health Check Execution Time:** < 200ms.

---

## 5.6 Database Health

**Purpose:** Verify database connections are active, schemas are current,
and performance is within acceptable bounds.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| DB-01 | SQLite connection active | Connection open | CRITICAL |
| DB-02 | PRAGMA integrity_check | "ok" | CRITICAL |
| DB-03 | All tables accessible | All queries return | CRITICAL |
| DB-04 | Write test succeeds (write + delete test record) | Write and delete OK | CRITICAL |
| DB-05 | Index health (PRAGMA index_check) | No index errors | IMPORTANT |
| DB-06 | Database size within bounds | Size <= MAX_DB_SIZE_MB | IMPORTANT |
| DB-07 | Simple query latency < 100ms | Latency OK | IMPORTANT |
| DB-08 | WAL checkpoint not stuck | WAL size < MAX_WAL_SIZE | OPTIONAL |

**Database Health Score:**
- DB-01 through DB-04 failure: Database Health = FAILED.
- DB-05 through DB-07 failure: Database Health = DEGRADED.
- DB-08 failure: Database Health = WARN.

**Monitoring Frequency:** Every 10 minutes during operation.

**Health Check Execution Time:** < 500ms.

---

## 5.7 Infrastructure Health

**Purpose:** Verify that all infrastructure services (data feeds, caches,
event bus) are operational and performing within latency bounds.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| IH-01 | At least one data feed READY | Dhan or yfinance | CRITICAL |
| IH-02 | Active feed returns valid quote for NIFTY | Valid TickerQuote | CRITICAL |
| IH-03 | Data feed quote latency < 5,000ms | Within budget | IMPORTANT |
| IH-04 | GLOBAL_SYMBOL_MAP loaded | Non-empty map | CRITICAL |
| IH-05 | Cache accessible and non-empty | Cache populated | IMPORTANT |
| IH-06 | EventBus can publish and deliver test event | Event delivered | CRITICAL |
| IH-07 | EventBus subscriber count > 0 | At least 1 subscriber | IMPORTANT |
| IH-08 | Dhan feed status logged | Status recorded | OPTIONAL |
| IH-09 | yfinance fallback tested | Fallback functional | IMPORTANT |

**Infrastructure Health Score:**
- IH-01, IH-02, IH-04, IH-06 failure: Infrastructure Health = FAILED.
- IH-03, IH-05, IH-07, IH-09 failure: Infrastructure Health = DEGRADED.
- IH-08 failure: Infrastructure Health = WARN.

**Monitoring Frequency:** Every 5 minutes during operation.

**Health Check Execution Time:** < 5,000ms (includes network call for IH-02).

---

## 5.8 AI Health

**Purpose:** Verify that all AI components are initialized, producing valid
outputs, and within performance bounds.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| AI-01 | All 5 DebateAgents registered | Count == 5 | CRITICAL |
| AI-02 | BullAgent produces score in [0.0, 10.0] | Valid score | CRITICAL |
| AI-03 | BearAgent produces score in [0.0, 10.0] | Valid score | CRITICAL |
| AI-04 | NeutralAgent produces score in [0.0, 10.0] | Valid score | CRITICAL |
| AI-05 | RiskAgent produces score in [0.0, 10.0] | Valid score | CRITICAL |
| AI-06 | RegimeAgent produces score in [0.0, 10.0] | Valid score | CRITICAL |
| AI-07 | RegimeClassifier produces valid RegimeEnum | Valid enum value | CRITICAL |
| AI-08 | ScoreAggregator produces composite in [0.0, 10.0] | Valid composite | CRITICAL |
| AI-09 | DecisionEngine threshold applied correctly | Correct APPROVED/REJECTED | CRITICAL |
| AI-10 | Strategy count > 0 (at least one active strategy) | Count >= 1 | CRITICAL |
| AI-11 | k-NN model loaded or initialized | Model available | IMPORTANT |
| AI-12 | All scanner agents operational | Count >= 1 | IMPORTANT |

**AI Health Score:**
- AI-01 through AI-10 failure: AI Health = FAILED.
- AI-11, AI-12 failure: AI Health = DEGRADED.

**Monitoring Frequency:** Every 30 minutes during operation.

**Health Check Execution Time:** < 2,000ms (all smoke tests with synthetic input).

---

## 5.9 Performance Health

**Purpose:** Verify that latency-sensitive operations are within their defined budgets.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| PH-01 | GlobalIntelligence cycle latency p99 | <= 17ms | IMPORTANT |
| PH-02 | MarketIntelligence cycle latency p99 | <= 19ms | IMPORTANT |
| PH-03 | Full trading cycle latency p99 | <= 172ms (baseline) | IMPORTANT |
| PH-04 | Full trading cycle latency p99 | <= 200ms (SLA) | CRITICAL |
| PH-05 | Database write latency p99 | <= 50ms | IMPORTANT |
| PH-06 | Data feed quote latency p99 | <= 5,000ms | IMPORTANT |
| PH-07 | EventBus delivery latency p99 | <= 10ms | IMPORTANT |
| PH-08 | Memory usage within bounds | <= MAX_MEMORY_MB | IMPORTANT |
| PH-09 | CPU usage within bounds (1-minute avg) | <= MAX_CPU_PCT | OPTIONAL |
| PH-10 | Disk write throughput acceptable | >= MIN_DISK_WRITE_MBps | OPTIONAL |

**Performance Health Score:**
- PH-04 failure: Performance Health = FAILED (SLA violated).
- PH-01 through PH-03, PH-05 through PH-08 failure: Performance Health = DEGRADED.
- PH-09, PH-10 failure: Performance Health = WARN.

**Monitoring Frequency:** Every 5 minutes during operation. Alert on first violation.

**Health Check Execution Time:** < 1,000ms (reads from SystemMonitor metrics).

---

## 5.10 Security Health

**Purpose:** Verify security conditions are met and no security regressions exist.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| SH-01 | No CRITICAL CVEs in dependencies | Zero | CRITICAL |
| SH-02 | No HIGH CVEs in dependencies | Zero | CRITICAL |
| SH-03 | No secrets in log files (spot check) | Zero secrets | CRITICAL |
| SH-04 | Secrets Snapshot not serialized to disk | No snapshot file | CRITICAL |
| SH-05 | Process not running as root (Linux/Docker) | Non-root user | IMPORTANT |
| SH-06 | Database file permissions correct | Owner-only access | IMPORTANT |
| SH-07 | No unexpected network listeners | Only expected ports | OPTIONAL |

**Security Health Score:**
- SH-01 through SH-04 failure: Security Health = FAILED.
- SH-05, SH-06 failure: Security Health = DEGRADED.
- SH-07 failure: Security Health = WARN.

**Monitoring Frequency:** Startup only for SH-01 through SH-04; daily for SH-03.

**Health Check Execution Time:** < 500ms (reads from pre-computed scan results).

---

## 5.11 Operational Health

**Purpose:** Verify operational systems (Telegram, dashboard) are available
for operator interaction.

**Health Checks:**

| Check ID | Check Description | Expected Result | Failure Severity |
|----------|-------------------|-----------------|------------------|
| OP-01 | Telegram bot connected | Bot active | OPTIONAL |
| OP-02 | All 13 Telegram commands registered | Count == 13 | OPTIONAL |
| OP-03 | Dashboard data pipeline active | Data flowing | OPTIONAL |
| OP-04 | Startup log writable | Write OK | IMPORTANT |
| OP-05 | Log rotation working (no disk full risk) | Disk > 500MB | IMPORTANT |
| OP-06 | Shutdown Manager registered (SIGTERM handler) | Handler registered | CRITICAL |
| OP-07 | PID lock file current | PID matches process | IMPORTANT |

**Operational Health Score:**
- OP-06 failure: Operational Health = FAILED.
- OP-04, OP-05, OP-07 failure: Operational Health = DEGRADED.
- OP-01, OP-02, OP-03 failure: Operational Health = WARN.

**Monitoring Frequency:** Every 15 minutes during operation.

**Health Check Execution Time:** < 500ms.

---

## 5.12 Certification Health Matrix

The Certification Health Matrix defines which component health states lead
to which certification outcomes.

`
CERTIFICATION HEALTH MATRIX

Component Health   Classification   Certification Impact
-----------------  --------------   --------------------
HEALTHY            CRITICAL         No impact (positive)
HEALTHY            IMPORTANT        No impact (positive)
HEALTHY            OPTIONAL         No impact (positive)
DEGRADED           CRITICAL         SYSTEM_NOT_CERTIFIED
DEGRADED           IMPORTANT        SYSTEM_CERTIFIED_DEGRADED (with note)
DEGRADED           OPTIONAL         SYSTEM_CERTIFIED (with warning)
FAILED             CRITICAL         SYSTEM_NOT_CERTIFIED
FAILED             IMPORTANT        SYSTEM_CERTIFIED_DEGRADED (if recovery available)
FAILED             OPTIONAL         SYSTEM_CERTIFIED (with warning)

CERTIFICATION OUTCOMES:
  SYSTEM_CERTIFIED:           All CRITICAL components HEALTHY.
                               All IMPORTANT components HEALTHY or DEGRADED.
                               System enters full operational mode.

  SYSTEM_CERTIFIED_DEGRADED:  All CRITICAL components HEALTHY.
                               One or more IMPORTANT components FAILED
                               (with fallback available).
                               System enters operational mode with noted degradation.
                               Operator notified via Telegram.

  SYSTEM_NOT_CERTIFIED:       Any CRITICAL component DEGRADED or FAILED.
                               System halts. Startup Diagnostic Report written.
                               Operator notified via Telegram (if available).
`

---

*End of Part V*

---

# PART VI — FAILURE RECOVERY

## 6.1 Startup Failure Classification

Bootstrap failures are classified into four severity levels, each with a
defined response protocol.

`
FAILURE CLASSIFICATION

LEVEL 1 — FATAL:
  Definition: The system cannot start in any operational mode.
  Examples: Python import error, database corruption, missing CRITICAL config.
  Response: Halt immediately. Write Startup Diagnostic Report. Notify operator.
  Recovery: Requires human intervention. System does not self-recover.

LEVEL 2 — CRITICAL:
  Definition: A CRITICAL component failed; trading cannot proceed safely.
  Examples: All 5 DebateAgents not registered, kill switch not operational,
            DecisionEngine initialization failed.
  Response: Halt. Write Startup Diagnostic Report. Notify operator.
  Recovery: Requires human intervention or controlled restart after fix.

LEVEL 3 — DEGRADED:
  Definition: An IMPORTANT component failed; system can operate with reduced
              functionality.
  Examples: yfinance fallback active (Dhan down), Telegram bot unreachable,
            k-NN model not loaded (fresh start used instead).
  Response: Log DEGRADED status. Continue with noted limitations.
            Notify operator. Attempt recovery in background.
  Recovery: Recovery Manager attempts background recovery every RECOVERY_RETRY_INTERVAL.

LEVEL 4 — WARNING:
  Definition: An OPTIONAL component failed; minimal impact on operation.
  Examples: Dashboard data pipeline unavailable, plugin failed to load.
  Response: Log WARNING. Continue with no special action.
  Recovery: Recovery Manager may attempt recovery on next startup.
`

---

## 6.2 Configuration Failure Recovery

**Failure Scenario:** Configuration loading fails because a required key is missing
or a value is out of range.

`
CONFIGURATION FAILURE RECOVERY WORKFLOW

Failure detected: ConfigurationLoader.validate() finds missing or invalid key.

Step 1: Log failure with specific key name and expected constraint.
Step 2: Write Startup Diagnostic Report (section: Configuration Errors).
Step 3: Include in diagnostic report:
          - Missing key name.
          - Expected type and range.
          - Suggested correction (e.g., "Set DECISION_THRESHOLD to a float between 0.0 and 10.0").
Step 4: Attempt Telegram notification (if Telegram token already loaded).
Step 5: Halt with exit code 1.

Human Resolution:
  1. Read Startup Diagnostic Report.
  2. Correct config.py or environment variable.
  3. Restart the system.
  4. Confirm startup log shows configuration loaded successfully.

Automated Recovery: None. Configuration errors require human correction.
`

---

## 6.3 Dependency Failure Recovery

**Failure Scenario:** A CRITICAL dependency fails to initialize, blocking
the components that depend on it.

`
DEPENDENCY FAILURE RECOVERY WORKFLOW

Failure detected: Component B cannot start because Component A (dependency) is FAILED.

Step 1: Log: "Component B blocked — dependency A is FAILED."
Step 2: Attempt A recovery (Strategy: RESTART, up to MAX_RECOVERY_ATTEMPTS=3).
Step 3: Each restart attempt:
          a. Log attempt number and timestamp.
          b. Re-initialize A from scratch.
          c. Run A's self-validation.
          d. If successful: register A as READY. Resume B initialization.
          e. If failed: wait RECOVERY_RETRY_INTERVAL_S. Try again.
Step 4: If MAX_RECOVERY_ATTEMPTS exhausted:
          a. Check if A has a defined fallback (e.g., Dhan → yfinance).
          b. If fallback available: Switch to fallback. Resume B initialization.
          c. If no fallback: Classify as LEVEL 2 (CRITICAL). Halt.
Step 5: On HALT: Write Startup Diagnostic Report. Notify operator.

Data Feed Specific Recovery:
  Dhan feed fails → Auto-switch to yfinance.
  yfinance fails  → No data feed. LEVEL 2 failure. Halt.
  Both recover    → Log recovery. Continue on active feed.
`

---

## 6.4 Database Failure Recovery

**Failure Scenario:** The SQLite database is inaccessible, corrupted, or
the schema migration fails.

`
DATABASE FAILURE RECOVERY WORKFLOW

Case A — Database file not found:
  Step 1: Log: "Database not found at path {path}. Creating new database."
  Step 2: Create new SQLite database file.
  Step 3: Apply initial schema (all CREATE TABLE and CREATE INDEX statements).
  Step 4: Verify schema applied correctly.
  Step 5: Continue startup with empty database (fresh start).
  Note: State recovery will find no previous state. Fresh start proceeds.

Case B — Integrity check fails:
  Step 1: Log CRITICAL: "SQLite integrity_check failed. Database may be corrupted."
  Step 2: Write Startup Diagnostic Report with integrity_check output.
  Step 3: Attempt to restore from backup:
            a. Locate most recent backup in data/backups/.
            b. Verify backup integrity.
            c. Copy backup to primary path.
            d. Re-run integrity_check on restored backup.
            e. If restore succeeds: Continue startup with restored database.
            f. If no backup or restore fails: LEVEL 1 (FATAL) failure. Halt.
  Step 4: On successful restore: Log restored backup date and timestamp.
          Notify operator: "Database restored from backup {date}."

Case C — Schema migration fails:
  Step 1: Log CRITICAL: "Schema migration from v{old} to v{new} failed."
  Step 2: Restore pre-migration backup (taken automatically before migration).
  Step 3: Write Startup Diagnostic Report with migration error detail.
  Step 4: Halt. Migration failure requires developer investigation.
  Human Resolution: Investigate migration script. Fix migration. Restart.
`

---

## 6.5 Knowledge Failure Recovery

**Failure Scenario:** The knowledge base is unavailable or inconsistent at startup.

`
KNOWLEDGE FAILURE RECOVERY WORKFLOW

Case A — Knowledge base empty (no items):
  Response: DEGRADED-WARN.
  Action: Log WARNING. Continue startup.
  Impact: First trading cycle may have lower confidence scores.
  Recovery: Knowledge base populates during first operational cycles.

Case B — Knowledge contradictions detected:
  Response: DEGRADED-WARN.
  Action: Log the count and nature of contradictions. Continue startup.
  Impact: Knowledge queries may return conflicting items.
  Recovery: Learning system reconciles contradictions during operation.
  Monitoring: Contradiction count tracked; if growing, operator notified.

Case C — Knowledge cache population failure:
  Response: DEGRADED.
  Action: Log failure. Continue with empty cache (slower first-cycle queries).
  Recovery: Cache populates during first knowledge query cycle.

Case D — Knowledge database schema mismatch:
  Response: CRITICAL.
  Action: Attempt migration. If migration fails: Halt.
          If migration succeeds: Continue with warning.
`

---

## 6.6 AI Initialization Failure Recovery

**Failure Scenario:** One or more AI components fail to initialize.

`
AI INITIALIZATION FAILURE RECOVERY WORKFLOW

Case A — Fewer than 5 DebateAgents registered:
  Response: LEVEL 2 (CRITICAL).
  Action: Identify which agent(s) are missing.
          Log: "Missing debate agents: {list of missing agents}."
          Attempt single-agent restart (up to MAX_RECOVERY_ATTEMPTS).
          If recovery fails: Halt. Debate requires exactly 5 agents.
  Human Resolution: Investigate agent initialization error. Fix. Restart.

Case B — RegimeClassifier fails:
  Response: LEVEL 3 (DEGRADED).
  Action: Use UNKNOWN regime as fallback.
          Strategy weights default to equal weighting.
          Log: "Regime classifier unavailable. Using equal strategy weights."
          Attempt background recovery every 30 minutes.

Case C — StrategyLab has zero active strategies:
  Response: LEVEL 2 (CRITICAL).
  Action: Log: "No active strategies available."
          Check evolved_strategies directory for strategy files.
          If strategy files exist but loading failed: Report specific load errors.
          If no strategy files: Fresh start — strategies will be generated in first cycles.
  Note: If truly no strategies exist, the system can still start but will generate
        no trade decisions until strategies are available from the research pipeline.

Case D — k-NN model not loaded:
  Response: LEVEL 3 (DEGRADED).
  Action: Initialize k-NN model from scratch (empty training set).
          Log: "k-NN model not found. Initializing fresh model."
          Impact: First N cycles use equal strategy weights until k-NN accumulates data.
`

---

## 6.7 Partial Startup

**Scenario:** The system reaches SYSTEM_CERTIFIED_DEGRADED — some IMPORTANT
components are unavailable but all CRITICAL components are operational.

`
PARTIAL STARTUP PROTOCOL

Trigger: Health Manager reports SYSTEM_CERTIFIED_DEGRADED.

Step 1: Bootstrap Manager logs: "SYSTEM_CERTIFIED_DEGRADED — entering partial operation."
Step 2: Record which components are DEGRADED or FAILED.
Step 3: Document the operational impact of each degraded component.
Step 4: Send Telegram notification:
          "IIOS starting in DEGRADED mode.
           Missing: {list of degraded components}.
           Impact: {description of reduced functionality}.
           All CRITICAL systems operational. Trading may proceed."
Step 5: Activate operational mode with noted limitations.
Step 6: Recovery Manager continues background recovery attempts for each degraded component.
Step 7: On successful recovery of a degraded component:
          Log: "Component {name} recovered — returning to full capability."
          Update Service Registry.
          Send Telegram notification: "System fully recovered."
`

---

## 6.8 Rollback on Startup Failure

**Scenario:** A recent code change caused a startup failure that was not present
in the previous version.

`
ROLLBACK PROTOCOL (Startup Regression)

Indicators of regression-induced failure:
  - System started successfully yesterday. Fails today.
  - Failure correlates with a recent deployment.
  - Error message references a module changed in recent deployment.

Rollback Steps:
  1. On VPS, run:
     cd /root/ai-trading-brain
     git log --oneline -5   (identify the last known-good commit)
     git checkout {last-good-commit}
  2. Rebuild Docker:
     docker compose build --no-cache
     docker compose down
     docker compose up -d
     sleep 8
     docker compose ps
  3. Verify both containers healthy.
  4. Confirm startup log shows successful startup.
  5. Notify Architecture Council of rollback event.
  6. Create an Engineering Decision Record for the rollback.

Rollback Constraints:
  - Database rollback is separate from code rollback.
  - If a schema migration ran with the failed code, the migration must be
    reversed before rolling back the code.
  - Schema rollback is a manual procedure (Runbook DB-002).
`

---

## 6.9 Safe Shutdown Protocol

`
SAFE SHUTDOWN PROTOCOL

Trigger: SIGTERM, Telegram /shutdown command, or kill switch event.

Phase 1 — Signal Receipt (< 1 second):
  1. Shutdown Manager receives signal.
  2. Sets system state to SHUTTING_DOWN.
  3. Publishes SHUTDOWN_INITIATED event to EventBus.
  4. MasterOrchestrator stops accepting new cycle triggers.

Phase 2 — Cycle Completion (< 30 seconds):
  5. Wait for current cycle to complete (or MAX_CYCLE_WAIT_S timeout).
  6. If timeout: abort current cycle. Log aborted cycle.

Phase 3 — State Flush (< 10 seconds):
  7. Flush strategy performance metrics to SQLite.
  8. Flush paper trade journal to CSV.
  9. Flush knowledge base pending writes.
  10. Flush cycle telemetry to SQLite.
  11. Write shutdown record:
        - Shutdown timestamp.
        - Shutdown type (CLEAN).
        - Last cycle timestamp.
        - Total cycles this session.

Phase 4 — Service Deregistration (< 5 seconds):
  12. Deregister all components from Service Registry (reverse init order).
  13. Close Telegram bot connection.
  14. Close data feed connections.
  15. Close EventBus.
  16. Close SQLite connections.
  17. Release PID lock file.

Phase 5 — Final Exit (< 1 second):
  18. Log: "IIOS SHUTDOWN COMPLETE. Total runtime: {duration}."
  19. Exit with code 0.

TOTAL CLEAN SHUTDOWN TARGET: < 47 seconds.
`

---

## 6.10 Restart Recovery Workflows

`
RECOVERY WORKFLOW A — Transient Network Failure During Startup

Scenario: Data feed initialization fails due to network timeout.

Step 1: DataFeedManager.init() fails with TimeoutError.
Step 2: Recovery Manager classifies: transient failure (network timeout is retryable).
Step 3: Retry with exponential backoff:
          Attempt 1: Wait 2s. Retry.
          Attempt 2: Wait 4s. Retry.
          Attempt 3: Wait 8s. Retry.
Step 4: After 3 failed attempts for Dhan: Switch to yfinance fallback.
Step 5: Test yfinance: Get NIFTY quote. If successful: proceed with yfinance.
Step 6: If yfinance also fails 3 times: LEVEL 2 failure. Halt.

---

RECOVERY WORKFLOW B — Crash Recovery (unexpected shutdown)

Scenario: System crashed during previous operation. Restart initiated.

Step 1: Bootstrap Manager reads last shutdown record.
Step 2: Last record is UNEXPECTED (no clean shutdown record found).
Step 3: Bootstrap Manager activates RECOVERY_MODE flag.
Step 4: Normal startup proceeds (all stages).
Step 5: At Stage 14 (State Recovery): full state recovery from SQLite and CSV.
Step 6: After Stage 45 (SYSTEM_READY):
          a. Reconcile recovered open positions against broker.
          b. Log reconciliation results.
          c. Send Telegram: "System recovered from unexpected shutdown.
             {N} positions recovered. {N} strategies active."
Step 7: Wait RECOVERY_AUTO_RESUME_MINUTES (default: 5) before first trading cycle.
Step 8: Resume normal operation.

---

RECOVERY WORKFLOW C — Container Restart (Docker restart policy)

Scenario: Docker container restarted by Docker due to health check failure or crash.

Step 1: Docker starts container from image. Entrypoint is main.py.
Step 2: main.py begins bootstrap.
Step 3: Bootstrap reads previous state from persistent volume (./data:/app/data).
Step 4: Recovery mode activates (same as Workflow B from Step 4).
Step 5: All state persisted to ./data volume is recovered.
Step 6: State NOT in volume (in-memory only) is lost — learning cycle re-runs.
`

---

*End of Part VI*

# PART VII — OPERATIONAL MODES

## 7.1 Operational Mode Framework

IIOS supports ten operational modes that define which capabilities are active,
what constraints apply, and what level of operator oversight is required.
The operational mode is set at startup and governs system behavior for the
entire session. Changing operational mode requires a restart.

---

## 7.2 Development Mode

**Mode Code:** DEV
**Trigger:** --mode DEV or ENVIRONMENT=dev
**Primary Use:** Active development and feature testing by engineering teams.

**Characteristics:**
- Full startup sequence runs.
- All components initialized normally.
- Paper trading only (PAPER_TRADING always = True in DEV).
- Extended debug logging (DEBUG level for all components).
- Fake data feed available (bypass network calls with fixture data).
- Health check intervals reduced (faster feedback).
- Shorter latency timeouts (fail fast on slow operations).
- No Telegram notifications sent (dev mode suppresses external notifications).
- Dashboard runs in development server mode.

**Restrictions:**
- No live trading. If --live is passed with --mode DEV: override to paper. Log warning.
- No production database writes. Uses data/dev.db instead of data/main.db.
- Kill switch thresholds may be overridden for testing (with explicit warning).

**Exit Criteria:**
DEV mode exits when the process is terminated. No production state is affected.

---

## 7.3 Testing Mode

**Mode Code:** TEST
**Trigger:** --mode TEST or invoked by test runner.
**Primary Use:** Automated testing (pytest, integration tests, CI/CD pipeline).

**Characteristics:**
- Minimal startup sequence (only components needed for the test suite).
- All external calls mocked (data feeds, Telegram, broker).
- In-memory SQLite (not file-based). Test database is destroyed after tests.
- Health checks run against mock components.
- No Telegram notifications.
- No network calls (isolated environment).
- Deterministic random seeds (for reproducible test results).

**Restrictions:**
- No live trading.
- No filesystem side effects (no files written to data/ or logs/).
- All I/O goes through test fixtures.

**Testing Mode Startup (abbreviated):**
Components initialized: ConfigurationLoader, LoggingSystem, EventBus,
  MockDataFeedManager, MockDatabase, AIAgentRegistry (with mock agents).
Skipped: Physical database, Telegram bot, Dashboard, Plugins.

---

## 7.4 Replay Mode

**Mode Code:** REPLAY
**Trigger:** --mode REPLAY --replay-date {YYYY-MM-DD}
**Primary Use:** Re-running historical data through the full pipeline to
verify system behavior on known historical periods.

**Characteristics:**
- Full startup sequence runs.
- All components initialized normally.
- Data feed replaced by historical data replayer (reads from data/historical/).
- Events replayed at configurable speed (1x, 10x, 100x real-time).
- Paper trading in replay mode (no real orders).
- Replay results written to data/replay_{date}.db.
- Dashboard shows replay progress and results.
- No Telegram notifications during replay (summary sent on completion).

**Restrictions:**
- No live data feed. Historical replayer is the only data source.
- Cannot replay a date for which historical data is not available.

**Replay Completion:**
On replay completion, the system writes a Replay Summary Report to
logs/replay_{date}_summary.txt containing:
- Total cycles replayed.
- Trade decisions made (APPROVED and REJECTED counts).
- Paper P&L from replay.
- Strategy performance during replay period.
- Comparison to actual historical performance (if available).

---

## 7.5 Paper Trading Mode

**Mode Code:** PAPER
**Trigger:** --paper or --mode PAPER
**Primary Use:** Full system operation with simulated trade execution.
This is the primary mode for the first 30 days of production operation.

**Characteristics:**
- Full startup sequence runs.
- All components initialized normally.
- OrderManager operates in PAPER_TRADING mode.
- Trades executed in paper journal (data/paper_trades.csv).
- No real orders sent to Dhan broker.
- All monitoring, learning, and analytics operate normally.
- Dashboard shows paper P&L.
- All 13 Telegram commands available.
- Full telemetry to SQLite.

**Paper Trade Execution:**
- Order is sized by CapitalRiskEngine (uses paper capital allocation).
- Order is written to paper_trades.csv with: symbol, direction, qty, price, timestamp, strategy.
- P&L is tracked against closing prices fetched from data feed.
- Performance metrics updated normally (win rate, Sharpe, drawdown).

**Paper Trading Transition to Production:**
Paper trading mode must run for minimum 30 days before Gate 5 (production
authorization) can be passed. The 30-day requirement is enforced in the
Gate 5 readiness checklist.

---

## 7.6 Simulation Mode

**Mode Code:** SIM
**Trigger:** --mode SIM --sim-config {path}
**Primary Use:** Monte Carlo simulation of system behavior under specified market scenarios.

**Characteristics:**
- Full startup sequence (AI and decision components).
- Data feed replaced by Monte Carlo scenario generator.
- Scenarios defined in simulation configuration file.
- Multiple parallel simulations run for each scenario.
- No persistence to production database.
- Results written to data/sim_{run_id}.db.
- Dashboard shows simulation progress.
- No Telegram notifications during simulation.

**Simulation Output:**
- Distribution of P&L outcomes across scenarios.
- Strategy win rates and Sharpe ratios per scenario.
- Risk metrics (VaR, MaxDD) per scenario.
- Decision distribution (APPROVED vs REJECTED counts per scenario).

---

## 7.7 Research Mode

**Mode Code:** RESEARCH
**Trigger:** --mode RESEARCH
**Primary Use:** Strategy research, backtesting, and evolution without live market interaction.

**Characteristics:**
- Minimal market data dependencies (uses historical data).
- StrategyLab, ResearchLab, and ValidationEngine are the primary active components.
- No trading cycles. No decision engine cycles.
- Strategy evolution and backtesting run continuously.
- Results written to data/research.db and strategy_lab/evolved_strategies/.
- Dashboard shows research pipeline progress.

**Research Mode Components (active):**
- StrategyLab (strategy generation and evolution).
- Backtesting engine.
- WalkForwardTester.
- ResearchLab (promotion gate evaluation).
- ValidationEngine.
- LearningSystem (performance tracking).

**Research Mode Components (inactive):**
- Decision engine.
- Debate agents.
- OrderManager.
- Risk management stack.

---

## 7.8 Production Mode

**Mode Code:** PROD
**Trigger:** --live --mode PROD
**Primary Use:** Live trading with real capital.
**Authorization Requirement:** Gate 5 approval required. Unauthorized production
mode activation is rejected at startup.

**Characteristics:**
- Full startup sequence runs.
- All components initialized normally.
- OrderManager operates in LIVE_TRADING mode.
- Orders sent to Dhan broker via production API.
- All positions are real positions with real capital.
- All monitoring, learning, and analytics operate normally.
- All 13 Telegram commands available.
- Full telemetry to SQLite.
- Architecture Council notification sent on production mode activation.

**Production Mode Authorization Check:**
At startup, if --live is specified, Bootstrap Manager checks:
1. A production authorization file exists: data/PRODUCTION_AUTHORIZED.
2. The file contains a valid Architecture Council authorization signature.
3. The authorization date is within the validity period.
If any check fails: halt with error "Production mode not authorized."

**Production Mode Kill Switch:**
Kill switch is armed immediately. VIX monitoring starts at Stage 22 initialization.
If VIX > 45.0 or daily loss > 2.0% at any point during startup: startup halts.
System does not start a production session when kill switch conditions are met.

---

## 7.9 Disaster Recovery Mode

**Mode Code:** DR
**Trigger:** --mode DR or automatic activation on severe failure detection.
**Primary Use:** Restoring the system after a major failure that leaves the
system in an inconsistent or potentially dangerous state.

**Characteristics:**
- Minimal component initialization (Emergency Mode components only).
- All trading suspended.
- Position reconciliation runs.
- Operator must explicitly authorize each recovery step.
- Full audit trail maintained.
- Architecture Council notified immediately on DR mode activation.

**DR Mode Sequence:**
1. Initialize Emergency Mode components only.
2. Load all recoverable state.
3. Send Telegram alert: "DR MODE ACTIVATED. Immediate attention required."
4. Display position reconciliation report via Telegram.
5. Wait for operator commands (/approve_recovery or /abort_recovery).
6. On /approve_recovery: Execute recovery steps.
7. On completion: Report recovery outcome. Restart in PAPER mode.

---

## 7.10 Maintenance Mode

**Mode Code:** MAINT
**Trigger:** --mode MAINT or automatic activation after repeated restart failures.
**Primary Use:** System is running but no trading occurs. Used during configuration
changes, upgrades, or investigation of issues.

**Characteristics:**
- Full startup sequence.
- All components initialized.
- Trading disabled (MasterOrchestrator does not run trading cycles).
- All monitoring and health checks active.
- Telegram bot active (operator interaction available).
- Dashboard active.
- Recovery Manager active.

**Maintenance Mode Exit:**
Operator issues /resume command via Telegram. Bootstrap Manager verifies:
1. All CRITICAL and IMPORTANT components are READY.
2. Health Manager confirms HEALTHY status.
3. No open critical findings in Risk Tracker.
System transitions to PAPER or PROD mode as configured.

---

## 7.11 Emergency Mode

**Mode Code:** EMERGENCY
**Trigger:** Automatic — triggered by irrecoverable IMPORTANT component failure,
repeated restart failures (>= 3 in 60 minutes), or explicit operator command.

**Characteristics:**
- Minimal component initialization (Emergency Mode components only).
- No new positions opened.
- Existing positions monitored.
- Kill switch monitoring active.
- Operator notification sent immediately.
- All decisions require operator approval via Telegram.

**Emergency Mode Components (active):**
Logging, Database, StateManager, DataFeedManager, EventBus, RiskGuardian,
OrderManager (monitoring only), TradeMonitor, TelegramBot.

**Emergency Mode Exit:**
Operator issues /resume command. System restarts in MAINT mode for health
verification before returning to normal operation.

---

*End of Part VII*

---

# PART VIII — ENGINEERING CONSTITUTION

## 8.1 Constitution Overview

The Bootstrap Engineering Constitution defines 110 binding rules governing
every aspect of IIOS system startup, initialization, and operational readiness.
These rules have no exceptions without Architecture Council approval and
an Engineering Decision Record.

**Rule Prefix Key:**
- BC.S   — Startup Rules
- BC.D   — Dependency Rules
- BC.C   — Configuration Rules
- BC.L   — Logging Rules
- BC.H   — Health Rules
- BC.F   — Failure Rules
- BC.R   — Recovery Rules
- BC.SD  — Shutdown Rules
- BC.M   — Mode Rules
- BC.Sec — Security Rules
- BC.P   — Performance Rules
- BC.G   — Governance Rules

---

## 8.2 Startup Rules

**BC.S.1** Bootstrap Manager is the first and only process to execute at startup.
No component may self-initialize before Bootstrap Manager grants initialization authority.

**BC.S.2** The Startup Identifier (UUID) is generated before any other action.
Every log entry, telemetry record, and diagnostic report for a session carries this identifier.

**BC.S.3** The startup log is initialized before any other startup operation.
No startup event may go unlogged.

**BC.S.4** Startup arguments are validated before resource loading begins.
Invalid argument combinations cause immediate halt with usage information.

**BC.S.5** Environment discovery runs before configuration loading.
A Python version below minimum causes immediate halt.

**BC.S.6** Configuration loading always runs before component initialization.
No component receives configuration from any source other than the Configuration Snapshot.

**BC.S.7** The Configuration Snapshot is immutable after creation.
Runtime code must not modify configuration values.

**BC.S.8** All startup operations have defined timing budgets.
Operations that exceed their budget are logged as PERF_WARN.

**BC.S.9** The total bootstrap duration must be below 30 seconds.
Any startup that takes longer than 60 seconds is aborted and logged as a timeout failure.

**BC.S.10** Every startup produces a startup completion record.
The record includes: duration, operational mode, active feed, component count, certification status.

**BC.S.11** A unique PID lock file is written at startup and released at shutdown.
A second instance of IIOS must not start if the PID lock indicates an active instance.

**BC.S.12** The SIGTERM handler is registered exactly once, at the end of successful startup.
It must not be registered before SYSTEM_CERTIFIED is issued.

**BC.S.13** The MasterOrchestrator does not start its first cycle until SYSTEM_CERTIFIED is issued.
This is an unconditional constraint with no override.

**BC.S.14** Every startup stage produces at least one log entry:
stage start timestamp, stage completion timestamp, and stage outcome.

**BC.S.15** Startup stages run in the order defined by the startup plan.
Stages may not be reordered at runtime.

---

## 8.3 Dependency Rules

**BC.D.1** All component dependencies are declared in the component's __manifest__.json.
Implicit dependencies (components that work only if another component happens to be present)
are forbidden.

**BC.D.2** The dependency graph must be a directed acyclic graph.
Any cycle detected by the Dependency Resolver causes immediate halt.

**BC.D.3** A component may not call any method on a dependency before that dependency
is registered as READY in the Service Registry.

**BC.D.4** The Startup Coordinator enforces dependency order.
Manual ordering overrides in code are forbidden.

**BC.D.5** A CRITICAL dependency failure halts the entire startup sequence.
No component that depends on a FAILED CRITICAL component may proceed.

**BC.D.6** An IMPORTANT dependency failure activates the fallback strategy if one exists,
or marks the dependent component DEGRADED.

**BC.D.7** An OPTIONAL dependency failure is logged and the dependent component
continues without that dependency.

**BC.D.8** The Dhan data feed and the yfinance data feed have a primary-fallback relationship.
The fallback relationship is defined in the component manifests and enforced by the
DataFeedManager, not by ad-hoc code.

**BC.D.9** Singleton factory functions are the only authorized way to obtain singleton instances.
Direct instantiation of StrategyPerformanceTracker, RegimeStrategyMap,
TelegramBot, or DataFeedManager is prohibited.

**BC.D.10** Singleton factory functions are called after the relevant component is READY
in the Service Registry. Calling a factory function before the component is initialized
produces an informative error, not a silent None return.

---

## 8.4 Configuration Rules

**BC.C.1** All configuration values live in config.py. No other configuration source exists.

**BC.C.2** All configuration values that affect trading decisions are validated at startup.
A configuration value that affects trading but is not validated at startup is a specification violation.

**BC.C.3** DECISION_THRESHOLD is always imported from config.py.
The value 6.5 must not appear as a literal in any source file.

**BC.C.4** KILL_SWITCH_VIX is always imported from config.py.
The value 45.0 must not appear as a literal in any source file.

**BC.C.5** KILL_SWITCH_DAILY_LOSS_PCT is always imported from config.py.
The value 0.02 must not appear as a literal in any source file.

**BC.C.6** Promotion gate thresholds (WIN_RATE, SHARPE, MAX_DD) are always imported from config.py.
Their values must not appear as literals in any source file.

**BC.C.7** Configuration changes take effect only after a restart.
Runtime configuration mutation is forbidden.

**BC.C.8** Environment-specific values (API tokens, database paths) are injected
through environment variables, not through config.py.

**BC.C.9** PAPER_TRADING must be a boolean. Any value that is not a boolean is a
configuration validation error.

**BC.C.10** Configuration validation errors include the key name, the invalid value
(for non-secret values), the expected constraint, and a suggested correction.

---

## 8.5 Logging Rules

**BC.L.1** The startup log is the first file opened. It captures all events from
the first instant of the process through to SYSTEM_READY.

**BC.L.2** All log entries include: timestamp (ISO-8601), log level, Startup ID,
component name, and message.

**BC.L.3** Secrets are never logged. The logging system must validate that
known-sensitive values (token, password, key, secret) do not appear in any log message.

**BC.L.4** Log rotation occurs daily. Retention is configurable (default: 30 days).
Log rotation is tested quarterly.

**BC.L.5** Log entries for startup events use a consistent format:
[{STAGE_ID}] {stage_name} — {STARTED | COMPLETED | FAILED} ({duration_ms}ms).

**BC.L.6** The startup log is not truncated. It is appended. Each restart appends to
the daily log file. The startup record header makes each session identifiable by Startup ID.

**BC.L.7** Performance log entries use a consistent format:
[PERF] {component_name} {operation_name}: {duration_ms}ms ({PASS | WARN | FAIL}).

**BC.L.8** Health check log entries use a consistent format:
[HEALTH] {component_name} {check_id}: {HEALTHY | DEGRADED | FAILED} ({detail}).

**BC.L.9** Recovery events use a consistent format:
[RECOVERY] {component_name}: attempt {N}/{MAX} — {RESTARTING | SUCCEEDED | FAILED}.

**BC.L.10** All log entries for a single bootstrap session are searchable by Startup ID.

---

## 8.6 Health Rules

**BC.H.1** Every component has a health check callback registered at initialization time.
A component without a health check callback cannot be registered in the Service Registry.

**BC.H.2** Health check callbacks complete within HEALTH_CHECK_TIMEOUT_MS (default: 500ms).
A timeout is treated as a health check failure.

**BC.H.3** Health check callbacks are read-only. They may not modify component state.

**BC.H.4** Health check callbacks may not call external services (no network calls).
They check only internal component state.

**BC.H.5** The Health Manager runs health checks after all components are initialized.
It does not run health checks for components that are still initializing.

**BC.H.6** The Health Report is produced after all health checks complete.
It is the only input to the Self-Certification decision.

**BC.H.7** All 5 DebateAgent health checks must pass for AI Health to be HEALTHY.
A single DebateAgent health failure causes AI Health = FAILED.

**BC.H.8** RiskGuardian health must be HEALTHY for SYSTEM_CERTIFIED to be issued.
A DEGRADED or FAILED RiskGuardian always results in SYSTEM_NOT_CERTIFIED.

**BC.H.9** Performance health is evaluated against actual measured latencies,
not estimated latencies.

**BC.H.10** Database health check includes a write test (write + delete a test record).
A read-only health check is insufficient.

---

## 8.7 Failure Rules

**BC.F.1** LEVEL 1 (FATAL) failures halt the system immediately.
No recovery attempt is made for FATAL failures.

**BC.F.2** Every failure produces an actionable error message.
Vague messages ("initialization failed", "unknown error") are forbidden.

**BC.F.3** Every LEVEL 2 (CRITICAL) or LEVEL 1 (FATAL) failure produces a
Startup Diagnostic Report.

**BC.F.4** LEVEL 3 (DEGRADED) failures allow the system to continue with
noted limitations. The limitations are logged and communicated to the operator.

**BC.F.5** LEVEL 4 (WARNING) failures allow the system to continue without
any restriction. The warning is logged and does not affect the Health Report.

**BC.F.6** Failure messages include the component name, the failure cause,
and the suggested resolution.

**BC.F.7** Failures in OPTIONAL components never halt startup.

**BC.F.8** Failure recovery attempts are logged with attempt number and outcome.

**BC.F.9** A component that fails after MAX_RECOVERY_ATTEMPTS is marked PERMANENTLY_FAILED
in the Service Registry and is not retried further in the current session.

**BC.F.10** The kill switch (RiskGuardian) is a CRITICAL component.
Any failure to initialize the kill switch causes SYSTEM_NOT_CERTIFIED regardless
of any other component's health.

---

## 8.8 Recovery Rules

**BC.R.1** Recovery attempts use exponential backoff.
Attempt 1: 2s delay. Attempt 2: 4s. Attempt 3: 8s. Attempt 4: 16s.
Maximum delay is capped at MAX_RECOVERY_BACKOFF_S.

**BC.R.2** Recovery is classified before the first attempt:
TRANSIENT (retry), CONFIGURATION (no retry without fix), PERMANENT (no retry).

**BC.R.3** TRANSIENT failures are network timeouts, temporary unavailability.
CONFIGURATION failures are missing secrets, wrong paths.
PERMANENT failures are corrupted databases, missing critical modules.

**BC.R.4** Fallback substitution (Dhan → yfinance) is preferred over repeated retries
when a fallback is available.

**BC.R.5** Recovery Manager monitors recovery success rate per component.
A component with a chronic failure pattern (>= MAX_CHRONIC_FAILURES recoveries)
is disabled and the operator is notified.

**BC.R.6** State recovery after restart is recovery-first. The system loads
previous state before initializing components to their default state.

**BC.R.7** State older than MAX_STATE_AGE_HOURS is not recovered. Fresh start is used.

**BC.R.8** Recovery from database corruption requires manual intervention.
The system does not attempt to repair a corrupted database automatically.

**BC.R.9** After a successful recovery, the previously FAILED component is
re-registered in Service Registry with its new READY state.

**BC.R.10** Recovery events are published to EventBus so all interested
components are notified of the restored capability.

---

## 8.9 Shutdown Rules

**BC.SD.1** The SIGTERM handler always delegates to Shutdown Manager.
It does not implement shutdown logic directly.

**BC.SD.2** Clean shutdown completes current cycle or waits MAX_CYCLE_WAIT_S.
It does not abort the cycle immediately on SIGTERM.

**BC.SD.3** State flush precedes connection close.
Connections must not be closed before state is flushed to durable storage.

**BC.SD.4** Components are deregistered from Service Registry in the reverse
order of their initialization.

**BC.SD.5** The shutdown record (CLEAN_SHUTDOWN) is written as the last
operation before exit. This record is how the next startup detects clean vs crash.

**BC.SD.6** Exit code 0 means clean shutdown. Exit code 1 means error.
Exit code 2 means emergency shutdown.

**BC.SD.7** The PID lock file is deleted as part of shutdown. A remaining PID lock
file after shutdown indicates a crash (handled by the next startup).

**BC.SD.8** Shutdown must complete within SHUTDOWN_TIMEOUT_S (default: 60 seconds).
Components that do not shut down within their timeout are force-closed.

**BC.SD.9** The Telegram bot sends a shutdown notification before the connection
is closed (if Telegram is available). The notification includes reason and final status.

**BC.SD.10** No new EventBus events are published after SHUTDOWN_INITIATED.

---

## 8.10 Mode Rules

**BC.M.1** Operational mode is set at startup and does not change during operation.
Mode changes require a restart.

**BC.M.2** Production mode requires an authorization file (data/PRODUCTION_AUTHORIZED).
Production mode without authorization is rejected at startup.

**BC.M.3** Development mode always forces PAPER_TRADING = True.
Development mode cannot be used with live trading.

**BC.M.4** Testing mode always uses in-memory (not file-based) databases.
Tests must not affect production or development data.

**BC.M.5** Emergency mode is entered automatically when restart frequency
exceeds RESTART_FREQUENCY_THRESHOLD. It cannot be suppressed by configuration.

**BC.M.6** Safe mode is a valid degraded operational state. Safe mode activation
is logged as a significant operational event and communicated to the operator.

**BC.M.7** Replay mode uses a dedicated replay database. It does not write to
the production or development database.

**BC.M.8** Maintenance mode allows all monitoring to continue while trading is suspended.
Maintenance mode is not a diagnostic mode — it is a safe operational holding state.

**BC.M.9** Disaster Recovery mode requires immediate Architecture Council notification.
DR mode activation is an operational incident.

**BC.M.10** Research mode may not be run in parallel with Paper or Production mode.
Research mode consumes significant CPU and can interfere with trading cycle latency.

---

## 8.11 Security Rules

**BC.Sec.1** Secrets are never written to disk, never logged, and never passed
as string arguments to functions that may log their inputs.

**BC.Sec.2** The process must not run as root. Docker containers use a non-root user.

**BC.Sec.3** The data/ directory permissions restrict access to the owner only.
Group and other read/write permissions are prohibited.

**BC.Sec.4** A CVE scan runs at every deployment. Critical CVEs block deployment.
A deployment with a known critical CVE is a security incident.

**BC.Sec.5** Secret detection runs on every commit. A commit with a secret is
rejected at the CI/CD pipeline gate.

**BC.Sec.6** API tokens for the Dhan broker are rotated according to the Dhan
token policy. Expired tokens cause a configuration failure at startup.

**BC.Sec.7** Telegram bot tokens are rotated annually or immediately on compromise.

**BC.Sec.8** The audit trail in SQLite is append-only. No record may be deleted
or modified after insertion.

**BC.Sec.9** Input from Telegram commands is validated and sanitized before
being used in any operation.

**BC.Sec.10** The kill switch cannot be disabled by a Telegram command or configuration change.
Disabling the kill switch requires code modification (which requires Architecture Council approval).

---

## 8.12 Performance Rules

**BC.P.1** GlobalIntelligence cycle latency must be <= 17ms p99.
This target is measured by the SystemMonitor and reported in cycle telemetry.

**BC.P.2** MarketIntelligence cycle latency must be <= 19ms p99.

**BC.P.3** Full trading cycle latency baseline is 172ms p99.
The SLA is 200ms p99. Exceeding the SLA is a DEGRADED condition.

**BC.P.4** Health checks must complete within 500ms per component.
A health check that takes longer is treated as a failure.

**BC.P.5** Database writes must complete within 50ms p99.
A database write that takes longer than 500ms is a PERF_FAIL event.

**BC.P.6** The bootstrap process must complete within 30 seconds.
A bootstrap that takes longer than 60 seconds is a BOOT_TIMEOUT failure.

**BC.P.7** Memory usage must stay within MAX_MEMORY_MB (configurable in config.py).
A process that exceeds memory limits is a performance incident.

**BC.P.8** No optimization is implemented without profiling data that identifies
the bottleneck. Intuitive optimization is prohibited.

**BC.P.9** Performance targets are measured and reported, not estimated or assumed.
SystemMonitor metrics are the source of truth for performance compliance.

**BC.P.10** A performance regression > 10% from the established baseline triggers
a performance review before the next deployment.

---

## 8.13 Governance Rules

**BC.G.1** Bootstrap specification changes require Architecture Council approval.
No bootstrap modification is made speculatively.

**BC.G.2** Protected modules (RiskGuardian, backtesting_ai, validation_engine,
evolved_strategies, data/) are not modified by the bootstrap process.
Bootstrap interacts with them only by reading their state.

**BC.G.3** Every bootstrap rule deviation requires an Engineering Decision Record.
Undocumented deviations are specification violations.

**BC.G.4** The bootstrap sequence is tested in the CI/CD pipeline on every commit.
A change that breaks bootstrap tests is not merged.

**BC.G.5** Bootstrap failures that occur in production are root-cause analyzed within 24 hours.
Root cause analysis is documented in an incident record.

**BC.G.6** The operational mode authorization mechanism (Gate 5 production authorization file)
is reviewed by the Architecture Council after every production mode activation.

**BC.G.7** Emergency Mode and DR Mode activations are operational incidents.
They are reported to the Architecture Council within 1 hour.

**BC.G.8** The startup log is an engineering record. It must not be deleted or
truncated. Retention is managed by the log rotation policy.

**BC.G.9** Bootstrap component changes (adding new bootstrap manager components)
follow the same Engineering Decision Record process as core trading layer changes.

**BC.G.10** The Bootstrap Engineering Constitution is reviewed quarterly.
Rules that are no longer applicable are archived (not deleted).
New rules are added through the Architecture Council amendment process.

---

*End of Part VIII*

---

# PART IX — READINESS CHECKLISTS

## 9.1 Checklist Purpose

Readiness checklists are structured verification tools used to confirm that
each prerequisite category is complete before system startup, testing,
or production authorization. Each checklist is an engineering record, not
an informal review. Checklists are stored in docs/readiness/.

---

## 9.2 Environment Ready Checklist

`
ENVIRONMENT READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] Python version >= 3.10 confirmed.
[  ] Virtual environment activated (.venv/ or container Python).
[  ] All required environment variables set (DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN,
     TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DB_PATH, LOG_PATH).
[  ] Network connectivity to Dhan API endpoint verified (TCP test).
[  ] Network connectivity to yfinance (finance.yahoo.com) verified (TCP test).
[  ] Disk space >= 1GB in data/ directory confirmed.
[  ] Disk space >= 500MB in logs/ directory confirmed.
[  ] Available memory >= 512MB confirmed.
[  ] Docker installed and running (for containerized deployment).
[  ] Docker Compose installed and version confirmed.
[  ] SSH key available for VPS access (if deploying to VPS).
[  ] VPS accessible (ssh -i ~/.ssh/trading_vps root@178.18.252.24 responds).

ENVIRONMENT READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.3 Repository Ready Checklist

`
REPOSITORY READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] git status shows clean working tree (no uncommitted changes).
[  ] All expected module directories present.
[  ] All __manifest__.json files present and parseable.
[  ] Import graph analysis shows no cycles.
[  ] Critical interface signatures match expected (interface comparison tool).
[  ] Protected module hashes match build manifest.
[  ] requirements.txt is complete (all imports satisfied).
[  ] build_manifest.json is current (updated by last CI/CD run).
[  ] No CRITICAL or HIGH CVEs in dependency scan (safety/pip-audit).
[  ] No secrets detected in codebase (detect-secrets).
[  ] CI/CD pipeline passes on current branch HEAD.
[  ] Version tag consistent with wave completion record.

REPOSITORY READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.4 Configuration Ready Checklist

`
CONFIGURATION READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] config.py loads without import errors.
[  ] All CRITICAL configuration keys present.
[  ] DECISION_THRESHOLD = 6.5 (or documented alternative with EDR).
[  ] KILL_SWITCH_VIX = 45.0 (or documented alternative with EDR).
[  ] KILL_SWITCH_DAILY_LOSS_PCT = 0.02 (or documented alternative with EDR).
[  ] PROMOTION_WIN_RATE >= 0.50.
[  ] PROMOTION_SHARPE > 0.8.
[  ] PROMOTION_MAX_DD < 0.15.
[  ] PAPER_TRADING = True (for paper mode) or = False (for live mode with authorization).
[  ] LAYER_LATENCY_CRIT_MS > LAYER_LATENCY_WARN_MS for all layers.
[  ] SCHEDULE dict non-empty and valid.
[  ] GlobalIntelligence override: WARN=5000, CRIT=12000.
[  ] No magic numbers in config.py (all values have descriptive names and comments).

CONFIGURATION READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.5 Knowledge Ready Checklist

`
KNOWLEDGE READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] Knowledge base database file exists at DB_PATH.
[  ] SQLite PRAGMA integrity_check returns "ok".
[  ] All expected knowledge base tables present.
[  ] Schema version matches expected version.
[  ] Knowledge item count >= minimum threshold.
[  ] No CRITICAL knowledge contradictions detected.
[  ] Provenance completeness >= 90%.
[  ] No knowledge items older than MAX_KB_AGE.
[  ] Knowledge cache population succeeds within 1,000ms.
[  ] OntologyValidator rejects test invalid entity reference.
[  ] OntologyValidator accepts test valid entity reference.

KNOWLEDGE READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.6 Ontology Ready Checklist

`
ONTOLOGY READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] Ontology source file/database accessible.
[  ] Entity type count > 0.
[  ] Relationship type count > 0.
[  ] Attribute type count > 0.
[  ] No undefined entity references in ontology.
[  ] No undefined relationship endpoint references.
[  ] Ontology loads within 500ms.
[  ] OntologyValidator initialized and registered in Service Registry.

ONTOLOGY READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.7 Infrastructure Ready Checklist

`
INFRASTRUCTURE READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] At least one data feed (Dhan or yfinance) returns valid NIFTY quote.
[  ] GLOBAL_SYMBOL_MAP loaded non-empty.
[  ] Data feed quote for NIFTY: bare symbol "NIFTY" mapped to "^NSEI".
[  ] Data feed quote for BANKNIFTY: bare symbol "BANKNIFTY" mapped to "^NSEBANK".
[  ] EventBus test event published and received.
[  ] SystemMonitor layer timing context manager functional.
[  ] SQLite connection established and integrity check passed.
[  ] WAL mode enabled on SQLite database.
[  ] All required SQLite indexes present.
[  ] In-memory cache initialized.
[  ] GlobalDataAI 5-minute cache pre-warm thread started.

INFRASTRUCTURE READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.8 AI Ready Checklist

`
AI READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] Exactly 5 DebateAgents registered: BullAgent, BearAgent, NeutralAgent,
     RiskAgent, RegimeAgent.
[  ] BullAgent smoke test: returns score in [0.0, 10.0].
[  ] BearAgent smoke test: returns score in [0.0, 10.0].
[  ] NeutralAgent smoke test: returns score in [0.0, 10.0].
[  ] RiskAgent smoke test: returns score in [0.0, 10.0].
[  ] RegimeAgent smoke test: returns score in [0.0, 10.0].
[  ] RegimeClassifier produces valid RegimeEnum (not UNKNOWN on valid input).
[  ] ScoreAggregator: composite score of [6.0, 6.0, 6.0, 6.0, 6.0] = 6.0.
[  ] DecisionEngine: score 6.499 → TRADE_REJECTED.
[  ] DecisionEngine: score 6.5 → TRADE_APPROVED.
[  ] DecisionEngine: score 6.501 → TRADE_APPROVED.
[  ] At least one strategy active in StrategyLab.
[  ] k-NN model loaded or fresh model initialized (with log noting fresh start).
[  ] At least one scanner agent operational.
[  ] RiskGuardian: VIX 45.0 → KILL_SWITCH_TRIGGERED event published.
[  ] RiskGuardian: VIX 44.99 → No kill switch event.

AI READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.9 Database Ready Checklist

`
DATABASE READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] SQLite database file exists at DB_PATH.
[  ] PRAGMA integrity_check: "ok".
[  ] PRAGMA foreign_key_check: no violations.
[  ] All tables exist: knowledge_items, strategy_performance, learning_state,
     regime_context, cycle_telemetry, agent_scores, paper_trades_meta.
[  ] All indexes exist (verified by PRAGMA index_list).
[  ] Schema version matches expected version (from schema_version table).
[  ] Write test: INSERT test record + SELECT + DELETE all succeed.
[  ] Query latency: simple SELECT < 100ms.
[  ] Database size <= MAX_DB_SIZE_MB.
[  ] WAL checkpoint not stuck (WAL file size within limits).
[  ] Backup from previous session exists in data/backups/ (if not fresh start).

DATABASE READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.10 Operational Ready Checklist

`
OPERATIONAL READINESS
Date: ____________  Engineer: ____________  Session: ____________

[  ] Telegram bot connected (test message sent and received).
[  ] All 13 Telegram commands registered and responding.
[  ] Dashboard data pipeline active.
[  ] Startup log writable and structured format confirmed.
[  ] Log rotation working (no disk full risk: disk > 500MB free).
[  ] SIGTERM handler registered.
[  ] PID lock file written with current process PID.
[  ] ShutdownManager registered with Recovery Manager.
[  ] MasterOrchestrator initialized and ready for first cycle.
[  ] ControlTower receiving telemetry events.
[  ] All 13 Telegram commands:
     /start /stop /status /health /positions /pnl /strategies
     /learn /perf /regime /diag /shutdown /resume
     All registered and responding.

OPERATIONAL READY: [ YES / NO ]
Signed: _________________________  Date: __________
`

---

## 9.11 System Ready Certification

`
SYSTEM READY CERTIFICATION
Date: ____________  Engineer: ____________  Session: ____________

PREREQUISITE CHECKLISTS:
[  ] Environment Ready checklist: PASSED.
[  ] Repository Ready checklist: PASSED.
[  ] Configuration Ready checklist: PASSED.
[  ] Knowledge Ready checklist: PASSED.
[  ] Ontology Ready checklist: PASSED.
[  ] Infrastructure Ready checklist: PASSED.
[  ] AI Ready checklist: PASSED.
[  ] Database Ready checklist: PASSED.
[  ] Operational Ready checklist: PASSED.

HEALTH VERIFICATION:
[  ] Repository Health: HEALTHY.
[  ] Configuration Health: HEALTHY.
[  ] Knowledge Health: HEALTHY or DEGRADED (document degradation reason).
[  ] Ontology Health: HEALTHY.
[  ] Database Health: HEALTHY.
[  ] Infrastructure Health: HEALTHY (Dhan active) or DEGRADED-WARN (yfinance fallback).
[  ] AI Health: HEALTHY.
[  ] Performance Health: HEALTHY or DEGRADED (document if degraded).
[  ] Security Health: HEALTHY.
[  ] Operational Health: HEALTHY or DEGRADED (optional components only).

SELF-CERTIFICATION RESULT:
[  ] Bootstrap Manager issued: SYSTEM_CERTIFIED / SYSTEM_CERTIFIED_DEGRADED.
(SYSTEM_NOT_CERTIFIED blocks this checklist — do not proceed.)

OPERATIONAL MODE AUTHORIZED:
[  ] PAPER_TRADING mode authorized (default — no special authorization required).
[  ] PRODUCTION mode authorized (requires data/PRODUCTION_AUTHORIZED file).

SYSTEM READY CERTIFICATION:
System certified: [ YES / NO ]
Certification level: [ FULL / DEGRADED ]
Degradation notes (if any): ___________________________

Signed by Bootstrap Manager (automatic): SYSTEM_READY event published.
Countersigned by Operator: _________________________  Date: __________
Operational mode: ____________  Startup duration: _____ ms
`

---

*End of Part IX*

---

# APPENDIX A — BOOTSTRAP TIMING SPECIFICATIONS

## A.1 Stage Timing Budget Table

`
BOOTSTRAP STAGE TIMING BUDGETS

Stage  Name                          Budget_ms   Critical Path   Group
-----  ----                          ---------   -------------   -----
0      Process Start                 500         YES             SEQUENTIAL
1      Startup Log Init              100         YES             SEQUENTIAL
2      Startup ID Generation         10          YES             SEQUENTIAL
3      Argument Parsing              50          YES             SEQUENTIAL
4      Environment Discovery         5000        YES             SEQUENTIAL
5      Configuration Loading         500         YES             SEQUENTIAL
6      Environment Variable Loading  100         YES             SEQUENTIAL
7      Secrets Loading               100         YES             SEQUENTIAL
8      Repository Validation         2000        YES             SEQUENTIAL
9      Module Discovery              500         YES             SEQUENTIAL
10     Dependency Graph              200         YES             SEQUENTIAL
11     Startup Plan                  100         YES             SEQUENTIAL
12     Logging Full Init             200         NO              PG-1
13     Database Connection           2000        YES             PG-1
14     State Recovery                1000        YES             SEQUENTIAL
15     Knowledge Base Init           1000        YES             PG-2
16     Ontology Loading              500         YES             PG-2
17     Shared Utilities              200         NO              PG-3
18     Core Infrastructure           100         NO              PG-3
19     Data Feed Init                5000        YES             SEQUENTIAL
20     Cache Init                    500         NO              PG-4
21     EventBus Init                 100         YES             PG-4
22     Layer 1: GlobalIntelligence   12000       YES             SEQUENTIAL
23     Layer 2: MarketIntelligence   5000        YES             SEQUENTIAL
24     Layer 3: MetaLearning         3000        YES             SEQUENTIAL
25     Layer 4: OpportunityEngine    2000        NO              PG-5
26     Layer 5: StrategyLab          2000        YES             PG-5
27     Layer 6: CapitalRiskEngine    500         YES             SEQUENTIAL
28     Layer 7: RiskControl          1000        YES             PG-6
29     Layer 8: MarketSimulation     1000        NO              PG-6
30     Layer 9: RiskGuardian         500         YES             SEQUENTIAL
31     Layer 10: DebateAndDecision   2000        YES             PG-7+SEQ
32     Layer 11: ExecutionEngine     1000        YES             SEQUENTIAL
33     Layer 12: TradeMonitoring     500         NO              PG-8
34     Layer 13: LearningSystem      1000        YES             SEQUENTIAL
35     Layer 14: PerformanceAnalytics 500        NO              PG-9
36     Layer 15: ResearchLab         500         YES             SEQUENTIAL
37     Layer 16: ValidationEngine    500         YES             SEQUENTIAL
38     Layer 17: ControlTower        500         YES             SEQUENTIAL
39     Telegram Bot Init             3000        NO              PG-10
40     Dashboard Init                500         NO              PG-10
41     Plugin Loading                10000       NO              OPTIONAL
42     Health Verification           5000        YES             SEQUENTIAL
43     Self-Certification            100         YES             SEQUENTIAL
44     Mode Activation               100         YES             SEQUENTIAL
45     SYSTEM_READY Announcement     100         YES             SEQUENTIAL

TOTAL ESTIMATED (critical path, sequential):  32,760ms
TOTAL WITH PARALLELISM SAVINGS:              ~24,000ms
TARGET:                                       < 30,000ms
`

---

## A.2 Startup State Transition Diagram

`
BOOTSTRAP STATE MACHINE

    [NOT_STARTED]
         |
         v
    [INITIALIZING_BOOTSTRAP]
         |
         +--- BootstrapManager.start() called
         v
    [LOADING_RESOURCES]
         |
         +--- Configuration, Environment, Secrets loaded
         |--- Repository validation complete
         v
    [COMPUTING_STARTUP_PLAN]
         |
         +--- Module discovery complete
         |--- Dependency graph built
         v
    [INITIALIZING_INFRASTRUCTURE]
         |
         +--- Database, Logging, StateManager ready
         v
    [INITIALIZING_DATA_LAYER]
         |
         +--- DataFeedManager ready
         v
    [INITIALIZING_AI_LAYERS]
         |
         +--- Layers 1–9 ready
         v
    [INITIALIZING_DECISION_LAYER]
         |
         +--- All 5 DebateAgents ready
         |--- DecisionEngine ready
         v
    [INITIALIZING_EXECUTION_LAYER]
         |
         +--- OrderManager, TradeMonitor ready
         v
    [INITIALIZING_LEARNING_LAYER]
         |
         +--- LearningEngine, PerformanceTracker ready
         v
    [INITIALIZING_PERIPHERALS]
         |
         +--- Telegram, Dashboard, Plugins ready
         v
    [RUNNING_HEALTH_CHECKS]
         |
         +--- All health checks complete
         v
    [CERTIFYING]
         |
         +--- CERTIFIED -------> [OPERATIONAL]
         |--- CERTIFIED_DEGRADED -> [OPERATIONAL_DEGRADED]
         +--- NOT_CERTIFIED ---> [STARTUP_FAILED]

    [OPERATIONAL]
         |
         +--- SIGTERM received ---> [SHUTTING_DOWN] ---> [STOPPED]
         |--- CRITICAL failure ---> [RECOVERING] or [EMERGENCY_MODE]
         |--- Kill switch --------> [KILL_SWITCH_ACTIVE]

    [STARTUP_FAILED]
         |
         +--- Diagnostic Report written
         |--- Operator notified
         +--- Exit code 1
`

---

*End of Appendix A*

---

# APPENDIX B — GLOSSARY

**Bootstrap:** The controlled startup process that transforms IIOS from zero to OPERATIONAL.

**Bootstrap Manager:** The single top-level orchestrator of the startup process.

**Certification:** The self-verification decision (CERTIFIED / NOT_CERTIFIED) issued at the end of startup.

**Configuration Snapshot:** The immutable copy of all configuration values read at startup.

**Critical Path:** The longest dependency chain in the startup sequence, determining minimum startup time.

**Dependency DAG:** The directed acyclic graph of component initialization dependencies.

**Emergency Mode:** Minimal startup mode for position management and kill switch monitoring only.

**Environment Snapshot:** The immutable copy of all environment variable values read at startup.

**Health Check Callback:** The function registered by each component to report its health state.

**Health Report:** The structured report produced by Health Manager after running all health checks.

**Kill Switch:** The RiskGuardian mechanism that halts trading when VIX > 45.0 or daily loss > 2.0%.

**Operational Mode:** The runtime configuration governing which capabilities are active.

**Parallel Group:** A set of components with no dependency between them that can initialize concurrently.

**Recovery Manager:** The component that orchestrates component recovery after failures.

**Secrets Snapshot:** The in-memory, never-persisted record of all sensitive credentials.

**Service Registry:** The runtime directory of all registered components and their readiness states.

**Singleton Factory Function:** The only authorized way to obtain a singleton component instance.

**Startup Identifier:** The UUID generated at the start of each bootstrap session.

**State Manager:** The component that manages persistence and recovery of system state across restarts.

**Wave:** A cohesive unit of implementation that adds one complete IIOS capability layer.

---

## B.1 Document Metrics

`
DOCUMENT METRICS

Document Code:        IIOS-BSS-001
Document Version:     1.0
Total Parts:          9 + 2 Appendices
Total Sections:       90+
Bootstrap Components: 21
Bootstrap Stages:     45
Health Categories:    12
Operational Modes:    10
Constitution Rules:   110
Readiness Checklists: 10
Parallel Groups:      10

Architecture Constants:
  Decision Threshold:           6.5
  Kill Switch VIX:              45.0
  Kill Switch Daily Loss:       2.0%
  GlobalIntelligence Latency:   <= 17ms p99
  MarketIntelligence Latency:   <= 19ms p99
  Full Cycle Baseline:          172ms p99
  Full Cycle SLA:               200ms p99
  Bootstrap Target Duration:    < 30,000ms
  Emergency Bootstrap Target:   < 10,000ms
  Debate Agents Required:       Exactly 5
  IIOS Layers:                  17
  Promotion Win Rate:           >= 50%
  Promotion Sharpe:             > 0.8
  Promotion Max Drawdown:       < 15%
`

---

## B.2 Amendment History

`
AMENDMENT HISTORY

Version  Date           Author              Description
1.0      2026-07-05     Architecture        Initial issue. Complete bootstrap
                        Council             specification: 9 parts, 45 stages,
                                            21 components, 110 constitution rules,
                                            10 readiness checklists, 10 modes.

AMENDMENT POLICY:
All amendments require Architecture Council approval and an Engineering Decision Record.
Minor editorial corrections may be made by the Document Owner without a vote.
`

---

## B.3 Closing Statement

The SYSTEM_BOOTSTRAP_SPECIFICATION defines the complete engineering blueprint
for how the Investment Intelligence Operating System transitions from zero
to a verified operational state. Every stage is specified. Every dependency
is made explicit. Every failure is classified and handled. Every component
declares its health and registers its readiness.

The bootstrap process is not a detail — it is the foundation of operational
confidence. A system whose startup is deterministic, auditable, and complete
is a system that can be trusted. A system that starts in an unknown state
is a system that behaves in unknown ways.

IIOS does not start until it certifies itself. It does not trade until it
is certified. This is not a constraint — it is a guarantee.

**SYSTEM_BOOTSTRAP_SPECIFICATION.md — END OF DOCUMENT**

*Document Code: IIOS-BSS-001 | Version: 1.0 | Status: CONTROLLED*
*Issuing Authority: Architecture Council*
*Investment Intelligence Operating System*

---

*[End of SYSTEM_BOOTSTRAP_SPECIFICATION.md]*