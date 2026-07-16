# Order Lifecycle — Developer Guide

How to work with, extend, and integrate the `iios.execution.lifecycle` package.

---

## 1. IIOS v1.0 Framework Conventions

Every class in this package that produces logs, audit records, or errors follows
the IIOS v1.0 pattern. **Do not use `import logging` (stdlib).**

### Logging

```python
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

SYSTEM_ID = "iios:execution:lifecycle:mycomponent"

_log   = get_logger(__name__, engine_id=SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=SYSTEM_ID, component="MyComponent")

# Structured log
_log.info("Order processed.", order_id=order_id, state=state.value)

# Audit log — use the method that matches the event category:
# log_lifecycle_event(engine_id, from_state, to_state, version, *, actor, **kwargs)
# log_workflow_event(workflow_id, stage, event, *, actor, **kwargs)
# log_validation_event(...)
# log_failure(...)
```

### Error reporting

```python
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.errors.error_context import ErrorContext

ctx = ErrorContext(engine_id=SYSTEM_ID, operation="my_op", stage="execution")
_get_err_mgr().report_failure(SYSTEM_ID, exc, ctx)
```

### Lifecycle (for service-like classes)

```python
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin, EngineState

class MyService(LifecycleAwareMixin):
    SYSTEM_ID = "iios:execution:lifecycle:myservice"
    VERSION   = "1.0.0"

    def _on_start(self) -> None:
        # Called by self.start()
        ...

    def _on_stop(self) -> None:
        # Called by self.stop()
        ...

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING
```

> **Note:** `lifecycle_state` is a *method*, call it as `self.lifecycle_state()`.

---

## 2. Exception Hierarchy

All exceptions inherit from `IIOSError` (from `iios.common.errors.exceptions`).
Use the package-specific base `OrderLifecycleError` for any new error in this package.

```
IIOSError
└── OrderLifecycleError          EL-000  (base for all lifecycle errors)
    ├── InvalidTransitionError   EL-001
    ├── OrderNotFoundError       EL-002
    ├── OrderValidationError     EL-003
    ├── DuplicateOrderError      EL-004
    ├── RegistryCapacityError    EL-005
    ├── OrderTerminalError       EL-006
    ├── InvalidFillError         EL-007
    └── RegistryNotRunningError  EL-008
```

When adding a new error:
1. Pick the next `EL-NNN` code.
2. Subclass `OrderLifecycleError`.
3. Export from `exceptions.py` and `__init__.py`.

---

## 3. Adding a New State

Editing the state machine is a **protected operation** (see C6 Lock Manifest
in Section 7). Only do this with explicit approval.

Steps:
1. Add the new `OrderState` member to `order_state.py`.
2. Add its outgoing transitions to `VALID_TRANSITIONS`.
3. Add it to the appropriate derived set (`ACTIVE_STATES`, `TERMINAL_STATES`, etc.)
4. Add a mapping entry to `_STATE_EVENT_MAP` in `order_event.py`.
5. Add a new `OrderEventType` if needed.
6. Update `VALID_TRANSITIONS` for every state that can transition *to* the new state.
7. Update tests and docs.

---

## 4. Adding a New Order Type

1. Add the new `OrderType` member to the `OrderType` enum in `constants.py`.
2. Add a `create_<type>_order(...)` method to `OrderFactory`.
3. Add price-validation logic to `OrderValidator._validate_prices`.
4. Add a corresponding test in `TestOrderFactory`.

---

## 5. Working with the OrderRegistry

### Startup and shutdown

```python
registry = OrderRegistry(max_orders=500_000)
registry.start()   # REQUIRED before any operation
# ... use registry ...
registry.stop()    # clean shutdown; logs active order count
```

### Apply a transition

```python
order, transition, event = registry.apply_transition(
    order.order_id,
    OrderState.VALIDATED,
    reason = "validation passed",
    actor  = ACTOR_VALIDATOR,
)
```

Returns `(Order, OrderTransition, OrderEvent)`.

### Apply a fill

