# Execution Engine Guide

Full reference for all 9 states, validation rules, context assembly,
order lifecycle coordination, statistics, and event semantics.

---

## 1. The 9 Engine Execution States

| State | Meaning | Active? | Terminal? |
|---|---|---|---|
| `IDLE` | Execution registered; processing not yet started | ✗ | ✗ |
| `VALIDATING` | ExecutionRequest is being validated | ✓ | ✗ |
| `PREPARING` | ExecutionContext is being assembled | ✓ | ✗ |
| `READY` | Context prepared; ready for execution | ✓ | ✗ |
| `EXECUTING` | Execution logic is running | ✓ | ✗ |
| `WAITING` | Awaiting external signal (broker ACK) | ✓ | ✗ |
| `COMPLETED` | Execution finished successfully | ✗ | **✓** |
| `FAILED` | Execution failed | ✗ | **✓** |
| `CANCELLED` | Execution was cancelled | ✗ | **✓** |

All three terminal states (`COMPLETED`, `FAILED`, `CANCELLED`) have no outgoing
transitions. There is no recovery path at the engine level — a new execution
request must be submitted.

---

## 2. Transition Table

```
IDLE        → VALIDATING | CANCELLED
VALIDATING  → PREPARING | FAILED | CANCELLED
PREPARING   → READY | FAILED | CANCELLED
READY       → EXECUTING | CANCELLED
EXECUTING   → WAITING | COMPLETED | FAILED | CANCELLED
WAITING     → EXECUTING | COMPLETED | FAILED | CANCELLED
COMPLETED   → (terminal)
FAILED      → (terminal)
CANCELLED   → (terminal)
```

---

## 3. Validation

### 3.1 Request Validation (IDLE → VALIDATING)

The engine validates these fields before leaving VALIDATING:

| Field | Rule |
|---|---|
| `request_id` | Non-empty |
| `order_id` | Non-empty |
| `decision_id` | Non-empty |
| `portfolio_id` | Non-empty |
| `strategy_id` | Non-empty |
| `expires_at` | Must not be in the past |

Failure → engine transitions to FAILED and returns `ExecutionResult.failure()`.

### 3.2 Context Validation (PREPARING → READY)

After the context is assembled, these checks run:

| Check | Severity | Rule |
|---|---|---|
| `context.request is not None` | Error | Required |
| `context.order is not None` | Error | order_id must resolve |
| `order.state` not terminal | Error | Cannot execute a FILLED order |
| `order.state` is CREATED/VALIDATED/PENDING/RECOVERED | Error | Must be in submittable state |
| `portfolio_snapshot` present | Warning | Without it, portfolio constraints are skipped |
| `decision` present | Warning | Without it, decision constraints are skipped |

Warnings do not block execution.

---

## 4. Context Assembly (PREPARING phase)

`ExecutionFactory.create_context()` resolves:

1. **Order** — looks up `request.order_id` in the provided `OrderRegistry`.
   If the registry is not provided or the order is not found, `context.order` is None
   (context validation will then fail).

2. **PortfolioIntelligenceSnapshot** — passed directly from the caller.
   Optional; absence generates a warning.

3. **Decision** — passed directly from the caller.
   Optional; absence generates a warning.

4. **StrategySnapshot** — passed directly from the caller.
   Optional; absence generates a warning.

The assembled `ExecutionContext` is frozen (`@dataclass(frozen=True)`) — it cannot
be mutated after creation.

---

## 5. Order Lifecycle Coordination (READY phase)

After the context is validated and the engine transitions to READY, the engine
coordinates the M1 Order lifecycle:

```python
# Order must be in VALIDATED state
if order.state == OrderState.VALIDATED:
    order_registry.apply_transition(
        order.order_id,
        OrderState.PENDING_SUBMISSION,
        reason = "execution engine — ready for broker",
        actor  = ACTOR_SYSTEM,
    )
```

This advances the order to `PENDING_SUBMISSION`, making it visible to the
future Broker Adapter layer.

If the advancement fails (e.g., concurrent modification), a warning is logged
and execution continues — the broker adapter will handle order state reconciliation.

---

## 6. ExecutionSnapshot Publishing

Snapshots are published at:

| Moment | Event type | Contents |
|---|---|---|
| READY (after context) | `EXECUTION_PREPARED` | Full context info |
| EXECUTING start | `EXECUTION_READY` | Same snapshot |
| COMPLETED | `EXECUTION_COMPLETED` | Terminal snapshot + result |
| FAILED | `EXECUTION_FAILED` | Terminal snapshot + result |
| CANCELLED | `EXECUTION_CANCELLED` | Terminal snapshot + result |

Snapshots are frozen (`@dataclass(frozen=True)`) and include:
`execution_state`, `has_order`, `has_portfolio`, `has_decision`, `has_strategy`,
`context_completeness`, `is_terminal`, `succeeded`, `duration_ms_so_far`.

---

## 7. ExecutionResult

`ExecutionResult` is returned by `ExecutionEngine.submit()` regardless of outcome:

```python
result = engine.submit(request, ...)

if result.succeeded:
    print("Order at:", order.state.value)   # PENDING_SUBMISSION
else:
    print("Failed:", result.error_message)
    print("Errors:", result.validation_errors)
```

Factory methods:
- `ExecutionResult.success(execution_id, request_id, order_id, started_at, ...)`
- `ExecutionResult.failure(execution_id, ..., error_message, validation_errors, ...)`
- `ExecutionResult.cancelled(execution_id, ..., reason, ...)`

---

## 8. Statistics

### Per-execution (`ExecutionStatistics`)

| Attribute | Description |
|---|---|
| `total_duration` | Wall-clock seconds from VALIDATING to terminal |
| `validation_duration` | Seconds in VALIDATING |
| `preparation_duration` | Seconds in PREPARING |
| `execution_duration` | Seconds in EXECUTING (plus WAITING) |
| `succeeded` | True if terminal state is COMPLETED |
| `final_state` | Terminal EngineExecutionState |
| `state_durations` | Seconds spent in each completed state |

### Engine-wide (`EngineStatistics`)

| Attribute | Description |
|---|---|
| `execution_count` | Total executions completed |
| `success_count` | Count reaching COMPLETED |
| `failure_count` | Count reaching FAILED |
| `cancellation_count` | Count reaching CANCELLED |
| `success_rate` | `success_count / execution_count` |
| `failure_rate` | `failure_count / execution_count` |
| `avg_execution_time_ms` | Mean wall-clock duration |
| `avg_preparation_time_ms` | Mean preparation phase duration |

---

## 9. Cancellation

```python
cancelled = engine.cancel("EXEC-001", reason="risk limit exceeded")
# Returns True if successfully cancelled, False if already terminal
```

Any execution in a non-terminal state can be cancelled. The execution
transitions to CANCELLED and an `ExecutionResult.cancelled()` is set.

---

## 10. Event Listeners

```python
def on_event(event: ExecutionEvent) -> None:
    if event.event_type == ExecutionEventType.EXECUTION_COMPLETED:
        publish_to_monitoring(event.to_dict())

engine.add_listener(on_event)
engine.remove_listener(on_event)
```

Listeners are called **outside** the registry lock.
A faulty listener (raises an exception) is logged as a warning and does not
interrupt other listeners.
