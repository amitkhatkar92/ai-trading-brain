# AI Supervisor Lifecycle — C13 M1

## Overview

The **AI Supervisor Lifecycle** subsystem manages the operational lifecycle of
enterprise autonomous supervision sessions. It is the foundational building
block of the C13 AI Supervisor & Autonomous Governance platform.

**Package:** `iios.supervisor.lifecycle`  
**Primary interface:** `SupervisorLifecycle`  
**Module:** C13 — Phase 1, Module 1  
**Version:** 1.0.0

---

## Responsibilities

| Responsibility             | Implemented |
|----------------------------|-------------|
| Create supervisor sessions | ✅          |
| Manage lifecycle transitions | ✅        |
| Track lifecycle state      | ✅          |
| Maintain immutable history | ✅          |
| Publish lifecycle events   | ✅          |
| Validate transitions       | ✅          |

## Non-Responsibilities (intentional exclusions)

- AI reasoning
- Governance policy evaluation
- Decision making
- Autonomous optimization
- Execution routing

---

## Lifecycle States

```
CREATED → INITIALIZING → DISCOVERING → VALIDATING → READY
        → SUPERVISING ↔ MONITORING → COMPLETED → ARCHIVED

any active state → PAUSED → RESUMING → (prior active state)
any non-terminal state → FAILED → ARCHIVED
```

| State       | Description                                     |
|-------------|-------------------------------------------------|
| CREATED     | Session created, not yet initialized            |
| INITIALIZING | Supervisor is initialising resources           |
| DISCOVERING | Discovering supervised entities                 |
| VALIDATING  | Validating discovered entities                  |
| READY       | Ready to begin supervision                      |
| SUPERVISING | Active supervision in progress                  |
| MONITORING  | Monitoring supervised processes                 |
| PAUSED      | Supervision temporarily suspended               |
| RESUMING    | Transitioning back from PAUSED                  |
| COMPLETED   | Supervision completed successfully              |
| FAILED      | Supervision failed; reason recorded             |
| ARCHIVED    | Terminal immutable state                        |

---

## Quick Start

```python
from iios.supervisor.lifecycle import SupervisorLifecycle, SupervisorType, SupervisorScope

lc = SupervisorLifecycle()
lc.start()

session = lc.create(
    "sup-001",
    workflow_id         = "wf-001",
    supervisor_type     = SupervisorType.RISK,
    supervisor_scope    = SupervisorScope.ENTERPRISE,
)

lc.initialize(session.session_id)
lc.discover(session.session_id)
lc.validate_session(session.session_id)
lc.mark_ready(session.session_id)
lc.start_supervising(session.session_id)
lc.start_monitoring(session.session_id)
lc.complete(session.session_id)
lc.archive(session.session_id)

lc.stop()
```

---

## Module Files

| File                         | Purpose                                   |
|------------------------------|-------------------------------------------|
| `constants.py`               | Enumerations, state machine, system IDs   |
| `exceptions.py`              | SL-000 … SL-009 error hierarchy           |
| `supervisor_session.py`      | Mutable session domain object             |
| `supervisor_lifecycle.py`    | Primary public interface                  |
| `supervisor_state.py`        | Immutable state record + guard helper     |
| `supervisor_transition.py`   | Immutable transition record               |
| `supervisor_context.py`      | Immutable operational context             |
| `supervisor_metadata.py`     | Immutable supplementary metadata          |
| `supervisor_history.py`      | Bounded event/transition history          |
| `supervisor_statistics.py`   | Thread-safe lifecycle statistics          |
| `supervisor_registry.py`     | Thread-safe session registry              |
| `supervisor_factory.py`      | Session construction factory              |
| `supervisor_validation.py`   | Structural integrity validator            |
| `supervisor_events.py`       | Immutable event value objects (10 types)  |
| `__init__.py`                | Public surface / `__all__`               |

---

## Events

| Event                        | Emitted On                     |
|------------------------------|--------------------------------|
| `SUPERVISOR_CREATED`         | `create()`                     |
| `SUPERVISOR_INITIALIZED`     | `initialize()`                 |
| `SUPERVISOR_VALIDATED`       | `validate_session()`           |
| `SUPERVISOR_STARTED`         | `start_supervising()`          |
| `SUPERVISOR_MONITORING_STARTED` | `start_monitoring()`        |
| `SUPERVISOR_PAUSED`          | `pause()`                      |
| `SUPERVISOR_RESUMED`         | `resume()`                     |
| `SUPERVISOR_COMPLETED`       | `complete()`                   |
| `SUPERVISOR_FAILED`          | `fail()`                       |
| `SUPERVISOR_ARCHIVED`        | `archive()`                    |

---

## Error Codes

| Code   | Exception                             |
|--------|---------------------------------------|
| SL-000 | `SupervisorLifecycleError` (base)     |
| SL-001 | `SupervisorSessionNotFoundError`      |
| SL-002 | `SupervisorInvalidTransitionError`    |
| SL-003 | `SupervisorSessionTerminatedError`    |
| SL-004 | `SupervisorLifecycleNotRunningError`  |
| SL-005 | `SupervisorCapacityExceededError`     |
| SL-006 | `SupervisorValidationError`           |
| SL-007 | `SupervisorHistoryError`              |
| SL-008 | `SupervisorRegistryError`             |
| SL-009 | `SupervisorConfigurationError`        |

---

## Valid State Transitions

```
CREATED      → INITIALIZING, FAILED
INITIALIZING → DISCOVERING, FAILED
DISCOVERING  → VALIDATING, FAILED
VALIDATING   → READY, DISCOVERING, FAILED
READY        → SUPERVISING, PAUSED, FAILED
SUPERVISING  → MONITORING, PAUSED, COMPLETED, FAILED
MONITORING   → SUPERVISING, PAUSED, COMPLETED, FAILED
PAUSED       → RESUMING, FAILED
RESUMING     → SUPERVISING, MONITORING, READY, FAILED
COMPLETED    → ARCHIVED
FAILED       → ARCHIVED
ARCHIVED     → (terminal, immutable)
```

---

## Thread Safety

All public methods of `SupervisorLifecycle`, `SupervisorRegistry`,
`SupervisorHistory`, and `SupervisorStatistics` are thread-safe.

---

## Future Modules

- **M2** AI Supervisor Engine
- **M3** AI Governance Policy Framework
- **M4** Autonomous Governance Framework
- **M5** AI Supervisor Snapshot
- **M6** AI Supervisor Integration
