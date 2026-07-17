# Transition Guide

## Overview

The Gateway Lifecycle enforces a strict state machine.  Every transition
is validated against `VALID_TRANSITIONS` before being applied.  Invalid
transitions raise `InvalidGatewayTransitionError` (EGL-001).

## GatewayLifecycle methods

Each method corresponds to exactly one state transition:

| Method                          | Transition                    |
|---------------------------------|-------------------------------|
| `receive(gateway_id)`           | CREATED → RECEIVED            |
| `start_validation(gateway_id)`  | RECEIVED → VALIDATING         |
| `mark_ready(gateway_id)`        | VALIDATING → READY            |
| `queue(gateway_id)`             | READY → QUEUED                |
| `start_routing(gateway_id)`     | QUEUED → ROUTING              |
| `dispatch(gateway_id)`          | ROUTING → DISPATCHED          |
| `complete(gateway_id)`          | DISPATCHED → COMPLETED        |
| `fail(gateway_id, reason=...)`  | any active → FAILED           |
| `cancel(gateway_id, reason=...)` | any active → CANCELLED       |
| `archive(gateway_id)`           | COMPLETED/FAILED/CANCELLED → ARCHIVED |

All methods accept optional `actor` and `reason` keyword arguments.

## Direct transition on GatewayRequest

Low-level consumers may call `transition_to()` directly:

```python
request.transition_to(
    GatewayState.RECEIVED,
    actor="iios:gateway:engine",
    reason="Accepted by gateway",
    metadata={"queue_depth": 42},
)
```

This bypasses the lifecycle's statistics tracking.  Prefer lifecycle
methods in production code.

## Transition record

Every `transition_to()` call returns a `GatewayTransition`:

```python
transition = request.transition_to(GatewayState.RECEIVED)

transition.transition_id  # UUID
transition.gateway_id
transition.from_state     # GatewayState.CREATED
transition.to_state       # GatewayState.RECEIVED
transition.triggered_at   # Unix timestamp
transition.actor
transition.reason
transition.is_valid        # True for valid transitions
transition.is_terminal     # True if to_state == ARCHIVED
transition.to_dict()
```

## History chain

After N transitions, `request.history.transitions()` returns a list
where each `to_state[i] == from_state[i+1]`.  The validator checks this
with `validate_history()`.

## Pre-validation

Check whether a transition is possible without applying it:

```python
result = lc.validate_transition(gateway_id, GatewayState.DISPATCHED)
if result.is_valid:
    lc.dispatch(gateway_id)
else:
    print(result.errors)
```
