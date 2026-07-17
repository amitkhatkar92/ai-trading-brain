# Execution Risk Lifecycle — Developer Guide

**IIOS C6 Execution Intelligence — Phase 4, Module 1**

---

## Architecture Principles

This module follows the IIOS Lifecycle Pattern established in Phase 3
(Position Lifecycle). All conventions are identical:

1. **Pure domain object** — `ExecutionRisk` is NOT a `LifecycleAwareMixin`.
   It is a thread-safe domain object with an internal `RLock`.
2. **LifecycleAwareMixin registry** — `RiskRegistry` uses `_on_start` /
   `_on_stop` and guards all writes with `_assert_running()`.
3. **Immutable records** — `RiskStateRecord`, `RiskTransition`, `RiskEvent`
   are all `frozen=True` dataclasses.
4. **Stateless services** — `RiskFactory` and `RiskValidator` hold no state.
5. **No calculations** — the lifecycle tracks state only; no risk scores,
   no broker calls, no order routing.

---

## Adding a New Transition

To add a new allowed transition (e.g. PASSED → REVIEWING):

1. Add `REVIEWING` to `RiskState` in `constants.py`
2. Add the transition to `VALID_TRANSITIONS` in `constants.py`
3. Add a `make_risk_reviewing()` factory in `execution_risk_event.py`
4. Add `RiskEventType.RISK_REVIEWING` in `constants.py`
5. Register the factory in `_STATE_EVENT_FACTORY` in `execution_risk.py`
6. Add `record_reviewing()` to `RiskStatistics`
7. Update `__init__.py` exports
8. Add tests

---

## Thread Safety Contract

| Operation            | Lock held                       |
|----------------------|---------------------------------|
| `transition_to()`    | `ExecutionRisk._lock` (RLock)   |
| `register()`         | `RiskRegistry._lock` (Lock)     |
| `notify_transition()`| `RiskRegistry._lock` (Lock)     |
| `get()`              | `RiskRegistry._lock` (Lock)     |
| `statistics()`       | `RiskRegistry._lock` (Lock)     |

Event emission in `transition_to()` happens **outside** the lock to avoid
deadlocks when listener callbacks call back into the risk object.

---

## Lifecycle Guard Pattern

Every `RiskRegistry` write method must call `_assert_running()` first:

```python
def register(self, risk: ExecutionRisk) -> None:
    self._assert_running()   # raises RiskRegistryNotRunningError if stopped
    with self._lock:
        ...
```

Read operations (`get`, `all`, `by_*`) are permitted after `stop()` to allow
post-shutdown inspection.

---

## Statistics Update Flow

The registry does **not** automatically listen to `ExecutionRisk` events.
The caller must explicitly call `registry.notify_transition()` after a
successful `risk.transition_to()`:

```python
transition = risk.transition_to(RiskState.PASSED, evaluation_time_ms=5.2)
registry.notify_transition(risk, RiskState.PASSED, evaluation_time_ms=5.2)
```

Future modules (Risk Engine) will encapsulate this in a single call.

---

## Validation Usage

```python
validator = RiskValidator()

# Check a single invariant
result = validator.validate_transition(risk, RiskState.PASSED)
if not result.is_valid:
    print(result.errors)

# Full validation
result = validator.validate_full(risk)
validator.raise_if_invalid(result)   # raises RiskValidationError on failure
```

---

## History Eviction Policy

`RiskHistory` uses a bounded list.  When `max_size` is reached, the oldest
entry is evicted (FIFO).  Eviction counts are tracked via:

- `history.evicted_transitions`
- `history.evicted_states`
- `history.total_transitions` — includes evicted entries

The default `max_size` is `DEFAULT_MAX_HISTORY = 500`.

---

## Context Usage

`RiskContext` is an optional immutable context object for tracing operations:

```python
from iios.execution.risk.lifecycle import make_risk_context

ctx = make_risk_context(
    risk_id="rid-001",
    execution_id="exec-001",
    requester="risk-engine",
    metadata={"session": "session-42"},
)
```

Context objects are never modified; create a new one per operation.

---

## Import Path

```python
# Recommended — always import from the package root
from iios.execution.risk.lifecycle import (
    ExecutionRisk,
    RiskFactory,
    RiskRegistry,
    RiskState,
    RiskCategory,
    InvalidRiskTransitionError,
)
```

---

## Prohibited Patterns

```python
# Never import from sub-modules directly
from iios.execution.risk.lifecycle.execution_risk import ExecutionRisk  # ❌

# Never access _state directly
risk._state = RiskState.PASSED  # ❌  — use transition_to()

# Never share a RiskHistory across multiple ExecutionRisk objects
shared_history = RiskHistory()
r1 = ExecutionRisk(..., history=shared_history)  # ❌ — not supported
```
