# Gateway Lifecycle Guide

## Overview

The Gateway Lifecycle (C6 Phase 5 M1) manages the complete lifecycle of an
execution request through the Execution Gateway.  It defines states,
transitions, history, events, and statistics.

It does NOT route orders, communicate with brokers, execute trades, or
perform risk calculations.

## Creating a request

```python
lc = GatewayLifecycle()
lc.start()

# Option 1 — from individual fields
request = lc.create(
    execution_id="EX-001",
    order_id="ORD-001",
    portfolio_id="PORT-A",
    strategy_id="STRAT-1",
    workflow_id="WF-001",
    correlation_id="COR-001",
)

# Option 2 — from a GatewayContext
ctx     = make_gateway_context("EX-001", "ORD-001", "PORT-A", "STRAT-1",
              symbol="NIFTY25JAN25CE", side="BUY", quantity=50, price=200.0)
request = lc.create_from_context(ctx)
```

## Driving the lifecycle

```python
gid = request.gateway_id

lc.receive(gid)            # CREATED → RECEIVED
lc.start_validation(gid)  # RECEIVED → VALIDATING
lc.mark_ready(gid)         # VALIDATING → READY
lc.queue(gid)              # READY → QUEUED
lc.start_routing(gid)     # QUEUED → ROUTING
lc.dispatch(gid)           # ROUTING → DISPATCHED
lc.complete(gid)           # DISPATCHED → COMPLETED
lc.archive(gid)            # COMPLETED → ARCHIVED
```

## Handling failures and cancellations

```python
# Fail from any active state
lc.fail(gid, reason="Broker connectivity lost")

# Cancel from any active state
lc.cancel(gid, reason="User cancelled the order")

# Archive after outcome
lc.archive(gid)
```

## State machine rules

- Only transitions listed in `VALID_TRANSITIONS` are permitted.
- `InvalidGatewayTransitionError` (EGL-001) is raised on any invalid attempt.
- `ARCHIVED` is the only true terminal state — no transitions out.

## Validation

```python
# Check lifecycle consistency
result = lc.validate_request(gid)
if not result.is_valid:
    print(result.errors)

# Check whether a transition is possible
result = lc.validate_transition(gid, GatewayState.DISPATCHED)

# Validate history chain integrity
result = lc.validate_history(gid)
```

## Querying

```python
lc.all()                               # all registered requests
lc.active()                            # requests in active states
lc.completed()                         # COMPLETED only
lc.failed()                            # FAILED only
lc.cancelled()                         # CANCELLED only
lc.archived()                          # ARCHIVED only
lc.by_execution_id("EX-001")          # filter by execution ID
lc.by_portfolio_id("PORT-A")          # filter by portfolio
lc.by_strategy_id("STRAT-1")         # filter by strategy
lc.by_state(GatewayState.ROUTING)     # filter by exact state
```

## Statistics

```python
stats = lc.statistics()
stats.requests_received
stats.requests_completed
stats.requests_failed
stats.requests_cancelled
stats.average_lifecycle_time_ms
stats.completion_rate
stats.failure_rate
stats.to_dict()
```

## Events

Global listeners receive all events from all requests:

```python
def on_event(event: GatewayEvent):
    print(f"{event.event_type.value} — {event.gateway_id}")

lc.add_event_listener(on_event)
```

Per-request listeners receive events from a single request:

```python
request.add_event_listener(on_event)
```

Events are fired for: RECEIVED, READY, QUEUED, DISPATCHED, COMPLETED,
FAILED, CANCELLED, ARCHIVED.  CREATED is emitted globally by the factory.
