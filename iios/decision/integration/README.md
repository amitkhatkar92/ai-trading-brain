# Decision Integration

**C9 Decision Intelligence — Phase 1, Module 6**

`iios.decision.integration` is the **sole public entry point** into the
Decision Intelligence subsystem.

All external modules MUST communicate through `DecisionIntegrationEngine`.
M1-M5 internals are never exposed directly.

---

## Architecture

```
                          ┌─────────────────────────────────────┐
External Caller           │     DecisionIntegrationEngine        │
──────────────────────▶   │  (PRIMARY PUBLIC INTERFACE)          │
submit(request)           └──────────────┬──────────────────────┘
                                         │  orchestrates
                    ┌────────────────────┼────────────────────┐
                    │                    │                     │
              ┌─────┴──────┐   ┌─────────┴──────┐  ┌─────────┴──────────┐
              │  M1         │   │  M2            │  │  M3                │
              │  Decision   │   │  Decision      │  │  Decision Policy   │
              │  Lifecycle  │   │  Engine        │  │  Framework         │
              └─────────────┘   └───────────────┘  └────────────────────┘
                    │                    │                     │
              ┌─────┴──────┐            │            ┌────────┴──────────┐
              │  M4         │            │            │  M5               │
              │  Decision   │◀───────────┘            │  Decision         │
              │  Optim.     │                         │  Snapshot         │
              └─────────────┘                         └───────────────────┘
```

---

## Package Layout

| File | Purpose |
|------|---------|
| `decision_integration_engine.py` | **Primary public interface** |
| `decision_integration_manager.py` | Starts/stops M1-M5 components |
| `decision_integration_context.py` | Per-request mutable workflow state |
| `decision_integration_request.py` | Immutable public request value object |
| `decision_integration_response.py` | Immutable public response value object |
| `decision_integration_snapshot.py` | Integration-level snapshot with timing |
| `decision_integration_registry.py` | Tracks in-flight and completed requests |
| `decision_integration_validation.py` | Validates requests and readiness |
| `decision_integration_health.py` | Health monitoring for all components |
| `decision_integration_status.py` | Service-level status report |
| `decision_integration_statistics.py` | Thread-safe performance counters |
| `decision_integration_history.py` | Bounded history of responses + events |
| `decision_integration_events.py` | Typed event objects + factory functions |
| `decision_component_registry.py` | Manages M1-M5 component instances |
| `decision_component_factory.py` | Creates default M1-M5 instances |
| `constants.py` | Enums, identifiers, capacity defaults |
| `exceptions.py` | Error hierarchy DI-000 to DI-009 |
| `__init__.py` | Public exports |

---

## Quick Start

```python
from iios.decision.integration import (
    DecisionIntegrationEngine,
    DecisionIntegrationRequest,
)

# Create and start the engine (creates default M1-M5 components)
engine = DecisionIntegrationEngine()
engine.start()

# Build a request
request = DecisionIntegrationRequest.create(
    "dec-001",
    portfolio_id      = "pf-001",
    strategy_id       = "strat-001",
    decision_scope    = "order",
    decision_type     = "order",
    decision_priority = "high",
    inputs            = {"risk_score": 0.3, "confidence": 0.85},
)

# Execute the full workflow
response = engine.submit(request)

print(response.status)           # IntegrationStatus.SUCCESS
print(response.session_id)       # M1 lifecycle session
print(response.snapshot_id)      # M5 DecisionSnapshot ID
print(response.decision_status)  # "approved" / "rejected" / ...
print(response.decision_score)   # 0.78

engine.stop()
```

---

## Workflow Phases

| # | Phase | Component | Description |
|---|-------|-----------|-------------|
| 1 | VALIDATING | — | Request validation (6 checks) |
| 2 | LIFECYCLE | M1 | Create session, advance through CREATING → READY |
| 3 | ENGINE | M2 | Submit to Decision Engine (optional) |
| 4 | POLICY | M3 | Evaluate against registered policies (optional) |
| 5 | OPTIMIZATION | M4 | Optimize over approved candidates (optional) |
| 6 | SNAPSHOT | M5 | Build and store DecisionSnapshot |
| 7 | COMPLETING | M1 | Advance lifecycle to ACTIVE → COMPLETED |

Optional components (ENGINE, POLICY, OPTIMIZATION) are skipped gracefully
when not registered. The workflow always produces a response.

---

## Public API

