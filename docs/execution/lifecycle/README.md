# Order Lifecycle — Package README

**Package path:** `iios/execution/lifecycle/`
**Version:** 1.0.0
**IIOS Component:** C6 Execution Intelligence — Phase 1, Module 1

---

## Purpose

The Order Lifecycle package provides a **pure, broker-agnostic order state machine**
for the IIOS trading framework. It handles every stage of an order's life — from
creation through validation, submission, acknowledgement, fills, and terminal states —
without any dependency on a specific broker, network protocol, or message format.

The package is the foundation on which higher-level execution components
(broker adapters, OMS, risk-overlay) are built.

---

## Package Structure

```
iios/execution/lifecycle/
├── __init__.py           # Public API — all exports
├── constants.py          # System IDs, enums, bounds
├── exceptions.py         # Exception hierarchy (EL-000 … EL-008)
├── order_state.py        # OrderState enum + VALID_TRANSITIONS table
├── order_transition.py   # Immutable OrderTransition record
├── order_event.py        # Immutable OrderEvent record + OrderEventType
├── order_context.py      # Immutable routing context (frozen dataclass)
├── order_metadata.py     # Mutable tags / notes / version
├── order_history.py      # Append-only, thread-safe transition log
├── order_statistics.py   # Fill, timing, and counter statistics
├── order.py              # Order — the central domain object
├── order_validation.py   # Stateless validator (new / transition / fill)
├── order_factory.py      # Factory — creates validated Order instances
└── order_registry.py     # Thread-safe registry (LifecycleAwareMixin)
```

---

## Quick Start

```python
from decimal import Decimal
from iios.execution.lifecycle import (
    OrderFactory, OrderRegistry, OrderContext,
    OrderSide, OrderState,
    ACTOR_VALIDATOR, ACTOR_BROKER, ACTOR_EXCHANGE,
)

# 1 ── Build the context that routes the order to the right portfolio/strategy
ctx = OrderContext(
    strategy_id  = "MEAN_REVERSION_V3",
    portfolio_id = "EQUITY_INDIA_01",
    decision_id  = "DEC-20260521-001",
    workflow_id  = "WF-CYCLE-042",
)

# 2 ── Create a factory and produce an order
factory = OrderFactory()
order   = factory.create_limit_order(
    context     = ctx,
    instrument  = "RELIANCE",
    exchange    = "NSE",
    side        = OrderSide.BUY,
    quantity    = Decimal("100"),
    limit_price = Decimal("2800.00"),
)

# 3 ── Start the registry and register the order
registry = OrderRegistry()
registry.start()
registry.register(order)

# 4 ── Subscribe to lifecycle events
def on_event(event):
    print(f"[{event.event_type.value}] {event.order_id}")

registry.add_listener(on_event)

# 5 ── Drive the state machine
registry.apply_transition(order.order_id, OrderState.VALIDATED,
                          reason="validation passed", actor=ACTOR_VALIDATOR)
registry.apply_transition(order.order_id, OrderState.PENDING_SUBMISSION,
                          reason="queued for submission", actor="scheduler")
registry.apply_transition(order.order_id, OrderState.SUBMITTED,
                          reason="sent to broker", actor=ACTOR_BROKER)
registry.apply_transition(order.order_id, OrderState.ACKNOWLEDGED,
                          reason="broker ack received", actor=ACTOR_EXCHANGE)

# 6 ── Record fills (partial then complete)
registry.apply_fill(order.order_id, Decimal("60"), Decimal("2798.50"))
registry.apply_fill(order.order_id, Decimal("40"), Decimal("2800.00"))

print(f"Final state : {order.state}")         # FILLED
print(f"Fill %      : {order.fill_pct:.1f}")  # 100.0
print(f"Avg price   : {order.average_price}") # ~2799.10

registry.stop()
```

---

## Key Concepts

| Concept | Class | Notes |
|---|---|---|
| State machine | `OrderState`, `VALID_TRANSITIONS` | 14 states, only FILLED is terminal |
| Immutable context | `OrderContext` | Strategy / portfolio / decision routing |
| Mutable metadata | `OrderMetadata` | Tags, notes, version counter |
| Transition record | `OrderTransition` | Frozen dataclass; carries actor + reason |
| Event | `OrderEvent` | Emitted after every successful mutation |
| History | `OrderHistory` | Append-only deque; thread-safe |
| Statistics | `OrderStatistics` | Fill%, timing, retry/cancel/fail counts |
| Central object | `Order` | Owns history, metadata, statistics |
| Validation | `OrderValidator` | Stateless; called by factory and registry |
| Factory | `OrderFactory` | Validates + logs on creation |
| Registry | `OrderRegistry` | Thread-safe; owns all state mutations |

---

## Error Codes

| Code | Exception | When raised |
|---|---|---|
| EL-000 | `OrderLifecycleError` | Generic lifecycle error |
| EL-001 | `InvalidTransitionError` | Requested transition not in VALID_TRANSITIONS |
| EL-002 | `OrderNotFoundError` | `get()` with unknown order_id |
| EL-003 | `OrderValidationError` | New-order validation failure |
| EL-004 | `DuplicateOrderError` | `register()` with already-known order_id |
| EL-005 | `RegistryCapacityError` | max_orders limit reached |
| EL-006 | `OrderTerminalError` | Transition attempted on FILLED order |
| EL-007 | `InvalidFillError` | Fill on non-fill-eligible state or overfill |
| EL-008 | `RegistryNotRunningError` | Operation before `registry.start()` |

---

## Thread Safety

`OrderRegistry` is fully thread-safe:

- All mutations (`register`, `apply_transition`, `apply_fill`) hold `threading.RLock`.
- Event listeners are dispatched **outside** the lock to prevent deadlocks.
- `OrderHistory` and `OrderStatistics` each carry their own `threading.Lock`.
- `Order` carries a `threading.RLock` for internal consistency.

---

## Related Documentation

- [LIFECYCLE_GUIDE.md](LIFECYCLE_GUIDE.md) — All 14 states explained, transition rules, fill semantics, recovery
- [STATE_DIAGRAM.md](STATE_DIAGRAM.md) — Mermaid state diagram
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — IIOS framework conventions, how to extend, C6 lock manifest

---

## Tests

```
tests/unit/iios/execution/lifecycle/test_order_lifecycle.py
```

13 test classes, 123 test cases.  Target coverage ≥ 95 %.

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/iios/execution/lifecycle/ -v --tb=short
```
