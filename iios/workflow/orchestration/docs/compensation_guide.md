# Compensation Guide

## Overview

Compensation enables _saga_ patterns: when a multi-step workflow
fails, previously-completed steps are undone in reverse (LIFO) order.

---

## How to define compensation

Attach a `compensation_step_id` to any step that needs reversibility:

```python
from iios.workflow.orchestration import WorkflowFactory

# Main step
reserve = WorkflowFactory.create_task_step(
    "reserve_funds", "reserve_handler",
    compensation_step_id="cancel_reservation",
)

# Compensation step (called automatically on failure)
cancel = WorkflowFactory.create_compensation_step(
    "cancel_reservation", "cancel_handler"
)

saga = WorkflowFactory.create_saga_workflow(
    "payment-saga", [reserve, cancel]
)
```

---

## Compensation execution

`WorkflowCompensationEngine.compensate()`:

1. Sets workflow status to `COMPENSATING`
2. Collects all completed steps that have a `compensation_step_id`
3. Reverses the order (LIFO — last completed is compensated first)
4. Executes the compensation step's handler
5. Calls `runtime.increment_compensation()` on success
6. Logs errors but continues compensating remaining steps

Compensation errors do **not** raise — the engine is best-effort.

---

## Compensation handler signature

Same as a regular step handler:

```python
def cancel_handler(
    step:    WorkflowStep,
    inputs:  Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    # undo whatever reserve_handler did
    return {"cancelled": True}
```

---

## Enabling compensation

Compensation is enabled per-definition:

```python
defn = WorkflowFactory.create_sequential_workflow(
    "my-saga", steps,
    enable_compensation=True,  # ← default True for sagas
)
```

When `enable_compensation=False`, the compensation engine is skipped
even on failure.
