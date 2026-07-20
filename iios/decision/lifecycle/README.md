# iios.decision.lifecycle — Decision Lifecycle Guide

> **C9 Decision Intelligence · Phase 1 · Module 1**
>
> This module manages **decision state transitions only**.
> It performs **no policy evaluation**, **no optimization**, **no execution**, and **no broker communication**.

---

## Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [State Diagram](#state-diagram)
4. [State Reference](#state-reference)
5. [Transition Guide](#transition-guide)
6. [API Reference](#api-reference)
7. [Event Reference](#event-reference)
8. [Validation Checks](#validation-checks)
9. [Statistics](#statistics)
10. [Developer Guide](#developer-guide)

---

## Overview

`DecisionLifecycle` is the **primary public interface** for institutional decision session management.  It enforces a strict, immutable-history state machine across all decision sessions, providing:

- Strict state-transition enforcement
- Immutable per-session transition history
- Lifecycle event publication
- Six observability counters
- Thread-safe concurrent operation
- Five structural validation checks

---

## Quick Start

```python
from iios.decision.lifecycle import DecisionLifecycle, DecisionScope, DecisionType

lc = DecisionLifecycle()
lc.start()

# Create a session
session = lc.create(
    "decision-001",
    workflow_id    = "wf-morning-open",
    portfolio_id   = "p-india-eq",
    strategy_id    = "st-momentum",
    decision_scope = DecisionScope.ORDER,
    decision_type  = DecisionType.ORDER,
    decision_reason = "momentum breakout signal",
)

sid = session.session_id

# Advance through the lifecycle
lc.initialize(sid)    # CREATED → INITIALIZING
lc.collect(sid)       # INITIALIZING → COLLECTING
lc.evaluate(sid)      # COLLECTING → EVALUATING
lc.ready(sid)         # EVALUATING → READY
lc.activate(sid)      # READY → ACTIVE
lc.complete(sid)      # ACTIVE → COMPLETED
lc.archive(sid)       # COMPLETED → ARCHIVED

lc.stop()
```

### Pause / Resume

```python
# At any point from COLLECTING, EVALUATING, READY, or ACTIVE:
lc.pause(sid)          # → PAUSED
lc.resume(sid)         # → RESUMING
lc.collect(sid)        # back into COLLECTING (or any valid target state)
```

### Failure

```python
lc.fail(sid, reason="position limit reached")   # any non-terminal → FAILED
lc.archive(sid)                                  # FAILED → ARCHIVED
```

---

## State Diagram

```
                    ┌──────────────────────────────────────────────────────┐
                    │         DECISION LIFECYCLE STATE MACHINE             │
                    └──────────────────────────────────────────────────────┘

   ┌─────────┐
   │ CREATED │ ─── initialize() ──► INITIALIZING
   └─────────┘                         │
                                    collect()
                                        │
                                        ▼
                                   COLLECTING ◄────── resume()
                                        │                  ▲
                                   evaluate()          RESUMING ◄── resume()
                                        │                  ▲
                                        ▼              pause() can come from:
                                   EVALUATING          COLLECTING / EVALUATING
                                        │              READY / ACTIVE
                                     ready()               │
                                        │              pause() ─────────────►
                                        ▼                                   │
                                      READY                              PAUSED
                                        │                                   │
                                    activate()                          resume()
                                        │                                   │
                                        ▼                                   ▼
                                      ACTIVE                            RESUMING
                                        │
                                    complete()
                                        │
                                        ▼
                                   COMPLETED ─── archive() ──► ARCHIVED
                                                                   (terminal,
                                                                    immutable)
  fail() can be called from any
  non-terminal, non-immutable state:
     CREATED / INITIALIZING / COLLECTING /
     EVALUATING / READY / ACTIVE / PAUSED / RESUMING
          │
          ▼
        FAILED ─── archive() ──► ARCHIVED
```

---

## State Reference

| State | Value | Description | Terminal? | Active? |
|---|---|---|---|---|
| `CREATED` | `"created"` | Session created, awaiting initialization | No | No |
| `INITIALIZING` | `"initializing"` | System resources being initialized | No | Yes |
| `COLLECTING` | `"collecting"` | Data collection in progress | No | Yes |
| `EVALUATING` | `"evaluating"` | Decision evaluation in progress | No | Yes |
| `READY` | `"ready"` | Decision ready to activate | No | Yes |
| `ACTIVE` | `"active"` | Decision is actively executing | No | Yes |
| `PAUSED` | `"paused"` | Execution temporarily suspended | No | Yes |
| `RESUMING` | `"resuming"` | Transitioning back from pause | No | Yes |
| `COMPLETED` | `"completed"` | Decision completed successfully | Yes | No |
| `FAILED` | `"failed"` | Decision failed | Yes | No |
| `ARCHIVED` | `"archived"` | Session archived (immutable) | Yes | No |

---

## Transition Guide

### Valid Transition Table

| From | To | Trigger Method |
|---|---|---|
| CREATED | INITIALIZING | `initialize()` |
| CREATED | FAILED | `fail()` |
| INITIALIZING | COLLECTING | `collect()` |
| INITIALIZING | FAILED | `fail()` |
| COLLECTING | EVALUATING | `evaluate()` |
| COLLECTING | PAUSED | `pause()` |
| COLLECTING | FAILED | `fail()` |
| EVALUATING | READY | `ready()` |
| EVALUATING | PAUSED | `pause()` |
| EVALUATING | FAILED | `fail()` |
| READY | ACTIVE | `activate()` |
| READY | PAUSED | `pause()` |
| READY | FAILED | `fail()` |
| ACTIVE | COMPLETED | `complete()` |
| ACTIVE | PAUSED | `pause()` |
| ACTIVE | FAILED | `fail()` |
| PAUSED | RESUMING | `resume()` |
| PAUSED | FAILED | `fail()` |
| RESUMING | COLLECTING | `collect()` |
| RESUMING | EVALUATING | `evaluate()` |
| RESUMING | READY | `ready()` |
| RESUMING | FAILED | `fail()` |
| COMPLETED | ARCHIVED | `archive()` |
| FAILED | ARCHIVED | `archive()` |
| ARCHIVED | _(none)_ | Immutable |

### Error Behaviour

An invalid transition raises `DecisionInvalidTransitionError` immediately.  The session state is **not modified**.

```python
from iios.decision.lifecycle import DecisionInvalidTransitionError

try:
    lc.collect(session_id)   # Only valid from INITIALIZING, not from CREATED
except DecisionInvalidTransitionError as e:
    print(e.from_state, "→", e.to_state)
```

---

## API Reference

### `DecisionLifecycle`

```python
class DecisionLifecycle(LifecycleAwareMixin):
    def __init__(
        self,
        max_active_sessions:   int = 5_000,
        max_archived_sessions: int = 10_000,
        max_history:           int = 1_000,
        max_transitions:       int = 50_000,
    ) -> None: ...
```

#### Lifecycle Control

| Method | Description |
|---|---|
| `start()` | Start the lifecycle engine |
| `stop()` | Stop the lifecycle engine |

#### Session Management

| Method | Signature | Returns |
|---|---|---|
| `create()` | `(decision_id, *, session_id, workflow_id, portfolio_id, strategy_id, decision_scope, decision_type, decision_priority, decision_trigger, decision_reason, metadata, actor)` | `DecisionSession` |

#### State Transitions

| Method | Signature | Transition |
|---|---|---|
| `initialize()` | `(session_id, *, actor, reason)` | CREATED → INITIALIZING |
| `collect()` | `(session_id, *, actor, reason)` | INITIALIZING/RESUMING → COLLECTING |
| `evaluate()` | `(session_id, *, actor, reason)` | COLLECTING/RESUMING → EVALUATING |
| `ready()` | `(session_id, *, actor, reason)` | EVALUATING/RESUMING → READY |
| `activate()` | `(session_id, *, actor, reason)` | READY → ACTIVE |
| `pause()` | `(session_id, *, actor, reason)` | COLLECTING/EVALUATING/READY/ACTIVE → PAUSED |
| `resume()` | `(session_id, *, actor, reason)` | PAUSED → RESUMING |
| `complete()` | `(session_id, *, actor, reason)` | ACTIVE → COMPLETED |
| `fail()` | `(session_id, *, reason, actor)` | any non-terminal → FAILED |
| `archive()` | `(session_id, *, actor, reason)` | COMPLETED/FAILED → ARCHIVED |

#### Queries

| Method | Returns |
|---|---|
| `get(session_id)` | `DecisionSession` (raises if not found) |
| `find(session_id)` | `Optional[DecisionSession]` |
| `find_archived(session_id)` | `Optional[DecisionSession]` |
| `all_active()` | `List[DecisionSession]` |
| `by_state(state)` | `List[DecisionSession]` |
| `by_decision(decision_id)` | `List[DecisionSession]` |

#### Observability

| Method | Returns |
|---|---|
| `statistics()` | `DecisionStatistics` |
| `history()` | `DecisionHistory` |
| `validate(session_id)` | `DecisionValidationResult` |

#### Listeners

```python
lc.add_listener(my_callback)      # fn(DecisionEvent) -> None
lc.remove_listener(my_callback)
```

---

## Event Reference

| Event | Factory | Emitted when |
|---|---|---|
| `DECISION_CREATED` | `make_decision_created()` | `create()` called |
| `DECISION_INITIALIZED` | `make_decision_initialized()` | `initialize()` called |
| `DECISION_STARTED` | `make_decision_started()` | `activate()` called |
| `DECISION_PAUSED` | `make_decision_paused()` | `pause()` called |
| `DECISION_RESUMED` | `make_decision_resumed()` | `resume()` called |
| `DECISION_COMPLETED` | `make_decision_completed()` | `complete()` called |
| `DECISION_FAILED` | `make_decision_failed()` | `fail()` called |
| `DECISION_ARCHIVED` | `make_decision_archived()` | `archive()` called |

Events are **frozen dataclasses** and are immutable once created.

```python
from iios.decision.lifecycle import DecisionEvent, DecisionEventType

def handle_event(event: DecisionEvent) -> None:
    if event.event_type == DecisionEventType.DECISION_COMPLETED:
        duration = event.payload.get("duration_s", 0)
        print(f"Decision {event.decision_id} completed in {duration:.2f}s")

lc.add_listener(handle_event)
```

---

## Validation Checks

`lc.validate(session_id)` runs five structural checks:

| Check | Code | Verifies |
|---|---|---|
| Identifier Consistency | `IDENTIFIER_CONSISTENCY` | `session_id` and `decision_id` are non-empty strings |
| Lifecycle Consistency | `LIFECYCLE_CONSISTENCY` | State is a valid `DecisionState`; terminal states have `end_time`; ACTIVE has `start_time` |
| Transition Validity | `TRANSITION_VALIDITY` | Every consecutive pair in state history is a permitted transition |
| Timestamp Consistency | `TIMESTAMP_CONSISTENCY` | State history timestamps are monotonically non-decreasing; `updated_at ≥ created_at` |
| History Integrity | `HISTORY_INTEGRITY` | `len(state_history) == transition_count + 1`; last history record matches current state |

```python
result = lc.validate(session_id)

if not result.is_valid:
    for code in result.failed_checks:
        print(f"FAILED check: {code.value}")
    for msg in result.error_messages:
        print(f"  → {msg}")
```

---

## Statistics

`lc.statistics()` returns a `DecisionStatistics` instance with six counters:

| Counter | Description |
|---|---|
| `sessions_created` | Total sessions created since start |
| `sessions_completed` | Total sessions completed successfully |
| `sessions_failed` | Total sessions that reached FAILED state |
| `sessions_archived` | Total sessions archived |
| `average_session_duration_s` | Exponential moving average (α=0.1) of completed session durations |
| `transition_count` | Total state transitions executed |

```python
st = lc.statistics()
print(f"Created:   {st.sessions_created}")
print(f"Completed: {st.sessions_completed}")
print(f"Failed:    {st.sessions_failed}")
print(f"Archived:  {st.sessions_archived}")
print(f"Avg dur:   {st.average_session_duration_s:.3f}s")
print(f"Transitions: {st.transition_count}")

snapshot = st.snapshot()   # Dict snapshot
```

---

## Developer Guide

### Architecture

```
iios/decision/lifecycle/
├── __init__.py                  — Public exports
├── constants.py                 — Enums, state machine, default constants
├── exceptions.py                — Exception hierarchy (DL-000..DL-006)
├── decision_lifecycle.py        — PRIMARY PUBLIC INTERFACE ← start here
├── decision_session.py          — Mutable session domain object
├── decision_state.py            — Immutable state record + can_transition()
├── decision_transition.py       — Immutable transition record + make_transition()
├── decision_context.py          — Frozen routing context (from_session)
├── decision_metadata.py         — Frozen supplementary metadata
├── decision_events.py           — Frozen events + 8 factory functions
├── decision_history.py          — Thread-safe bounded event/transition history
├── decision_statistics.py       — Thread-safe counters (EMA duration)
├── decision_registry.py         — Thread-safe active + archived session store
├── decision_factory.py          — Stateless session factory
└── decision_validation.py       — 5-check validator
```

### Thread Safety

- `DecisionLifecycle._lock` (RLock) guards all registry mutations and transitions
- `DecisionStatistics` has its own `Lock`
- `DecisionHistory` has its own `Lock`
- `DecisionRegistry` has its own `RLock`

`DecisionSession` itself is **not** thread-safe; concurrent transitions to the same session are serialized by `DecisionLifecycle._lock`.

### Exception Hierarchy

```
IIOSError
└── DecisionLifecycleError          (DL-000)  base
    ├── DecisionSessionNotFoundError  (DL-001)
    ├── DecisionInvalidTransitionError(DL-002)  .from_state, .to_state
    ├── DecisionLifecycleNotRunningError(DL-003)
    ├── DecisionSessionAlreadyExistsError(DL-004)
    ├── DecisionValidationError       (DL-005)  .failed_checks tuple
    └── DecisionSessionTerminatedError (DL-006)
```

### Adding a New Scope or Type

1. Add value to `DecisionScope` or `DecisionType` in `constants.py`
2. No other changes required — enums are used as-is throughout

### Adding a New State

This is a **breaking change** — do not do this without explicit approval.  It requires:

1. New entry in `DecisionState`
2. New rows in `VALID_TRANSITIONS`
3. Update `ACTIVE_STATES` / `TERMINAL_STATES` / `IMMUTABLE_STATES` / `SUCCESS_STATES` as needed
4. New event type in `DecisionEventType` + factory function in `decision_events.py`
5. New transition method in `DecisionLifecycle`
6. Update validation check 3 and 5 if needed
7. New tests

### Running Tests

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/decision/lifecycle/ -v
```

Expected: **174 tests, all passing**.
