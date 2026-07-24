# Developer Guide — C16 M1 Workflow Lifecycle

## Module Boundaries

This module manages **lifecycle states only**.

| Responsibility              | This module | Later C16 modules |
|-----------------------------|-------------|-------------------|
| State transitions           | ✅           |                   |
| Audit history               | ✅           |                   |
| Lifecycle events            | ✅           |                   |
| Statistics                  | ✅           |                   |
| Workflow execution          |             | ✅                 |
| Business logic              |             | ✅                 |
| Orchestration               |             | ✅                 |
| Governance evaluation       |             | ✅                 |
| AI reasoning                |             | ✅                 |

## Key Design Rules

1. **Session immutability of identity** — `session_id` and `workflow_id` never change.
2. **Transition immutability** — `WorkflowTransition` and `WorkflowStateRecord` are frozen dataclasses.
3. **Session mutability** — `WorkflowSession._state` changes on each transition. All mutations are lock-protected.
4. **No business logic** — `WorkflowLifecycle` methods only update state, record history, update stats, and emit events.
5. **Lock discipline** — Always acquire `self._lock` before reading or writing mutable state. Never hold two locks simultaneously.

## Adding a New Transition

1. Add target state to `WorkflowLifecycleState` if needed.
2. Update `VALID_TRANSITIONS` in `constants.py`.
3. Add the event type to `WorkflowEventType` if needed.
4. Add the method to `WorkflowLifecycle` calling `self._apply(...)`.
5. Update `__init__.py` exports if new symbols were added.
6. Add tests for the new transition path.

## Error Handling

All exceptions derive from `WorkflowLifecycleError` (WLC-000).

```python
from iios.workflow.lifecycle import (
    WorkflowLifecycle,
    WorkflowInvalidTransitionError,
    WorkflowSessionNotFoundError,
)

lc = WorkflowLifecycle()
session = lc.create_session("wf-123")

try:
    lc.complete(session.session_id)   # invalid: CREATED → COMPLETED
except WorkflowInvalidTransitionError as e:
    print(e.from_state, "→", e.to_state)
```

## Event Subscription

```python
from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowEventType

lc = WorkflowLifecycle()

def on_event(event):
    print(f"[{event.event_type.value}] session={event.session_id}")

lc.event_bus().add_listener(on_event)

session = lc.create_session("wf-456")
lc.initialize(session.session_id)
# prints: [workflow_created] session=ws-...
# prints: [workflow_initialized] session=ws-...
```

## Validation

```python
from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowValidator

lc = WorkflowLifecycle()
session = lc.create_session("wf-789")

validator = WorkflowValidator()
report = validator.validate(session)
print(report.passed)          # True
print(report.failed_checks)   # []
```
