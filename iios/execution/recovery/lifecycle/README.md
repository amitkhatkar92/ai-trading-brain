# Execution Recovery Lifecycle

**C7 Execution Recovery & Resilience — Phase 1, Module 1**

## Overview

The Execution Recovery Lifecycle (`iios.execution.recovery.lifecycle`) manages
the lifecycle of recovery sessions for the execution subsystem.

This module manages **recovery state transitions only**.

It performs **no recovery actions**, no failover, no broker communication,
and no trade execution.

---

## Lifecycle States

```
CREATED → INITIALIZING → DETECTING → ASSESSING → READY → RECOVERING → VERIFYING → COMPLETED
                                                                         ↑         ↓
                                                                         └─ retry ─┘

Any active state → FAILED / ABORTED
Terminal states  → ARCHIVED
```

| State        | Meaning                                          |
|-------------|--------------------------------------------------|
| CREATED     | Session created, not yet initialised              |
| INITIALIZING| Setting up recovery prerequisites                 |
| DETECTING   | Detecting the scope of the failure                |
| ASSESSING   | Assessing impact and building recovery plan       |
| READY       | Assessment complete; awaiting execution approval  |
| RECOVERING  | Recovery actions are being executed               |
| VERIFYING   | Verifying recovery outcome                        |
| COMPLETED   | Recovery verified and successful                  |
| FAILED      | Recovery failed with an unrecoverable error       |
| ABORTED     | Recovery was cancelled by an operator or policy   |
| ARCHIVED    | Terminal session moved to cold storage            |

---

## Valid Transitions

```
CREATED      → INITIALIZING
INITIALIZING → DETECTING, FAILED, ABORTED
DETECTING    → ASSESSING, FAILED, ABORTED
ASSESSING    → READY, FAILED, ABORTED
READY        → RECOVERING, FAILED, ABORTED
RECOVERING   → VERIFYING, FAILED, ABORTED
VERIFYING    → COMPLETED, RECOVERING (retry), FAILED, ABORTED
COMPLETED    → ARCHIVED
FAILED       → ARCHIVED
ABORTED      → ARCHIVED
ARCHIVED     → (none — terminal)
```

---

## Quick Start

```python
from iios.execution.recovery.lifecycle import RecoveryLifecycle, RecoveryTrigger

lifecycle = RecoveryLifecycle()
lifecycle.start()

# Create a recovery session
session = lifecycle.create(
    execution_session_id = "exec-001",
    subsystem_id         = "execution_gateway",
    recovery_trigger     = RecoveryTrigger.AUTOMATIC,
    recovery_reason      = "Gateway timeout exceeded threshold",
)

# Drive through the lifecycle
lifecycle.initialize(session.session_id)
lifecycle.detect(session.session_id)
lifecycle.assess(session.session_id)
lifecycle.ready(session.session_id)
lifecycle.begin_recovery(session.session_id)
lifecycle.verify(session.session_id)
lifecycle.complete(session.session_id)
lifecycle.archive(session.session_id)

lifecycle.stop()
```

---

## Retry Loop

If verification fails, the session may loop back to RECOVERING:

```python
lifecycle.begin_recovery(session.session_id)
lifecycle.verify(session.session_id)
# Verification incomplete — retry
lifecycle.retry_recovery(session.session_id)   # VERIFYING → RECOVERING
lifecycle.verify(session.session_id)
lifecycle.complete(session.session_id)
```

---

## Failure and Abort

```python
# Fail with reason
lifecycle.fail(session.session_id, "broker connection lost")

# Abort (operator-initiated)
lifecycle.abort(session.session_id, "operator cancelled", actor="operator")
```

---

## Event Listeners

```python
from iios.execution.recovery.lifecycle import RecoveryEvent

def on_event(event: RecoveryEvent) -> None:
    print(f"[{event.event_type.value}] session={event.session_id}")

lifecycle.add_event_listener(on_event)
lifecycle.remove_event_listener(on_event)
```

---

## Package Structure

```
iios/execution/recovery/lifecycle/
├── constants.py                  # Enums, state machine, limits
├── exceptions.py                 # RC-000 … RC-008 hierarchy
├── recovery_context.py           # Immutable input DTO
├── recovery_metadata.py          # Supplementary metadata DTO
├── recovery_session.py           # Core mutable domain object
├── recovery_state.py             # StateRecord + can_transition()
├── recovery_transition.py        # Immutable transition record
├── recovery_events.py            # Domain events + factory functions
├── recovery_validation.py        # Stateless validator
├── recovery_statistics.py        # Thread-safe accumulator
├── recovery_history.py           # Bounded deque history
├── recovery_registry.py          # LifecycleAwareMixin session store
├── recovery_factory.py           # LifecycleAwareMixin factory
├── recovery_lifecycle.py         # PRIMARY ENTRY POINT
└── __init__.py                   # Full public surface
```

---

## Recovery Triggers

| Trigger         | Description                              |
|----------------|------------------------------------------|
| MANUAL         | Operator-initiated recovery              |
| AUTOMATIC      | System rule matched failure condition    |
| POLICY         | Recovery policy engine decision          |
| HEALTH_CHECK   | Health monitor detected an issue         |
| WATCHDOG       | Watchdog timer expired                   |
| CIRCUIT_BREAKER| Circuit breaker tripped                  |
| EXTERNAL       | External system signal                   |

---

## Statistics

```python
stats = lifecycle.statistics()
print(stats.sessions_created)
print(stats.sessions_completed)
print(stats.completion_rate)      # fraction of terminated sessions that completed
print(stats.average_duration_ms)  # average time in RECOVERING → COMPLETED
```

---

## Future Modules

- **M2**: Recovery Engine — executes recovery actions
- **M3**: Recovery Policy Framework — policy-driven recovery decisions
- **M4**: Failover Framework — subsystem failover coordination
- **M5**: Recovery Snapshot — captures subsystem state for recovery
- **M6**: Recovery Integration — integrates all modules