```python
order, transition, event = registry.apply_fill(
    order.order_id,
    fill_qty   = Decimal("50"),
    fill_price = Decimal("2800.00"),
    actor      = ACTOR_EXCHANGE,
)
# order.state is now PARTIALLY_FILLED or FILLED
```

Returns `(Order, OrderTransition, OrderEvent)`.

### Querying

```python
order  = registry.get(order_id)                         # raises OrderNotFoundError
orders = registry.get_by_portfolio("PORT-001")          # list[Order]
orders = registry.get_by_strategy("STRAT-001")          # list[Order]
orders = registry.get_by_state(OrderState.ACKNOWLEDGED) # list[Order]
active = registry.get_active()                          # all ACTIVE_STATES
stats  = registry.statistics()                          # RegistryStatistics
```

### Event listeners

```python
def my_listener(event: OrderEvent) -> None:
    # called outside the registry lock
    publish_to_kafka(event.to_dict())

registry.add_listener(my_listener)
registry.remove_listener(my_listener)
```

> Listeners that raise exceptions are swallowed and logged as warnings.

---

## 6. Thread Safety Notes

- `OrderRegistry._lock` is a `threading.RLock` — reentrant within the same thread.
- Listeners are dispatched **after** the lock is released, so they may safely call
  registry read methods (`get`, `count`, `statistics`).
- Do **not** call `apply_transition` or `apply_fill` from inside a listener — this
  would cause a deadlock on a non-reentrant path.
- `OrderHistory` and `OrderStatistics` each manage their own `threading.Lock`.

---

## 7. C6 Lock Manifest

The following elements of this package are **locked** at version 1.0.0.
Changes require an explicit architectural review and approval.

| Element | What is locked |
|---|---|
| `OrderState` enum values | Renaming or removing any existing state |
| `VALID_TRANSITIONS` table | Removing any existing valid edge |
| `TERMINAL_STATES` | Only `FILLED` must remain terminal |
| `OrderTransition` fields | `transition_id`, `order_id`, `from_state`, `to_state`, `reason`, `actor`, `occurred_at` |
| `OrderEvent` fields | `event_id`, `order_id`, `event_type`, `occurred_at` |
| `OrderContext` fields | `strategy_id`, `portfolio_id`, `decision_id`, `workflow_id` |
| Error codes | EL-000 through EL-008 semantics |
| `OrderRegistry` public methods | `register`, `apply_transition`, `apply_fill`, `get`, `get_active`, `statistics`, `add_listener`, `remove_listener`, `start`, `stop` |
| `OrderFactory` public methods | `create_market_order`, `create_limit_order`, `create_stop_order`, `create_stop_limit_order`, `clone` |

**Additive changes** (new states, new event types, new query methods) are permitted
without review, provided they do not alter any locked element above.

---

## 8. Testing Conventions

```
tests/unit/iios/execution/lifecycle/test_order_lifecycle.py
```

- Uses `pytest` with `pytest-asyncio` in `STRICT` mode.
- Class names prefixed with `Test` (e.g., `TestOrderRegistry`).
- `OrderRegistry` fixture starts and stops the registry around each test.
- Use `factory.create_*` methods to build test orders — do not call `Order()` directly
  unless testing constructor edge cases.
- Thread-safety tests use `threading.Thread` directly (no `asyncio`).

Run the full suite:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/iios/execution/lifecycle/ -v
```

Run with coverage:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/iios/execution/lifecycle/ `
    --cov=iios/execution/lifecycle --cov-report=term-missing
```

---

## 9. Deployment

Follow the mandatory deployment rule from `copilot-instructions.md`:

```powershell
git add iios/execution/lifecycle/ tests/unit/iios/execution/lifecycle/ docs/execution/lifecycle/
git commit -m "feat(c6): Order Lifecycle Module 1 — state machine, factory, registry"
git push origin main
ssh -i ~/.ssh/trading_vps root@178.18.252.24 `
    "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

Both containers must show `Up … (healthy)` before the deploy is considered complete.
