# CORE FRAMEWORK ARCHITECTURE
## AI Trading Brain / Investment Intelligence Operating System (IIOS)

**Document Status:** AUTHORITATIVE
**Document Type:** Core Framework Design Specification
**Version:** 1.0.0
**Date:** 2026-07-02
**Authority:** Human Principal

**Parent Documents:**
- `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` — Supreme constitutional authority
- `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` — Engineering design bridge
- `ENGINEERING_STANDARDS.md` — Mandatory engineering standards
- `REPOSITORY_ARCHITECTURE.md` — Repository design authority

---

## Purpose Statement

This document defines the complete Core Framework of the AI Trading Brain / Investment Intelligence Operating System. The Core Framework is the engineering foundation upon which every module, layer, service, engine, AI agent, repository, and cross-cutting concern is built.

The Core Framework is not a layer. It is not a feature. It is not an optional infrastructure component. It is the ground on which the entire system stands. Without the Core Framework, there is no system — only a collection of disconnected scripts. With the Core Framework, there is a coherent, governable, observable, and evolvable investment intelligence platform.

This document answers:
- What shared engineering infrastructure exists?
- What contracts must every component fulfil?
- What lifecycle does every component participate in?
- How are errors, configuration, and dependencies managed?
- How does the framework govern itself?

This is NOT implementation. This is NOT source code. This is the engineering constitution of the IIOS Core Framework.

---

## Document Authority

| Attribute | Value |
|---|---|
| Governed by | Human Principal |
| Enforced by | All engineering work; ENGINEERING_STANDARDS.md Constitution |
| Referenced by | Every `src/` package in the repository |
| Supersedes | All ad hoc infrastructure decisions |
| Amendment process | ADR + Human Principal approval |
| Version | 1.0.0 |
| Next review | Quarterly (October 2026) |

---

## Framework Scope

| In Scope | Out of Scope |
|---|---|
| All base classes and abstract interfaces | Business logic of any specific layer |
| All shared utilities | Layer-specific algorithms |
| Error hierarchy and recovery policies | Strategy-specific calculations |
| Configuration and secrets management | Broker-specific protocols |
| Dependency injection and service registry | Data feed implementation details |
| Application lifecycle management | Trading decision logic |
| Cross-cutting concerns: logging, monitoring, audit, metrics | Market intelligence analysis |
| Framework governance and constitution | AI agent debate logic |

---

## Framework Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INVESTMENT INTELLIGENCE OPERATING SYSTEM              │
│                    17-Layer Hierarchical Multi-Agent Platform            │
├─────────────────────────────────────────────────────────────────────────┤
│  Layer 17  │  Layer 16  │  ... │  Layer 2  │  Layer 1  │ Infrastructure │
├─────────────────────────────────────────────────────────────────────────┤
│                        CORE FRAMEWORK                                    │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │  Base      │ │  Error       │ │ Configuration│ │  Cross-Cutting   │ │
│  │  Classes   │ │  Framework   │ │  Framework   │ │  Services        │ │
│  └────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘ │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │  Common    │ │  Dependency  │ │  Lifecycle   │ │  Application     │ │
│  │  Utilities │ │  Management  │ │  Management  │ │  Context         │ │
│  └────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

| Part | Title |
|---|---|
| I | Core Framework Philosophy |
| II | Core Components |
| III | Common Utilities |
| IV | Error Framework |
| V | Configuration Framework |
| VI | Dependency Management |
| VII | Framework Lifecycle |
| VIII | Cross-Cutting Services |
| IX | Framework Governance |
| X | Core Framework Constitution |

---
## PART I — CORE FRAMEWORK PHILOSOPHY

### 1.1 Why a Core Framework is Required

A complex, multi-agent, real-time financial system is composed of dozens of independently developed components. Each component has its own concerns: fetching market data, generating trade hypotheses, evaluating risk, executing orders. When these components are developed without a shared foundation, the following problems are inevitable:

**Problem 1: Inconsistent error handling.** One module silently catches exceptions. Another re-raises them. Another logs them at DEBUG level. The system becomes unreliable and undebuggable because errors are treated differently everywhere.

**Problem 2: Duplicated boilerplate.** Every component implements its own logging setup, its own configuration loading, its own retry logic. The same five-line pattern appears fifty times, each slightly different.

**Problem 3: Invisible dependencies.** Component A secretly depends on a global variable set by Component B. Component C reads from a file path hardcoded in a string literal. The system becomes a hidden web of undeclared couplings.

**Problem 4: Unmanaged lifecycle.** Components initialise themselves on import, in whatever order Python resolves imports. Startup is unpredictable. Shutdown never happens — connections leak, files stay open, state is never persisted.

**Problem 5: No common observability.** There is no consistent way to ask: "Is this component healthy?" Every component has its own idea of what healthy means, expressed differently.

**Problem 6: Untestable components.** Because components acquire their own dependencies, mock injecting is difficult or impossible. Testing requires the full system.

The Core Framework solves all six problems by providing a single, well-designed foundation that every component builds upon. The framework is not a constraint on development — it is a liberation from the above problems.

---

### 1.2 Core Framework Goals

The Core Framework is designed to achieve six primary goals:

| Goal | Description | Measured By |
|---|---|---|
| **Consistency** | Every component behaves predictably in the same situations | Zero surprise exceptions; uniform log format across all 17 layers |
| **Observability** | Every component can be monitored, measured, and traced | All components emit health status, timing, and correlation IDs |
| **Testability** | Every component can be tested in isolation | All dependencies are injectable; no hidden global state |
| **Evolvability** | The system can grow without rewriting the foundation | New components add to the framework, they do not modify it |
| **Reliability** | The system recovers from failures gracefully | Retry policies, circuit breakers, and fallback mechanisms defined |
| **Security** | The system enforces security contracts at the framework level | Secrets never exposed; all input validated before entry |

---

### 1.3 Core Framework Responsibilities

The Core Framework is responsible for:

| Responsibility | What It Provides |
|---|---|
| **Base contracts** | Abstract classes and interfaces that all components implement |
| **Configuration** | A unified way to load, validate, and access configuration at all levels |
| **Error management** | A complete exception hierarchy and recovery policy |
| **Lifecycle** | A defined boot, ready, and shutdown sequence for all components |
| **Dependency injection** | A service registry and factory system for dependency resolution |
| **Cross-cutting concerns** | Logging, monitoring, audit, metrics, and tracing shared by all components |
| **Common utilities** | Reusable utility functions for time, string, file, validation, and serialisation |
| **Application context** | A single object that carries per-request/per-cycle context (IDs, timestamps) |
| **Governance** | Rules that prevent the framework from being bypassed or duplicated |

The Core Framework is NOT responsible for:
- Any business logic (that belongs in layers 1–17)
- Any market data fetching (that belongs in `data_feeds/`)
- Any trading decisions (that belongs in `debate_engine/`, `strategy_lab/`)
- Any broker communication (that belongs in `integrations/brokers/`)

---

### 1.4 Scalability Philosophy

The Core Framework is designed to scale vertically (more components in the same process) and horizontally (multiple processes or containers) without modification:

| Scalability Dimension | How the Framework Supports It |
|---|---|
| **More agents** | `BaseAgent` abstract class accommodates any number of agents without framework change |
| **More layers** | `BaseEngine` abstract class and the layer registry accept new layers without framework modification |
| **More data sources** | `BaseFeed` abstract class accepts new implementations without framework modification |
| **More brokers** | `BaseService` abstract class with the plugin registry accommodates new broker adapters |
| **More metrics** | `MetricsCollector` accepts new metric registrations without framework restructuring |
| **Higher throughput** | The framework uses thread-safe data structures and locks; no single-threaded bottlenecks in infrastructure |
| **Multiple processes** | Application context is serialisable; cross-process correlation via `cycle_id` UUID4 |

---

### 1.5 Maintainability Philosophy

The Core Framework maintains itself through three mechanisms:

**Mechanism 1 — Stability contracts.** Once a base class or interface is published, its public methods are never removed or renamed. Only additive changes are made. Any breaking change requires a deprecation window and a MAJOR version increment.

**Mechanism 2 — Single-file ownership.** Every component of the Core Framework is owned by exactly one engineer or team. The owner is responsible for reviewing all changes and keeping the component's documentation current.

**Mechanism 3 — Self-documentation.** Every base class, interface, and utility function has a complete docstring that explains its purpose, its contract, its parameters, and its exceptions. The framework is the first piece of documentation an engineer reads.

---

### 1.6 Reliability Philosophy

Reliability in the Core Framework means that the infrastructure never fails silently and recovers from errors in a defined way.

| Reliability Property | Mechanism |
|---|---|
| **Fail loudly** | All errors in the framework layer bubble up to the calling component. The framework does not swallow exceptions. |
| **Fail predictably** | When a failure occurs, the behaviour is deterministic: the same input produces the same failure, the same way, every time. |
| **Recover gracefully** | Retry policies, circuit breaker states, and fallback mechanisms are defined in the framework and available to all components. |
| **Degrade safely** | When a non-critical component fails (e.g., telemetry write), the system logs the failure and continues. When a critical component fails (e.g., kill-switch thread), the system shuts down safely. |
| **State integrity** | The framework ensures that persistent state (databases, CSV journals) is only written through defined transactional interfaces. |

---

### 1.7 Extensibility Philosophy

The Core Framework is extended — never modified — when new capabilities are required. Every extension point in the framework follows one of three patterns:

| Extension Pattern | When Used | Example |
|---|---|---|
| **Abstract Base Class** | When a new type of component is needed | New `BaseFeed` subclass for a new data source |
| **Plugin Registry** | When a new instance of an existing type is needed | New agent registered in `AgentRegistry` |
| **Event Subscription** | When a new reaction to an existing event is needed | New handler subscribing to `TradeClosedEvent` |

The framework publishes these extension points explicitly. Code that bypasses these patterns and directly modifies framework internals violates the framework contract.

---

### 1.8 Technology Independence Philosophy

The Core Framework is designed so that specific technologies can be swapped without affecting the business logic:

| Technology | Current Choice | Framework Abstraction | Alternative (if needed) |
|---|---|---|---|
| Market data | yfinance / Dhan | `BaseFeed` interface | Any feed implementing `BaseFeed` |
| Database | SQLite | `BaseRepository` interface | PostgreSQL, MongoDB |
| Message queue | In-process EventBus | `BaseEventBus` interface | Redis, RabbitMQ |
| Notification | Telegram | `BaseNotifier` interface | Email, Slack, SMS |
| Scheduler | APScheduler | `BaseScheduler` interface | Celery, cron |
| Logging | Python `logging` | `LoggingFactory` wrapper | Structlog, Loguru |
| Configuration | Environment variables | `ConfigurationManager` | Consul, Vault |
| Secrets | Environment variables | `SecretsManager` | HashiCorp Vault, AWS Secrets Manager |

The business logic (layers 1–17) depends only on the framework abstractions. The specific technology choices are made at the infrastructure layer, within the declared extension points.

---

### 1.9 Anti-Patterns Prevented

| Anti-Pattern | Description | How the Framework Prevents It |
|---|---|---|
| Framework bypass | A component directly instantiates a concrete dependency | `DependencyManager` provides all services; direct instantiation is prohibited |
| Configuration sprawl | Config values scattered in random modules | `ConfigurationManager` is the single source |
| Silent failure | `except: pass` silently discards errors | `BaseException` hierarchy forces explicit handling |
| Undeclared lifecycle | Component initialises on import | `LifecycleManager` controls init/shutdown explicitly |
| Hidden state | Module-level mutable globals | `ApplicationContext` is the only approved shared state carrier |
| Test pollution | Tests depend on each other's side effects | Framework components are injectable; no shared state across tests |
| Duplicate utilities | Time formatting written ten different ways | `TimeUtility` provides one canonical implementation |
| Ad hoc retry | Each caller implements its own retry loop | `RetryPolicy` provides one canonical retry mechanism |

---

## PART II — CORE COMPONENTS

### 2.1 Component Overview

The Core Framework consists of 25 named components organised into five groups. Every component has a single declared responsibility. No component duplicates the responsibility of another.

**Component Groups:**

| Group | Components | Purpose |
|---|---|---|
| Foundation | CoreConstants, GlobalConfiguration, ConfigurationManager, EnvironmentManager | System-level values and configuration |
| Lifecycle | LifecycleManager, DependencyManager, ApplicationContext, ContextManager | System startup, shutdown, and per-cycle state |
| Base Classes | BaseFeed, BaseAgent, BaseEngine, BaseManager, BaseService, BaseRepository, BaseScheduler, BaseValidator | Abstract contracts for all component types |
| Data Structures | BaseEntity, BaseValueObject, BaseDTO, BaseRequest, BaseResponse, BaseResult, BaseEvent, BaseModel | Typed data transfer and domain objects |
| Framework Services | ExceptionBase, RetryPolicy, CircuitBreaker, HealthCheck | Error handling and resilience |

---

### 2.2 Core Constants

**Component:** `CoreConstants`
**Location:** `src/common/constants.py`
**Owner:** Engineering Foundation

**Responsibility:** Defines all system-level constants that do not change at runtime. These are the invariant numeric and string values that the entire system references.

| Constant Category | Examples | Type |
|---|---|---|
| Temporal constants | `MARKET_OPEN_HOUR_IST = 9`, `MARKET_OPEN_MINUTE_IST = 15` | `int` |
| | `MARKET_CLOSE_HOUR_IST = 15`, `MARKET_CLOSE_MINUTE_IST = 30` | `int` |
| | `IST_UTC_OFFSET_HOURS = 5`, `IST_UTC_OFFSET_MINUTES = 30` | `int` |
| | `TRADING_DAYS = (0, 1, 2, 3, 4)` (Mon–Fri) | `tuple[int]` |
| Layer constants | `MIN_LAYER_NUMBER = 1`, `MAX_LAYER_NUMBER = 17` | `int` |
| | `LAYER_NAME_MAX_LENGTH = 64` | `int` |
| Symbol constants | `NSE_SUFFIX = ".NS"`, `BSE_SUFFIX = ".BO"` | `str` |
| | `INDEX_SYMBOLS = ("NIFTY", "BANKNIFTY", "SENSEX")` | `tuple[str]` |
| Numeric limits | `MAX_CONVICTION_SCORE = 10.0`, `MIN_CONVICTION_SCORE = 0.0` | `float` |
| | `MAX_POSITION_SIZE_PCT = 0.20` | `float` |
| | `MAX_DAILY_LOSS_PCT = 0.02` | `float` |
| ID constants | `UUID4_LENGTH = 36` | `int` |
| | `CYCLE_ID_PREFIX = "CYC"` | `str` |
| Status constants | `STATUS_PENDING = "PENDING"` | `str` |
| | `STATUS_OPEN = "OPEN"` | `str` |
| | `STATUS_CLOSED = "CLOSED"` | `str` |
| | `STATUS_CANCELLED = "CANCELLED"` | `str` |
| | `STATUS_ERROR = "ERROR"` | `str` |
| Direction constants | `DIRECTION_LONG = "LONG"`, `DIRECTION_SHORT = "SHORT"` | `str` |
| Regime constants | `REGIME_TRENDING_BULLISH = "TRENDING_BULLISH"` | `str` |
| | `REGIME_TRENDING_BEARISH = "TRENDING_BEARISH"` | `str` |
| | `REGIME_RANGE_BOUND = "RANGE_BOUND"` | `str` |
| | `REGIME_HIGH_VOLATILITY = "HIGH_VOLATILITY"` | `str` |
| | `REGIME_UNKNOWN = "UNKNOWN"` | `str` |
| Strategy constants | `STRATEGY_FAMILY_MOMENTUM = "MOMENTUM"` | `str` |
| | `STRATEGY_FAMILY_MEAN_REVERSION = "MEAN_REVERSION"` | `str` |
| | `STRATEGY_FAMILY_BREAKOUT = "BREAKOUT"` | `str` |
| | `STRATEGY_FAMILY_ARBITRAGE = "ARBITRAGE"` | `str` |
| Version constant | `FRAMEWORK_VERSION = "1.0.0"` | `str` |

**Governance rules for `CoreConstants`:**
- Constants are UPPER_SNAKE_CASE
- No constant references another constant at definition (order-independent)
- No constant has a mutable default (no lists, no dicts — use tuples)
- All constants have an inline type annotation and comment
- No business logic depends on the constant's name (only its value)

---

### 2.3 Global Configuration

**Component:** `GlobalConfiguration`
**Location:** `src/config/global_config.py`
**Owner:** Control Tower

**Responsibility:** Holds all runtime-configurable values for the system. Unlike `CoreConstants`, these values may differ between environments and may be changed without a code release.

**Configuration Sections:**

| Section | Key Constants | Configurable Range |
|---|---|---|
| Latency | `LAYER_LATENCY_WARN_MS` | 100–10,000 ms |
| | `LAYER_LATENCY_CRIT_MS` | 200–60,000 ms |
| Risk | `DAILY_LOSS_LIMIT` | 0.01–0.05 (1%–5% of capital) |
| | `MAX_OPEN_POSITIONS` | 1–20 |
| | `KILL_SWITCH_VIX_THRESHOLD` | 30–60 |
| Capital | `PAPER_CAPITAL` | Any positive INR amount |
| | `LIVE_CAPITAL` | Any positive INR amount |
| | `PER_STRATEGY_BUDGET_PCT` | 0.01–0.30 |
| Data | `YAHOO_TIMEOUT_SECONDS` | 5–30 |
| | `DATA_CACHE_TTL_SECONDS` | 60–600 |
| | `GLOBAL_DATA_CACHE_TTL_SECONDS` | 120–3600 |
| Strategy | `MIN_SIGNAL_RR` | 1.0–5.0 |
| | `MIN_WIN_RATE_PCT` | 0.30–0.70 |
| | `AUTO_DISABLE_THRESHOLD` | 3–10 consecutive losses |
| Debate | `CONVICTION_THRESHOLD` | 5.0–9.0 |
| | `NUM_DEBATE_AGENTS` | 3–7 |
| Schedule | `CONTINUOUS_SCAN_INTERVAL` | 10–120 seconds |
| | `EOD_HOUR_IST` | 15–18 |
| | `PRE_MARKET_HOUR_IST` | 8–9 |

**Access pattern:** `GlobalConfiguration` is accessed through `ConfigurationManager.get(key)`. Direct attribute access is permitted only in `config.py`. All other modules use the manager.

---

### 2.4 Configuration Manager

**Component:** `ConfigurationManager`
**Location:** `src/config/configuration_manager.py`
**Owner:** Control Tower

**Responsibility:** Provides the single interface through which all modules access configuration values. Validates configuration at startup. Supports type-safe access with default values.

**Interface Contract:**

| Method | Signature | Purpose |
|---|---|---|
| `get` | `(key: str, default: T = None) -> T` | Returns typed config value |
| `get_int` | `(key: str, default: int = 0) -> int` | Returns integer config value |
| `get_float` | `(key: str, default: float = 0.0) -> float` | Returns float config value |
| `get_bool` | `(key: str, default: bool = False) -> bool` | Returns boolean config value |
| `get_str` | `(key: str, default: str = "") -> str` | Returns string config value |
| `get_list` | `(key: str, default: list = None) -> list` | Returns list config value |
| `validate_all` | `() -> ValidationResult` | Validates all config values against schema |
| `reload` | `() -> None` | Hot-reloads environment variables (runtime safe) |
| `is_feature_enabled` | `(feature_name: str) -> bool` | Returns feature flag state |
| `set_runtime` | `(key: str, value: Any) -> None` | Sets a runtime-only config override |
| `clear_runtime` | `(key: str) -> None` | Clears a runtime override; reverts to static |
| `get_all` | `() -> Dict[str, Any]` | Returns full config snapshot (for diagnostics) |

**Type safety:** All `get_*` methods perform type coercion and raise `ConfigurationError` if the coercion fails. They never return `None` when a `default` is provided.

---

### 2.5 Environment Manager

**Component:** `EnvironmentManager`
**Location:** `src/config/environment_manager.py`
**Owner:** Control Tower

**Responsibility:** Detects and manages the current execution environment (development, testing, production). Provides environment-specific configuration overlays.

| Method | Signature | Purpose |
|---|---|---|
| `current_environment` | `() -> EnvironmentType` | Returns `DEVELOPMENT`, `TESTING`, or `PRODUCTION` |
| `is_development` | `() -> bool` | Returns True in development environment |
| `is_testing` | `() -> bool` | Returns True in test environment |
| `is_production` | `() -> bool` | Returns True in production environment |
| `is_paper_trading` | `() -> bool` | Returns current paper trading flag state |
| `get_data_path` | `() -> Path` | Returns environment-appropriate data directory |
| `get_log_path` | `() -> Path` | Returns environment-appropriate log directory |
| `get_db_path` | `(db_name: str) -> Path` | Returns environment-appropriate database path |

**Environment detection:** The environment is determined by the `TRADING_ENV` environment variable:
- `TRADING_ENV=development` → `EnvironmentType.DEVELOPMENT`
- `TRADING_ENV=testing` → `EnvironmentType.TESTING`
- `TRADING_ENV=production` → `EnvironmentType.PRODUCTION`
- Unset or unknown → `EnvironmentType.DEVELOPMENT` (safe default)

---

### 2.6 Dependency Manager

**Component:** `DependencyManager`
**Location:** `src/common/dependency_manager.py`
**Owner:** Engineering Foundation

**Responsibility:** Provides a simple dependency injection container. Services register themselves; consumers request them by type or name. The manager handles singleton lifecycle.

