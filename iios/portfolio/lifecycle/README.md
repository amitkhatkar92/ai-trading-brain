# Portfolio Lifecycle — C10 M1

**Package:** `iios.portfolio.lifecycle`  
**Version:** 1.0.0  
**Layer:** Portfolio Intelligence — Phase 1, Module 1  

---

## Overview

The Portfolio Lifecycle subsystem manages the **lifecycle of portfolio sessions** throughout their operational existence. Its sole purpose is to govern **state transitions** — nothing else.

### What it does

| Responsibility | Included? |
|---|---|
| Portfolio state transitions | ✅ Yes |
| Session creation | ✅ Yes |
| Lifecycle event dispatch | ✅ Yes |
| History accumulation | ✅ Yes |
| Structural integrity validation | ✅ Yes |

### What it intentionally does NOT do

| Out-of-scope capability | Excluded |
|---|---|
| Portfolio optimisation | ❌ |
| Capital allocation | ❌ |
| Rebalancing calculation | ❌ |
| Execution routing | ❌ |

---

## Primary Interface

`PortfolioLifecycle` is the **only** interface external callers should use.

```python
from iios.portfolio.lifecycle import PortfolioLifecycle, PortfolioType

lc = PortfolioLifecycle()
lc.start()

# Create a session
session = lc.create(
    "pf-001",
    portfolio_name="Institutional Growth Fund",
    portfolio_type=PortfolioType.EQUITY,
)

# Progress through the lifecycle
lc.initialize(session.session_id)
lc.load(session.session_id)
lc.validate_session(session.session_id)
lc.ready(session.session_id)
lc.activate(session.session_id)

# Optional: rebalance
lc.rebalance(session.session_id)
lc.activate(session.session_id)    # back to active after rebalancing

# Complete and archive
lc.complete(session.session_id)
lc.archive(session.session_id)

lc.stop()
```

---

## State Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                  PORTFOLIO LIFECYCLE STATE MACHINE               │
└──────────────────────────────────────────────────────────────────┘

  CREATED ──────────────────────────────────────────► FAILED
     │                                                    │
     ▼                                                    │
  INITIALIZING ────────────────────────────────────► FAILED
     │                                                    │
     ▼                                                    │
  LOADING ◄────────── VALIDATING                    FAILED
     │                    │                              │
     ▼                    ▼                              │
  LOADING ───────────► VALIDATING                   FAILED
                          │                              │
                          ▼                              │
                        READY ──────────────────────► FAILED
                          │                              │
                          │◄─────── RESUMING             │
                          ▼             ▲                │
                        ACTIVE ──────► PAUSED ─────► FAILED
                          │             │
                          │◄──── REBALANCING ──────► FAILED
                          │
                          ▼
                       COMPLETED ───────────────────► ARCHIVED
                          
  FAILED ──────────────────────────────────────────► ARCHIVED
