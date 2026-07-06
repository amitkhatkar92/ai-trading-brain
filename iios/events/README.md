# IIOS Event & Messaging Framework

**Package:** `iios/events/`  
**Tests:** `tests/unit/events/test_events_messaging.py`

---

## Overview

The Event & Messaging Framework provides the full event-driven backbone of the IIOS system:

| Component | Location | Purpose |
|---|---|---|
| Event constants | `event_constants.py` | Limits, defaults, header names |
| Event exceptions | `event_exceptions.py` | Full exception hierarchy |
| Event priority | `event_priority.py` | `EventPriority`, `MessagePriority` IntEnums |
| Event metadata | `event_metadata.py` | `EventMetadata`, `Event` dataclasses |
| Event context | `event_context.py` | Thread-local stack, spans, instrumentation |
| Event factory | `event_factory.py` | Fluent event creation |
| Event registry | `event_registry.py` | Type catalogue with validators |
| Event dispatcher | `event_dispatcher.py` | Fan-out with retries, isolation |
| Event router | `event_router.py` | fnmatch-based routing |
| Event bus | `event_bus.py` | Sticky, delayed, scheduled, DLQ |
| Event manager | `event_manager.py` | High-level façade |
| Messaging | `messaging/` | CQRS — Command/Query/Response buses |
| Workflow | `workflow/` | Pipeline + Saga patterns |

---

## Quick Start

```python
from iios.events import get_event_manager, reset_event_manager

mgr = get_event_manager()
mgr.on("order.placed", lambda e: print("Order placed:", e.payload))
mgr.emit("order.placed", {"order_id": "ORD001", "qty": 10})
```

### Command Bus

```python
from iios.events import get_command_bus, reset_command_bus, Response

bus = get_command_bus()
bus.register("order.cancel", lambda cmd: Response.ok(cmd.command_id, {"cancelled": True}))

from iios.events import MessageFactory
factory = MessageFactory("risk_engine")
cmd = factory.command("order.cancel", {"order_id": "ORD001"})
response = bus.dispatch(cmd)
assert response.success
```

### Query Bus

```python
from iios.events import get_query_bus, Response

bus = get_query_bus()
bus.register("portfolio.nav", lambda q: Response.ok(q.query_id, {"nav": 1_000_000}))
```

### Saga Workflow

```python
from iios.events import SagaWorkflow

saga = SagaWorkflow("place_order")
saga.step(
    "reserve_funds",
    handler=lambda ctx: reserve(ctx["order"]),
    compensate=lambda ctx: release(ctx["order"]),
)
saga.step(
    "submit_to_exchange",
    handler=lambda ctx: submit(ctx["order"]),
    compensate=lambda ctx: cancel(ctx["order"]),
)
state = saga.execute({"order": {...}})
# On failure, compensation runs in reverse order
```

---

## Architecture Notes

- **Sync-first** — no asyncio dependency in the core path; async can be layered on top
- **Thread-safe** — all shared state protected by `threading.RLock()`
- **Singletons** — `get_X()` / `reset_X()` pattern; `reset_X()` required in test teardown
- **Isolation** — `EventDispatcher(isolate_failures=True)`: one bad handler never stops others
- **Idempotency** — duplicate `event_id` detection in `EventBus` (deque-bounded)
- **Sticky events** — new subscribers receive the last published value immediately
- **DLQ** — failed events and messages accumulate in Dead Letter Queues for inspection

---

## Layer in IIOS Architecture

```
Layer 17 — ControlTower
    │
    ▼
iios/events/          ← THIS PACKAGE
    │   EventBus, EventManager
    │   CommandBus, QueryBus, ResponseBus
    │   WorkflowEngine (Pipeline + Saga)
    │
    ▼
iios/infrastructure/events/   ← SEPARATE (basic bus, do not modify)
```
