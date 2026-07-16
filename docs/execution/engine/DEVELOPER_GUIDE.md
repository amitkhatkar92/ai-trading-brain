# Execution Engine — Developer Guide

How to work with, extend, and integrate `iios.execution.engine`.

---

## 1. IIOS v1.0 Framework Conventions

### Logging

```python
from iios.common.logging.logging_manager import get_logger
from iios.common.logging.audit_logger import get_audit_logger

SYSTEM_ID = "iios:execution:engine:mycomponent"

_log   = get_logger(__name__, engine_id=SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=SYSTEM_ID, component="MyComponent")

_log.info("Operation completed.", execution_id=eid)
_audit.log_workflow_event(workflow_id=SYSTEM_ID, stage="submit", event="done")
```

**Do not use `import logging` (stdlib).**

Available audit methods:
- `log_lifecycle_event(engine_id, from_state, to_state, version)`
- `log_workflow_event(workflow_id, stage, event, *, actor, **kwargs)`
- `log_failure(...)`, `log_validation_event(...)`, `log_security_event(...)`

### Error Reporting

```python
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.errors.error_context import ErrorContext

ctx = ErrorContext(engine_id=SYSTEM_ID, operation="my_op", stage="preparation")
_get_err_mgr().report_failure(SYSTEM_ID, exc, ctx)
```

### Lifecycle (for service-like classes)

```python
from iios.investment.workflow.engine_lifecycle import LifecycleAwareMixin, EngineState

class MyService(LifecycleAwareMixin):
    SYSTEM_ID = "iios:execution:engine:myservice"
    VERSION   = "1.0.0"

    def _on_start(self) -> None: ...
    def _on_stop(self)  -> None: ...

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING
        # IMPORTANT: lifecycle_state() is a METHOD, not a property
```

---

## 2. Exception Hierarchy

```
IIOSError
└── ExecutionEngineError          EX-000  (base for all engine errors)
    ├── ExecutionRequestError     EX-001
    ├── ExecutionValidationError  EX-002
    ├── ExecutionPreparationError EX-003
    ├── ExecutionRegistryError    EX-004
    ├── ExecutionNotFoundError    EX-005
    ├── DuplicateExecutionError   EX-006
    ├── ExecutionCapacityError    EX-007
    ├── ExecutionEngineNotRunningError EX-008
    ├── ExecutionStateError       EX-009
    └── ExecutionCancelledError   EX-010
```

When adding a new error:
1. Pick the next `EX-NNN` code.
2. Subclass `ExecutionEngineError`.
3. Export from `exceptions.py` and `__init__.py`.

---

## 3. Adding a New Engine State

Editing the state machine is a **protected operation** (see Section 7).

Steps:
1. Add the new `EngineExecutionState` member to `execution_state.py`.
2. Add its outgoing transitions to `VALID_ENGINE_TRANSITIONS`.
3. Add it to the appropriate derived sets (`ACTIVE_ENGINE_STATES`, etc.).
4. Add a mapping entry to `_STATE_EVENT_MAP` in `execution_events.py`.
5. Add a new `ExecutionEventType` if needed.
6. Update all `VALID_ENGINE_TRANSITIONS` entries that can reach the new state.
7. Update tests and documentation.

---

## 4. Extending Validation

Add a new check to `ExecutionValidator`:

```python
class ExecutionValidator:
    def validate_risk_budget(
        self,
        request: ExecutionRequest,
        risk_budget: float,
    ) -> ValidationResult:
        if request.notional_value > risk_budget:
            return ValidationResult.fail(
                f"[RISK_BUDGET_EXCEEDED] "
                f"Notional {request.notional_value} > budget {risk_budget}"
            )
        return ValidationResult.ok()
```

Then call it in `ExecutionEngine.submit()` during the VALIDATING phase.

---

## 5. Adding Intelligence to ExecutionContext

The `ExecutionContext` is frozen; new optional fields require a schema change:

1. Add the field to `ExecutionContext` (with `Optional[T] = None`).
2. Add the corresponding `has_<field>` property.
3. Update `completeness` denominator.
4. Update `ExecutionFactory.create_context()` to accept and pass the new field.
5. Update tests and documentation.

---

## 6. Working with the Preferred Entry Point (ExecutionManager)

```python
manager = ExecutionManager(max_executions=500_000)
manager.start()

# Create request
request = manager.create_request(
    order_id     = "ORD-001",
    decision_id  = "DEC-001",
    portfolio_id = "PORT-001",
    strategy_id  = "STRAT-001",
    execution_mode = ExecutionMode.PAPER,
)

# Listen for events
def on_complete(event: ExecutionEvent) -> None:
    if event.event_type == ExecutionEventType.EXECUTION_COMPLETED:
        print("Done:", event.execution_id)

manager.add_listener(on_complete)

# Submit
result = manager.submit(
    request,
    order_registry     = order_registry,      # M1 OrderRegistry
    portfolio_snapshot = portfolio_snapshot,  # optional
    decision           = decision,            # optional
    strategy_snapshot  = strategy_snapshot,   # optional
)

# Query
record = manager.get_record(result.execution_id)
stats  = manager.statistics()

manager.stop()
```

---

## 7. C6 Lock Manifest

The following elements are **locked** at version 1.0.0.
Changes require explicit architectural review and approval.

| Element | What is locked |
|---|---|
| `EngineExecutionState` enum values | Renaming or removing any existing state |
| `VALID_ENGINE_TRANSITIONS` table | Removing any existing valid edge |
| `TERMINAL_ENGINE_STATES` | `{COMPLETED, FAILED, CANCELLED}` |
| `ExecutionRequest` fields | `order_id`, `decision_id`, `portfolio_id`, `strategy_id`, `execution_mode`, `priority` |
| `ExecutionContext` fields | `request`, `order`, `portfolio_snapshot`, `decision`, `strategy_snapshot` |
| `ExecutionResult` factories | `success()`, `failure()`, `cancelled()` signatures |
| Error codes | EX-000 through EX-010 semantics |
| `ExecutionEngine` public methods | `submit()`, `cancel()`, `start()`, `stop()`, `statistics()` |
| `ExecutionManager` public methods | Same as engine + `create_request()` |
| `ExecutionRegistry` public methods | `register()`, `apply_transition()`, `get()`, `get_active()`, `statistics()` |
| `ExecutionFactory` public methods | `create_request()`, `create_context()`, `gen_execution_id()` |

**Additive changes** (new states, new event types, new query methods, new optional
context fields) are permitted without review, provided no locked element is altered.

---

## 8. Testing Conventions

```
tests/unit/iios/execution/engine/test_execution_engine.py
```

- 15 test classes, 121 test cases.
- `ExecutionEngine` and `ExecutionRegistry` fixtures start/stop the service.
- Use `MagicMock` for `OrderRegistry` when you want to control order resolution.
- Integration tests (Part 14) use the real M1 `OrderRegistry`.
- Thread-safety tests (Part 15) use `threading.Thread` directly.

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/iios/execution/engine/ -v
```

---

## 9. Deployment

```powershell
git add iios/execution/engine/ tests/unit/iios/execution/engine/ docs/execution/engine/
git commit -m "feat(c6): Execution Engine Module 2 — state machine, context, registry, 121 tests"
git push origin main
ssh -i ~/.ssh/trading_vps root@178.18.252.24 `
    "cd /root/ai-trading-brain && git pull origin main && docker compose build --no-cache && docker compose down && docker compose up -d && sleep 8 && docker compose ps"
```

Both containers must show `Up … (healthy)` before the deploy is considered complete.