| Method | Signature | Purpose |
|---|---|---|
| `register_singleton` | `(interface: Type[T], implementation: T) -> None` | Registers a singleton service |
| `register_factory` | `(interface: Type[T], factory: Callable[[], T]) -> None` | Registers a factory for transient instances |
| `resolve` | `(interface: Type[T]) -> T` | Returns the registered implementation |
| `resolve_by_name` | `(name: str) -> Any` | Returns the registered component by name |
| `is_registered` | `(interface: Type[T]) -> bool` | Returns True if an implementation is registered |
| `get_all` | `(interface: Type[T]) -> List[T]` | Returns all implementations of an interface |
| `clear` | `() -> None` | Clears all registrations (test support only) |

---

### 2.7 Lifecycle Manager

**Component:** `LifecycleManager`
**Location:** `src/common/lifecycle_manager.py`
**Owner:** Control Tower

**Responsibility:** Manages the initialisation and shutdown sequence of all registered components. Ensures components start in dependency order and shut down in reverse order.

**Lifecycle States:**

```
CREATED → INITIALISING → INITIALISED → STARTING → RUNNING → STOPPING → STOPPED
                                           ↑                       ↓
                                      RESTARTING ←────────────────┘
                                           ↓
                                      ERROR (on failure)
```

| Method | Signature | Purpose |
|---|---|---|
| `register` | `(component: LifecycleAware, priority: int) -> None` | Registers component at priority level |
| `initialise_all` | `() -> None` | Calls `initialise()` on all components in priority order |
| `start_all` | `() -> None` | Calls `start()` on all initialised components |
| `stop_all` | `() -> None` | Calls `stop()` on all running components (reverse order) |
| `restart_component` | `(component_name: str) -> None` | Stops and re-starts one component |
| `get_state` | `(component_name: str) -> LifecycleState` | Returns current lifecycle state |
| `get_all_states` | `() -> Dict[str, LifecycleState]` | Returns all component states (health overview) |
| `is_all_running` | `() -> bool` | Returns True if all registered components are RUNNING |

**Priority ordering:** Lower priority number = initialised first.

| Priority | Components |
|---|---|
| 1 | `SecretsManager`, `EnvironmentManager` |
| 2 | `ConfigurationManager` |
| 3 | `LoggingService` |
| 4 | `DatabaseService` |
| 5 | `DataFeedManager` |
| 6 | `AuditService`, `MetricsCollector` |
| 10 | All 17 operational layers |
| 20 | `TelegramBot`, `DashboardService` |
| 99 | `APScheduler` (last: starts jobs only after all services are ready) |

---

### 2.8 Application Context

**Component:** `ApplicationContext`
**Location:** `src/common/application_context.py`
**Owner:** Engineering Foundation

**Responsibility:** Carries per-cycle, per-request, or per-operation context through the call stack. Provides correlation IDs, timestamps, and caller identity without requiring them to be passed as parameters to every function.

**Context Fields:**

| Field | Type | Description |
|---|---|---|
| `cycle_id` | `str` | UUID4 identifying the current cognitive cycle |
| `started_at` | `datetime` | UTC timestamp when the cycle started |
| `environment` | `EnvironmentType` | Current execution environment |
| `is_paper_trading` | `bool` | Whether paper trading mode is active |
| `regime_type` | `Optional[str]` | Regime detected in this cycle (set by Layer 2) |
| `kill_switch_active` | `bool` | Current kill-switch state |
| `correlation_chain` | `List[str]` | Ordered list of operation IDs in this cycle |
| `caller_layer` | `Optional[str]` | Name of the layer currently executing |
| `properties` | `Dict[str, Any]` | Extensible property bag for layer-specific context |

**Threading model:** `ApplicationContext` is stored in thread-local storage. Each cycle's thread has its own context. Contexts from different cycles do not interfere.

**Access methods:**

| Method | Signature | Purpose |
|---|---|---|
| `current` | `() -> ApplicationContext` | Returns context for current thread |
| `create_cycle_context` | `(cycle_id: str) -> ApplicationContext` | Creates and stores a new cycle context |
| `push_operation` | `(operation_id: str) -> None` | Adds operation to correlation chain |
| `pop_operation` | `() -> None` | Removes last operation from chain |
| `set_regime` | `(regime: str) -> None` | Records detected regime in context |
| `set_layer` | `(layer_name: str) -> None` | Records currently executing layer |
| `clear` | `() -> None` | Clears current thread's context |

---

### 2.9 Context Manager (Execution Context)

