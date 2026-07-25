# Developer Guide

## Adding a new step type

1. Add the value to `StepType` in `constants.py`
2. Handle it in `WorkflowStepExecutor._execute_core()` if needed
3. Document it in `workflow_definition_guide.md`

---

## Adding a new engine

All sub-engines follow the same pattern:

```python
class WorkflowMyEngine:
    """Stateless engine — hold no mutable state."""

    def __init__(self, dependency: SomeDep) -> None:
        self._dep = dependency

    def do_thing(self, ...) -> ...:
        ...
```

Wire the new engine into `WorkflowExecutor` and expose it via
`WorkflowOrchestrationEngine` if external access is needed.

---

## Custom handler example

```python
import time
from iios.workflow.orchestration import WorkflowOrchestrationEngine, WorkflowStep

def slow_io_handler(
    step:    WorkflowStep,
    inputs:  dict,
    context: dict,
) -> dict:
    time.sleep(0.1)          # simulate I/O
    return {"result": "ok"}

engine = WorkflowOrchestrationEngine()
engine.initialize()
engine.register_handler("slow_io", slow_io_handler)
```

---

## Subscribing to orchestration events

```python
from iios.workflow.orchestration import OrchestrationEventType

def on_step_done(event):
    print(f"Step completed: {event.payload}")

engine.event_bus().add_listener(
    OrchestrationEventType.WORKFLOW_STEP_COMPLETED,
    on_step_done,
)
```

---

## Thread safety contract

| Component | Lock type |
|---|---|
| WorkflowRuntime | `threading.RLock` |
| WorkflowRegistry | `threading.Lock` |
| WorkflowStateStore | `threading.Lock` |
| WorkflowCheckpointManager | `threading.Lock` |
| WorkflowHistory | `threading.Lock` |
| WorkflowStatistics | `threading.Lock` |
| WorkflowEventEngine | `threading.Lock` |
| WorkflowQueueManager | `threading.Lock` |
| WorkflowResourceManager | `threading.Semaphore` |
| WorkflowScheduler | `threading.Lock` |

All public methods are safe to call from multiple threads concurrently.

---

## Testing conventions

```python
def make_handler(outputs=None):
    def h(step, inputs, ctx):
        return outputs or {}
    return h

def make_step(name="s1", handler="h", deps=None):
    return WorkflowFactory.create_task_step(name, handler, dependencies=deps or [])
```

Keep tests stateless — create fresh engine / registry instances per test.