| Method | Description |
|--------|-------------|
| `initialize()` | Pre-start configuration hook |
| `start()` | Start the engine and all components |
| `stop()` | Stop the engine and all components |
| `restart()` | Stop then start |
| `health()` | `DecisionIntegrationHealth` — aggregate health report |
| `status()` | `DecisionIntegrationStatus` — service status |
| `statistics()` | `dict` — performance counters |
| `snapshot(id?)` | Latest (or named) `DecisionIntegrationSnapshot` |
| `history()` | `DecisionIntegrationHistory` — responses + events |
| `validate(request)` | Validate without executing |
| `submit(request)` | Execute the full workflow → `DecisionIntegrationResponse` |
| `query(request_id?, session_id?, decision_id?)` | Look up a prior response |

---

## Custom Component Injection

```python
from iios.decision.integration import (
    DecisionIntegrationEngine,
    DecisionComponentRegistry,
    ComponentType,
)
from iios.decision.lifecycle import DecisionLifecycle
from iios.decision.snapshot  import DecisionSnapshotStore

# Build a custom registry (lifecycle + snapshot only)
registry = DecisionComponentRegistry()
lc       = DecisionLifecycle()
lc.start()
registry.register(ComponentType.LIFECYCLE, lc)
store    = DecisionSnapshotStore(validate=False)
registry.register(ComponentType.SNAPSHOT, store)

engine = DecisionIntegrationEngine(component_registry=registry)
engine.start()
```

---

## Validation Rules

Six checks are run on every request before the workflow starts:

| Check | Description |
|-------|-------------|
| REQUEST_CONSISTENCY | `request_id` and `decision_id` must be non-empty |
| CONTEXT_CONSISTENCY | `decision_scope` and `decision_type` must be non-empty |
| COMPONENT_READINESS | Lifecycle component must be registered and running |
| SUBSYSTEM_CONSISTENCY | No contradictory component states |
| WORKFLOW_CONSISTENCY | No conflicting workflow configuration |
| DEADLINE_CONSISTENCY | `deadline_s` must be > 0 |

---

## Events

| Event | When emitted |
|-------|-------------|
| `INITIALIZED` | After `initialize()` |
| `STARTED` | After `start()` |
| `STOPPED` | After `stop()` |
| `RESTARTED` | After `restart()` |
| `REQUEST_SUBMITTED` | When a request is accepted |
| `REQUEST_COMPLETED` | When a request finishes (success or partial) |
| `REQUEST_FAILED` | When a request fails |
| `SNAPSHOT_PUBLISHED` | When an M5 snapshot is built and stored |
| `HEALTH_CHANGED` | When the overall health level changes |

---

## Error Codes

| Code | Exception | Description |
|------|-----------|-------------|
| DI-000 | `DecisionIntegrationError` | Base exception |
| DI-001 | `IntegrationNotRunningError` | Engine not started |
| DI-002 | `IntegrationRequestError` | Malformed request |
| DI-003 | `IntegrationValidationError` | Validation checks failed |
| DI-004 | `ComponentNotFoundError` | Required component absent |
| DI-005 | `ComponentNotReadyError` | Component registered but not running |
| DI-006 | `IntegrationTimeoutError` | Request exceeded deadline |
| DI-007 | `IntegrationWorkflowError` | Unrecoverable workflow error |
| DI-008 | `DuplicateIntegrationError` | Duplicate request ID |
| DI-009 | `IntegrationConfigurationError` | Misconfiguration |

---

## Statistics

| Key | Description |
|-----|-------------|
| `requests_submitted` | Total requests accepted |
| `requests_completed` | Total requests completed (success + partial) |
| `requests_failed` | Total requests that failed |
| `requests_in_flight` | Currently processing |
| `sessions_created` | M1 lifecycle sessions created |
| `snapshots_published` | M5 snapshots built and stored |
| `policy_evaluations` | M3 policy evaluations completed |
| `optimized_decisions` | M4 optimization runs completed |
| `average_response_time_s` | Arithmetic mean end-to-end time |
| `ema_response_time_s` | EMA of end-to-end time (α=0.1) |
| `throughput_per_minute` | Sliding 60-second window |
| `subsystem_availability` | % of submitted requests that completed |

---

## What This Module Does NOT Do

- Evaluate policies (delegated to M3 `DecisionPolicyEngine`)
- Optimize candidates (delegated to M4 `DecisionOptimizationEngine`)
- Execute trades or place orders
- Expose M1-M4 internal objects to external callers
- Implement Portfolio Intelligence, Reporting, or Dashboards