**Component:** `ExecutionContextManager` (distinct from Python's `contextmanager`)
**Location:** `src/common/execution_context.py`
**Owner:** Engineering Foundation

**Responsibility:** Provides structured context scopes that automatically push/pop the execution context, measure duration, and emit telemetry on exit.

**Scope Types:**

| Scope Type | Used For | Auto-Emits |
|---|---|---|
| `CycleScope` | One complete cognitive cycle | Cycle start/end events, cycle duration |
| `LayerScope` | One layer's execution within a cycle | Layer timing, layer error if exception |
| `OperationScope` | Any named sub-operation within a layer | Operation timing, error context |
| `TransactionScope` | A database write transaction | Transaction success/failure event |

---

### 2.10 Base Interfaces

**Component:** `BaseInterfaces`
**Location:** `src/common/interfaces.py`
**Owner:** Engineering Foundation

**Responsibility:** Defines the pure abstract interfaces that all framework-managed components implement. Interfaces declare contracts without any implementation.

**Core Interfaces:**

| Interface | Key Contracts | Implementing Components |
|---|---|---|
| `LifecycleAware` | `initialise()`, `start()`, `stop()`, `get_name()` | All services, all layers, scheduler |
| `HealthCheckable` | `check_health() -> HealthStatus` | All services, all layers |
| `Observable` | `get_metrics() -> MetricsSnapshot` | All components |
| `Configurable` | `configure(config: ConfigurationManager)` | All configurable components |
| `Auditable` | `get_audit_record() -> AuditRecord` | Decision-making components |
| `Serialisable` | `to_dict() -> dict`, `from_dict(d: dict) -> Self` | All DTOs, all domain objects |
| `Validatable` | `validate() -> ValidationResult` | All DTOs, all request objects |
| `Resettable` | `reset() -> None` | Test-support interface |
| `Describable` | `describe() -> ComponentDescription` | All registered components |

---

### 2.11 Base Models

**Component:** `BaseModel`
**Location:** `src/common/base_model.py`
**Owner:** Engineering Foundation

**Responsibility:** Root base class for all domain models. Provides identity, timestamps, and serialisation.

**Inherited Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | UUID4 unique identifier |
| `created_at` | `datetime` | UTC creation timestamp |
| `updated_at` | `datetime` | UTC last-modified timestamp |
| `version` | `int` | Optimistic concurrency version counter |

**Inherited Methods:**

| Method | Purpose |
|---|---|
| `to_dict()` | Serialise to Python dict (JSON-serialisable) |
| `from_dict(d)` | Deserialise from dict (class method) |
| `validate()` | Validate invariants; return `ValidationResult` |
| `is_equal(other)` | Identity-based equality |

---

### 2.12 Base Services

**Component:** `BaseService`
**Location:** `src/common/base_service.py`
**Owner:** Engineering Foundation

**Responsibility:** Abstract base for all services (stateful, long-lived components). Combines `LifecycleAware`, `HealthCheckable`, and `Observable`.

**Lifecycle Methods (must override):**

| Method | When Called | Must Do |
|---|---|---|
| `_do_initialise()` | By `LifecycleManager` at startup | Allocate resources, validate config |
| `_do_start()` | After all services initialised | Start background threads if needed |
| `_do_stop()` | On shutdown or restart | Release resources, join threads |
| `_do_health_check()` | On demand | Return `HealthStatus.HEALTHY` or `DEGRADED` or `UNHEALTHY` |
| `_do_get_metrics()` | On demand | Return component-specific `MetricsSnapshot` |

**Provided Behaviour (by `BaseService`, not overridden):**

| Behaviour | Description |
|---|---|
| Lifecycle state machine | Tracks state; raises `LifecycleError` on invalid transitions |
| Logging | Provides `self.logger` configured with package.class name |
| Configuration access | Provides `self.config` (the `ConfigurationManager` instance) |
| Context access | Provides `self.context` (the `ApplicationContext`) |
| Error wrapping | Wraps `_do_*` exceptions in framework-typed errors |

---

### 2.13 Base Repository

**Component:** `BaseRepository`
**Location:** `src/common/base_repository.py`
**Owner:** Engineering Foundation

**Responsibility:** Abstract base for all database access objects. Provides CRUD contract and transactional safety.

| Method | Signature | Purpose |
|---|---|---|
| `save` | `(entity: E) -> E` | Persist a new or updated entity |
| `find_by_id` | `(entity_id: str) -> Optional[E]` | Retrieve entity by ID |
| `find_all` | `(limit: int = 100) -> List[E]` | Retrieve all entities (paginated) |
| `find_where` | `(criteria: Criteria) -> List[E]` | Retrieve with filter criteria |
| `delete` | `(entity_id: str) -> bool` | Delete entity by ID (soft-delete preferred) |
| `count` | `(criteria: Criteria = None) -> int` | Count matching entities |
| `exists` | `(entity_id: str) -> bool` | Check entity existence |
| `begin_transaction` | `() -> Transaction` | Begin explicit transaction |
| `commit_transaction` | `(tx: Transaction) -> None` | Commit transaction |
| `rollback_transaction` | `(tx: Transaction) -> None` | Rollback transaction |

**Security constraint:** All query parameters are bound via parameterised statements. String interpolation into SQL is prohibited.

---

### 2.14 Base Engine

**Component:** `BaseEngine`
**Location:** `src/common/base_engine.py`
**Owner:** Engineering Foundation

**Responsibility:** Abstract base for all IIOS operational layer engines (Layers 1–17). Extends `BaseService` with cognitive-cycle execution semantics.

| Method | Signature | Mandatory | Purpose |
|---|---|---|---|
| `execute` | `(context: ApplicationContext) -> EngineResult` | Yes | Run this layer's logic for one cycle |
| `get_layer_number` | `() -> int` | Yes | Return 1–17 |
| `get_layer_name` | `() -> str` | Yes | Return human-readable layer name |
| `get_dependencies` | `() -> List[str]` | Yes | Return names of layers this engine consumes |
| `get_latency_warn_ms` | `() -> int` | No | Override default latency warning threshold |
| `get_latency_crit_ms` | `() -> int` | No | Override default latency critical threshold |
| `get_last_result` | `() -> Optional[EngineResult]` | No | Return last execution result (cached) |

**`EngineResult` fields:**

| Field | Type | Description |
|---|---|---|
| `layer_name` | `str` | Layer that produced this result |
| `cycle_id` | `str` | Cycle this result belongs to |
| `success` | `bool` | Whether execution succeeded |
| `duration_ms` | `int` | Execution duration |
| `payload` | `Any` | Layer-specific output (typed at layer level) |
| `error` | `Optional[str]` | Error message if `success=False` |
| `metrics` | `Dict[str, float]` | Layer-specific metrics for telemetry |

---

### 2.15 Base Manager

**Component:** `BaseManager`
**Location:** `src/common/base_manager.py`
**Owner:** Engineering Foundation

**Responsibility:** Abstract base for all manager components (components that coordinate multiple services or maintain a pool of resources). Distinct from `BaseEngine` (which executes per-cycle) and `BaseService` (which is a single-concern service).

| Method | Signature | Mandatory | Purpose |
|---|---|---|---|
| `get_managed_items` | `() -> List[Managed]` | Yes | Return all items under management |
| `register` | `(item: Managed) -> None` | Yes | Add an item to the managed collection |
| `deregister` | `(name: str) -> bool` | Yes | Remove an item from management |
| `get_by_name` | `(name: str) -> Optional[Managed]` | Yes | Retrieve managed item by name |
| `get_status_summary` | `() -> ManagerStatusSummary` | Yes | Return health of all managed items |

---

### 2.16 Base Agent

**Component:** `BaseAgent`
**Location:** `src/common/base_agent.py`
**Owner:** Engineering Foundation

**Responsibility:** Abstract base for all 62+ AI agents. Defines the opinion-generation contract used by the debate engine.

| Method | Signature | Mandatory | Purpose |
|---|---|---|---|
| `analyse` | `(context: AgentContext) -> AgentOpinion` | Yes | Analyse hypothesis and return scored opinion |
| `get_agent_name` | `() -> str` | Yes | Return unique agent name |
| `get_agent_role` | `() -> AgentRole` | Yes | Return BULL, BEAR, RISK, TECHNICAL, or FUNDAMENTAL |
| `get_weight` | `() -> float` | No | Return debate weight (default 1.0) |
| `get_confidence` | `() -> float` | No | Return current confidence in own analysis |
| `explain` | `() -> str` | No | Return human-readable explanation of last opinion |

**`AgentOpinion` fields:**

| Field | Type | Description |
|---|---|---|
| `agent_name` | `str` | Agent that produced this opinion |
| `agent_role` | `AgentRole` | Agent's declared role |
| `score` | `float` | Opinion score: 0.0–10.0 (10=strong agree, 0=strong reject) |
| `confidence` | `float` | Agent's confidence in own score: 0.0–1.0 |
| `rationale` | `str` | Explanation of the score |
| `signals` | `List[str]` | List of signals that drove the score |
| `weight` | `float` | Agent's weight in final conviction calculation |

---

### 2.17 Base Scheduler

**Component:** `BaseScheduler`
**Location:** `src/common/base_scheduler.py`
**Owner:** Control Tower

**Responsibility:** Abstract base for scheduling engines. Provides a consistent interface for scheduling, pausing, resuming, and cancelling jobs.

| Method | Signature | Mandatory | Purpose |
|---|---|---|---|
| `schedule_job` | `(job: ScheduledJob) -> str` | Yes | Schedule a job; return job ID |
| `cancel_job` | `(job_id: str) -> bool` | Yes | Cancel a scheduled job |
| `pause_job` | `(job_id: str) -> bool` | Yes | Pause a scheduled job |
| `resume_job` | `(job_id: str) -> bool` | Yes | Resume a paused job |
| `get_next_run` | `(job_id: str) -> Optional[datetime]` | Yes | Return next scheduled run time |
| `get_all_jobs` | `() -> List[JobStatus]` | Yes | Return status of all scheduled jobs |
| `shutdown` | `(wait: bool = True) -> None` | Yes | Shut down scheduler; optionally wait for running jobs |

---

### 2.18 Base Validator

**Component:** `BaseValidator`
**Location:** `src/common/base_validator.py`
**Owner:** Engineering Foundation

**Responsibility:** Abstract base for all validation components. Provides a consistent interface for validating domain objects, DTOs, and configuration.

| Method | Signature | Mandatory | Purpose |
|---|---|---|---|
| `validate` | `(subject: T) -> ValidationResult` | Yes | Validate subject; return result with all errors |
| `validate_or_raise` | `(subject: T) -> T` | No | Validate; raise `ValidationError` if invalid |
| `is_valid` | `(subject: T) -> bool` | No | Returns True only if valid (no errors) |

**`ValidationResult` fields:**

| Field | Type | Description |
|---|---|---|
| `is_valid` | `bool` | True if no violations |
| `violations` | `List[ValidationViolation]` | All validation failures |
| `subject_type` | `str` | Type name of the validated subject |
| `validated_at` | `datetime` | UTC timestamp of validation |

**`ValidationViolation` fields:**

| Field | Type | Description |
|---|---|---|
| `field` | `str` | Field path that failed (e.g., `"hypothesis.stop_loss"`) |
| `constraint` | `str` | Constraint that was violated (e.g., `"must_be_positive"`) |
| `value` | `Any` | The value that failed |
| `message` | `str` | Human-readable explanation |
| `severity` | `ViolationSeverity` | ERROR or WARNING |

---

### 2.19 Base Exception

**Component:** `BaseException` (project root exception)
**Location:** `src/common/errors.py`
**Owner:** Engineering Foundation

**Responsibility:** Root of the complete project exception hierarchy. All custom exceptions in the system extend from `TradingBrainError`. Detailed hierarchy in Part IV.

**Base fields carried by all framework exceptions:**

| Field | Type | Description |
|---|---|---|
| `message` | `str` | Human-readable error description |
| `error_code` | `str` | Machine-readable error code (e.g., `"FEED_TIMEOUT"`) |
| `cycle_id` | `Optional[str]` | Cycle context when error occurred |
| `layer_name` | `Optional[str]` | Layer where error originated |
| `timestamp` | `datetime` | UTC timestamp of error |
| `context` | `Dict[str, Any]` | Additional diagnostic context |
| `cause` | `Optional[Exception]` | Original exception that triggered this one |
| `is_recoverable` | `bool` | Whether the caller may retry |

---

### 2.20 Base Event

**Component:** `BaseEvent`
**Location:** `src/common/events.py`
**Owner:** Engineering Foundation

**Responsibility:** Root of the event hierarchy for the in-process EventBus. All events inherit from `BaseEvent`.

| Field | Type | Description |
|---|---|---|
| `event_id` | `str` | UUID4 |
| `event_type` | `str` | Event type name (e.g., `"TRADE_OPENED"`) |
| `cycle_id` | `str` | Cycle that produced this event |
| `emitted_at` | `datetime` | UTC timestamp |
| `emitter_name` | `str` | Component that emitted the event |
| `payload` | `Dict[str, Any]` | Event-specific data |

**Standard system events:**

| Event Type | Emitter | Payload |
|---|---|---|
| `CYCLE_STARTED` | MasterOrchestrator | `cycle_id`, `started_at`, `regime_type` |
| `CYCLE_COMPLETED` | MasterOrchestrator | `cycle_id`, `duration_ms`, `orders_submitted` |
| `CYCLE_FAILED` | MasterOrchestrator | `cycle_id`, `error`, `layer_name` |
| `LAYER_COMPLETED` | SystemMonitor | `layer_name`, `duration_ms`, `status` |
| `LAYER_TIMEOUT` | SystemMonitor | `layer_name`, `duration_ms`, `threshold_ms` |
| `KILL_SWITCH_ACTIVATED` | RiskGuardian | `reason`, `activated_at`, `vix_level` |
| `KILL_SWITCH_CLEARED` | RiskGuardian | `cleared_at`, `cleared_by` |
| `TRADE_OPENED` | OrderManager | `order_id`, `symbol`, `direction`, `quantity` |
| `TRADE_CLOSED` | TradeMonitor | `order_id`, `close_price`, `pnl`, `reason` |
| `STRATEGY_DISABLED` | StrategyHealthMonitor | `strategy_id`, `reason`, `consecutive_losses` |
| `DAILY_LOSS_LIMIT_REACHED` | RiskGuardian | `daily_pnl`, `limit` |
| `FEED_FAILOVER` | DataFeedManager | `from_feed`, `to_feed`, `reason` |

---

### 2.21 Base Entity

**Component:** `BaseEntity`
**Location:** `src/common/base_entity.py`
**Owner:** Engineering Foundation

**Responsibility:** Base class for domain entities — objects with unique identity that persist over time. Extends `BaseModel` with domain-specific behaviour.

**Rules for entities:**
- An entity has a unique `id` (UUID4)
- An entity is equal to another entity if and only if their `id` is equal (identity-based equality)
- An entity owns its own invariants; it validates them in `validate()`
- An entity tracks its modification history through `version` (optimistic concurrency)
- An entity may contain value objects but entities never contain other entities by value (only by ID reference)

---

### 2.22 Base Value Object

**Component:** `BaseValueObject`
**Location:** `src/common/base_value_object.py`
**Owner:** Engineering Foundation

**Responsibility:** Base class for domain value objects — immutable objects defined entirely by their attributes, with no identity.

**Rules for value objects:**
- A value object has no `id` field
- A value object is equal to another if all its attributes are equal (structural equality)
- A value object is always immutable (`frozen=True` in dataclass terms)
- A value object validates its own invariants at construction time
- A value object contains no domain services; it is pure data + invariant rules

**Examples of value objects in the IIOS:**

| Value Object | Key Attributes | Invariants |
|---|---|---|
| `Money` | `amount: Decimal`, `currency: str` | `amount >= 0`, `currency` in ISO 4217 |
| `Price` | `value: float`, `currency: str` | `value > 0` |
| `Percentage` | `value: float` | `0.0 <= value <= 1.0` |
| `RewardRiskRatio` | `reward: float`, `risk: float` | `reward > 0`, `risk > 0` |
| `Conviction` | `score: float` | `0.0 <= score <= 10.0` |
| `TradeDirection` | `value: str` | `value in ("LONG", "SHORT")` |
| `MarketRegime` | `type: str`, `confidence: float` | `type in KNOWN_REGIMES`, `0 ≤ confidence ≤ 1` |

---

### 2.23 Base DTO

**Component:** `BaseDTO`
**Location:** `src/common/base_dto.py`
**Owner:** Engineering Foundation

**Responsibility:** Base class for data transfer objects — typed data containers for crossing layer boundaries. DTOs carry data with no business logic.

**Rules for DTOs:**
- DTOs are `frozen=True` dataclasses (immutable at boundaries)
- DTOs have no methods beyond `validate()` and `to_dict()` / `from_dict()`
- DTOs carry only data from the standard type vocabulary (str, int, float, bool, datetime, Optional, List, Dict)
- DTO field names follow `snake_case`
- DTOs always include: `produced_at: datetime` (UTC), `source_layer: str`
- DTOs are valid (all invariants satisfied) at the moment of creation; they are never modified after crossing a boundary

---

### 2.24 Base Request / Base Response / Base Result

**Component:** `BaseRequest`, `BaseResponse`, `BaseResult`
**Location:** `src/common/messaging.py`
**Owner:** Engineering Foundation

**`BaseRequest`:** Typed input to a service or engine operation. Fields:
- `request_id: str` — UUID4
- `requested_at: datetime` — UTC
- `requester: str` — Name of requesting component
- `cycle_id: Optional[str]` — Parent cycle

**`BaseResponse`:** Typed output from a service or engine operation. Fields:
- `response_id: str` — UUID4
- `request_id: str` — Echoed from request
- `responded_at: datetime` — UTC
- `success: bool`
- `error: Optional[str]` — Error message if not success

**`BaseResult`:** Typed result of a computation (not a service call). Does NOT inherit from `BaseResponse`. Fields:
- `result_id: str` — UUID4
- `produced_at: datetime` — UTC
- `producer: str` — Component name
- `is_success: bool`
- `value: Optional[T]` — Result value (generic type)
- `error: Optional[str]` — Error if not success

---

## PART III — COMMON UTILITIES

### 3.1 Utility Design Principles

Common utilities are pure functions or stateless utility classes with no dependencies on any project-specific business logic. They exist to eliminate code duplication and provide one canonical implementation of recurring programming patterns. Every utility:

- Has a single named responsibility
- Takes inputs, produces outputs, has no side effects (unless explicitly named `_writer` or `_logger`)
- Is unit-tested to 100% branch coverage
- Is documented with input/output examples
- Raises typed exceptions from `common/errors.py`
- Is located in `src/common/`

---

### 3.2 Date and Time Utilities (`time_utils.py`)

Provides all time-related operations needed across the system. All functions produce timezone-aware results. All timestamp operations use UTC internally.

| Function | Signature | Description |
|---|---|---|
| `utc_now` | `() -> datetime` | Returns current UTC time, timezone-aware |
| `ist_now` | `() -> datetime` | Returns current IST time (UTC+5:30) |
| `to_utc` | `(dt: datetime) -> datetime` | Converts any timezone-aware dt to UTC |
| `to_ist` | `(dt: datetime) -> datetime` | Converts any timezone-aware dt to IST |
| `is_market_open` | `() -> bool` | True if current time is within NSE market hours |
| `is_pre_market` | `() -> bool` | True if within pre-market window (08:30–09:15 IST) |
| `market_open_today` | `() -> datetime` | Today's market open in UTC |
| `market_close_today` | `() -> datetime` | Today's market close in UTC |
| `minutes_to_close` | `() -> int` | Minutes remaining until close; 0 if market closed |
| `is_trading_day` | `(date: date) -> bool` | True for Monday–Friday, excluding NSE holidays |
| `next_trading_day` | `(from_date: date) -> date` | Returns next valid trading day |
| `trading_days_between` | `(start: date, end: date) -> int` | Count of trading days in range |
| `iso_timestamp` | `(dt: datetime) -> str` | ISO 8601 string: `"2026-07-02T09:15:00+05:30"` |
| `iso_date` | `(date: date) -> str` | ISO date string: `"2026-07-02"` |
| `from_iso_timestamp` | `(s: str) -> datetime` | Parse ISO 8601 to timezone-aware datetime |
| `format_duration_ms` | `(ms: int) -> str` | Human-readable: `"1h 23m 45s"` |
| `seconds_since` | `(dt: datetime) -> float` | Seconds elapsed since given timestamp |
| `is_stale` | `(dt: datetime, ttl_seconds: int) -> bool` | True if more than ttl_seconds have elapsed |
| `floor_to_minute` | `(dt: datetime) -> datetime` | Truncate to minute: removes seconds/microseconds |
| `ceil_to_minute` | `(dt: datetime) -> datetime` | Round up to next minute |

---

### 3.3 UUID and ID Generation (`id_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `generate_uuid4` | `() -> str` | Returns a new UUID4 string (hyphenated format) |
| `generate_cycle_id` | `() -> str` | Returns `"CYC-" + uuid4()` for cycle identification |
| `generate_decision_id` | `() -> str` | Returns `"DEC-" + uuid4()` |
| `generate_order_id` | `() -> str` | Returns `"ORD-" + uuid4()` |
| `generate_event_id` | `() -> str` | Returns `"EVT-" + uuid4()` |
| `is_valid_uuid4` | `(s: str) -> bool` | True if string is a valid UUID4 |
| `is_valid_id` | `(s: str, prefix: str) -> bool` | True if string matches prefix + UUID4 pattern |
| `short_id` | `(full_id: str) -> str` | Returns last 8 characters for display |

---

### 3.4 String Utilities (`string_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `snake_to_pascal` | `(s: str) -> str` | `"market_regime"` → `"MarketRegime"` |
| `pascal_to_snake` | `(s: str) -> str` | `"MarketRegime"` → `"market_regime"` |
| `truncate` | `(s: str, max_len: int, suffix: str = "...") -> str` | Truncates with suffix |
| `is_empty_or_whitespace` | `(s: str) -> bool` | True if None, empty, or all whitespace |
| `safe_upper` | `(s: Optional[str]) -> str` | Upper-case or empty string if None |
| `safe_strip` | `(s: Optional[str]) -> str` | Strip or empty string if None |
| `mask_secret` | `(s: str, visible_chars: int = 4) -> str` | `"ABCDEF123"` → `"****3"` |
| `format_currency` | `(amount: float, currency: str = "INR") -> str` | `"₹ 12,345.67"` |
| `format_percentage` | `(value: float, decimals: int = 2) -> str` | `0.1234` → `"12.34%"` |
| `pluralise` | `(word: str, count: int) -> str` | `"trade", 1` → `"trade"`; `"trade", 2` → `"trades"` |
| `slugify` | `(s: str) -> str` | `"NIFTY 50"` → `"nifty-50"` |
| `sanitise_log_string` | `(s: str) -> str` | Strips control characters, limits to 500 chars |
| `join_non_empty` | `(parts: List[str], sep: str = ", ") -> str` | Joins only non-empty parts |
| `pad_left` | `(s: str, width: int, char: str = " ") -> str` | Left-pads string to width |

---

### 3.5 Number Utilities (`number_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `clamp` | `(value: float, min_v: float, max_v: float) -> float` | Constrains value to [min_v, max_v] |
| `round_to_tick` | `(price: float, tick_size: float) -> float` | Rounds to nearest tick size |
| `pct_change` | `(old: float, new: float) -> float` | Percent change: `(new-old)/old` |
| `is_within_pct` | `(a: float, b: float, pct: float) -> bool` | True if `|a-b|/b <= pct` |
| `safe_divide` | `(num: float, den: float, default: float = 0.0) -> float` | Division; returns default if den is 0 |
| `round_price` | `(price: float, decimals: int = 2) -> float` | Rounds financial price |
| `reward_risk_ratio` | `(entry: float, target: float, stop: float, direction: str) -> float` | Calculates R:R |
| `kelly_fraction` | `(win_rate: float, avg_win: float, avg_loss: float) -> float` | Kelly criterion |
| `sharpe_ratio` | `(returns: List[float], risk_free_rate: float = 0.0) -> float` | Sharpe ratio |
| `max_drawdown` | `(equity_curve: List[float]) -> float` | Max drawdown as fraction |
| `annualised_return` | `(total_return: float, trading_days: int) -> float` | Annualised return |
| `is_valid_price` | `(price: float) -> bool` | True if positive and finite |
| `is_positive` | `(value: float) -> bool` | True if strictly > 0 |
| `format_number` | `(n: float, decimals: int = 2) -> str` | `12345.678` → `"12,345.68"` |

---

### 3.6 File Utilities (`file_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `ensure_dir` | `(path: Path) -> Path` | Creates directory tree if not exists; returns path |
| `safe_read_text` | `(path: Path, encoding: str = "utf-8") -> Optional[str]` | Reads file; returns None if missing |
| `safe_write_text` | `(path: Path, content: str, encoding: str = "utf-8") -> bool` | Atomic write via temp file |
| `append_line` | `(path: Path, line: str) -> None` | Appends single line (thread-safe via lock) |
| `rotate_file` | `(path: Path, max_files: int = 30) -> None` | Rotates log-style files |
| `file_size_bytes` | `(path: Path) -> int` | File size in bytes; 0 if not exists |
| `is_older_than` | `(path: Path, seconds: int) -> bool` | True if file mtime > seconds ago |
| `list_files` | `(directory: Path, pattern: str = "*") -> List[Path]` | Lists files matching pattern |
| `delete_file` | `(path: Path) -> bool` | Deletes file; returns True if deleted |
| `compute_md5` | `(path: Path) -> str` | MD5 hex digest of file contents |
| `safe_json_load` | `(path: Path) -> Optional[dict]` | Loads JSON file; returns None on error |
| `safe_json_dump` | `(path: Path, data: dict) -> bool` | Writes JSON with indent=2 |

---

### 3.7 Path Utilities (`path_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `get_repo_root` | `() -> Path` | Returns repository root directory |
| `get_data_dir` | `() -> Path` | Returns `data/` directory for current environment |
| `get_logs_dir` | `() -> Path` | Returns `logs/` directory |
| `get_reports_dir` | `() -> Path` | Returns `reports/` directory |
| `get_models_dir` | `() -> Path` | Returns `models/` directory |
| `get_db_path` | `(db_name: str) -> Path` | Returns full path to a named database |
| `get_csv_path` | `(name: str) -> Path` | Returns full path to a named CSV file |
| `daily_log_path` | `(component: str) -> Path` | `logs/trading_brain_2026-07-02.log` |
| `is_safe_path` | `(path: Path, base: Path) -> bool` | True if path is within base (path traversal prevention) |
| `resolve_relative` | `(relative: str) -> Path` | Resolves relative path against repo root |

---

### 3.8 JSON Utilities (`json_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `to_json` | `(obj: Any, indent: int = None) -> str` | Serialises to JSON string; handles datetime, UUID |
| `from_json` | `(s: str) -> Any` | Parses JSON string; raises `SerialisationError` on failure |
| `to_json_file` | `(path: Path, obj: Any, indent: int = 2) -> None` | Writes to file atomically |
| `from_json_file` | `(path: Path) -> Any` | Reads from file; raises `SerialisationError` if missing/invalid |
| `safe_get` | `(d: dict, *keys: str, default: Any = None) -> Any` | Nested dict access with default |
| `merge_dicts` | `(base: dict, override: dict) -> dict` | Deep merge; override wins on conflict |
| `flatten_dict` | `(d: dict, sep: str = ".") -> dict` | `{"a": {"b": 1}}` → `{"a.b": 1}` |
| `filter_none` | `(d: dict) -> dict` | Removes keys with None values |

---

### 3.9 CSV Utilities (`csv_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `append_row` | `(path: Path, row: dict, fieldnames: List[str]) -> None` | Thread-safe append to CSV |
| `read_all_rows` | `(path: Path) -> List[dict]` | Reads all rows as dicts |
| `read_today_rows` | `(path: Path, date_field: str) -> List[dict]` | Reads rows where date_field is today |
| `count_rows` | `(path: Path) -> int` | Count rows without loading all into memory |
| `write_header` | `(path: Path, fieldnames: List[str]) -> None` | Writes header if file is empty |
| `validate_csv` | `(path: Path, required_fields: List[str]) -> bool` | Validates CSV structure |
| `to_dataframe` | `(path: Path) -> Any` | Reads CSV into pandas DataFrame (optional dep) |

---

### 3.10 Encryption and Hashing Utilities (`crypto_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `sha256_hex` | `(data: str) -> str` | SHA-256 hex digest |
| `sha256_file` | `(path: Path) -> str` | SHA-256 of file contents |
| `md5_hex` | `(data: str) -> str` | MD5 hex digest (for non-security checksums only) |
| `hmac_sha256` | `(key: str, message: str) -> str` | HMAC-SHA256 for API signature verification |
| `generate_token` | `(length: int = 32) -> str` | Cryptographically secure random token |
| `constant_time_compare` | `(a: str, b: str) -> bool` | Timing-safe string comparison |
| `mask_for_log` | `(value: str) -> str` | Returns `"***"` for logging secrets |

**Security rule:** `md5_hex` is never used for password hashing or security-sensitive operations. It is provided solely for file integrity checksums.

---

### 3.11 Validation Utilities (`validation_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `is_valid_symbol` | `(symbol: str) -> bool` | True if valid NSE/BSE symbol format |
| `is_valid_uuid4` | `(s: str) -> bool` | True if valid UUID4 string |
| `is_valid_email` | `(s: str) -> bool` | True if valid email format |
| `is_valid_url` | `(s: str) -> bool` | True if valid HTTP/HTTPS URL |
| `is_valid_iso_date` | `(s: str) -> bool` | True if valid ISO 8601 date string |
| `is_valid_iso_timestamp` | `(s: str) -> bool` | True if valid ISO 8601 datetime string |
| `is_valid_price` | `(price: float) -> bool` | True if finite and positive |
| `is_valid_quantity` | `(qty: int) -> bool` | True if positive integer |
| `is_valid_percentage` | `(pct: float) -> bool` | True if 0.0 ≤ pct ≤ 1.0 |
| `is_valid_conviction` | `(score: float) -> bool` | True if 0.0 ≤ score ≤ 10.0 |
| `is_valid_direction` | `(direction: str) -> bool` | True if "LONG" or "SHORT" |
| `is_valid_regime` | `(regime: str) -> bool` | True if in `CoreConstants.KNOWN_REGIMES` |
| `is_valid_strategy_id` | `(sid: str) -> bool` | True if matches strategy ID pattern |
| `assert_not_none` | `(value, name: str) -> None` | Raises `ValidationError` if None |
| `assert_positive` | `(value: float, name: str) -> None` | Raises `ValidationError` if ≤ 0 |
| `assert_in_range` | `(value, lo, hi, name: str) -> None` | Raises `ValidationError` if out of range |
| `assert_non_empty` | `(s: str, name: str) -> None` | Raises `ValidationError` if empty/whitespace |

---

### 3.12 Retry Utilities (`retry_utils.py`)

| Class/Function | Signature | Description |
|---|---|---|
| `RetryPolicy` | `(max_attempts, delay_seconds, backoff, exceptions)` | Configurable retry policy |
| `RetryPolicy.execute` | `(fn: Callable, *args, **kwargs) -> Any` | Executes with retry; raises on exhaustion |
| `with_retry` | `(max_attempts: int, delay: float, backoff: float = 2.0)` | Decorator for retry |
| `DEFAULT_RETRY_POLICY` | — | 3 attempts, 1s delay, 2x backoff, catches `IOError` |
| `FEED_RETRY_POLICY` | — | 2 attempts, 0.5s delay, no backoff, catches `FeedTimeoutError` |
| `DATABASE_RETRY_POLICY` | — | 3 attempts, 0.1s delay, 1.5x backoff, catches `DatabaseError` |
| `NO_RETRY_POLICY` | — | 1 attempt; for operations that must not retry |

**RetryPolicy parameters:**

| Parameter | Type | Description |
|---|---|---|
| `max_attempts` | `int` | Maximum number of attempts (1 = no retry) |
| `delay_seconds` | `float` | Initial delay between attempts |
| `backoff_multiplier` | `float` | Multiplier for delay after each failure (1.0 = constant) |
| `max_delay_seconds` | `float` | Cap on delay (prevents infinite growth) |
| `retriable_exceptions` | `tuple[Type[Exception]]` | Which exception types trigger a retry |
| `on_retry` | `Optional[Callable]` | Callback invoked before each retry attempt |

---

### 3.13 Caching Utilities (`cache_utils.py`)

| Class/Function | Description |
|---|---|
| `TTLCache` | Simple in-memory dictionary cache with per-entry TTL |
| `TTLCache.get` | `(key: str) -> Optional[T]` — Returns value if not stale |
| `TTLCache.set` | `(key: str, value: T, ttl_seconds: int)` — Stores with TTL |
| `TTLCache.invalidate` | `(key: str)` — Explicitly removes entry |
| `TTLCache.invalidate_all` | `()` — Clears all entries |
| `TTLCache.is_stale` | `(key: str) -> bool` — True if entry is expired |
| `TTLCache.size` | `() -> int` — Current entry count |
| `cached_property` | Decorator: property computed once and cached per-instance |
| `lru_cache_with_ttl` | Decorator: LRU cache with TTL expiry (thread-safe) |

**Cache design constraints:**
- All caches are in-memory only (no persistent cache in this system)
- TTL is always required; no cache entry is eternal
- Cache access is thread-safe via `threading.RLock`
- Cache misses do not raise exceptions; they return `None` or trigger a refresh callback

---

### 3.14 Serialisation Utilities (`serialisation_utils.py`)

| Function | Signature | Description |
|---|---|---|
| `serialise_dto` | `(dto: BaseDTO) -> dict` | Converts DTO to serialisable dict |
| `deserialise_dto` | `(d: dict, dto_class: Type[T]) -> T` | Constructs DTO from dict |
| `serialise_datetime` | `(dt: datetime) -> str` | ISO 8601 UTC string |
| `deserialise_datetime` | `(s: str) -> datetime` | Parses ISO 8601 to UTC datetime |
| `serialise_enum` | `(e: Enum) -> str` | Returns enum's `.value` |
| `deserialise_enum` | `(s: str, enum_class: Type[E]) -> E` | Constructs enum from string |
| `to_json_safe` | `(obj: Any) -> Any` | Recursively converts to JSON-serialisable types |
| `from_json_safe` | `(data: Any, target_type: Type[T]) -> T` | Deserialises with type coercion |

---

### 3.15 Registry and Factory Utilities (`registry.py`)

| Class | Description |
|---|---|
| `Registry[T]` | Generic typed registry mapping names to implementations |
| `Registry.register` | `(name: str, item: T)` — Registers an item |
| `Registry.get` | `(name: str) -> T` — Retrieves by name; raises if not found |
| `Registry.get_or_none` | `(name: str) -> Optional[T]` — Returns None if not found |
| `Registry.all` | `() -> List[T]` — Returns all registered items |
| `Registry.names` | `() -> List[str]` — Returns all registered names |
| `Registry.is_registered` | `(name: str) -> bool` — Check registration |
| `Factory[T]` | Generic factory mapping names to factory callables |
| `Factory.register_creator` | `(name: str, creator: Callable[[], T])` — Registers creator |
| `Factory.create` | `(name: str) -> T` — Calls creator and returns new instance |
| `PluginLoader` | Discovers and loads plugins from a directory |
| `PluginLoader.load_all` | `(directory: Path, base_class: Type[T]) -> List[T]` |
| `PluginLoader.validate_plugin` | `(plugin: Any, base_class: Type) -> bool` |

---

## PART IV — ERROR FRAMEWORK

### 4.1 Error Framework Philosophy

The error framework is the system's policy for what happens when things go wrong. In a real-money trading system, errors have consequences. A swallowed exception can mean an orphaned position. A cryptic error message can mean an hour of debugging during market hours. An unclassified exception can mean the wrong recovery strategy is applied.

The error framework prevents these consequences through four mechanisms:

| Mechanism | Description |
|---|---|
| **Typed exceptions** | Every error type is a named class with a known meaning. No anonymous `Exception` |
| **Contextual enrichment** | Every exception carries `cycle_id`, `layer_name`, and diagnostic context |
| **Recoverability classification** | Every exception declares whether the caller should retry |
| **Recovery policies** | Named recovery policies declare how each error class is handled |

---

### 4.2 Complete Exception Hierarchy

```
TradingBrainError                              ← Root of all custom exceptions
│
├── ConfigurationError                         ← Configuration problems
│   ├── MissingConfigError                     ← Required key not found
│   ├── InvalidConfigError                     ← Value out of range or wrong type
│   ├── SecretNotFoundError                    ← Required secret missing
│   └── ConfigValidationError                  ← Schema validation failure
│
├── ValidationError                            ← Input validation failures
│   ├── FieldValidationError                   ← Specific field failed constraint
│   ├── SymbolValidationError                  ← Invalid market symbol format
│   ├── PriceValidationError                   ← Invalid price (negative, NaN, inf)
│   ├── QuantityValidationError                ← Invalid order quantity
│   └── RequestValidationError                 ← Incoming request fails schema
│
├── DataError                                  ← Data quality and availability
│   ├── FeedUnavailableError                   ← No data source is available
│   ├── FeedTimeoutError                       ← Data source timed out
│   ├── FeedPartialError                       ← Feed returned incomplete data
│   ├── StaleDataError                         ← Cached data is too old
│   ├── MalformedDataError                     ← Data structure invalid
│   ├── InsufficientHistoryError               ← Not enough bars for analysis
│   └── DataIntegrityError                     ← Data consistency violation
│
├── TradingError                               ← Trading business logic errors
│   ├── KillSwitchActiveError                  ← Kill-switch is set; no orders
│   ├── InsufficientCapitalError               ← Insufficient budget for position
│   ├── RiskApprovalExpiredError               ← Risk approval TTL exceeded
│   ├── RiskApprovalAbsentError                ← Order submitted without approval
│   ├── PositionLimitExceededError             ← Max open positions reached
│   ├── DailyLossLimitReachedError             ← Daily loss threshold crossed
│   ├── StopLossAbsentError                    ← Hypothesis missing stop-loss
│   ├── ConvictionBelowThresholdError          ← Conviction score < threshold
│   ├── MarketClosedError                      ← Attempted order outside hours
│   └── OrderRejectedError                     ← Broker rejected order
│
├── StrategyError                              ← Strategy lifecycle errors
│   ├── StrategyNotFoundError                  ← Unknown strategy ID
│   ├── StrategyDisabledError                  ← Strategy auto-disabled
│   ├── StrategyEvolutionError                 ← Strategy evolution failure
│   ├── BacktestFailedError                    ← Backtesting run error
│   ├── BacktestInsufficientDataError          ← Not enough data for backtest
│   └── PromotionGateFailedError               ← Strategy failed promotion criteria
│
├── BrokerError                                ← Broker communication
│   ├── BrokerAuthenticationError              ← Broker auth failed
│   ├── BrokerTokenExpiredError                ← API token expired
│   ├── BrokerAPIError                         ← Unexpected broker API response
│   ├── BrokerRateLimitError                   ← Too many requests
│   ├── BrokerConnectionError                  ← Network connection to broker failed
│   └── OrderNotFoundError                     ← Order ID unknown to broker
│
├── SecurityError                              ← Security policy violations
│   ├── UnauthorisedAccessError                ← Access denied (e.g., Telegram)
│   ├── TokenValidationError                   ← Token format invalid
│   ├── SecretExposureError                    ← Secret value detected in output
│   └── PathTraversalError                     ← Attempted path traversal attack
│
├── InfrastructureError                        ← Infrastructure failures
│   ├── DatabaseError                          ← SQLite operation failed
│   ├── DatabaseConnectionError                ← Cannot open database
│   ├── DatabaseMigrationError                 ← Schema migration failed
│   ├── DatabaseIntegrityError                 ← Constraint violation
│   ├── FileSystemError                        ← File read/write operation failed
│   ├── SchedulerError                         ← Job scheduling failure
│   ├── NotificationDeliveryError              ← Telegram message failed
│   └── HealthCheckError                       ← Health check could not run
│
└── SystemError                                ← System-level failures
    ├── LayerTimeoutError                      ← Layer exceeded CRIT latency
    ├── LifecycleError                         ← Invalid lifecycle state transition
    ├── DependencyNotRegisteredError           ← Dependency injection miss
    ├── CircularDependencyError                ← Import cycle detected
    └── FrameworkViolationError                ← Framework contract violated
```

---

### 4.3 Exception Classification Matrix

| Exception Category | Recoverable | Retry Policy | Kill-Switch | Alert Level |
|---|---|---|---|---|
| `ConfigurationError` | No | No retry | System exits | ERROR + Telegram |
| `ValidationError` | No | No retry | No | WARNING |
| `DataError.FeedUnavailableError` | Yes | `FEED_RETRY_POLICY` | If all feeds fail | ERROR |
| `DataError.FeedTimeoutError` | Yes | `FEED_RETRY_POLICY` | No | WARNING |
| `DataError.StaleDataError` | Yes | Refresh cache | No | WARNING |
| `TradingError.KillSwitchActiveError` | No | No retry | Already active | INFO |
| `TradingError.InsufficientCapitalError` | No | No retry | No | WARNING |
| `TradingError.DailyLossLimitReachedError` | No | No retry | Activate | ERROR + Telegram |
| `TradingError.ConvictionBelowThresholdError` | No | No retry | No | INFO |
| `StrategyError.StrategyDisabledError` | No | No retry | No | INFO |
| `BrokerError.BrokerTokenExpiredError` | Yes | Token refresh | No | WARNING + Telegram |
| `BrokerError.BrokerRateLimitError` | Yes | Delay + retry | No | WARNING |
| `SecurityError.UnauthorisedAccessError` | No | No retry | No | WARNING + Audit |
| `InfrastructureError.DatabaseError` | Yes | `DATABASE_RETRY_POLICY` | If persistent | ERROR |
| `SystemError.LayerTimeoutError` | Yes | Skip layer | Cycle aborted | ERROR |
| `SystemError.LifecycleError` | No | No retry | System exits | CRITICAL |

---

### 4.4 Business Error Policy

Business errors represent conditions that the business logic itself declares as invalid. They are expected in normal operation (e.g., conviction below threshold is a normal rejection). They are never unexpected.

**Business error handling rules:**

| Rule | Description |
|---|---|
| BE-01 | Business errors are logged at INFO or WARNING level — never ERROR |
| BE-02 | Business errors do not activate the kill-switch |
| BE-03 | Business errors do not trigger Telegram alerts |
| BE-04 | Business errors are counted in the cycle's business metrics |
| BE-05 | Business errors never propagate beyond the layer that raised them |
| BE-06 | Business errors carry the hypothesis or decision context that led to them |

---

### 4.5 System Error Policy

System errors represent conditions that the infrastructure or framework did not expect. They require human attention.

**System error handling rules:**

| Rule | Description |
|---|---|
| SE-01 | System errors are logged at ERROR or CRITICAL level |
| SE-02 | System errors trigger a Telegram alert to the Human Principal |
| SE-03 | System errors are recorded to the audit log |
| SE-04 | Recoverable system errors trigger the appropriate retry policy |
| SE-05 | Non-recoverable system errors abort the current cycle |
| SE-06 | Non-recoverable system errors in a critical component trigger controlled shutdown |
| SE-07 | System errors include full stack trace in the log (but never in Telegram alerts) |
| SE-08 | Five consecutive system errors of the same type in one cycle activate the kill-switch |

---

### 4.6 Recovery Policy

The framework defines named recovery policies. Each recoverable error class is associated with exactly one recovery policy.

| Policy Name | Max Attempts | Delay | Backoff | On Exhaustion |
|---|---|---|---|---|
| `NO_RECOVERY` | 1 | — | — | Raise exception |
| `IMMEDIATE_RETRY` | 2 | 0s | 1.0x | Raise exception |
| `BRIEF_RETRY` | 3 | 0.5s | 1.5x | Raise exception |
| `STANDARD_RETRY` | 3 | 1.0s | 2.0x | Raise exception |
| `PATIENT_RETRY` | 5 | 2.0s | 2.0x, max 30s | Raise exception |
| `FEED_RETRY` | 2 | 0.5s | 1.0x | Failover to next feed |
| `BROKER_TOKEN_REFRESH` | 1 | 0s | — | Refresh token; retry original |
| `DATABASE_RETRY` | 3 | 0.1s | 1.5x | Raise `DatabaseError` |
| `LAYER_SKIP` | 1 | 0s | — | Skip layer; log and continue cycle |

---

### 4.7 Circuit Breaker

The circuit breaker prevents a repeatedly failing component from being called continuously.

**Circuit Breaker States:**

```
CLOSED (normal operation)
    │
    │ failure_count >= threshold
    ▼
OPEN (calls blocked)
    │
    │ after timeout_seconds
    ▼
HALF_OPEN (one probe call allowed)
    │                    │
    │ probe succeeds      │ probe fails
    ▼                    ▼
CLOSED              OPEN (reset timer)
```

| Parameter | Default | Description |
|---|---|---|
| `failure_threshold` | 5 | Consecutive failures before OPEN |
| `timeout_seconds` | 60 | Time in OPEN before HALF_OPEN probe |
| `success_threshold` | 2 | Successes in HALF_OPEN to return to CLOSED |

**Circuit breakers in the system:**

| Circuit | Component | Threshold |
|---|---|---|
| Yahoo Feed | `YahooFeed` | 3 failures → OPEN for 30s |
| Dhan Feed | `DhanFeed` | 5 failures → OPEN for 60s |
| Telegram | `TelegramBot` | 5 failures → OPEN for 300s |
| Database write | `DatabaseService` | 3 failures → OPEN for 10s |

---

### 4.8 Error Logging Standards

Every caught exception is logged following this pattern:

| Field | Content |
|---|---|
| Level | `ERROR` (system errors), `WARNING` (business/recoverable errors) |
| Logger | `package.module` |
| Message | `"<action> failed: <short reason>"` |
| Cycle ID | From `ApplicationContext.current().cycle_id` |
| Layer | From `ApplicationContext.current().caller_layer` |
| Exception type | Full class name |
| Error code | Machine-readable code from exception |
| Stack trace | Always included for ERROR level; never for WARNING |
| Sensitive data | Masked before logging |

---

## PART V — CONFIGURATION FRAMEWORK

### 5.1 Configuration Framework Overview

The configuration framework governs how all configuration values are defined, validated, accessed, and changed in the AI Trading Brain. It implements a four-tier hierarchy where each tier can override the tier below it.

**Configuration Hierarchy:**

```
Tier 4: Runtime Overrides (Telegram bot commands, in-memory only)
             │ (highest priority — wins over all below)
             ▼
Tier 3: Environment Variables (secrets, deployment-specific values)
             │
             ▼
Tier 2: Application Config File (config.py — operational constants)
             │
             ▼
Tier 1: Core Constants (CoreConstants — immutable system invariants)
             │ (lowest priority)
```

When looking up any configuration value, the `ConfigurationManager` checks each tier from top to bottom and returns the first non-None value found.

---

### 5.2 Tier 1: Core Constants

Core constants are defined in `src/common/constants.py`. They are:
- Hard-coded at compile time
- Never overridable at runtime
- Never loaded from files or environment
- Never exposed to external configuration systems

Examples: `MIN_LAYER_NUMBER = 1`, `DIRECTION_LONG = "LONG"`, `MARKET_OPEN_HOUR_IST = 9`

---

### 5.3 Tier 2: Application Configuration (`config.py`)

The application configuration file is the primary file for operational constants. It:
- Loads environment variable-sourced values at import time
- Provides defaults for all non-secret configuration values
- Is the single file an engineer edits to change system behaviour
- Must pass `validate_config()` on every startup

**Configuration file structure:**

```
config.py
│
├── [1] Latency Configuration
├── [2] Schedule Configuration
│   ├── Pre-market slot (08:45 IST)
│   ├── Market-open slot (09:15 IST)
│   ├── 10 intraday slots (every 45 minutes)
│   ├── EOD slot (15:45 IST)
│   └── Maintenance slot (22:00 IST)
├── [3] Risk Parameters
├── [4] Capital Parameters
├── [5] Data Feed Parameters
├── [6] Strategy Parameters
├── [7] Debate Parameters
├── [8] Monitoring Parameters
├── [9] Symbol Maps
│   ├── GLOBAL_SYMBOL_MAP (S&P, Nikkei, VIX → Yahoo tickers)
│   ├── NSE_INDEX_MAP (NIFTY, BANKNIFTY → Yahoo tickers)
│   └── SECTOR_ETF_MAP (sector names → ETF tickers)
└── [10] Path Configuration
```

---

### 5.4 Tier 3: Environment Variables

Environment variables carry:
- All secrets (API keys, tokens, passwords)
- Deployment-specific values (database paths, log levels, environment name)
- Feature flag overrides

**Environment variable naming convention:** `UPPER_SNAKE_CASE`, prefixed by system or broker name.

**Complete environment variable registry:**

| Variable | Required | Default | Description |
|---|---|---|---|
| `TRADING_ENV` | No | `development` | Environment type |
| `PAPER_TRADING` | No | `true` | Paper/live mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `DHAN_ACCESS_TOKEN` | In production | None | Dhan API token |
| `DHAN_CLIENT_ID` | In production | None | Dhan client ID |
| `TELEGRAM_BOT_TOKEN` | In production | None | Telegram bot token |
| `TELEGRAM_CHAT_ID` | In production | None | Authorised chat ID |
| `DB_PATH` | No | `data/trading_brain.db` | Primary database path |
| `TELEMETRY_DB_PATH` | No | `data/telemetry.db` | Telemetry database |
| `PAPER_TRADES_CSV` | No | `data/paper_trades.csv` | Paper trade journal |
| `AUDIT_LOG_PATH` | No | `data/audit.log` | Audit log path |
| `LOG_DIR` | No | `logs/` | Log file directory |
| `DATA_DIR` | No | `data/` | Data directory root |
| `REPORTS_DIR` | No | `reports/` | Reports directory |

---

### 5.5 Tier 4: Runtime Overrides

Runtime overrides are in-memory configuration changes made while the process is running. They:
- Take highest precedence over all other tiers
- Are never persisted to disk
- Are lost on process restart
- Are set only via the Telegram bot (`/flag` command) or internal system logic

**Operations that create runtime overrides:**

| Trigger | Override Created |
|---|---|
| Telegram `/kill` command | `kill_switch_active = True` |
| Telegram `/resume` command | `kill_switch_active = False` |
| VIX crosses threshold | `kill_switch_active = True` (from `RiskGuardian`) |
| Daily loss limit crossed | `kill_switch_active = True` (from `RiskGuardian`) |
| Telegram `/flag <name> <value>` | Any feature flag toggled |

---

### 5.6 Feature Flags

Feature flags are boolean values that enable or disable specific system capabilities.

| Flag | Tier | Default | Who Sets It |
|---|---|---|---|
| `PAPER_TRADING` | T3 (env var) | `true` | Human Principal via deploy |
| `TELEGRAM_ENABLED` | T3 (env var) | `true` | Human Principal via deploy |
| `CONTINUOUS_SCAN_ENABLED` | T2 (config.py) | `true` | Engineering |
| `OPTIONS_SCANNING_ENABLED` | T2 (config.py) | `false` | Engineering |
| `ARBITRAGE_SCANNING_ENABLED` | T2 (config.py) | `false` | Engineering |
| `MONTE_CARLO_ENABLED` | T2 (config.py) | `true` | Engineering |
| `STRESS_TEST_ENABLED` | T2 (config.py) | `true` | Engineering |
| `WALK_FORWARD_DAILY` | T2 (config.py) | `true` | Engineering |
| `AUTO_DISABLE_STRATEGIES` | T2 (config.py) | `true` | Engineering |
| `DEBUG_CYCLE_TIMING` | T4 (runtime) | `false` | Human Principal via Telegram |
| `EMERGENCY_MODE` | T4 (runtime) | `false` | RiskGuardian (auto-set) |

---

### 5.7 Configuration Validation

All configuration values are validated at startup by `ConfigurationValidator` (`src/config/validator.py`). Validation occurs in five passes:

| Pass | What Is Checked | Failure Action |
|---|---|---|
| Pass 1: Presence | All required environment variables are non-empty | Log error; exit |
| Pass 2: Type | All numeric values are parseable as the declared type | Log error; exit |
| Pass 3: Range | All numeric values are within declared bounds | Log error; exit |
| Pass 4: Dependencies | Inter-variable dependencies (e.g., if Dhan token present, client ID must also be present) | Log error; exit |
| Pass 5: Paths | Declared directories exist and are writable | Create directories if possible; log error if not |

**Validation schema fields:**

| Schema Field | Description |
|---|---|
| `name` | Config key name |
| `required` | Whether the key must be present |
| `type` | Python type for coercion |
| `min_value` | Minimum allowed numeric value |
| `max_value` | Maximum allowed numeric value |
| `allowed_values` | Enumerated valid string values |
| `depends_on` | Other keys that must also be set |
| `default` | Value if not set (for non-required keys) |
| `is_secret` | Whether to mask in diagnostics output |

---

### 5.8 Hot Reload

The `ConfigurationManager` supports hot-reload of Tier 3 (environment variable) values. Hot reload:
- Re-reads all environment variables from the process environment
- Updates non-secret, non-path values immediately
- Does NOT restart any services (services read config through the manager on each use)
- Logs all changed values at INFO level (secrets are masked)
- Is triggered by the Telegram `/reload_config` command

**Values NOT hot-reloaded:**
- `DB_PATH` and other path variables (would require database reconnection)
- `DHAN_ACCESS_TOKEN` (token rotation has its own dedicated flow)
- `TELEGRAM_BOT_TOKEN` (bot restart required)
- `TRADING_ENV` (requires full restart)

---

### 5.9 Configuration Access Pattern

All modules access configuration through one of two patterns:

**Pattern A — At construction (recommended for stable values):**
The component reads all its config values in `_do_initialise()` and stores them as instance attributes. This avoids repeated dictionary lookups during hot paths.

**Pattern B — At use (required for hot-reloadable values):**
The component calls `self.config.get("KEY")` on every use. Required for feature flags and any value that may change at runtime.

**Forbidden pattern:** Accessing `config.py` values by direct attribute reference inside layer modules (e.g., `import config; config.LAYER_LATENCY_WARN_MS`). All access must go through `ConfigurationManager`.

---

### 5.10 Configuration Version Management

When a configuration key is changed or removed:

| Change Type | Process |
|---|---|
| Add new key | Add to `config.py`; add to schema; add validation; update `README.md` in `src/config/` |
| Change default | Update in `config.py`; update schema; note in commit message and CHANGELOG |
| Change valid range | Update schema; update `copilot-instructions.md` if a threshold is affected |
| Rename key | Old name becomes an alias (reads same value); new name is added; alias removed after one release cycle |
| Remove key | Add to deprecated list in schema; emit `DeprecationWarning` for one release; remove in next MAJOR |

---

## PART VI — DEPENDENCY MANAGEMENT

### 6.1 Dependency Management Philosophy

Dependency management is the practice of controlling how components obtain their collaborators. Without a dependency management strategy, components acquire their own dependencies — leading to tight coupling, hidden dependencies, and untestable code.

The Core Framework's dependency management strategy is based on four principles:
1. **Inversion of control:** Components do not construct their dependencies — they declare them.
2. **Explicit registration:** All services are registered in one place (`DependencyManager`) at startup.
3. **Interface-based coupling:** Components depend on interfaces (abstract classes), not concrete implementations.
4. **Testability first:** Any component can be tested in isolation by providing mock implementations.

---

### 6.2 Dependency Injection

Dependency injection is the mechanism by which components receive their dependencies from an external source rather than constructing them internally.

**Injection Patterns:**

| Pattern | When Used | Example |
|---|---|---|
| **Constructor injection** | Mandatory dependencies (always required) | `OrderManager(feed: BaseFeed, config: ConfigurationManager)` |
| **Property injection** | Optional or framework-provided dependencies | `self.logger = LoggingFactory.get_logger(__name__)` |
| **Method injection** | Per-call dependencies | `execute(context: ApplicationContext)` |

**Rules:**
- Constructor injection is preferred over property injection
- No component uses `DependencyManager.resolve()` inside its `execute()` method (resolve at construction time)
- The `ApplicationContext` is always method-injected (it is per-cycle, not per-component)

---

### 6.3 Service Registry

The `ServiceRegistry` is a specialised dictionary mapping interface types to their registered implementations. It is the single source of truth for all resolvable dependencies.

**Registration Map (at system startup):**

| Interface | Registered Implementation | Lifecycle |
|---|---|---|
| `BaseFeed` (primary) | `DhanFeed` | Singleton |
| `BaseFeed` (fallback) | `YahooFeed` | Singleton |
| `ConfigurationManager` | `ConfigurationManager` | Singleton |
| `SecretsManager` | `SecretsManager` | Singleton |
| `EnvironmentManager` | `EnvironmentManager` | Singleton |
| `LoggingService` | `LoggingService` | Singleton |
| `DatabaseService` | `DatabaseService` | Singleton |
| `AuditService` | `AuditService` | Singleton |
| `MetricsCollector` | `MetricsCollector` | Singleton |
| `EventBus` | `InProcessEventBus` | Singleton |
| `HealthCheckService` | `HealthCheckService` | Singleton |
| `BaseScheduler` | `APSchedulerAdapter` | Singleton |
| `BaseNotifier` | `TelegramNotifier` | Singleton |
| `DataFeedManager` | `DataFeedManager` | Singleton |
| `StrategyRegistry` | `StrategyRegistry` | Singleton |
| `AgentRegistry` | `AgentRegistry` | Singleton |

---

### 6.4 Service Lifecycle Classification

| Lifecycle Type | Description | Number of Instances | Cleanup Required |
|---|---|---|---|
| **Singleton** | One instance shared by all consumers | 1 | Yes — `stop()` called at shutdown |
| **Transient** | New instance on every `resolve()` call | One per call | No — garbage collected |
| **Scoped** | One instance per scope (e.g., per-cycle) | One per cycle | Yes — at cycle end |

**Current lifecycle assignments:**

| Component | Lifecycle |
|---|---|
| All services (feeds, DB, audit, metrics) | Singleton |
| All operational layer engines | Singleton |
| `ApplicationContext` | Scoped (per cognitive cycle) |
| `EngineResult` | Transient (created per layer execution) |
| `AgentOpinion` | Transient (created per debate agent analysis) |
| `ValidationResult` | Transient |
| `HealthStatus` | Transient (fetched fresh on each request) |

---

### 6.5 Singleton Policy

Singletons are the primary service lifecycle in this system. The singleton policy:

| Rule | Description |
|---|---|
| SNG-01 | Singletons are never instantiated directly by consuming code |
| SNG-02 | Singletons are registered once at startup in `MasterOrchestrator._register_services()` |
| SNG-03 | Singletons are accessed via typed getter functions: `get_feed_manager()`, `get_performance_tracker()` |
| SNG-04 | Getter functions are defined in the owning package's `__init__.py` |
| SNG-05 | Getter functions return the registered singleton or raise `DependencyNotRegisteredError` |
| SNG-06 | Singletons must implement `LifecycleAware` to participate in managed shutdown |
| SNG-07 | Thread safety is the singleton's own responsibility (via `threading.Lock`) |
| SNG-08 | Singletons hold no per-request or per-cycle state (that belongs in `ApplicationContext`) |

---

### 6.6 Factory Pattern

Factories create new instances of a component on demand, without the caller knowing the concrete type. Factories are used for:

| Use Case | Factory | Creates |
|---|---|---|
| Create order records | `OrderRecordFactory` | `OrderRecord` DTO instances |
| Create debate contexts | `AgentContextFactory` | `AgentContext` instances per analysis |
| Create engine results | `EngineResultFactory` | `EngineResult` instances per layer execution |
| Create audit records | `AuditRecordFactory` | `AuditRecord` instances |
| Create validation results | `ValidationResultFactory` | `ValidationResult` instances |

Factories are registered in the `DependencyManager` as transient services.

---

### 6.7 Plugin Loader

The `PluginLoader` is a specialised factory that discovers and loads plugin implementations from a directory. It is used for:
- Loading evolved strategy JSON files from `strategy_lab/evolved_strategies/`
- Loading debate agent prompts from `prompts/debate_agent_prompts/`

**Plugin loading process:**

| Step | Action |
|---|---|
| 1 | Scan designated directory for files matching expected pattern |
| 2 | For each file: load and validate against the plugin schema |
| 3 | For valid plugins: instantiate and register in the appropriate registry |
| 4 | For invalid plugins: log at WARNING level; skip; continue |
| 5 | Report total loaded/skipped count to `MetricsCollector` |

---

## PART VII — FRAMEWORK LIFECYCLE

### 7.1 Lifecycle Overview

The framework lifecycle defines the ordered sequence of events from process start to process stop. It is the most critical sequence in the system — every subsequent behaviour depends on the lifecycle completing correctly.

```
                    ┌─────────────────────────────────────────────┐
                    │              SYSTEM LIFECYCLE                │
                    └──────────────────────┬──────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────┐
                    │               BOOT PHASE                     │
                    │  Parse CLI → Load env → Validate config      │
                    └──────────────────────┬──────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────┐
                    │          INITIALISATION PHASE                │
                    │  Secrets → Logging → DB → Feeds → Services  │
                    └──────────────────────┬──────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────┐
                    │            REGISTRATION PHASE                │
                    │  Register services → Register modules        │
                    │  Register agents → Register strategies       │
                    └──────────────────────┬──────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────┐
                    │             HEALTH CHECK PHASE               │
                    │  Check all registered services               │
                    │  Check data feed availability                │
                    │  Check database accessibility                │
                    └──────────────────────┬──────────────────────┘
                                           │
                    ┌──────────────────────▼──────────────────────┐
                    │               READY STATE                    │
                    │  All green → Log "SYSTEM READY" banner       │
                    │  Start scheduler → Begin cognitive cycles    │
                    └──────────────────────┬──────────────────────┘
                                           │
                            (Running indefinitely)
                                           │
                    ┌──────────────────────▼──────────────────────┐
                    │             SHUTDOWN PHASE                   │
                    │  SIGTERM → Drain → Stop services → Exit 0   │
                    └─────────────────────────────────────────────┘
```

---

### 7.2 Boot Phase

The boot phase runs before any framework component is initialised. It is the responsibility of `main.py`.

| Step | Action | Failure |
|---|---|---|
| B-01 | Parse command-line arguments: `--paper`, `--telegram`, `--status` | Print usage; exit 1 |
| B-02 | Set `PAPER_TRADING` environment variable from `--paper` flag | — |
| B-03 | Load `.env` file if present (development only) | Log warning; continue |
| B-04 | Call `validate_config()` | Log all failures; exit 1 |
| B-05 | Validate all required secrets present | Log which secrets are missing; exit 1 |
| B-06 | Set process title (`ai-trading-brain`) | Silently ignored if not supported |
| B-07 | Register SIGTERM / SIGINT signal handlers | Log warning if not supported |

The boot phase takes < 1 second in all environments.

---

### 7.3 Initialisation Phase

The initialisation phase initialises all framework services in priority order. The `LifecycleManager` calls `_do_initialise()` on each registered component in ascending priority.

**Initialisation order:**

| Priority | Component | What Happens |
|---|---|---|
| 1 | `SecretsManager` | Loads all secrets from environment; validates non-empty |
| 2 | `EnvironmentManager` | Detects current environment; sets paths |
| 3 | `ConfigurationManager` | Loads config.py values; validates schema |
| 4 | `LoggingService` | Configures root logger, file handlers, rotation |
| 5 | `DatabaseService` | Opens `trading_brain.db` and `telemetry.db`; applies pending migrations |
| 6 | `AuditService` | Opens audit log file for append |
| 7 | `MetricsCollector` | Initialises in-memory metrics registry |
| 8 | `EventBus` | Initialises pub/sub registry |
| 9 | `DataFeedManager` | Tests data feed availability; selects primary |
| 10 | All operational layers (1–17) | Each engine calls `_do_initialise()` |
| 20 | `TelegramBot` | Authenticates with Telegram API |
| 99 | `APScheduler` | Loads all job definitions (does not start) |

**Failure policy:** If any component at priority 1–9 fails to initialise, the process exits immediately with an ERROR log. Layer failures (priority 10) are logged and the layer is marked UNAVAILABLE for the first cycle.

---

### 7.4 Registration Phase

After initialisation, all discoverable components are registered in their respective registries.

| Registration | What Is Registered | Registry |
|---|---|---|
| Layer registration | All 17 layer engines | `LayerRegistry` |
| Agent registration | All 62+ debate agents | `AgentRegistry` |
| Strategy registration | All evolved strategy definitions | `StrategyRegistry` |
| Feed registration | All feed adapters in priority order | `DataFeedManager.feed_priority_list` |
| Job registration | All 10 scheduler slots | `APScheduler` job store |

---

### 7.5 Health Check Phase

Before entering the ready state, the system performs a pre-flight health check on all registered components.

**Health Check Results:**

| Status | Meaning | Action |
|---|---|---|
| `HEALTHY` | Component is fully operational | Continue |
| `DEGRADED` | Component is operational with reduced capability | Log WARNING; continue |
| `UNAVAILABLE` | Component is not operational | Log ERROR; Telegram alert |
| `CRITICAL` | Component failure prevents safe operation | Log CRITICAL; exit 1 |

**Critical components** (UNAVAILABLE → exit 1):
- `DatabaseService`
- `ConfigurationManager`
- `SecretsManager`
- `RiskGuardian` (Layer 9)

**Non-critical components** (UNAVAILABLE → WARNING, continue):
- `TelegramBot`
- `DhanFeed` (if `YahooFeed` is available)
- `DashboardService`
- Any layer above 9

---

### 7.6 Ready State

The ready state is reached when:
1. All critical components are HEALTHY or DEGRADED
2. At least one data feed is HEALTHY
3. The primary database is accessible
4. The scheduler is loaded with all 10 job slots

On reaching the ready state:
- A structured "SYSTEM READY" banner is logged at INFO level
- A startup notification is sent via Telegram (if enabled)
- The first cognitive cycle is executed immediately (pre-market or market-hours depending on time)
- The scheduler is started

---

### 7.7 Cognitive Cycle Lifecycle

Within the ready state, the system runs cognitive cycles. Each cycle has its own lifecycle:

```
CycleContext created (generate cycle_id)
          │
          ▼
Layer 1: GlobalIntelligence.execute(context)
          │
          ▼
Layer 2: MarketIntelligence.execute(context) [reads Layer 1 result]
          │
          ▼
Layer 3: MetaLearning.execute(context) [reads Layer 2 result]
          │
          ▼
Layers 4–10: (OpportunityEngine → Debate → Decision)
          │
          ▼
Layer 11: ExecutionEngine.execute(context) [reads approved DecisionRecord]
          │
          ▼
Layers 12–17: (Monitoring → Learning → Analytics → Control)
          │
          ▼
CycleContext cleared
Cycle telemetry written to telemetry.db
CYCLE_COMPLETED event emitted
```

**Cycle failure policy:** If a layer raises `LayerTimeoutError` or an unhandled exception, the cycle logs the error at ERROR level and continues with the next layer (skipping the failed layer). The decision to skip is logged to the `cycle_log` table.

---

### 7.8 Shutdown Phase

Shutdown is triggered by:
- SIGTERM from Docker Compose (`docker compose down`)
- SIGINT from keyboard interrupt (Ctrl+C in development)
- Critical infrastructure failure
- Human Principal's Telegram `/shutdown` command

**Shutdown sequence:**

| Step | Action | Timeout |
|---|---|---|
| S-01 | Set `shutdown_requested` flag | Immediate |
| S-02 | APScheduler pauses: no new jobs | Immediate |
| S-03 | Wait for current cycle to complete | 60 seconds max |
| S-04 | Stop all operational layers (17→1) | 5 seconds each |
| S-05 | Stop `TelegramBot` | 5 seconds |
| S-06 | Write session summary to telemetry.db | 3 seconds |
| S-07 | Stop `AuditService` (flush and close) | 3 seconds |
| S-08 | Stop `DatabaseService` (WAL checkpoint) | 10 seconds |
| S-09 | Stop `LoggingService` (flush handlers) | 2 seconds |
| S-10 | Log shutdown banner | Immediate |
| S-11 | `exit(0)` | Immediate |

---

### 7.9 Restart and Recovery

**Component restart:** The `LifecycleManager.restart_component()` stops and re-initialises a single component without stopping the rest of the system. Used when a non-critical service enters an error state.

**Full system restart:** Not available in-process. A full restart requires a Docker container restart (`docker compose restart ai-trading-brain`).

**Recovery from cycle failure:** If a cognitive cycle fails mid-execution (layer crash, not layer skip):
1. The cycle is marked as FAILED in `cycle_log`
2. The kill-switch remains in its current state (not automatically activated by cycle failure)
3. The next scheduled cycle begins normally
4. If 3 consecutive cycles fail, a Telegram alert is sent and the kill-switch is activated

---

## PART VIII — CROSS-CUTTING SERVICES

### 8.1 Cross-Cutting Services Overview

Cross-cutting services are services that every component in the system uses, regardless of its layer or responsibility. They cannot belong to any single layer — they belong to the Core Framework. Every cross-cutting service:
- Is a registered singleton in the `ServiceRegistry`
- Implements `LifecycleAware` and `HealthCheckable`
- Is available via a typed getter from `DependencyManager`
- Is thread-safe (may be called from multiple threads simultaneously)

**Cross-Cutting Services:**

| Service | Getter | Primary Consumer |
|---|---|---|
| `LoggingService` | `get_logger(name)` | All modules |
| `MonitoringService` | `get_monitoring()` | All layers |
| `AuditService` | `get_audit()` | Decision-making modules |
| `MetricsCollector` | `get_metrics()` | All services |
| `TracingService` | `get_tracer()` | All layer executions |
| `NotificationService` | `get_notifier()` | Risk guardian, trade monitor |
| `SecurityService` | `get_security()` | All boundary-crossing points |
| `HealthCheckService` | `get_health()` | Monitoring, Docker |
| `PerformanceMeasurer` | `get_perf_measurer()` | SystemMonitor |
| `DiagnosticsService` | `get_diagnostics()` | Control tower |

---

### 8.2 Logging Service

**Service:** `LoggingService`
**Owner:** Engineering Foundation

**Responsibility:** Configure and provide loggers to all modules. Manage log file rotation. Enforce log format standards.

**Log format (structured):**

```
2026-07-02T09:17:23.441+05:30 [INFO ] [execution_engine.order_manager] [cycle=CYC-a1b2c3] [layer=ExecutionEngine] Order submitted | order_id=ORD-x9y8z7 symbol=TATASTEEL direction=LONG qty=50
```

**Format fields:**

| Field | Format | Example |
|---|---|---|
| Timestamp | ISO 8601 with timezone | `2026-07-02T09:17:23.441+05:30` |
| Level | 5-char padded | `[INFO ]`, `[ERROR]`, `[DEBUG]` |
| Logger | Package.module | `[execution_engine.order_manager]` |
| Cycle ID | Short ID | `[cycle=CYC-a1b2]` |
| Layer | Layer name | `[layer=ExecutionEngine]` |
| Message | Free text | `Order submitted` |
| Key-value pairs | `key=value` | `order_id=ORD-x9y8 symbol=TATASTEEL` |

**Log handlers:**

| Handler | Destination | Level | Rotation |
|---|---|---|---|
| `FileHandler` | `logs/trading_brain_YYYY-MM-DD.log` | `DEBUG` | Daily at midnight IST |
| `AuditFileHandler` | `data/audit.log` | `AUDIT` (custom) | Never (append-only) |
| `StreamHandler` | stdout | `INFO` | — |
| `CycleHandler` | `logs/cycle_YYYY-MM-DD.log` | `DEBUG` (if enabled) | Daily |

**Logging standards (enforced by framework):**

| Standard | Description |
|---|---|
| No bare `print()` | All output goes through the logging system |
| No secrets in logs | All sensitive values masked before logging |
| Cycle ID in every log | Provided automatically by `LoggingService` if context is set |
| Error includes trace | `logger.exception()` for all ERROR-level events |
| Rate limiting | High-frequency paths use `logger.debug()` only |

---

### 8.3 Monitoring Service

**Service:** `MonitoringService` (wraps `SystemMonitor`)
**Owner:** Control Tower

**Responsibility:** Track the health and performance of all system components. Provide the `time_layer()` context manager for layer timing.

**Interface:**

| Method | Signature | Purpose |
|---|---|---|
| `time_layer` | `(layer_name: str) -> ContextManager` | Times a layer; records to telemetry; alerts on threshold breach |
| `record_cycle_start` | `(cycle_id: str)` | Records cycle start to telemetry |
| `record_cycle_end` | `(cycle_id: str, summary: CycleSummary)` | Records cycle completion |
| `record_layer_timing` | `(layer_name: str, duration_ms: int, status: str)` | Records individual layer timing |
| `get_cycle_health` | `(last_n: int = 10) -> CycleHealthReport` | Returns health of last N cycles |
| `get_layer_health` | `(layer_name: str) -> LayerHealthReport` | Returns timing stats for one layer |
| `is_system_healthy` | `() -> bool` | True if all critical layers < CRIT threshold |

**Latency thresholds (from `config.py`):**

| Layer | WARN (ms) | CRIT (ms) |
|---|---|---|
| GlobalIntelligence (L1) | 5,000 | 12,000 |
| MarketIntelligence (L2) | 2,000 | 5,000 |
| MetaLearning (L3) | 2,000 | 5,000 |
| OpportunityEngine (L4) | 2,000 | 5,000 |
| StrategyLab (L5) | 2,000 | 5,000 |
| CapitalRiskEngine (L6) | 2,000 | 5,000 |
| RiskControl (L7) | 2,000 | 5,000 |
| MarketSimulation (L8) | 2,000 | 5,000 |
| RiskGuardian (L9) | 500 | 2,000 |
| DebateEngine (L10) | 2,000 | 5,000 |
| ExecutionEngine (L11) | 1,000 | 3,000 |
| TradeMonitoring (L12) | 2,000 | 5,000 |
| LearningSystem (L13) | 2,000 | 5,000 |
| PerformanceAnalytics (L14) | 5,000 | 15,000 |
| ResearchLab (L15) | 5,000 | 15,000 |
| ValidationEngine (L16) | 10,000 | 30,000 |
| ControlTower (L17) | 2,000 | 5,000 |

---

### 8.4 Audit Service

**Service:** `AuditService`
**Owner:** Engineering Foundation

**Responsibility:** Write an append-only, tamper-evident audit trail of all significant system events and decisions.

**What is audited:**

| Event Category | Events Audited |
|---|---|
| Decisions | Every `DecisionRecord` produced and whether it was approved/rejected |
| Orders | Every order submitted, including paper orders |
| Trade closes | Every position closed, with reason and P&L |
| Kill-switch | Every activation and clearance |
| Strategy lifecycle | Auto-disables, promotions, removals |
| Security events | Telegram auth failures, rejected commands, token events |
| Configuration changes | Runtime overrides, hot reloads |
| System lifecycle | Startup, shutdown, restarts |

**Audit record format:**

| Field | Type | Description |
|---|---|---|
| `sequence` | `int` | Monotonically increasing sequence number |
| `timestamp` | `str` | ISO 8601 UTC timestamp |
| `level` | `str` | AUDIT, SECURITY, or SYSTEM |
| `actor` | `str` | Component or person who triggered the event |
| `action` | `str` | Verb: SUBMITTED, APPROVED, REJECTED, ACTIVATED, etc. |
| `subject` | `str` | What was acted on (order_id, strategy_id, etc.) |
| `cycle_id` | `str` | Parent cycle |
| `detail` | `str` | Human-readable description |

**Immutability guarantee:** The audit log file is opened in append-only mode (`'a'`). No record is ever modified or deleted. The file is flushed on every write.

---

### 8.5 Metrics Collector

**Service:** `MetricsCollector`
**Owner:** Engineering Foundation

**Responsibility:** Collect, aggregate, and expose operational metrics from all system components.

**Metric Types:**

| Type | Description | Example |
|---|---|---|
| `Counter` | Monotonically increasing count | `orders_submitted_total` |
| `Gauge` | Instantaneous value | `open_positions_count`, `vix_level` |
| `Histogram` | Distribution of values | `layer_duration_ms` |
| `Timer` | Duration measurement | `cycle_duration_ms` |

**Standard system metrics:**

| Metric | Type | Description |
|---|---|---|
| `cycles_total` | Counter | Total cognitive cycles executed |
| `cycles_failed` | Counter | Cycles that ended in ERROR state |
| `orders_submitted_total` | Counter | Total orders submitted (paper + live) |
| `orders_filled_total` | Counter | Total orders filled |
| `open_positions_count` | Gauge | Current count of open positions |
| `daily_pnl_inr` | Gauge | Current day's realised P&L |
| `kill_switch_activations` | Counter | Total kill-switch activation events |
| `strategy_disabled_count` | Gauge | Current count of auto-disabled strategies |
| `feed_failover_count` | Counter | Total feed failover events |
| `layer_duration_ms` | Histogram | Per-layer execution time (labelled by `layer_name`) |
| `cycle_duration_ms` | Timer | Full cycle duration |
| `vix_level` | Gauge | Last observed VIX level |
| `conviction_score` | Histogram | Distribution of conviction scores for approved decisions |
| `win_rate_pct` | Gauge | Current rolling win rate (per strategy, labelled) |

---

### 8.6 Tracing Service

**Service:** `TracingService`
**Owner:** Engineering Foundation

**Responsibility:** Provide distributed-style tracing within the single process to correlate all operations within a cognitive cycle.

**Trace Model:**

| Concept | Description | ID Type |
|---|---|---|
| Trace | One complete cognitive cycle | `cycle_id` (UUID4) |
| Span | One layer's execution within a cycle | Auto-generated per layer |
| Sub-span | One named operation within a layer | Auto-generated per operation |

**Trace propagation:** The `cycle_id` is set in `ApplicationContext` at cycle start and carried through all 17 layers. Every log message, every database write, every audit record, and every metric includes the `cycle_id`.

---

### 8.7 Notification Service

**Service:** `NotificationService` (backed by `TelegramBot`)
**Owner:** Notifications

**Responsibility:** Deliver alerts and status updates to the Human Principal. Enforce notification rate limiting to prevent alert flooding.

**Notification levels:**

| Level | Trigger | Telegram Delivery |
|---|---|---|
| `INFO` | Normal operational events | Only for significant events (trade opened, EOD summary) |
| `WARNING` | Degraded operation | Immediate delivery |
| `ALERT` | Risk events, kill-switch | Immediate delivery with `⚠️` prefix |
| `CRITICAL` | System failures | Immediate delivery with `🚨` prefix |

**Rate limiting:**

| Rule | Policy |
|---|---|
| Same message deduplication | Same message body not sent more than once per 5 minutes |
| Alert flooding prevention | Maximum 10 messages per minute |
| Off-hours suppression | INFO-level messages suppressed between 22:00–08:00 IST |
| CRITICAL always sent | CRITICAL messages bypass all rate limits |

**Notification delivery guarantee:** If Telegram is unavailable, notifications are queued in memory (max 100 items). On reconnection, queued items are delivered in order. Items older than 1 hour are discarded.

---

### 8.8 Security Service

**Service:** `SecurityService`
**Owner:** Security

**Responsibility:** Enforce security policies at all system boundaries. Validate inputs. Mask sensitive values. Authenticate commands.

**Security enforcement points:**

| Boundary | Enforcement |
|---|---|
| Telegram command received | Validate `chat_id` matches `TELEGRAM_CHAT_ID` |
| Data feed response received | Validate response structure; reject malformed data |
| Broker API response received | Validate response signature if provided |
| Configuration loaded | Validate no secret value appears in a non-secret field |
| Log messages written | Scan for and mask token/key patterns before writing |
| Database query executed | Verify parameterised; no string interpolation |
| File path accessed | Validate against `is_safe_path()` (prevent traversal) |

---

### 8.9 Health Check Service

**Service:** `HealthCheckService`
**Owner:** Monitoring

**Responsibility:** Aggregate health from all registered components. Expose the system's composite health status to Docker's health check endpoint.

**Health aggregation logic:**

```
SYSTEM HEALTH = min(all component health statuses)
Where: HEALTHY > DEGRADED > UNAVAILABLE > CRITICAL
```

**Component health checks schedule:**
- Critical components: every 30 seconds
- Non-critical components: every 5 minutes
- On-demand: via Telegram `/status` command

**Health status fields:**

| Field | Type | Description |
|---|---|---|
| `component_name` | `str` | Component identifier |
| `status` | `HealthStatus` | HEALTHY, DEGRADED, UNAVAILABLE, CRITICAL |
| `message` | `str` | Human-readable status description |
| `checked_at` | `datetime` | When this check was performed |
| `metrics` | `Dict[str, float]` | Component-specific metrics at check time |

---

### 8.10 Performance Measurer

**Service:** `PerformanceMeasurer`
**Owner:** Control Tower

**Responsibility:** Provide precise timing measurements for performance-critical code paths.

| Method | Signature | Purpose |
|---|---|---|
| `measure` | `(name: str) -> ContextManager` | Times a named code block |
| `get_stats` | `(name: str) -> TimingStats` | Returns count, mean, p95, p99, max for named measurement |
| `get_all_stats` | `() -> Dict[str, TimingStats]` | Returns all timing statistics |
| `reset` | `(name: str = None) -> None` | Resets stats (all if name is None) |

**`TimingStats` fields:**

| Field | Description |
|---|---|
| `name` | Measurement name |
| `count` | Number of measurements |
| `total_ms` | Sum of all durations |
| `mean_ms` | Average duration |
| `min_ms` | Minimum observed |
| `max_ms` | Maximum observed |
| `p95_ms` | 95th percentile duration |
| `p99_ms` | 99th percentile duration |
| `last_ms` | Most recent duration |

---

### 8.11 Diagnostics Service

**Service:** `DiagnosticsService`
**Owner:** Control Tower

**Responsibility:** Produce a structured diagnostic snapshot of the entire system state on demand. Used by the `/status` Telegram command and the Streamlit dashboard.

**Diagnostic snapshot contents:**

| Section | Content |
|---|---|
| System | Version, uptime, environment, paper/live mode |
| Health | Health status of all registered components |
| Cycle | Last cycle: ID, duration, layers executed, errors |
| Risk | Kill-switch state, VIX level, daily P&L, daily loss limit |
| Positions | Count of open positions, symbols, total exposure |
| Strategies | Active/disabled strategy count, per-strategy win rate |
| Feeds | Primary feed, failover count, last successful fetch |
| Threads | All declared threads and their alive status |
| Metrics | Key system metrics snapshot |
| Errors | Last 5 ERROR-level log entries |

---

## PART IX — FRAMEWORK GOVERNANCE

### 9.1 Governance Philosophy

The Core Framework must be protected from degradation. Every engineer who adds to it, changes it, or extends it is making a decision that affects every other module in the system. Framework governance ensures those decisions are intentional, reviewed, and documented.

Framework governance has three tiers:

| Tier | Role | Responsibilities |
|---|---|---|
| L1 | Human Principal | Approve MAJOR version changes, interface changes, new base classes |
| L2 | Engineering Lead | Review all framework changes; enforce standards; manage deprecation |
| L3 | Automated | Lint, type check, test coverage, circular dependency scan on CI |

---

### 9.2 Framework Ownership

| Component | Primary Owner | Governance Level |
|---|---|---|
| `CoreConstants` | Engineering Foundation | L1 — no change without ADR |
| `BaseInterfaces` | Engineering Foundation | L1 — interface changes require MAJOR version |
| `BaseModel`, `BaseEntity`, `BaseValueObject` | Engineering Foundation | L1 |
| `BaseDTO`, `BaseRequest`, `BaseResponse`, `BaseResult` | Engineering Foundation | L1 |
| `BaseAgent`, `BaseEngine`, `BaseService` | Engineering Foundation | L1 |
| `BaseRepository`, `BaseScheduler`, `BaseValidator` | Engineering Foundation | L2 |
| `DependencyManager`, `LifecycleManager` | Control Tower | L1 |
| `ApplicationContext` | Engineering Foundation | L1 |
| `ErrorHierarchy` | Engineering Foundation | L1 — new exception types need ADR |
| `ConfigurationManager` | Control Tower | L2 |
| `LoggingService` | Engineering Foundation | L2 |
| `AuditService` | Engineering Foundation | L1 — audit integrity is critical |
| `MetricsCollector` | Engineering Foundation | L2 |
| `SecurityService` | Security | L1 |
| All utility modules | Engineering Foundation | L2 |

---

### 9.3 Extension Policy

The framework is extended by adding new implementations of declared abstract classes. New abstract classes are added only when a genuinely new type of component is introduced.

**Allowed extensions (no ADR required):**
- New concrete implementation of an existing base class (e.g., new feed adapter)
- New utility function in an existing utility module
- New constant in `CoreConstants` (additive)
- New event type in `BaseEvent` hierarchy (additive)
- New exception type in the exception hierarchy (additive)

**Extensions requiring ADR and L2 approval:**
- New utility module in `common/`
- New abstract base class
- New method added to an existing base class (affects all implementations)
- New cross-cutting service

**Extensions requiring ADR and L1 approval:**
- Change to any existing method signature in a base class
- Removal of any method from a base class
- New required field in any shared DTO
- Change to `ApplicationContext` structure
- Change to exception hierarchy (removing or renaming exceptions)
- New governance tier added

---

### 9.4 Interface Compatibility

All interfaces published by the Core Framework follow semantic versioning compatibility rules:

| Change | Compatible | Requires |
|---|---|---|
| Add optional method to interface | Yes | ADR (documentation only) |
| Add required method to interface | No | MAJOR version + migration |
| Change method signature | No | MAJOR version + deprecation |
| Remove method | No | MAJOR version + deprecation window |
| Add field to DTO | Yes (additive) | MINOR version |
| Remove field from DTO | No | MAJOR version + migration |
| Rename field in DTO | No | MAJOR version + migration |
| Change field type in DTO | No | MAJOR version + migration |

---

### 9.5 Versioning

The Core Framework follows the same semantic versioning as the system (see REPOSITORY_ARCHITECTURE.md Part VIII). The framework version is:
- Tracked in `CoreConstants.FRAMEWORK_VERSION`
- Written to every audit log entry
- Reported in the startup banner
- Included in every diagnostic snapshot

**Framework version increment triggers:**

| Trigger | Version Impact |
|---|---|
| New base class added | MINOR |
| New cross-cutting service added | MINOR |
| New method added to existing base class | MINOR |
| Breaking interface change | MAJOR |
| Error hierarchy breaking change | MAJOR |
| DTO breaking change | MAJOR |
| Bug fix in utility | PATCH |
| New utility function | PATCH |
| New constant | PATCH |

---

### 9.6 Deprecation Policy

When a framework component or interface is deprecated:

| Step | Action | Timeline |
|---|---|---|
| 1 | Mark with `@deprecated` decorator in source | Immediately |
| 2 | Log `DeprecationWarning` at runtime when deprecated path is called | Immediately |
| 3 | Add to `DEPRECATED.md` in `src/common/` | Immediately |
| 4 | Provide new interface or alternative | Same version as deprecation |
| 5 | Update all internal callers to use new interface | Within one release cycle |
| 6 | Remove deprecated interface | Next MAJOR version |

**Deprecation window:** Minimum one MINOR version (for non-breaking removals) or one MAJOR version (for breaking changes).

---

### 9.7 Migration Policy

When a breaking change is made to the Core Framework, a migration guide is required:

| Element | Contents |
|---|---|
| Affected interface | Exact interface name and version |
| What changed | Clear description of the before/after |
| Who is affected | List of all components that implement or use the interface |
| Migration steps | Numbered steps to migrate each consumer |
| Deadline | Version in which the old interface is removed |
| Author | Engineering Lead or Human Principal who approved the change |

Migration guides live in `docs/engineering/migrations/MIGRATION-<version>.md`.

---

### 9.8 Framework Evolution

The Core Framework is designed to grow in one direction: more expressiveness for component authors. Future evolution directions include:

| Evolution Area | Description | Planned |
|---|---|---|
| Async support | `BaseEngine.execute_async()` for non-blocking layer execution | Planned |
| Distributed tracing | Full OpenTelemetry integration | Planned |
| Schema registry | Formal DTO schema registry with validation | Planned |
| Event sourcing | Full event-sourced audit log (not just append-only text) | Planned |
| Feature flag service | External feature flag management (vs current in-memory) | Planned |
| Metrics export | Prometheus metrics endpoint | Planned |
| Hot-swappable services | Replace a service implementation without restart | Research |

Evolution is additive. No planned evolution requires removing existing interfaces.

---

## PART X — CORE FRAMEWORK CONSTITUTION

### 10.1 Constitutional Authority

The Core Framework Constitution is the supreme set of engineering rules governing how the IIOS Core Framework is used. These rules apply to every engineer, every tool, every component, and every artefact in the AI Trading Brain project.

These rules are not optional. They are not subject to individual engineer discretion. They are not waivable under time pressure. Any deviation requires an Architecture Decision Record and Human Principal approval.

---

### 10.2 Category A — Foundation Rules

| Rule ID | Rule |
|---|---|
| CF-A-01 | Every module, service, engine, agent, manager, repository, validator, and scheduler in the system derives from the appropriate Core Framework base class. No component operates outside the framework. |
| CF-A-02 | The `src/common/` package is the only approved shared library. No module creates its own competing shared library. |
| CF-A-03 | `CoreConstants` are the only approved source of system-level constant values. No module hardcodes values that belong in `CoreConstants`. |
| CF-A-04 | Every new base class or interface must be approved by an ADR before it is created. |
| CF-A-05 | No module bypasses `ConfigurationManager` to read configuration directly. All configuration access goes through the manager. |
| CF-A-06 | No module reads environment variables directly using `os.environ`. All environment access goes through `EnvironmentManager` or `SecretsManager`. |
| CF-A-07 | The `ApplicationContext` is the only approved carrier of per-cycle state. No module uses module-level variables to carry per-cycle state. |
| CF-A-08 | Every concrete implementation of a base class must implement ALL abstract methods. No partial implementations. |
| CF-A-09 | Framework version is the first entry in every startup log, diagnostic snapshot, and audit log. |
| CF-A-10 | The `LifecycleManager` starts and stops all components. No component starts itself on import. No component skips the shutdown sequence. |

---

### 10.3 Category B — Component Contract Rules

| Rule ID | Rule |
|---|---|
| CF-B-01 | Every service implementing `LifecycleAware` must implement `_do_initialise()`, `_do_start()`, `_do_stop()`, and `_do_health_check()`. Partial implementation is a framework violation. |
| CF-B-02 | Every layer engine must return an `EngineResult` from `execute()`. It NEVER returns `None`. A failed execution returns `EngineResult(success=False, error=...)`. |
| CF-B-03 | Every agent must return an `AgentOpinion` from `analyse()`. It NEVER returns `None`. An uncertain agent returns a score of 5.0 (neutral). |
| CF-B-04 | Every repository method that accepts user-derived input must use parameterised queries. String interpolation into SQL is a security violation. |
| CF-B-05 | Every DTO that crosses a layer boundary is `frozen=True`. DTOs are created complete and immutable. They are never modified after creation. |
| CF-B-06 | Every `BaseRequest` includes a `request_id`, `requested_at`, and `requester`. No anonymous requests. |
| CF-B-07 | Every `BaseResponse` echoes the `request_id` from its corresponding `BaseRequest`. |
| CF-B-08 | Every `BaseEntity` validates its own invariants in `validate()`. Entities are never in an invalid state after construction. |
| CF-B-09 | Every `BaseValueObject` validates its invariants in `__post_init__`. Value objects are immutable and self-consistent at creation. |
| CF-B-10 | Every event emitted to `EventBus` carries a `cycle_id`. Events without a cycle context are not permitted during cycle execution. |

---

### 10.4 Category C — Error Handling Rules

| Rule ID | Rule |
|---|---|
| CF-C-01 | Every custom exception in the system inherits from `TradingBrainError`. No exception inherits directly from Python's `Exception` or `BaseException`. |
| CF-C-02 | Every exception carries: `message`, `error_code`, `cycle_id` (if in cycle context), `layer_name` (if in layer context), `timestamp`. |
| CF-C-03 | Every exception declares `is_recoverable`. The caller uses this to decide whether to retry. |
| CF-C-04 | No exception is swallowed with `except Exception: pass` or equivalent. Every caught exception is either handled, re-raised, or logged at ERROR level with full context. |
| CF-C-05 | `except Exception as e: pass` is a framework violation. It is prohibited in ALL code in `src/`. |
| CF-C-06 | Business errors (expected conditions) are logged at WARNING or INFO level. System errors (unexpected conditions) are logged at ERROR or CRITICAL level. |
| CF-C-07 | Recovery policies are named and declared in `retry_utils.py`. Each error class is associated with exactly one named recovery policy. No inline retry loops. |
| CF-C-08 | Circuit breakers are declared components in `SecurityService`. No inline circuit breaker logic. |
| CF-C-09 | `LayerTimeoutError` is raised by `MonitoringService`, not by layer code. No layer self-reports its own timeout. |
| CF-C-10 | All errors raised during audit writes are logged to the primary log only. Audit errors never propagate to the caller (audit is best-effort). |

---

### 10.5 Category D — Configuration Rules

| Rule ID | Rule |
|---|---|
| CF-D-01 | Every configuration value used by a module is declared in the `ConfigurationSchema`. Undeclared configuration values are prohibited. |
| CF-D-02 | `validate_config()` is called before any other framework component is initialised. The system never starts in a misconfigured state. |
| CF-D-03 | Secrets are loaded from environment variables only. Secrets are never hardcoded, never in config files, never in log messages. |
| CF-D-04 | Feature flags are read through `ConfigurationManager.is_feature_enabled()`. No module reads a feature flag by direct environment variable access. |
| CF-D-05 | Runtime overrides (Tier 4) are set only by authorised actors: `RiskGuardian` (automatic) or Human Principal via Telegram. |
| CF-D-06 | Configuration changes that require a process restart are documented. Hot-reloadable values are documented as such. |
| CF-D-07 | Every new configuration key has a schema entry, a validation rule, and a description before it is used. |
| CF-D-08 | Configuration defaults in `config.py` represent the SAFE operating state. The system must be safe with default values, not optimised. |
| CF-D-09 | The `PAPER_TRADING` default is always `True`. Changing this default requires Human Principal written approval. |
| CF-D-10 | All path-related configuration values are resolved through `PathUtility`. No module constructs file paths by string concatenation. |

---

### 10.6 Category E — Dependency Rules

| Rule ID | Rule |
|---|---|
| CF-E-01 | Every service is registered with `DependencyManager` at startup. No service is instantiated by a consuming module. |
| CF-E-02 | Singletons are accessed via typed getter functions. No direct instantiation of a singleton anywhere in the codebase. |
| CF-E-03 | All required dependencies are declared in the constructor. No dependency is acquired inside `execute()` or other hot-path methods. |
| CF-E-04 | Components depend on interfaces (abstract base classes), not on concrete implementations. |
| CF-E-05 | The `DependencyManager` is the only registration point. No module maintains its own dependency registry. |
| CF-E-06 | Circular dependencies between framework components are prohibited. The framework itself must be a DAG. |
| CF-E-07 | Plugin implementations are discovered and registered by `PluginLoader`. Plugins are not imported directly. |
| CF-E-08 | Factory-created objects are transient. They must not be stored as instance attributes of a singleton. |
| CF-E-09 | `DependencyManager.clear()` is only callable from test code. It is forbidden in production code. |
| CF-E-10 | If a dependency cannot be resolved at startup, the component logs the failure and the system exits. No lazy resolution failures at runtime. |

---

### 10.7 Category F — Lifecycle Rules

| Rule ID | Rule |
|---|---|
| CF-F-01 | No component executes business logic before its `_do_initialise()` has been called by `LifecycleManager`. |
| CF-F-02 | All threads started by a component are started in `_do_start()` and stopped in `_do_stop()`. No threads are started on import. |
| CF-F-03 | The `SIGTERM` handler is registered in `main.py`. No framework component registers its own signal handler. |
| CF-F-04 | The shutdown sequence is executed in full. No component bypasses `_do_stop()` by calling `exit()` directly. |
| CF-F-05 | The `LifecycleManager` calls `stop_all()` in reverse initialisation order. Dependencies are always stopped before their consumers. |
| CF-F-06 | Every component handles `stop()` being called when it is not running (idempotent shutdown). |
| CF-F-07 | The pre-flight health check must complete before the scheduler starts. No jobs run on an unhealthy system. |
| CF-F-08 | Cognitive cycles do not start before the ready state is confirmed. No cycle runs during the initialisation phase. |

---

### 10.8 Category G — Observability Rules

| Rule ID | Rule |
|---|---|
| CF-G-01 | Every module uses `LoggingFactory.get_logger(__name__)` for its logger. No bare `print()` calls. |
| CF-G-02 | Every cognitive cycle has a unique `cycle_id` (UUID4) generated at cycle start and propagated to all 17 layers. |
| CF-G-03 | Every layer call is timed by `MonitoringService.time_layer()`. No layer is called outside this context manager. |
| CF-G-04 | Every significant operational event (order submitted, kill-switch activated, strategy disabled) emits an event to `EventBus`. |
| CF-G-05 | All audit events are written to `AuditService`. No audit event is written directly to a file or database. |
| CF-G-06 | All metrics are registered with `MetricsCollector`. No component maintains its own metrics storage. |
| CF-G-07 | Error logs at ERROR level always include the full exception context. `logger.exception()` is used, not `logger.error()`. |
| CF-G-08 | Health check results are never cached for more than 60 seconds. Stale health data is prohibited. |
| CF-G-09 | The diagnostic snapshot is always current (fetched on demand, never cached). |
| CF-G-10 | Secrets must never appear in any log, metric, trace, diagnostic snapshot, or Telegram message. |

---

### 10.9 Category H — Security Rules

| Rule ID | Rule |
|---|---|
| CF-H-01 | All secrets are loaded exclusively from environment variables through `SecretsManager`. |
| CF-H-02 | All database queries use parameterised statements. String interpolation into SQL is a framework violation. |
| CF-H-03 | All file paths accessed by the system are validated against `PathUtility.is_safe_path()` before use. |
| CF-H-04 | All data crossing a system boundary (Telegram, Dhan API, Yahoo Finance) is validated before processing. |
| CF-H-05 | All Telegram commands are authenticated by `chat_id` before execution. |
| CF-H-06 | All log messages are scanned for secret patterns before writing. `SecurityService.sanitise_for_log()` is mandatory. |
| CF-H-07 | The kill-switch is fail-safe: active by default. Clearing it requires explicit action. |
| CF-H-08 | The `PAPER_TRADING=true` default is a security control (financial safety). Disabling it requires Human Principal approval. |

---

### 10.10 Category I — Quality Rules

| Rule ID | Rule |
|---|---|
| CF-I-01 | Every public method in every framework class has a complete docstring: purpose, parameters, return type, exceptions. |
| CF-I-02 | Every framework component has a unit test achieving ≥ 95% branch coverage. |
| CF-I-03 | Every new base class has a conformance test that verifies each abstract method contract. |
| CF-I-04 | Pylint score for `src/common/` must be ≥ 9.0/10. The framework holds a higher standard than layer code. |
| CF-I-05 | Type annotations are mandatory for all framework method signatures. No untyped parameters or return values. |
| CF-I-06 | All framework utilities are pure functions (no side effects) where possible. Side effects are declared in the function name (`_write_`, `_log_`, `_send_`). |
| CF-I-07 | Every change to the Core Framework is backward-compatible or requires a MAJOR version and migration guide. |

---

### 10.11 Core Framework Constitution Reference Table

| ID | Category | Rule Summary | Enforcement |
|---|---|---|---|
| CF-A-01 | Foundation | Everything derives from Core Framework | PR review |
| CF-A-02 | Foundation | `common/` is the only shared library | PR review |
| CF-A-03 | Foundation | `CoreConstants` for all invariants | PR review |
| CF-A-04 | Foundation | New base class needs ADR | ADR process |
| CF-A-05 | Foundation | Config only via `ConfigurationManager` | CI + PR |
| CF-A-06 | Foundation | Env vars only via `EnvironmentManager` | CI + PR |
| CF-A-07 | Foundation | `ApplicationContext` carries per-cycle state | PR review |
| CF-A-08 | Foundation | All abstract methods implemented | CI type check |
| CF-A-09 | Foundation | Framework version in all banners | CI test |
| CF-A-10 | Foundation | `LifecycleManager` starts/stops all | PR review |
| CF-B-01 | Contracts | Full `LifecycleAware` implementation | CI type check |
| CF-B-02 | Contracts | Engines return `EngineResult`, never None | CI test |
| CF-B-03 | Contracts | Agents return `AgentOpinion`, never None | CI test |
| CF-B-04 | Contracts | Parameterised SQL only | PR review + security test |
| CF-B-05 | Contracts | DTOs are `frozen=True` at boundaries | CI type check |
| CF-B-06 | Contracts | Requests carry ID and requester | CI test |
| CF-B-07 | Contracts | Responses echo request ID | CI test |
| CF-B-08 | Contracts | Entities validate invariants | CI test |
| CF-B-09 | Contracts | Value objects immutable at creation | CI type check |
| CF-B-10 | Contracts | Events carry `cycle_id` | CI test |
| CF-C-01 | Errors | All exceptions from `TradingBrainError` | CI type check |
| CF-C-02 | Errors | Exceptions carry context fields | PR review |
| CF-C-03 | Errors | `is_recoverable` declared | PR review |
| CF-C-04 | Errors | No swallowed exceptions | CI lint + PR |
| CF-C-05 | Errors | `except Exception: pass` forbidden | CI lint |
| CF-C-06 | Errors | Business vs system error levels | PR review |
| CF-C-07 | Errors | Named retry policies | PR review |
| CF-C-08 | Errors | Circuit breakers via `SecurityService` | PR review |
| CF-C-09 | Errors | Timeout raised by `MonitoringService` | PR review |
| CF-C-10 | Errors | Audit errors best-effort only | PR review |
| CF-D-01 | Config | All config in schema | CI validation |
| CF-D-02 | Config | `validate_config()` before init | Process design |
| CF-D-03 | Config | Secrets from env only | CI secret scan |
| CF-D-04 | Config | Feature flags via manager | PR review |
| CF-D-05 | Config | Runtime overrides by authorised actors | PR review |
| CF-D-06 | Config | Restart-required values documented | PR review |
| CF-D-07 | Config | New keys have schema + docs | PR checklist |
| CF-D-08 | Config | Defaults represent safe state | PR review |
| CF-D-09 | Config | `PAPER_TRADING=True` is the default | Governance |
| CF-D-10 | Config | Paths via `PathUtility` | PR review |
| CF-E-01 | Dependencies | Services registered at startup | PR review |
| CF-E-02 | Dependencies | Singletons via getter functions | PR review |
| CF-E-03 | Dependencies | Dependencies declared in constructor | PR review |
| CF-E-04 | Dependencies | Depend on interfaces, not concretions | PR review |
| CF-E-05 | Dependencies | One registration point | PR review |
| CF-E-06 | Dependencies | No circular framework dependencies | CI dependency scan |
| CF-E-07 | Dependencies | Plugins via `PluginLoader` | PR review |
| CF-E-08 | Dependencies | Factories produce transient objects | PR review |
| CF-E-09 | Dependencies | `clear()` only in tests | PR review |
| CF-E-10 | Dependencies | Failures at startup, not runtime | Process design |
| CF-F-01 | Lifecycle | No logic before `_do_initialise()` | PR review |
| CF-F-02 | Lifecycle | Threads in `_do_start()` / `_do_stop()` | PR review |
| CF-F-03 | Lifecycle | SIGTERM handler in `main.py` only | PR review |
| CF-F-04 | Lifecycle | Full shutdown sequence | Process design |
| CF-F-05 | Lifecycle | Stop in reverse init order | Process design |
| CF-F-06 | Lifecycle | Idempotent `stop()` | CI test |
| CF-F-07 | Lifecycle | Health check before scheduler | Process design |
| CF-F-08 | Lifecycle | No cycles before ready state | Process design |
| CF-G-01 | Observability | Logger via `LoggingFactory` | CI lint |
| CF-G-02 | Observability | `cycle_id` on all cycles | CI test |
| CF-G-03 | Observability | Layer timing via `MonitoringService` | CI test |
| CF-G-04 | Observability | Events to `EventBus` | PR review |
| CF-G-05 | Observability | Audit via `AuditService` | PR review |
| CF-G-06 | Observability | Metrics via `MetricsCollector` | PR review |
| CF-G-07 | Observability | ERROR logs use `logger.exception()` | PR review |
| CF-G-08 | Observability | Health checks not cached >60s | CI test |
| CF-G-09 | Observability | Diagnostics always current | CI test |
| CF-G-10 | Observability | Secrets never in any output | CI security scan |
| CF-H-01 | Security | Secrets from `SecretsManager` | CI secret scan |
| CF-H-02 | Security | Parameterised SQL | PR review + test |
| CF-H-03 | Security | Path traversal prevention | PR review + test |
| CF-H-04 | Security | Boundary input validation | PR review + test |
| CF-H-05 | Security | Telegram `chat_id` auth | CI test |
| CF-H-06 | Security | Log sanitisation | CI test |
| CF-H-07 | Security | Kill-switch fail-safe | Process design |
| CF-H-08 | Security | `PAPER_TRADING=True` default | Governance |
| CF-I-01 | Quality | Complete docstrings | PR review |
| CF-I-02 | Quality | ≥ 95% branch coverage in `common/` | CI coverage |
| CF-I-03 | Quality | Conformance tests per base class | PR review |
| CF-I-04 | Quality | Pylint ≥ 9.0 in `common/` | CI lint |
| CF-I-05 | Quality | Full type annotations | CI type check |
| CF-I-06 | Quality | Pure functions where possible | PR review |
| CF-I-07 | Quality | Backward compatible or MAJOR version | PR review + ADR |

**Total mandatory rules: 75**

---

## DOCUMENT FOOTER

### Summary Metrics

| Metric | Value |
|---|---|
| Document title | CORE FRAMEWORK ARCHITECTURE |
| Document version | 1.0.0 |
| Date | 2026-07-02 |
| Parts | 10 (I–X) |
| Mandatory rules | 75 (CF-A-01 through CF-I-07) |
| Rule categories | 9 (Foundation, Contracts, Errors, Config, Dependencies, Lifecycle, Observability, Security, Quality) |
| Core components declared | 25 |
| Utility modules declared | 14 |
| Cross-cutting services declared | 10 |
| Abstract base classes | 11 (BaseAgent, BaseEngine, BaseService, BaseRepository, BaseManager, BaseScheduler, BaseValidator, BaseEntity, BaseValueObject, BaseDTO, BaseEvent) |
| Exception types in hierarchy | 46 |
| Lifecycle phases | 6 (Boot, Initialise, Register, HealthCheck, Ready, Shutdown) |
| Framework interfaces | 9 (LifecycleAware, HealthCheckable, Observable, Configurable, Auditable, Serialisable, Validatable, Resettable, Describable) |
| Standard system events | 12 |
| Circuit breakers declared | 4 |
| Named recovery policies | 9 |
| Governance tiers | 3 (L1 Human Principal, L2 Engineering Lead, L3 Automated) |
| Metric types | 4 (Counter, Gauge, Histogram, Timer) |
| Standard system metrics | 15 |
| Configuration tiers | 4 (CoreConstants, Application Config, Environment Variables, Runtime Overrides) |
| Feature flags declared | 11 |
| Environment variable entries | 14 |

---

### Master Compliance Checklist

Use this checklist when creating or modifying any component in the AI Trading Brain.

**Foundation (Category A)**
- [ ] Component derives from the appropriate Core Framework base class
- [ ] Configuration accessed through `ConfigurationManager`
- [ ] Environment variables accessed through `EnvironmentManager`
- [ ] Per-cycle state carried in `ApplicationContext`
- [ ] No business logic executes before `_do_initialise()`

**Component Contracts (Category B)**
- [ ] All abstract methods implemented (no partial implementations)
- [ ] `EngineResult` returned from all `execute()` calls (never None)
- [ ] `AgentOpinion` returned from all `analyse()` calls (never None)
- [ ] All DTOs are `frozen=True` at layer boundaries
- [ ] All `BaseRequest` objects include `request_id`, `requested_at`, `requester`

**Error Handling (Category C)**
- [ ] All custom exceptions inherit from `TradingBrainError`
- [ ] All exceptions carry `message`, `error_code`, `cycle_id`, `layer_name`, `timestamp`
- [ ] `is_recoverable` declared on every exception
- [ ] No `except Exception: pass` patterns
- [ ] Named recovery policy associated with every recoverable error class

**Configuration (Category D)**
- [ ] All configuration values in `ConfigurationSchema`
- [ ] New config keys have validation rules and descriptions
- [ ] No hardcoded secrets or credentials

**Dependencies (Category E)**
- [ ] All services registered at startup
- [ ] Singletons accessed via getter functions
- [ ] Dependencies declared in constructor

**Lifecycle (Category F)**
- [ ] Threads started in `_do_start()`, stopped in `_do_stop()`
- [ ] `stop()` is idempotent
- [ ] No direct `exit()` calls outside `main.py`

**Observability (Category G)**
- [ ] Logger obtained via `LoggingFactory.get_logger(__name__)`
- [ ] `cycle_id` propagated from `ApplicationContext`
- [ ] Layer timing via `MonitoringService.time_layer()`
- [ ] Significant events emit to `EventBus`
- [ ] No secrets in any log message

**Security (Category H)**
- [ ] All secrets via `SecretsManager`
- [ ] All SQL parameterised
- [ ] All file paths validated via `PathUtility.is_safe_path()`
- [ ] All boundary inputs validated before processing

**Quality (Category I)**
- [ ] Complete docstrings on all public methods
- [ ] Type annotations on all method signatures
- [ ] Unit tests with ≥ 95% branch coverage (for `common/`)
- [ ] Pylint score ≥ 9.0 (for `common/`)

---

### Component Inheritance Diagram

```
                    LifecycleAware ─┐
                    HealthCheckable ─┤
                    Observable ─────┤
                    Configurable ───┤── BaseService ──┬── BaseFeed
                                    │                 ├── BaseEngine (L1–L17)
                                    │                 ├── BaseManager
                                    │                 ├── BaseScheduler
                                    │                 └── BaseRepository
                    ─────────────────┤
                    Validatable ─────┤── BaseAgent
                                    │── BaseValidator
                    ─────────────────┤
                    Serialisable ────┤── BaseModel ────┬── BaseEntity
                    Validatable ─────┤                 └── BaseValueObject
                                    │── BaseDTO
                                    │── BaseEvent
                                    └── BaseRequest / BaseResponse / BaseResult
```

---

### Version History

| Version | Date | Author | Change Summary |
|---|---|---|---|
| 1.0.0 | 2026-07-02 | Human Principal | Initial authoritative release |

---

### Governing Documents

| Document | Role |
|---|---|
| `INVESTMENT_INTELLIGENCE_OPERATING_SYSTEM.md` | Supreme constitutional authority |
| `AI_TRADING_BRAIN_ENGINEERING_BLUEPRINT.md` | Engineering design bridge |
| `ENGINEERING_STANDARDS.md` | Mandatory engineering standards |
| `REPOSITORY_ARCHITECTURE.md` | Repository design authority |
| `CORE_FRAMEWORK_ARCHITECTURE.md` | This document — Core Framework design authority |

---

### Closing Statement

The Core Framework is the single most important engineering artefact in the AI Trading Brain. It is the foundation on which every intelligent agent, every risk control, every execution pathway, and every observability mechanism is built.

Every engineer who joins this project reads this document first. Every component they build derives from this framework. Every change they make is evaluated against this framework's constitution.

The framework is not a constraint. It is the grammar of the system — the shared language that makes every component intelligible to every other component and to every engineer who follows.

---
## SUPPLEMENT A — COMPLETE BASE CLASS SPECIFICATION

### A.1 `BaseService` Full Specification

`BaseService` is the primary abstract base for all long-lived, singleton-lifecycle components in the system. The table below shows all methods provided by `BaseService` and their contract.

**Provided (concrete) methods — do NOT override unless extending with `super()` call:**

| Method | Visibility | Provided By | Description |
|---|---|---|---|
| `initialise()` | Public | `BaseService` | Calls `_do_initialise()`; manages state transition; logs |
| `start()` | Public | `BaseService` | Calls `_do_start()`; manages state transition |
| `stop()` | Public | `BaseService` | Calls `_do_stop()`; manages state transition; idempotent |
| `check_health()` | Public | `BaseService` | Calls `_do_health_check()`; wraps with timing and error handling |
| `get_metrics()` | Public | `BaseService` | Calls `_do_get_metrics()`; returns `MetricsSnapshot` |
| `get_name()` | Public | `BaseService` | Returns value of `_service_name` (set in `__init__`) |
| `get_state()` | Public | `BaseService` | Returns current `LifecycleState` |
| `is_running()` | Public | `BaseService` | True if state is `RUNNING` |
| `configure(config)` | Public | `BaseService` | Stores config reference as `self.config` |
| `describe()` | Public | `BaseService` | Returns `ComponentDescription` for diagnostics |

**Abstract methods — MUST override in every concrete subclass:**

| Method | Visibility | Must Return | Description |
|---|---|---|---|
| `_do_initialise()` | Protected | None | Allocate resources, connect to dependencies |
| `_do_start()` | Protected | None | Start background threads, begin operation |
| `_do_stop()` | Protected | None | Stop threads, release resources, flush state |
| `_do_health_check()` | Protected | `HealthStatus` | Return current component health |
| `_do_get_metrics()` | Protected | `MetricsSnapshot` | Return component-specific metrics |

**State machine enforced by `BaseService`:**

| Current State | Allowed Transitions | Triggered By |
|---|---|---|
| `CREATED` | → `INITIALISING` | `initialise()` call |
| `INITIALISING` | → `INITIALISED` (success), → `ERROR` (exception) | `_do_initialise()` completion |
| `INITIALISED` | → `STARTING` | `start()` call |
| `STARTING` | → `RUNNING` (success), → `ERROR` (exception) | `_do_start()` completion |
| `RUNNING` | → `STOPPING` | `stop()` call |
| `STOPPING` | → `STOPPED` (success), → `ERROR` (exception) | `_do_stop()` completion |
| `STOPPED` | → `INITIALISING` | `initialise()` call (restart) |
| `ERROR` | → `INITIALISING` | `initialise()` call (recovery) |

Any other transition raises `LifecycleError`.

---

### A.2 `BaseEngine` Full Specification

`BaseEngine` extends `BaseService` with cognitive-cycle execution semantics. Every one of the 17 IIOS operational layers extends `BaseEngine`.

**Additional abstract methods (on top of `BaseService`):**

| Method | Visibility | Must Return | Description |
|---|---|---|---|
| `execute(context)` | Public | `EngineResult` | Execute this layer for one cognitive cycle |
| `get_layer_number()` | Public | `int` (1–17) | Return this engine's position in the layer hierarchy |
| `get_layer_name()` | Public | `str` | Return human-readable layer name |
| `get_dependencies()` | Public | `List[str]` | Return names of layers this engine reads from |

**Additional concrete methods provided by `BaseEngine`:**

| Method | Provided Behaviour |
|---|---|
| `get_last_result()` | Returns cached `EngineResult` from last `execute()` call |
| `get_latency_warn_ms()` | Returns override or default `LAYER_LATENCY_WARN_MS` |
| `get_latency_crit_ms()` | Returns override or default `LAYER_LATENCY_CRIT_MS` |
| `get_execution_count()` | Returns number of times `execute()` has been called |
| `get_last_duration_ms()` | Returns duration of last `execute()` call |
| `get_success_rate()` | Returns fraction of successful `execute()` calls |

---

### A.3 `BaseAgent` Full Specification

`BaseAgent` is the contract for all 62+ AI debate agents. Agents are stateless with respect to cycles — each `analyse()` call receives its full context and produces its opinion.

**All methods:**

| Method | Visibility | Must Return | Mandatory | Description |
|---|---|---|---|---|
| `analyse(context)` | Public | `AgentOpinion` | Yes | Core opinion-generation method |
| `get_agent_name()` | Public | `str` | Yes | Unique agent name |
| `get_agent_role()` | Public | `AgentRole` | Yes | `BULL`, `BEAR`, `RISK`, `TECHNICAL`, or `FUNDAMENTAL` |
| `get_weight()` | Public | `float` | No | Debate weight (default 1.0) |
| `get_confidence()` | Public | `float` | No | Current confidence (default 0.5) |
| `explain()` | Public | `str` | No | Explanation of last opinion |
| `reset()` | Public | `None` | No | Reset internal state (for test support) |

**`AgentRole` enum values:**

| Value | Description | Typical Score Bias |
|---|---|---|
| `BULL` | Optimistic — seeks reasons the trade will succeed | High scores (7–10) in bullish regimes |
| `BEAR` | Pessimistic — seeks reasons the trade will fail | Low scores (0–4) in bearish regimes |
| `RISK` | Risk-focused — evaluates position sizing risk | Low scores when stop is wide or capital is stretched |
| `TECHNICAL` | Technical analysis — chart patterns, indicators | Scores based on technical signal quality |
| `FUNDAMENTAL` | Fundamental analysis — valuation, macro context | Scores based on sector and macro alignment |

**`AgentContext` fields provided to each agent:**

| Field | Type | Description |
|---|---|---|
| `hypothesis` | `TradeHypothesis` | The proposed trade to evaluate |
| `global_snapshot` | `GlobalSnapshot` | Latest global market state |
| `regime_signal` | `RegimeSignal` | Current market regime |
| `symbol_history` | `List[PriceBar]` | Recent OHLCV bars for the hypothesis symbol |
| `sector_context` | `Dict[str, float]` | Sector performance context |
| `portfolio_context` | `PortfolioContext` | Current positions and exposure |
| `cycle_id` | `str` | Parent cycle identifier |
| `analysis_timestamp` | `datetime` | UTC time of this analysis request |

---

### A.4 `BaseRepository` Full Specification

`BaseRepository` is the abstract base for all database access classes. It enforces security and transactional rules through its base implementation.

**Additional provided behaviours:**

| Behaviour | Description |
|---|---|
| Connection management | `BaseRepository` holds and manages the DB connection |
| Parameterised query enforcement | All `_execute_query()` calls are routed through a parameterised wrapper |
| Auto-retry | Failed queries trigger `DATABASE_RETRY_POLICY` |
| Transaction scope | `begin_transaction()` sets `_in_transaction = True`; prevents nested transactions |
| Soft delete support | `delete()` sets `is_deleted = True` if the entity supports it |
| Timestamp auto-management | `save()` updates `created_at` and `updated_at` automatically |

**`Criteria` class for `find_where()` queries:**

| Field | Type | Description |
|---|---|---|
| `field` | `str` | Column name (validated against allowed column names) |
| `operator` | `str` | One of: `=`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `LIKE` |
| `value` | `Any` | Bound parameter value |
| `join_with` | `str` | `AND` or `OR` for multiple criteria |

Security rule: `Criteria.field` is validated against an allowlist of column names for the repository. An invalid field name raises `ValidationError`, not a query error.

---

### A.5 `BaseValidator` Full Specification

Validators are structured validation objects. Unlike ad hoc `if` statements, validators:
- Collect ALL violations (not just the first)
- Return a structured `ValidationResult`
- Can be composed (one validator calls another)

**Validator composition example:**

```
HypothesisValidator
├── calls: SymbolValidator (validates hypothesis.symbol)
├── calls: PriceValidator (validates hypothesis.entry_price)
├── calls: StopLossValidator (validates hypothesis.stop_loss relative to entry)
├── calls: TargetValidator (validates hypothesis.target relative to stop and entry)
└── calls: RRRValidator (validates reward:risk ratio ≥ MIN_SIGNAL_RR)
```

**`ValidationResult` aggregation:** A composed validator merges child `ValidationResult` objects. All violations from all children appear in the final `violations` list. The result is valid only if all children pass.

---

## SUPPLEMENT B — FRAMEWORK THREAD REGISTRY

### B.1 Declared Threads

Every thread in the system is declared here. No thread is created without a corresponding entry in this registry.

| Thread Name | Daemon | Owner | Start Trigger | Stop Trigger | Heartbeat Interval |
|---|---|---|---|---|---|
| `MainThread` | No | OS / Python | Process start | Process exit | N/A |
| `RiskGuardianThread` | Yes | `RiskGuardian` | `_do_start()` | `_do_stop()` | 10 seconds |
| `MarketMonitorThread` | Yes | `MarketMonitor` | `_do_start()` | `_do_stop()` | 30 seconds |
| `DataFeedPrimer` | Yes | `DataFeedManager` | `_do_start()` | `_do_stop()` | 60 seconds |
| `GlobalDataPrewarmer` | Yes | `GlobalDataAI` | `_do_start()` | `_do_stop()` | 300 seconds |
| `SchedulerThread` | Yes | `APScheduler` | Scheduler start | Scheduler shutdown | 60 seconds |
| `TelegramPollerThread` | Yes | `TelegramBot` | `_do_start()` | `_do_stop()` | 30 seconds |
| `AuditFlushThread` | Yes | `AuditService` | `_do_start()` | `_do_stop()` | 60 seconds |

**Thread safety rules:**

| Rule | Description |
|---|---|
| TH-01 | Every thread is named at creation. Unnamed threads are not permitted. |
| TH-02 | Every thread is declared in this registry before it is created. |
| TH-03 | Every daemon thread has a heartbeat mechanism. Missed heartbeats are alerted. |
| TH-04 | Thread communication uses `threading.Queue` or `threading.Event`. Never module-level globals. |
| TH-05 | All locks are `threading.Lock` or `threading.RLock`. No `time.sleep()` loops in place of locks. |
| TH-06 | Lock acquisition always uses context manager (`with self._lock:`). Never `acquire()`/`release()`. |
| TH-07 | No thread holds two locks simultaneously (deadlock prevention). |
| TH-08 | Thread stop is initiated by setting a `threading.Event` (`_stop_event`). Thread checks this event in its loop. |

---

## SUPPLEMENT C — EVENT BUS DESIGN

### C.1 EventBus Architecture

The `EventBus` is an in-process publish-subscribe system. It allows components to communicate without direct coupling.

```
Publisher               EventBus                   Subscriber
    │                      │                            │
    │── emit(event) ──────>│                            │
    │                      │── dispatch to handlers ───>│
    │                      │                            │── handle(event)
    │                      │<── handler returns ────────│
    │<── emit() returns ───│                            │
```

**Key design decisions:**
- **Synchronous dispatch:** The `EventBus` dispatches events synchronously in the emitter's thread. Handlers must be fast (< 5ms). Slow handlers block the cycle.
- **No event replay:** Events are not persisted. Subscribers that are offline when an event is emitted do not receive it.
- **Exception isolation:** An exception in one handler does not prevent other handlers from receiving the event.
- **Order guarantee:** Handlers for the same event type are called in registration order.

### C.2 EventBus Interface

| Method | Signature | Description |
|---|---|---|
| `subscribe` | `(event_type: str, handler: Callable[[BaseEvent], None]) -> str` | Register handler; return subscription ID |
| `unsubscribe` | `(subscription_id: str) -> bool` | Remove a handler |
| `emit` | `(event: BaseEvent) -> int` | Dispatch event; return count of handlers called |
| `get_subscribers` | `(event_type: str) -> List[str]` | Return handler names for event type |
| `get_all_event_types` | `() -> List[str]` | Return all registered event types |
| `clear_subscribers` | `(event_type: str = None) -> None` | Clear handlers (test support) |

### C.3 Standard Event Catalogue

| Event Type | Emitter | Key Payload Fields | Subscribers |
|---|---|---|---|
| `CYCLE_STARTED` | `MasterOrchestrator` | `cycle_id`, `started_at` | `MonitoringService`, `AuditService`, `MetricsCollector` |
| `CYCLE_COMPLETED` | `MasterOrchestrator` | `cycle_id`, `duration_ms`, `orders_submitted` | `MonitoringService`, `AuditService`, `MetricsCollector`, `TelegramBot` |
| `CYCLE_FAILED` | `MasterOrchestrator` | `cycle_id`, `error`, `layer_name` | `MonitoringService`, `AuditService`, `TelegramBot` |
| `LAYER_COMPLETED` | `MonitoringService` | `layer_name`, `duration_ms`, `status` | `MetricsCollector`, `DiagnosticsService` |
| `LAYER_TIMEOUT` | `MonitoringService` | `layer_name`, `duration_ms` | `AuditService`, `TelegramBot` |
| `KILL_SWITCH_ACTIVATED` | `RiskGuardian` | `reason`, `vix_level`, `daily_pnl` | `AuditService`, `TelegramBot`, `OrderManager`, `TradeMonitor` |
| `KILL_SWITCH_CLEARED` | `RiskGuardian` | `cleared_at`, `cleared_by` | `AuditService`, `TelegramBot` |
| `TRADE_OPENED` | `OrderManager` | `order_id`, `symbol`, `direction`, `quantity` | `TradeMonitor`, `AuditService`, `TelegramBot`, `MetricsCollector` |
| `TRADE_CLOSED` | `TradeMonitor` | `order_id`, `close_price`, `pnl`, `reason` | `LearningEngine`, `AuditService`, `TelegramBot`, `MetricsCollector` |
| `STRATEGY_DISABLED` | `StrategyHealthMonitor` | `strategy_id`, `reason` | `AuditService`, `TelegramBot`, `StrategyRegistry` |
| `DAILY_LOSS_LIMIT_REACHED` | `RiskGuardian` | `daily_pnl`, `limit` | `AuditService`, `TelegramBot`, `MasterOrchestrator` |
| `FEED_FAILOVER` | `DataFeedManager` | `from_feed`, `to_feed`, `reason` | `AuditService`, `TelegramBot`, `MonitoringService` |
| `SYSTEM_STARTUP` | `MasterOrchestrator` | `version`, `environment`, `paper_trading` | `AuditService`, `TelegramBot` |
| `SYSTEM_SHUTDOWN` | `MasterOrchestrator` | `reason`, `uptime_seconds` | `AuditService`, `TelegramBot` |

---

## SUPPLEMENT D — FRAMEWORK METRICS REFERENCE

### D.1 Complete Metrics Catalogue

All metrics registered with `MetricsCollector` at system startup:

**Counter Metrics (monotonically increasing):**

| Metric Name | Labels | Description |
|---|---|---|
| `cycles_total` | none | Total cognitive cycles executed |
| `cycles_failed_total` | none | Cycles that ended in ERROR state |
| `orders_submitted_total` | `direction`, `is_paper` | Orders submitted to execution engine |
| `orders_filled_total` | `direction`, `is_paper` | Orders confirmed filled |
| `orders_cancelled_total` | `reason` | Orders cancelled |
| `kill_switch_activations_total` | `reason` | Kill-switch activation events |
| `feed_failover_total` | `from_feed`, `to_feed` | Feed failover events |
| `strategies_disabled_total` | `reason` | Auto-disable events |
| `debate_approvals_total` | none | Hypotheses approved by debate engine |
| `debate_rejections_total` | `reason` | Hypotheses rejected by debate engine |
| `telegram_messages_sent_total` | `level` | Telegram messages sent |
| `telegram_commands_received_total` | `command` | Telegram commands received |
| `db_writes_total` | `table` | Database write operations |
| `validation_failures_total` | `error_code` | Validation failures |
| `circuit_breaker_opens_total` | `component` | Circuit breaker opens |

**Gauge Metrics (instantaneous value):**

| Metric Name | Labels | Description |
|---|---|---|
| `open_positions_count` | none | Current count of open positions |
| `daily_pnl_inr` | none | Realised P&L for current trading day |
| `paper_capital_inr` | none | Available paper trading capital |
| `vix_level` | none | Last observed VIX level |
| `active_strategies_count` | none | Count of enabled strategies |
| `disabled_strategies_count` | none | Count of auto-disabled strategies |
| `kill_switch_active` | none | 1 if active, 0 if not |
| `primary_feed_available` | `feed_name` | 1 if available, 0 if not |
| `system_health_score` | none | 0.0–1.0 composite health |
| `uptime_seconds` | none | Process uptime in seconds |

**Histogram Metrics (value distributions):**

| Metric Name | Labels | Buckets (ms) |
|---|---|---|
| `layer_duration_ms` | `layer_name` | 10, 50, 100, 500, 1000, 2000, 5000, 12000 |
| `cycle_duration_ms` | none | 50, 100, 200, 500, 1000, 2000, 5000 |
| `conviction_score` | none | 0, 1, 2, 3, 4, 5, 6, 6.5, 7, 8, 9, 10 |
| `reward_risk_ratio` | none | 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0 |
| `feed_response_ms` | `feed_name` | 100, 250, 500, 1000, 2000, 5000, 8000 |
| `db_query_ms` | `operation` | 1, 5, 10, 50, 100, 500 |

---

## SUPPLEMENT E — COMPLETE UTILITY QUICK REFERENCE

### E.1 Utility Module Cross-Reference

| Utility Need | Module | Function |
|---|---|---|
| Current UTC time | `time_utils` | `utc_now()` |
| Current IST time | `time_utils` | `ist_now()` |
| Is market open? | `time_utils` | `is_market_open()` |
| ISO timestamp string | `time_utils` | `iso_timestamp(dt)` |
| Is data stale? | `time_utils` | `is_stale(dt, ttl_seconds)` |
| New UUID4 | `id_utils` | `generate_uuid4()` |
| New cycle ID | `id_utils` | `generate_cycle_id()` |
| Short display ID | `id_utils` | `short_id(full_id)` |
| Format currency | `string_utils` | `format_currency(amount)` |
| Format percentage | `string_utils` | `format_percentage(value)` |
| Mask secret for log | `string_utils` | `mask_secret(s)` |
| Sanitise log string | `string_utils` | `sanitise_log_string(s)` |
| Clamp numeric value | `number_utils` | `clamp(value, min_v, max_v)` |
| Reward:risk ratio | `number_utils` | `reward_risk_ratio(entry, target, stop, dir)` |
| Kelly fraction | `number_utils` | `kelly_fraction(win_rate, avg_win, avg_loss)` |
| Sharpe ratio | `number_utils` | `sharpe_ratio(returns, risk_free)` |
| Max drawdown | `number_utils` | `max_drawdown(equity_curve)` |
| Safe division | `number_utils` | `safe_divide(num, den, default)` |
| Ensure directory | `file_utils` | `ensure_dir(path)` |
| Atomic file write | `file_utils` | `safe_write_text(path, content)` |
| Append to log | `file_utils` | `append_line(path, line)` |
| MD5 checksum | `file_utils` | `compute_md5(path)` |
| Repo root path | `path_utils` | `get_repo_root()` |
| Database path | `path_utils` | `get_db_path(db_name)` |
| Safe path check | `path_utils` | `is_safe_path(path, base)` |
| JSON to string | `json_utils` | `to_json(obj)` |
| JSON from string | `json_utils` | `from_json(s)` |
| Deep merge dicts | `json_utils` | `merge_dicts(base, override)` |
| Append CSV row | `csv_utils` | `append_row(path, row, fieldnames)` |
| Today's CSV rows | `csv_utils` | `read_today_rows(path, date_field)` |
| SHA-256 hash | `crypto_utils` | `sha256_hex(data)` |
| HMAC signature | `crypto_utils` | `hmac_sha256(key, message)` |
| Timing-safe compare | `crypto_utils` | `constant_time_compare(a, b)` |
| Validate symbol | `validation_utils` | `is_valid_symbol(symbol)` |
| Validate price | `validation_utils` | `is_valid_price(price)` |
| Validate direction | `validation_utils` | `is_valid_direction(direction)` |
| Assert not None | `validation_utils` | `assert_not_none(value, name)` |
| Assert positive | `validation_utils` | `assert_positive(value, name)` |
| Execute with retry | `retry_utils` | `RetryPolicy.execute(fn, *args)` |
| TTL cache get | `cache_utils` | `TTLCache.get(key)` |
| TTL cache set | `cache_utils` | `TTLCache.set(key, value, ttl)` |
| Serialise DTO | `serialisation_utils` | `serialise_dto(dto)` |
| Deserialise DTO | `serialisation_utils` | `deserialise_dto(d, dto_class)` |
| Registry lookup | `registry` | `Registry.get(name)` |
| Factory create | `registry` | `Factory.create(name)` |
| Load plugins | `registry` | `PluginLoader.load_all(dir, base_class)` |

---

## SUPPLEMENT F — FRAMEWORK DECISION RECORD LIBRARY

### F.1 Purpose

Architecture Decision Records (ADRs) document every significant framework design choice. Each ADR explains the context, the options considered, the decision made, and the consequences. The ADR library is the institutional memory of the Core Framework.

---

### F.2 ADR-001: Python Dataclasses for DTOs and Value Objects

| Field | Content |
|---|---|
| **ID** | ADR-001 |
| **Title** | Use Python `@dataclass(frozen=True)` for all DTOs and Value Objects |
| **Status** | Accepted |
| **Date** | 2024-01-01 |
| **Authors** | Human Principal |

**Context:**
The system needs to carry structured data across layer boundaries. Without a consistent approach, engineers use a mix of dictionaries, named tuples, and ad hoc objects. This leads to no type safety, no validation, and no clear ownership.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| Plain `dict` | Simple, no imports | No type safety, no autocomplete, hidden bugs |
| `typing.TypedDict` | Type-safe | Mutable, no methods, no `__post_init__` |
| `@dataclass` | Type-safe, methods, `__post_init__` | Mutable by default |
| `@dataclass(frozen=True)` | Immutable, type-safe, hashable, `__post_init__` | Slightly more verbose |
| Pydantic `BaseModel` | Runtime validation, rich features | Third-party dependency, heavier |

**Decision:**
Use `@dataclass(frozen=True)` for all DTOs and Value Objects. All classes that carry structured data across layer boundaries use this approach. `__post_init__` validates invariants at construction time. Frozen ensures no post-construction mutation.

**Consequences:**
- Positive: Type safety, immutability, hashability (can be used as dict keys or in sets)
- Positive: `__post_init__` provides a natural invariant validation point
- Positive: No additional dependencies
- Negative: Cannot add validation rules that are field-order dependent (minor — solved by checking in `__post_init__`)
- Negative: Engineers new to Python need to learn the dataclass pattern

---

### F.3 ADR-002: Synchronous EventBus Dispatch

| Field | Content |
|---|---|
| **ID** | ADR-002 |
| **Title** | EventBus uses synchronous in-process dispatch |
| **Status** | Accepted |
| **Date** | 2024-01-01 |
| **Authors** | Human Principal |

**Context:**
The system needs a decoupled communication mechanism between components. The primary concern is simplicity and debuggability over high throughput.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| Synchronous dispatch (in-emitter thread) | Simple, traceable, no extra threads | Slow handlers block emitter |
| Background thread pool | Non-blocking | Ordering not guaranteed, harder to debug |
| Message queue (Redis/RabbitMQ) | Persistent, distributed | External dependency, overkill for in-process |
| asyncio event queue | Non-blocking, modern | Would require async throughout — architectural mismatch |

**Decision:**
Use synchronous in-process dispatch. All handlers are called in the emitter's thread, in registration order. Handlers must complete in < 5ms. This is enforced by monitoring the total dispatch time in `EventBus.emit()`.

**Consequences:**
- Positive: Simple, debuggable, deterministic order
- Positive: No additional threads or external dependencies
- Positive: Stack trace for handler exceptions is directly readable
- Negative: Slow handlers block the cognitive cycle
- Mitigation: `MonitoringService` monitors dispatch time; slow handlers log a WARNING

---

### F.4 ADR-003: Singleton Pattern via Getter Functions

| Field | Content |
|---|---|
| **ID** | ADR-003 |
| **Title** | Singletons accessed via module-level getter functions |
| **Status** | Accepted |
| **Date** | 2024-01-01 |
| **Authors** | Human Principal |

**Context:**
Several services must have exactly one instance per process: `TelegramBot`, `DataFeedManager`, `StrategyPerformanceTracker`, `RegimeStrategyMap`. The naive approach (global module-level variable) is hard to test and creates import-time side effects.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| Module-level global variable | Simple | Import-time side effects, hard to mock in tests |
| Class-level `_instance` (`__new__`) | Classic GoF singleton | `__new__` override is non-obvious |
| Borg pattern (shared `__dict__`) | All instances share state | Confusing, unusual |
| `DependencyManager` registry | Centralised | Extra indirection |
| Module-level getter function | Lazy init, testable, idiomatic Python | None |

**Decision:**
All singletons are accessed via module-level getter functions (`get_telegram_bot()`, `get_feed_manager()`, etc.). Each getter initialises the singleton on first call and returns it on subsequent calls. The instance is stored in a module-level `_instance` variable. Test code can reset this variable to inject a mock.

**Consequences:**
- Positive: No import-time side effects
- Positive: Testable — `_instance` can be reset to inject mocks
- Positive: Idiomatic Python, discoverable
- Positive: Thread-safe with a `_lock` around the initialisation block
- Negative: Engineers must know to call the getter, not instantiate directly (enforced by Constitution rule CF-E-02)

---

### F.5 ADR-004: PAPER_TRADING Default True as Safety Control

| Field | Content |
|---|---|
| **ID** | ADR-004 |
| **Title** | `PAPER_TRADING=True` as the default and a financial safety control |
| **Status** | Accepted |
| **Date** | 2024-01-01 |
| **Authors** | Human Principal |

**Context:**
The system can execute live orders through Dhan. A misconfiguration or deployment error could trigger live orders in a context where paper trading was assumed. This is a financial safety concern — unintended live orders could cause real monetary loss.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| Default `PAPER_TRADING=False` | Real trading is explicit | A missing env var silently enables real trading |
| Default `PAPER_TRADING=True` | Safe by default; real trading requires explicit action | Real trading requires extra setup step |
| Always paper trading unless deployment mode = `production` | Ties to deployment mode | Deployment mode is a separate concern |

**Decision:**
Default `PAPER_TRADING=True`. Enabling live trading requires setting `PAPER_TRADING=false` explicitly in the environment. This is treated as a security control (CF-H-08), not just a configuration preference. Changing the default requires Human Principal written approval.

**Consequences:**
- Positive: System is always safe in a misconfigured or default state
- Positive: Live trading is explicit and audited
- Positive: Engineers can safely run the system locally without risk
- Negative: Extra step required to enable live trading
- Mitigation: The startup banner prominently displays `PAPER_TRADING: YES/NO`

---

### F.6 ADR-005: Named Recovery Policies over Inline Retry Logic

| Field | Content |
|---|---|
| **ID** | ADR-005 |
| **Title** | All retry logic must use named `RetryPolicy` objects |
| **Status** | Accepted |
| **Date** | 2024-02-01 |
| **Authors** | Human Principal |

**Context:**
Ad hoc retry loops appear throughout the codebase in different forms: `while retry_count < 3`, `for attempt in range(5)`, bare `except` with `sleep()`. This creates inconsistency, makes retry logic invisible to monitoring, and makes it impossible to reason about system behaviour under failure.

**Options Considered:**

| Option | Pros | Cons |
|---|---|---|
| Ad hoc retry loops | Simple to write | Invisible, inconsistent, untestable |
| Decorator-based retry | Concise call site | Configuration hidden in decorator, hard to vary |
| Named `RetryPolicy` objects | Explicit, testable, monitorable, consistent | Slightly more verbose |
| `tenacity` library | Rich features | Third-party dependency |

**Decision:**
All retry logic uses named `RetryPolicy` objects declared in `retry_utils.py`. The nine standard policies are pre-declared. New policies require a name, a description, and a review. The `execute()` method of each policy fires the `RETRY_ATTEMPTED` event to `EventBus`, making all retry activity visible to monitoring.

**Standard named policies:**

| Policy Name | Max Attempts | Backoff | Jitter | Use Case |
|---|---|---|---|---|
| `NO_RETRY` | 1 | — | — | Kill-switch, audit writes |
| `IMMEDIATE_RETRY` | 3 | 0ms | No | Fast local operations |
| `DATABASE_RETRY` | 3 | Exponential 100ms | Yes | Database writes |
| `NETWORK_RETRY` | 5 | Exponential 250ms | Yes | HTTP API calls |
| `FEED_RETRY` | 3 | Fixed 500ms | Yes | Market data feeds |
| `TELEGRAM_RETRY` | 5 | Exponential 1s | Yes | Telegram messages |
| `BROKER_RETRY` | 3 | Exponential 500ms | Yes | Broker order submission |
| `CACHE_RETRY` | 2 | Fixed 100ms | No | Cache misses |
| `PREWARM_RETRY` | 10 | Exponential 30s | Yes | Background pre-warm operations |

**Consequences:**
- Positive: All retry behaviour is explicit, named, and consistent
- Positive: All retry events visible through `EventBus` and metrics
- Positive: `RetryPolicy.execute()` catches and classifies non-recoverable exceptions and does NOT retry them
- Negative: Engineers must know the nine named policies and choose the right one

---

### F.7 ADR-006: Four-Tier Configuration Hierarchy

| Field | Content |
|---|---|
| **ID** | ADR-006 |
| **Title** | Four-tier configuration hierarchy with explicit precedence |
| **Status** | Accepted |
| **Date** | 2024-01-01 |
| **Authors** | Human Principal |

**Context:**
The system needs configuration at multiple levels: compile-time invariants, application defaults, deployment-specific values, and emergency runtime overrides. Without a formal hierarchy, engineers write configuration in whichever file is convenient, creating a maze of precedence rules.

**Decision:**
Adopt a four-tier hierarchy with explicit precedence (higher tier wins):

| Tier | Source | Mutability | Example |
|---|---|---|---|
| Tier 4 (highest) | Runtime overrides | Yes, by authorised actors | Kill-switch state |
| Tier 3 | Environment variables | No, set at deploy time | `PAPER_TRADING`, `DHAN_ACCESS_TOKEN` |
| Tier 2 | `config.py` application defaults | No, change requires redeploy | Scheduling slots, capital limits |
| Tier 1 (lowest) | `CoreConstants` | Never, compile-time constants | Symbol format, version, decimal precision |

**Consequences:**
- Positive: Clear precedence; every configuration value has an unambiguous source
- Positive: Emergency overrides (Tier 4) can change behaviour without restart
- Positive: Deployment-specific values (Tier 3) never need code changes
- Positive: Core invariants (Tier 1) can never be accidentally overridden
- Negative: Engineers must understand all four tiers to reason about configuration

---

### F.8 ADR-007: 17-Layer Ordered Execution Model

| Field | Content |
|---|---|
| **ID** | ADR-007 |
| **Title** | Cognitive cycles execute layers in a fixed, ordered sequence |
| **Status** | Accepted |
| **Date** | 2024-01-01 |
| **Authors** | Human Principal |

**Context:**
The system's 17 layers produce outputs that depend on the outputs of earlier layers. This dependency structure must be made explicit and enforced. The alternative — allowing layers to run in parallel or in arbitrary order — would create data races and inconsistent state.

**Decision:**
Cognitive cycles execute layers 1 through 17 in strict order. Each layer receives the `ApplicationContext` which accumulates outputs from earlier layers. A layer can only access results from layers with a lower number than itself. This is enforced by the `ApplicationContext` design: each layer's output is written to a fixed key, and access to unset keys returns `None`.

**Consequences:**
- Positive: Deterministic, reproducible cycle execution
- Positive: No data races — layers do not share mutable state
- Positive: Layer latency is individually measurable and attributable
- Positive: A layer can be inspected in isolation by providing a snapshot of the context up to its position
- Negative: Layers cannot be parallelised (even independent ones)
- Mitigation: Each layer is targeted at < 2s; the total cycle target is < 5s (current: 172ms)

---

### F.9 ADR Summary Table

| ID | Title | Status | Tier Impact |
|---|---|---|---|
| ADR-001 | Frozen dataclasses for DTOs | Accepted | Base classes |
| ADR-002 | Synchronous EventBus dispatch | Accepted | Cross-cutting |
| ADR-003 | Singleton getter functions | Accepted | DI / lifecycle |
| ADR-004 | PAPER_TRADING default True | Accepted | Config / security |
| ADR-005 | Named recovery policies | Accepted | Error / retry |
| ADR-006 | Four-tier configuration hierarchy | Accepted | Configuration |
| ADR-007 | 17-layer ordered execution | Accepted | Architecture |

All future framework-level decisions must follow this ADR format and be added to this library before the decision is implemented.

---

## SUPPLEMENT G — FRAMEWORK ANTI-PATTERN REFERENCE

The following anti-patterns are explicitly prohibited in the AI Trading Brain. Each represents a class of bugs or architectural violations observed in real trading systems.

| Anti-Pattern | Why Prohibited | Correct Alternative |
|---|---|---|
| `except Exception: pass` | Silently discards errors; trading bugs go undetected indefinitely | Catch, log, and re-raise or convert to `TradingBrainError` |
| `global order_manager` | Mutable module globals create race conditions across threads | Use `get_order_manager()` singleton getter |
| `os.environ["DHAN_TOKEN"]` directly | Bypasses `SecretsManager`; no sanitisation before logging | `SecretsManager.get("DHAN_TOKEN")` |
| Hardcoded `NIFTY50` symbol string | Breaks when symbol format changes | `CoreConstants.NIFTY50_SYMBOL` |
| `datetime.now()` without timezone | Naive datetimes cause IST/UTC confusion in scheduler | `time_utils.ist_now()` or `time_utils.utc_now()` |
| `pd.DataFrame.append()` in hot path | Deprecated; O(n²) memory copies in cycle | Pre-allocate list, convert to DataFrame once |
| `print(f"cycle {n}: {signal}")` | Not visible to monitoring; not filterable by level | `self.logger.info("cycle %s: %s", n, signal)` |
| `strategy.name` vs `strategy.strategy_name` | Attribute name ambiguity causes `AttributeError` in live code | Standardise on `strategy.strategy_id` (typed field) |
| `time.sleep()` in main thread | Blocks the scheduler from responding to SIGTERM | Use `threading.Event.wait(timeout=N)` |
| Starting thread in `__init__` | Creates threads on import; breaks test isolation | Start threads in `_do_start()` |
| `json.loads(user_input)` without try/except | `JSONDecodeError` propagates to Telegram handler | Wrap in `json_utils.safe_parse()` which returns `None` on error |
| `f"SELECT * FROM trades WHERE id = {trade_id}"` | SQL injection via symbol names or Telegram input | Always use parameterised queries with `?` placeholders |
| Catching `KeyboardInterrupt` in a thread | Suppresses SIGTERM propagation | Only `main.py` handles shutdown signals |
| `if result == None:` | Non-idiomatic; misses `__eq__` override cases | Always `if result is None:` |
| Returning `None` from `execute()` | Caller cannot distinguish "no result" from "crashed" | Always return `EngineResult(success=False, error=...)` |

---