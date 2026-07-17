# Execution Gateway Lifecycle — C6 Phase 5 M1

The **Execution Gateway Lifecycle** package manages the complete lifecycle of
an execution request as it enters and exits the Execution Gateway.

## Purpose

- Defines all valid lifecycle states and transitions
- Enforces a strict state machine (no skipping, no invalid transitions)
- Maintains immutable transition and state history
- Publishes typed domain events on every lifecycle milestone
- Tracks statistics across all gateway requests

## States

```
CREATED → RECEIVED → VALIDATING → READY → QUEUED → ROUTING → DISPATCHED
                                                        ↓            ↓
                                               FAILED ←──────────────┘
                                                  ↓
                                               ARCHIVED (terminal)

Any active state → FAILED | CANCELLED → ARCHIVED
DISPATCHED      → COMPLETED           → ARCHIVED
```

## Quick start

```python
from iios.execution.gateway.lifecycle import (
    GatewayLifecycle,
    make_gateway_context,
)

lc = GatewayLifecycle()
lc.start()

ctx     = make_gateway_context(
              "EX-001", "ORD-001", "PORT-A", "MOMENTUM-1",
              symbol="RELIANCE", side="BUY", quantity=100, price=2500.0)
request = lc.create_from_context(ctx)

lc.receive(request.gateway_id)
lc.start_validation(request.gateway_id)
lc.mark_ready(request.gateway_id)
lc.queue(request.gateway_id)
lc.start_routing(request.gateway_id)
lc.dispatch(request.gateway_id)
lc.complete(request.gateway_id)
lc.archive(request.gateway_id)

print(lc.statistics().to_dict())
lc.stop()
```

## Modules

| Module | Responsibility |
|---|---|
| `gateway_lifecycle.py`   | `GatewayLifecycle` — LifecycleAwareMixin coordinator (primary API) |
| `gateway_request.py`     | `GatewayRequest` — core domain object (state machine) |
| `gateway_registry.py`    | `GatewayRegistry` — LifecycleAwareMixin storage |
| `gateway_factory.py`     | `GatewayFactory` — creates GatewayRequest instances |
| `gateway_context.py`     | `GatewayContext` — immutable execution input data |
| `gateway_metadata.py`    | `GatewayMetadata` — mutable annotation store |
| `gateway_state.py`       | `GatewayStateRecord` — immutable state occupancy record |
| `gateway_transition.py`  | `GatewayTransition` — immutable transition record |
| `gateway_history.py`     | `GatewayHistory` — bounded, thread-safe history |
| `gateway_statistics.py`  | `GatewayStatistics` — mutable counters |
| `gateway_validation.py`  | `GatewayValidator`, `ValidationResult` |
| `gateway_events.py`      | `GatewayEvent` + 9 factory functions |
| `constants.py`           | Enums, sentinel sets, state machine, system IDs |
| `exceptions.py`          | Typed exception hierarchy (EGL-000..007) |

## Testing

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/execution/gateway/test_gateway_lifecycle.py -v
```

## Version

1.0.0 — C6 Execution Intelligence, Phase 5, Module 1
