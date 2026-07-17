# Execution Risk Integration Guide

## Overview

The Execution Risk Integration layer (C6 Phase 4 M6) is the single coordinated
interface to the Execution Risk subsystem.  All upstream modules (Execution
Gateway, Broker Adapters, Compliance) interact **only** through
`ExecutionRiskIntegrationManager`.

## Lifecycle

The manager must be started before any evaluation.

```python
manager = ExecutionRiskIntegrationManager()
manager.start()    # starts M2, M4, M5 internally
# ... use manager ...
manager.stop()     # stops M5, M4, M2 in reverse order
```

The manager is a `LifecycleAwareMixin`.  Calling `evaluate()` when not started
raises `IntegrationNotRunningError`.

## Registering rules

Rules are M3 `BaseRule` subclasses.  Register them after `start()`:

```python
manager.register_rule(PositionSizeRule())
manager.register_rule(DrawdownRule())
```

Rules with zero registrations result in an `ALLOW` decision (no rules → no
violations).

## Performing an evaluation

```python
ctx = IntegrationRequestFactory.create_equity_context(
    execution_id="EX-001", order_id="ORD-001",
    symbol="INFY", side="BUY", quantity=200, price=1450.0,
    portfolio_id="PORT-A", strategy_id="MOMENTUM-1",
)
request  = IntegrationRequestFactory.create_request(ctx, timeout_ms=2_000)
response = manager.evaluate(request)
```

### Response

| Field | Type | Description |
|---|---|---|
| `approved` | `bool` | True if action is ALLOW or ALLOW_WITH_WARNING |
| `action` | `str` | M4 ControlAction value |
| `risk_state` | `str` | PASSED / WARNING / BLOCKED |
| `snapshot` | `ExecutionRiskSnapshot` | Immutable M5 snapshot |
| `validation_passed` | `bool` | False if request was malformed |
| `error_message` | `str` | Non-empty only on error/validation failure |
| `elapsed_ms` | `float` | Total evaluation latency |

## Observability

```python
manager.health()      # SubsystemHealth — M2/M4/M5 component states
manager.status()      # SubsystemStatus enum
manager.statistics()  # IntegrationStatistics copy
manager.snapshot()    # ExecutionRiskIntegrationSnapshot — full point-in-time view
manager.history(50)   # last N responses
manager.events()      # all emitted IntegrationEvents
```

## Error handling

- Validation failures → `approved=False`, `validation_passed=False`
- M2 evaluation failure → `approved=False`, `error_message` set, fallback snapshot
- Unexpected exceptions → `approved=False`, wrapped in blocked response
- `IntegrationNotRunningError` propagates — callers must `start()` first