```

### Happy Path

```
CREATED → INITIALIZING → LOADING → VALIDATING → READY → ACTIVE → COMPLETED → ARCHIVED
```

### Pause / Resume

```
ACTIVE → PAUSED → RESUMING → READY → ACTIVE
```

### Rebalancing

```
ACTIVE → REBALANCING → ACTIVE
ACTIVE → REBALANCING → PAUSED
ACTIVE → REBALANCING → COMPLETED
```

---

## Transition Guide

### Valid Transitions Table

| From State     | Permitted Targets                                       |
|----------------|---------------------------------------------------------|
| `CREATED`      | `INITIALIZING`, `FAILED`                               |
| `INITIALIZING` | `LOADING`, `FAILED`                                    |
| `LOADING`      | `VALIDATING`, `FAILED`                                 |
| `VALIDATING`   | `READY`, `LOADING`, `FAILED`                           |
| `READY`        | `ACTIVE`, `PAUSED`, `FAILED`                           |
| `ACTIVE`       | `REBALANCING`, `PAUSED`, `COMPLETED`, `FAILED`         |
| `PAUSED`       | `RESUMING`, `FAILED`                                   |
| `RESUMING`     | `READY`, `ACTIVE`, `REBALANCING`, `LOADING`            |
| `REBALANCING`  | `ACTIVE`, `PAUSED`, `COMPLETED`, `FAILED`              |
| `COMPLETED`    | `ARCHIVED`                                             |
| `FAILED`       | `ARCHIVED`                                             |
| `ARCHIVED`     | *(terminal — no further transitions)*                  |

### State Sets

| Set | States |
|---|---|
| `ACTIVE_STATES` | INITIALIZING, LOADING, VALIDATING, READY, ACTIVE, PAUSED, RESUMING, REBALANCING |
| `TERMINAL_STATES` | COMPLETED, FAILED, ARCHIVED |
| `SUCCESS_STATES` | COMPLETED |
| `IMMUTABLE_STATES` | ARCHIVED |

---

## Module Structure

```
iios/portfolio/lifecycle/
├── __init__.py                 ← Public exports
├── constants.py                ← Enums, transitions, limits
├── exceptions.py               ← PL-000 to PL-009 error hierarchy
├── portfolio_context.py        ← Immutable session context
├── portfolio_events.py         ← Event value objects + 11 factories
├── portfolio_factory.py        ← Session factory
├── portfolio_history.py        ← Bounded history store
├── portfolio_lifecycle.py      ← PRIMARY PUBLIC INTERFACE
├── portfolio_metadata.py       ← Immutable session metadata
├── portfolio_registry.py       ← Thread-safe session registry
├── portfolio_session.py        ← Core domain object
├── portfolio_state.py          ← StateRecord + can_transition()
├── portfolio_statistics.py     ← Thread-safe statistics accumulator
├── portfolio_transition.py     ← Transition record + make_transition()
└── portfolio_validation.py     ← 5-check structural validator
```

---

## Exception Hierarchy

| Code | Class | Raised when |
|---|---|---|
| `PL-000` | `PortfolioLifecycleError` | Base class |
| `PL-001` | `PortfolioSessionNotFoundError` | session_id not in registry |
| `PL-002` | `PortfolioInvalidTransitionError` | transition not permitted |
| `PL-003` | `PortfolioSessionTerminatedError` | operation on ARCHIVED session |
| `PL-004` | `PortfolioLifecycleNotRunningError` | engine not started |
| `PL-005` | `PortfolioCapacityExceededError` | max_active_sessions reached |
| `PL-006` | `PortfolioValidationError` | validation checks fail |
| `PL-007` | `PortfolioHistoryError` | history operation error |
| `PL-008` | `PortfolioRegistryError` | registry operation error |
| `PL-009` | `PortfolioConfigurationError` | configuration error |

---

## Events

11 lifecycle events are dispatched automatically on every state transition:

| Event | State | Factory |
|---|---|---|
| `PORTFOLIO_CREATED` | CREATED | `make_portfolio_created()` |
| `PORTFOLIO_INITIALIZED` | INITIALIZING | `make_portfolio_initialized()` |
| `PORTFOLIO_LOADED` | LOADING | `make_portfolio_loaded()` |
| `PORTFOLIO_VALIDATED` | VALIDATING | `make_portfolio_validated()` |
| `PORTFOLIO_ACTIVATED` | ACTIVE | `make_portfolio_activated()` |
| `PORTFOLIO_PAUSED` | PAUSED | `make_portfolio_paused()` |
| `PORTFOLIO_RESUMED` | RESUMING | `make_portfolio_resumed()` |
| `PORTFOLIO_REBALANCING` | REBALANCING | `make_portfolio_rebalancing()` |
| `PORTFOLIO_COMPLETED` | COMPLETED | `make_portfolio_completed()` |
| `PORTFOLIO_FAILED` | FAILED | `make_portfolio_failed()` |
| `PORTFOLIO_ARCHIVED` | ARCHIVED | `make_portfolio_archived()` |

### Subscribing to Events

```python
def my_listener(event: PortfolioEvent) -> None:
    print(f"{event.event_type.value}: {event.session_id}")

lc.add_listener(my_listener)
# ... later ...
lc.remove_listener(my_listener)
```

Listener errors are absorbed — they never propagate to the lifecycle engine.

---

## Validation

Run structural integrity validation on any session:

```python
result = lc.validate(session_id)
if not result.is_valid:
    for msg in result.error_messages:
        print(msg)
```

Five checks are performed:

| Check | Code | Description |
|---|---|---|
| Identifier consistency | `IDENTIFIER_CONSISTENCY` | session_id and portfolio_id are non-empty |
| Lifecycle consistency | `LIFECYCLE_CONSISTENCY` | state is a valid PortfolioState |
| Transition validity | `TRANSITION_VALIDITY` | current state was reached via a valid transition |
| Timestamp consistency | `TIMESTAMP_CONSISTENCY` | timestamps are non-negative and logically ordered |
| History integrity | `HISTORY_INTEGRITY` | state_history is non-empty and matches current state |

---

## Statistics

```python
snap = lc.statistics()
# Keys:
# portfolio_sessions_created
# portfolio_sessions_completed
# portfolio_sessions_failed
# portfolio_sessions_archived
# transition_count
# average_session_duration_s
# ema_session_duration_s
# uptime_s
# active_sessions
# archived_sessions
```

---

## Developer Guide

### Configuration

```python
lc = PortfolioLifecycle(
    max_active_sessions   = 5_000,   # default
    max_archived_sessions = 10_000,  # default
    max_history           = 1_000,   # default
    max_transitions       = 50_000,  # default
)
```

### Thread Safety

All public methods are thread-safe. The registry, history, and statistics
all use internal locking.

### Error Handling Pattern

```python
from iios.portfolio.lifecycle import (
    PortfolioLifecycle,
    PortfolioSessionNotFoundError,
    PortfolioInvalidTransitionError,
    PortfolioLifecycleNotRunningError,
)

try:
    lc.activate(session_id)
except PortfolioInvalidTransitionError as e:
    # session cannot transition to ACTIVE from its current state
    print(f"Invalid: {e}")
except PortfolioSessionNotFoundError:
    print("Session does not exist")
except PortfolioLifecycleNotRunningError:
    print("Lifecycle engine not started — call lc.start() first")
```

### Checking Transition Validity Without Raising

```python
from iios.portfolio.lifecycle import can_transition, PortfolioState

if can_transition(PortfolioState.ACTIVE, PortfolioState.REBALANCING):
    lc.rebalance(session_id)
```
